"""저장된 합성 증거의 오프라인 진단. 모델 서버·네트워크·환경 변경 기능 없음."""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import re
from backend.explanation.catalog_provider import OllamaCatalogProvider
from backend.explanation.facts import build_facts,deterministic_document
from backend.explanation.narrative_catalog import prepare_catalog,parse_catalog,assemble_catalog
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

MODEL='qwen3:4b-instruct-2507-q4_K_M'
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(value):return hashlib.sha256(value).hexdigest()
def prepare(case):
    result=compare_scenarios(ComparisonInput(before=case['before'],after=case['after']))
    facts=build_facts(result);expected=deterministic_document(result,facts)
    return result,facts,expected,prepare_catalog(facts,expected)
def measure(case):
    result,facts,expected,prepared=prepare(case)
    body=OllamaCatalogProvider(MODEL)._build_request(prepared);wire=json.loads(body)
    lengths=[]
    for combination in product(prepared.summary_options,*(p.texts for p in prepared.policy_options)):
        content=dict(summary=combination[0],policy_texts={p.slot:text for p,text in zip(prepared.policy_options,combination[1:],strict=True)})
        raw=compact(content).decode();assembled=assemble_catalog(prepared,parse_catalog(raw,prepared))
        assert assembled.changed_facts==expected.changed_facts and assembled.unknown_information==expected.unknown_information
        assert assembled.next_actions==expected.next_actions
        lengths.append(len(raw.encode('utf-8')))
    return dict(case_id=case['case_id'],changed_input_fields=facts.changed_input_fields,summary_family=prepared.summary_family,
        slot_order=[p.slot for p in prepared.policy_options],policy_families=[p.family for p in prepared.policy_options],
        options_per_field=[len(prepared.summary_options)]+[len(p.texts) for p in prepared.policy_options],
        combinations=len(lengths),wire_bytes=len(body),wire_sha256=sha(body),context_bytes=len(prepared.model_input_json.encode()),
        system_prompt_bytes=len(wire['messages'][0]['content'].encode()),system_prompt_chars=len(wire['messages'][0]['content']),
        message_content_bytes=sum(len(m['content'].encode()) for m in wire['messages']),schema_bytes=len(compact(wire['format'])),
        inner_output_utf8_min=min(lengths),inner_output_utf8_max=max(lengths),inner_outputs_validated=len(lengths),
        token_count_offline=None,token_count_note='UTF8 byte/문자 수를 tokenizer 토큰 수라고 부르지 않는다. schema 문법 처리 비용은 별도 미측정.',
        options=wire['options'],stream=wire['stream'],shift=wire['shift'],truncate=wire['truncate'],
        python_result_sha256=sha(compact(result.model_dump())),facts_sha256=sha(compact(facts.model_dump())),
        canonical_sha256=sha(compact(expected.model_dump())))
def log_events(text):
    starts=[];events=[]
    for line_no,line in enumerate(text.splitlines(),1):
        stamp=re.search(r'time=(\S+)',line);timestamp=stamp[1] if stamp else None
        if 'msg="starting llama-server"' in line:
            port=re.search(r'--port (\d+)',line)
            starts.append(dict(line=line_no,timestamp=timestamp,port=int(port[1]) if port else None,
                context_shift='--context-shift' in line))
        name=None;extra={}
        if 'msg="llama-server started in ' in line:name='runner_ready'
        elif 'client connection closed before llama-server finished loading' in line:name='client_closed_during_load'
        elif 'msg="Load failed"' in line:name='load_failed_context_cancelled'
        elif 'processing task, is_child' in line:name='task_started'
        elif 'new prompt,' in line:
            name='prompt_started';extra['prompt_tokens']=int(re.search(r'task.n_tokens = (\d+)',line)[1])
        elif 'stop: cancel task' in line:name='task_cancelled'
        elif 'stop processing: n_tokens' in line:
            name='slot_released';extra['slot_n_tokens']=int(re.search(r'n_tokens = (\d+)',line)[1])
            extra['official_eval_count']=None
        if name:events.append(dict(line=line_no,timestamp=timestamp,event=name,runner_port=starts[-1]['port'] if starts else None,**extra))
    return dict(runner_starts=starts,events=events,normalized_text_sha256=sha(text.encode('utf-8')),
        note='네이티브 무타임스탬프 줄은 직전 runner 구간에만 대응. HTTP 요청 ID가 없어 정밀 요청 시각/생성 토큰 수를 복원하지 않는다.')
def historical_attempt(document):
    row=document['results'][0]
    return dict(case_id=row['case_id'],preload=document['preload'],provider_post_attempts=row['provider_post_attempts'],
        wire_bytes=row['request_bytes'],context_bytes=row['context_bytes'],transport_ms=row['transport_latency_ms'],
        service_ms=row['client_latency_ms'],post_error_type=row['post_error_type'],
        envelope_bytes=row['envelope_bytes'],model_metrics=row['model_metrics'],completion_reason=row['completion_reason'],
        source=row['api_result']['explanation_source'],fallback_reason=row['api_result']['fallback_reason'],
        structure_valid=row['structure_valid'],exact_candidate_match=row['exact_candidate_match'],
        raw_model_output_available=row['actual_model_output'] is not None,
        strict_equivalent_preload=False,official_generation_token_count=None)
def analyze(evidence,attempts,log_text):
    selected={c['case_id']:c for c in cases()};fixed=[]
    for row in evidence['actual_fixed30']['results']:
        m=measure(selected[row['case_id']]);assert m['wire_bytes']==row['request_bytes']
        m.update(actual_model_metrics=row['model_metrics'],client_ms=row['client_latency_ms'],accepted=row['api_result']['ai_success'])
        fixed.append(m)
    t08=measure(attempts[0]['case']);assert attempts[0]['case']==attempts[1]['case']
    for attempt in attempts:
        row=attempt['results'][0]
        assert t08['wire_bytes']==row['request_bytes']
        assert row['python_confirmed_result']==prepare(attempt['case'])[0].model_dump()
    largest=max(fixed,key=lambda m:(m['wire_bytes'],m['context_bytes'],m['case_id']))
    return dict(milestone='M3.8F-R1',mode='OFFLINE_ONLY',new_model_runs=0,actual_participants=0,real_responses=0,
        t08=t08,historical_attempts=[historical_attempt(a) for a in attempts],
        most_complex_definition='wire UTF8 bytes 최대, 동률이면 context bytes/ID. tokenizer 토큰 순위와 구분.',
        largest_fixed30=largest,fixed30=fixed,wire_delta_t08_minus_largest=t08['wire_bytes']-largest['wire_bytes'],
        native_log=log_events(log_text),
        confirmed=['preload omitted shift, actual catalog request uses shift=false',
                   'native runner starts alternate context-shift on/off',
                   'first actual call cancelled while replacement runner loading',
                   'second actual call reached a fresh runner and a 250-token prompt before cancellation'],
        unconfirmed=['equal-configuration warm T08 completion within6s','schema/grammar or generation latency contribution',
                     'network connect versus first-byte/read breakdown','official eval_count for both failed requests',
                     'RAM pressure as causal factor','whether fixing preload alone resolves second timeout'],
        limits=dict(provider_seconds=6,service_seconds=8,ui_seconds=12,envelope_bytes=32768,request_bytes=8192,inner_bytes=4096),
        root_cause_status='PARTIAL_CAUSAL_EVIDENCE_FULL_LATENCY_CAUSE_UNCONFIRMED',
        verdict='M3_T08_LIVE_RETEST_APPROVAL_REQUIRED')
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--first',type=Path,required=True)
    parser.add_argument('--second',type=Path,required=True);parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    sources=[args.evidence,args.first,args.second,args.log]
    if args.output.resolve() in [p.resolve() for p in sources] or args.output.exists():raise ValueError('REFUSE_OVERWRITE_SOURCE_OR_RESULT')
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    result=analyze(load(args.evidence),[load(args.first),load(args.second)],args.log.read_text(encoding='utf-8'))
    result['source_files']={p.name:dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in sources}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('mode','new_model_runs','wire_delta_t08_minus_largest','verdict')},ensure_ascii=False))
if __name__=='__main__':main()
