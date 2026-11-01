"""실제 설치 로컬 모델만 사용. 고정 합성30의 원문/후보검사/원본불변을 기록한다."""
import argparse
import asyncio
import json
import math
from pathlib import Path
import statistics
import sys
import time
from urllib.request import build_opener, ProxyHandler

from backend.explanation.catalog_provider import OllamaCatalogProvider
from backend.explanation import service
from backend.explanation.contracts import ExplanationDocument
from backend.explanation.facts import build_facts, deterministic_document
from backend.explanation.narrative_catalog import prepare_catalog, parse_catalog, assemble_catalog
from backend.explanation.narrative_contract import NarrativeContractError, parse_narrative
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

MODEL='qwen3:4b-instruct-2507-q4_K_M'
DIGEST='0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0'
def metadata(route):
    with build_opener(ProxyHandler({})).open('http://127.0.0.1:11434'+route,timeout=3) as response:return json.loads(response.read())


class RecordingProvider(OllamaCatalogProvider):
    """평가 전용 합성 기록. 제품 Provider에는 요청/응답 저장 기능이 없다."""
    def __init__(self):
        super().__init__(MODEL);self.posts=0;self.body=None;self.envelope=None;self.post_error=None;self.transport_ms=None;self.post_started=None
    def _post(self,body):
        self.posts+=1;self.body=body;self.post_started=time.perf_counter();start=self.post_started
        try:
            raw=super()._post(body);self.envelope=raw.decode('utf-8');return raw
        except Exception as exc:self.post_error=type(exc).__name__;raise
        finally:self.transport_ms=round((time.perf_counter()-start)*1000,2)


async def evaluate_case(case,phase):
    request=ComparisonInput(before=case['before'],after=case['after']);comparison=compare_scenarios(request)
    facts=build_facts(comparison);expected=deterministic_document(comparison,facts);prepared=prepare_catalog(facts,expected)
    provider=RecordingProvider();started=time.perf_counter();result=await service.explain(request,provider=provider)
    elapsed=round((time.perf_counter()-started)*1000,2)
    outer=None;content=None;decoded=None;structure=None;slots=None;candidate=None;legacy=None;diagnostic=None;stage=None
    if provider.envelope is not None:
        try:
            outer=json.loads(provider.envelope);content=outer.get('message',{}).get('content')
            decoded=json.loads(content) if type(content) is str else None
        except (ValueError,TypeError):pass
        if content is not None:
            try:parse_narrative(content,prepared._narrative);structure=True;slots=True
            except NarrativeContractError as exc:
                diagnostic=exc.code;stage=exc.stage
                if exc.stage=='text':structure=True;slots=True
                elif exc.code=='SLOT_SET_MISMATCH':structure=True;slots=False
                else:structure=False
            try:
                checked=parse_catalog(content,prepared);candidate=True
                assembled=assemble_catalog(prepared,checked)
                service.validate_output(assembled.model_dump_json(),expected);legacy=True
            except NarrativeContractError as exc:
                candidate=False;diagnostic=exc.code;stage=exc.stage
            except service.OutputRejected as exc:legacy=False;diagnostic=exc.code;stage='output_validator'
    assert result.facts==facts
    assert result.document.changed_facts==expected.changed_facts and result.document.unknown_information==expected.unknown_information
    assert result.document.next_actions==expected.next_actions
    assert [p.model_dump(exclude={'text'}) for p in result.document.policy_explanations]==[p.model_dump(exclude={'text'}) for p in expected.policy_explanations]
    if result.fallback:assert result.document==expected
    choices=None
    if candidate:
        choices=dict(summary=prepared.summary_options.index(decoded['summary'])+1,
          policy_texts={p.slot:p.texts.index(decoded['policy_texts'][p.slot])+1 for p in prepared.policy_options})
    request_wire=json.loads(provider.body) if provider.body is not None else None
    return dict(case_id=case['case_id'],name=case['name'],phase=phase,synthetic=True,original_fault_label_not_injected=case.get('fault'),
      model=MODEL,model_digest=DIGEST,provider_post_attempts=provider.posts,request_bytes=len(provider.body) if provider.body else None,
      context_bytes=len(prepared.model_input_json.encode()),candidate_context=prepared.model_input(),
      candidate_count=dict(summary=len(prepared.summary_options),policies={p.slot:len(p.texts) for p in prepared.policy_options}),
      summary_family=prepared.summary_family,policy_families=[dict(slot=p.slot,family=p.family,pending_after=p.pending_after) for p in prepared.policy_options],
      raw_envelope=provider.envelope,envelope_bytes=len(provider.envelope.encode()) if provider.envelope else None,
      actual_model_output=content,decoded_output=decoded,selected_option_numbers_evaluation_only=choices,
      completion_reason=outer.get('done_reason') if type(outer) is dict else None,
      model_metrics={k:v for k,v in (outer or {}).items() if k.endswith('_count') or k.endswith('_duration')},
      structure_valid=structure,slot_match=slots,exact_candidate_match=candidate,existing_validator_passed=legacy,
      diagnostic_code=diagnostic,failure_stage=stage,post_error_type=provider.post_error,
      client_latency_ms=elapsed,transport_latency_ms=provider.transport_ms,
      transport_timeout_observed=provider.post_error=='TimeoutError',
      service_deadline_observed=result.fallback_reason=='TIMEOUT' and provider.post_error is None and elapsed>=7900,
      candidate_extra_information=False if candidate else None,
      python_confirmed_result=comparison.model_dump(),deterministic_document=expected.model_dump(),api_result=result.model_dump(),
      rendered_core_preserved=True,model_novel_reasoning=False,
      human_review='NOT_PERFORMED',human_usefulness=None,codex_semantic_review='PENDING' if content is not None else 'NO_COMPLETE_OUTPUT')


def summary(rows):
    times=[r['client_latency_ms'] for r in rows];accepted=[r for r in rows if r['api_result']['ai_success']]
    reasons={r['api_result']['fallback_reason'] for r in rows}
    return dict(scenarios=len(rows),provider_post_attempts=sum(r['provider_post_attempts'] for r in rows),
      completed_model_contents=sum(r['actual_model_output'] is not None for r in rows),accepted=len(accepted),fallback=len(rows)-len(accepted),
      adoption_rate=len(accepted)/len(rows),fallback_rate=1-len(accepted)/len(rows),
      fallback_reasons={str(reason):sum(r['api_result']['fallback_reason']==reason for r in rows) for reason in reasons},
      request_mean_ms=statistics.mean(times),request_p50_ms=statistics.median(times),request_p95_nearest_rank_ms=sorted(times)[math.ceil(.95*len(times))-1],
      accepted_mean_ms=statistics.mean(r['client_latency_ms'] for r in accepted) if accepted else None,
      transport_timeouts=sum(r['transport_timeout_observed'] for r in rows),service_deadlines=sum(r['service_deadline_observed'] for r in rows),
      rendered_core_mismatches=0,human_reviews=0,human_useful_ratio=None,
      note='채택률과 사람의 유용성 비율을 분리한다. 반복입력/cache가 있는 고정합성평가이며 정상/거부/timeout을 구분한다.')


async def run(args):
    version=metadata('/api/version');tag=next(t for t in metadata('/api/tags')['models'] if t['name']==MODEL)
    assert version['version']=='0.40.11' and tag['digest']==DIGEST
    before_ps=metadata('/api/ps');args.output.parent.mkdir(parents=True,exist_ok=True)
    out=dict(milestone='M3.8E',evaluation='real-local-catalog-fixed30-v1',synthetic=True,actual_local_model=True,phase=args.phase,
      version=version,model=tag,model_ps_before=before_ps,
      limits=dict(transport_seconds=6,service_seconds=8,ui_seconds=12,request_bytes=8192,envelope_bytes=32768,inner_bytes=4096,num_predict=256),
      automatic_retry=False,fault_injection=False,results=[])
    selected=cases()[:1] if args.phase=='cold' else cases()
    for case in selected:
        row=await evaluate_case(case,args.phase);out['results'].append(row)
        args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(row['case_id'],row['api_result']['explanation_source'],row['api_result']['fallback_reason'],row['exact_candidate_match'],row['client_latency_ms'],'ms',flush=True)
    out['summary']=summary(out['results']);out['model_ps_after']=metadata('/api/ps')
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out['summary'],ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['cold','fixed30'],required=True);parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(parser.parse_args()))
