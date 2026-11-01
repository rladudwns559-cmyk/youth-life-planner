"""M3.8F-R2 승인 전용: 빈 준비1회, T08→EX06 각1회. 제품 계약 변경/재시도 없음."""
import argparse,asyncio,copy,json,re,time
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
from backend.explanation.catalog_provider import OllamaCatalogProvider
from backend.explanation import narrative_provider as transport
from tools import evaluate_local_catalog as evaluation
from tools.evaluate_explanation_scenarios import cases
from tools.diagnose_t08 import prepare,log_events

MODEL=evaluation.MODEL;DIGEST=evaluation.DIGEST
def timestamp():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def preload_body(prepared):
    request=json.loads(OllamaCatalogProvider(MODEL)._build_request(prepared))
    request['messages']=[]
    return json.dumps(request,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def valid_preload(raw):
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=transport._unique,parse_constant=transport._invalid_constant)
    if (not isinstance(value,dict) or value.get('model')!=MODEL or value.get('done') is not True
        or value.get('done_reason')!='load' or value.get('message',{}).get('content','')!=''
        or value.get('eval_count',0)!=0 or value.get('remote_host','') or value.get('remote_model','')):
        raise ValueError('PRELOAD_NOT_CONFIRMED')
    return value

@contextmanager
def observe_transport(trace):
    # 연구 프로세스에서만 관측한다. 기존 전송·timeout·read 상한 그대로 호출.
    original=transport.build_opener;started=time.perf_counter()
    def event(stage,**data):trace.append(dict(stage=stage,elapsed_ms=round((time.perf_counter()-started)*1000,3),at_kst=timestamp(),**data))
    class ObservedResponse:
        def __init__(self,response):self.response=response
        def __enter__(self):self.response.__enter__();return self
        def __exit__(self,*args):return self.response.__exit__(*args)
        def read(self,limit):
            event('read_started',limit_bytes=limit)
            try:raw=self.response.read(limit)
            except Exception as exc:event('read_error',error_type=type(exc).__name__);raise
            event('read_completed',bytes=len(raw));return raw
    class ObservedOpener:
        def __init__(self,opener):self.opener=opener
        def open(self,request,timeout):
            event('open_started',endpoint=request.full_url,timeout_seconds=timeout)
            try:response=self.opener.open(request,timeout=timeout)
            except Exception as exc:event('open_error',error_type=type(exc).__name__);raise
            event('headers_received');return ObservedResponse(response)
    def wrapped(*handlers):return ObservedOpener(original(*handlers))
    transport.build_opener=wrapped
    try:yield
    finally:transport.build_opener=original;event('transport_wrapper_finished')

class TimedRecordingProvider(evaluation.RecordingProvider):
    def __init__(self):super().__init__();self.transport_trace=[]
    def _post(self,body):
        with observe_transport(self.transport_trace):return super()._post(body)

def native_state(path):
    text=path.read_text(encoding='utf-8',errors='strict');state=log_events(text)
    launches=[line for line in text.splitlines() if 'msg="starting llama-server"' in line]
    last=launches[-1] if launches else ''
    context=re.search(r'(?:^| )-c (\d+)',last);parallel=re.search(r'(?:^| )-np (\d+)',last)
    state['launch_context']=int(context[1]) if context else None
    state['launch_parallel']=int(parallel[1]) if parallel else None
    return state
def compatible_ready(ps,native):
    models=[m for m in ps.get('models',[]) if m.get('name')==MODEL and m.get('digest')==DIGEST]
    starts=native['runner_starts']
    return bool(models and starts and not starts[-1]['context_shift'] and
        native.get('launch_context')==16384 and native.get('launch_parallel')==1 and
        any(e['event']=='runner_ready' and e['runner_port']==starts[-1]['port'] for e in native['events']))

async def evaluate_one(case,phase,native_log):
    instances=[];original=evaluation.RecordingProvider
    class Bound(TimedRecordingProvider):
        def __init__(self):super().__init__();instances.append(self)
    before=native_state(native_log);start_at=timestamp();start=time.perf_counter()
    evaluation.RecordingProvider=Bound
    try:row=await evaluation.evaluate_case(case,phase)
    finally:evaluation.RecordingProvider=original
    assert len(instances)==1 and instances[0].posts==1
    p=instances[0];after=native_state(native_log)
    row.update(request_id=phase,started_at_kst=start_at,finished_at_kst=timestamp(),
        diagnostic_wall_ms=round((time.perf_counter()-start)*1000,3),transport_trace=copy.deepcopy(p.transport_trace),
        native_before=before,native_after=after,runner_reload_observed=len(after['runner_starts'])>len(before['runner_starts']),
        cancelled_after_return=False if row['api_result']['ai_success'] else None)
    return row

async def run(output,native_log,first_case):
    if output.exists():raise ValueError('REFUSE_REEXECUTE_OR_OVERWRITE')
    output.parent.mkdir(parents=True,exist_ok=True)
    result=dict(milestone='M3.8F-R2',scope='APPROVED_CAUSE_DIAGNOSTIC',started_at_kst=timestamp(),
        actual_local_model=True,synthetic_profiles_only=True,historical_T08_failures_unchanged=True,
        generation_budget=2,preload_budget=1,automatic_retries=0,results=[],preload=None,
        limits=dict(provider_seconds=6,service_seconds=8,ui_seconds=12,envelope_bytes=32768,num_predict=256,num_ctx=16384),
        actual_participants=0,real_responses=0,status='STARTED')
    def save():output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    save() # 시작 기록이 있으면 같은 출력 경로로 재실행하지 않는다.
    try:
        version=evaluation.metadata('/api/version');tags=evaluation.metadata('/api/tags')
        tag=next(t for t in tags['models'] if t['name']==MODEL)
        assert version['version']=='0.40.11' and tag['digest']==DIGEST and tag['details']['quantization_level']=='Q4_K_M'
        result.update(version=version,model=tag,model_ps_before=evaluation.metadata('/api/ps'))
        _,_,_,prepared=prepare(first_case);body=preload_body(prepared);provider=TimedRecordingProvider()
        preload=dict(request=json.loads(body),started_at_kst=timestamp(),attempts=1,text_generation=False,success=False)
        result['preload']=preload;save();started=time.perf_counter()
        try:
            raw=await asyncio.wait_for(asyncio.to_thread(provider._post,body),timeout=8)
            preload['response']=valid_preload(raw);preload['envelope_bytes']=len(raw)
            result['model_ps_after_preload']=evaluation.metadata('/api/ps')
            preload['native_after']=native_state(native_log)
            preload['success']=compatible_ready(result['model_ps_after_preload'],preload['native_after'])
            if not preload['success']:preload['error_type']='PRELOAD_READY_GATE_FAILED'
        except Exception as exc:preload['error_type']=type(exc).__name__
        finally:
            preload.update(elapsed_ms=round((time.perf_counter()-started)*1000,3),transport_trace=copy.deepcopy(provider.transport_trace),finished_at_kst=timestamp())
            save()
        if not preload['success']:
            result['status']='STOPPED_PRELOAD_FAILED';return result
        control=next(c for c in cases() if c['case_id']=='EX06')
        for case,phase in [(first_case,'R2_DIAGNOSTIC_T08'),(control,'R2_DIAGNOSTIC_CONTROL_EX06')]:
            result['results'].append(await evaluate_one(case,phase,native_log));save()
        result.update(status='DIAGNOSTICS_FINISHED',model_ps_after=evaluation.metadata('/api/ps'))
        return result
    except Exception as exc:
        result.update(status='STOPPED_UNEXPECTED_ERROR',error_type=type(exc).__name__);return result
    finally:
        result['finished_at_kst']=timestamp();save()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-approved-r2',action='store_true');parser.add_argument('--first-evidence',type=Path,required=True)
    parser.add_argument('--native-log',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not args.execute_approved_r2:raise ValueError('EXPLICIT_R2_EXECUTION_FLAG_REQUIRED')
    original=json.loads(args.first_evidence.read_text(encoding='utf-8'))
    if args.output.resolve()==args.first_evidence.resolve() or args.output.exists():raise ValueError('REFUSE_REEXECUTE_OR_OVERWRITE')
    result=asyncio.run(run(args.output,args.native_log,original['case']))
    print(json.dumps(dict(status=result['status'],preload_success=(result['preload'] or {}).get('success'),
        generations=len(result['results']),results=[dict(case=r['case_id'],success=r['api_result']['ai_success'],
            fallback=r['api_result']['fallback_reason'],ms=r['client_latency_ms'],reload=r['runner_reload_observed']) for r in result['results']]),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
