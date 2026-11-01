"""사용자가 승인한 고정 합성30의 실제 로컬 모델 평가. 모의 응답을 사용하지 않는다."""
import argparse,asyncio,json,statistics,time
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
from backend.explanation.narrative_provider import OllamaNarrativeProvider
from backend.explanation.narrative_contract import prepare_narrative,parse_narrative,NarrativeContractError
from backend.explanation import service
from backend.explanation.facts import build_facts,deterministic_document
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

MODEL='qwen3:4b-instruct-2507-q4_K_M'
DIGEST='0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0'
def api(route):
    with build_opener(ProxyHandler({})).open('http://127.0.0.1:11434'+route,timeout=3) as response:return json.loads(response.read())

class RecordingProvider(OllamaNarrativeProvider):
    """평가 프로세스 전용 기록. 제품 제공자는 원문/요청을 저장하지 않는다."""
    def __init__(self):super().__init__(MODEL);self.posts=0;self.envelope=None;self.request_bytes=None;self.projection_bytes=None;self.post_error=None
    def _post(self,body):
        self.posts+=1;self.request_bytes=len(body)
        self.projection_bytes=len(json.loads(body)['messages'][1]['content'].encode('utf-8'))
        try:
            raw=super()._post(body)
            self.envelope=raw.decode('utf-8')
            return raw
        except Exception as exc:self.post_error=type(exc).__name__;raise

async def evaluate(case,label):
    request=ComparisonInput(before=case['before'],after=case['after']);comparison=compare_scenarios(request)
    facts=build_facts(comparison);expected=deterministic_document(comparison,facts);provider=RecordingProvider()
    start=time.perf_counter();result=await service.explain(request,provider=provider);elapsed=round((time.perf_counter()-start)*1000,2)
    inner=None;outer=None;wire_code=None
    if provider.envelope is not None:
        try:
            outer=json.loads(provider.envelope)
            inner=outer.get('message',{}).get('content')
            if inner is not None:
                try:parse_narrative(inner,prepare_narrative(facts,expected));wire_code='PASS'
                except NarrativeContractError as exc:wire_code=exc.code
        except (ValueError,TypeError):pass
    assert result.facts==facts and result.document.changed_facts==expected.changed_facts
    assert result.document.unknown_information==expected.unknown_information and result.document.next_actions==expected.next_actions
    assert [p.model_dump(exclude={'text'}) for p in result.document.policy_explanations]==[p.model_dump(exclude={'text'}) for p in expected.policy_explanations]
    return dict(case_id=case['case_id'],name=case['name'],phase=label,synthetic=True,original_fault_label_not_injected=case.get('fault'),
      model=MODEL,model_digest=DIGEST,actual_generation_requests=provider.posts,request_bytes=provider.request_bytes,projection_bytes=provider.projection_bytes,
      envelope_bytes=len(provider.envelope.encode()) if provider.envelope is not None else None,raw_envelope=provider.envelope,
      actual_model_output=inner,decoded_output=json.loads(inner) if wire_code=='PASS' else None,
      completion_reason=outer.get('done_reason') if type(outer) is dict else None,
      model_metrics={k:v for k,v in (outer or {}).items() if k.endswith('_count') or k.endswith('_duration')},
      wire_validation=wire_code,client_latency_ms=elapsed,post_error_type=provider.post_error,
      python_confirmed_result=comparison.model_dump(),deterministic_document=expected.model_dump(),api_result=result.model_dump(),
      rendered_core_preserved=True,human_semantic_review='NOT_PERFORMED',codex_semantic_review='PENDING' if inner is not None else 'NO_COMPLETE_OUTPUT')

async def run(args):
    version=api('/api/version');tag=next(t for t in api('/api/tags')['models'] if t['name']==MODEL)
    assert version['version']=='0.40.11' and tag['digest']==DIGEST
    path=args.output;path.parent.mkdir(parents=True,exist_ok=True)
    if args.phase=='cold':
        row=await evaluate(cases()[0],'cold_probe_separate_from_fixed30')
        out=dict(version=version,model=tag,actual_llm=True,synthetic=True,results=[row])
        path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Cold probe:',row['api_result']['explanation_source'],row['api_result']['fallback_reason'],row['client_latency_ms'],flush=True)
        return
    out=dict(evaluation='m3.8b-real-local-fixed30-v1',synthetic=True,actual_llm=True,version=version,model=tag,
      limits=dict(transport_seconds=6,service_seconds=8,ui_seconds=12,envelope_bytes=32768,content_bytes=4096,num_predict=256),
      fault_injection=False,results=[])
    for case in cases():
        row=await evaluate(case,'fixed30_after_separate_cold_probe');out['results'].append(row)
        path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(row['case_id'],row['api_result']['explanation_source'],row['api_result']['fallback_reason'],row['wire_validation'],row['client_latency_ms'],'ms',flush=True)
    rows=out['results'];latencies=[r['client_latency_ms'] for r in rows];successful=[r['client_latency_ms'] for r in rows if r['api_result']['ai_success']]
    out['summary']=dict(scenarios=len(rows),actual_generation_requests=sum(r['actual_generation_requests'] for r in rows),
      completed_model_contents=sum(r['actual_model_output'] is not None for r in rows),accepted=sum(r['api_result']['ai_success'] for r in rows),
      fallback=sum(r['api_result']['fallback'] for r in rows),reasons={str(reason):sum(r['api_result']['fallback_reason']==reason for r in rows) for reason in {r['api_result']['fallback_reason'] for r in rows}},
      request_mean_ms=statistics.mean(latencies),request_median_ms=statistics.median(latencies),request_p95_nearest_rank_ms=sorted(latencies)[28],
      accepted_mean_ms=statistics.mean(successful) if successful else None,rendered_core_mismatches=0,
      model_semantic_accuracy=None,human_reviews=0,note='Request latency includes fallback; human semantic quality not certified. Repeated fixed inputs/cache effects must be disclosed.')
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out['summary'],ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['cold','fixed30'],required=True);parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(parser.parse_args()))
