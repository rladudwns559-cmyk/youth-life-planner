"""T08 오프라인/전송 모의 진단. 실제 모델·실제 참가자는 실행하지 않는다."""
import asyncio,copy,json,socket,threading,time
from itertools import product
from pathlib import Path
import pytest
from backend.explanation import service,narrative_provider as transport
from backend.explanation.catalog_provider import OllamaCatalogProvider
from backend.explanation.contracts import ExplanationDocument
from backend.explanation.narrative_catalog import parse_catalog,assemble_catalog
from backend.explanation.narrative_contract import NarrativeContractError
from backend.web.comparison_schemas import ComparisonInput
from tools.diagnose_t08 import measure,prepare,log_events,main,compact,MODEL
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def case():
    return json.loads((ROOT/'docs/experiments/m3_8f/evidence/m38f-combined-actual.json').read_text(encoding='utf-8'))['case']
def payload(case):
    result,facts,canonical,prepared=prepare(case)
    return dict(facts=facts.model_dump(),template=canonical.model_dump(),schema=ExplanationDocument.model_json_schema()),canonical,prepared
def envelope(prepared):
    inner=dict(summary=prepared.summary_options[0],policy_texts={p.slot:p.texts[0] for p in prepared.policy_options})
    return compact(dict(model=MODEL,message=dict(role='assistant',content=compact(inner).decode()),done=True,done_reason='stop'))

def test_projection_determinism_and_no_network(case,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('NO_NETWORK_ALLOWED')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    before=copy.deepcopy(case);first=measure(case)
    for _ in range(3):assert measure(case)==first
    assert case==before and first['summary_family']=='S3'
    assert first['slot_order']==['p01','p02','p03']
    assert first['options_per_field']==[2,2,2,2] and first['combinations']==16
    assert first['token_count_offline'] is None

def test_candidate_context_schema_and_limits(case):
    _,_,_,p=prepare(case);wire=json.loads(OllamaCatalogProvider(MODEL)._build_request(p));context=json.loads(wire['messages'][1]['content'])
    assert list(context['policy_options'])==['p01','p02','p03']
    assert wire['format']['properties']['summary']['enum']==context['summary_options']
    for slot,options in context['policy_options'].items():assert wire['format']['properties']['policy_texts']['properties'][slot]['enum']==options
    assert wire['options']==dict(temperature=0,num_predict=256,num_ctx=16384)
    assert not wire['stream'] and not wire['shift'] and not wire['truncate']
    assert len(compact(wire))<=8192 and len(wire['messages'][1]['content'].encode())<=4096
    assert '1500000' not in str(context) and 'SAMPLE-001' not in str(context)

@pytest.mark.parametrize('choices',list(product(range(2),repeat=4)))
def test_all_T08_candidate_combinations_preserve_all_python_fields(case,choices):
    _,canonical,p=payload(case)
    raw=dict(summary=p.summary_options[choices[0]],policy_texts={policy.slot:policy.texts[i] for policy,i in zip(p.policy_options,choices[1:],strict=True)})
    document=assemble_catalog(p,parse_catalog(compact(raw).decode(),p))
    assert document.changed_facts==canonical.changed_facts
    assert document.unknown_information==canonical.unknown_information and document.next_actions==canonical.next_actions
    assert [x.model_dump(exclude={'text'}) for x in document.policy_explanations]==[x.model_dump(exclude={'text'}) for x in canonical.policy_explanations]

@pytest.mark.parametrize('fault',['missing','extra','duplicate','cross_slot','whitespace'])
def test_missing_duplicate_wrong_slot_or_nonexact_rejected(case,fault):
    _,_,p=payload(case);raw=json.loads(json.loads(envelope(p))['message']['content'])
    if fault=='missing':raw['policy_texts'].pop('p03')
    if fault=='extra':raw['policy_texts']['p99']=p.policy_options[0].texts[0]
    if fault=='cross_slot':raw['policy_texts']['p03']=p.policy_options[0].texts[0]
    if fault=='whitespace':raw['summary']+=' '
    value=compact(raw).decode()
    if fault=='duplicate':value=value.replace('"p01":','"p01":"중복", "p01":',1)
    with pytest.raises(NarrativeContractError):parse_catalog(value,p)

@pytest.mark.parametrize('extra,reason',[(0,None),(1,'RESPONSE_TOO_LONG')])
def test_exact32KiB_or_oversize_transport_boundary(case,monkeypatch,extra,reason):
    _,_,p=payload(case);raw=envelope(p);raw+=b' '*(32768+extra-len(raw));seen={}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):seen['limit']=limit;return raw[:limit]
    class Opener:
        def open(self,request,timeout):seen.update(timeout=timeout,endpoint=request.full_url);return Response()
    monkeypatch.setattr(transport,'build_opener',lambda *args:Opener())
    response=asyncio.run(service.explain(ComparisonInput(before=case['before'],after=case['after']),provider=OllamaCatalogProvider(MODEL)))
    assert seen['limit']==32769 and seen['timeout']==6 and seen['endpoint']=='http://127.0.0.1:11434/api/chat'
    assert response.fallback_reason==reason
    assert response.fallback==(extra==1)

def test_provider_read_timeout_whole_fallback_no_retry(case,monkeypatch):
    count=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):assert limit==32769;raise TimeoutError('PRIVATE_DIAGNOSTIC')
    class Opener:
        def open(self,request,timeout):count.append(timeout);return Response()
    monkeypatch.setattr(transport,'build_opener',lambda *args:Opener())
    _,canonical,_=payload(case)
    response=asyncio.run(service.explain(ComparisonInput(before=case['before'],after=case['after']),provider=OllamaCatalogProvider(MODEL)))
    assert count==[6] and response.fallback_reason=='TIMEOUT' and response.document==canonical
    assert not response.ai_success and 'PRIVATE_DIAGNOSTIC' not in response.model_dump_json()

def test_real_eight_second_service_deadline_ignores_late_thread_result(case):
    # 실제 모델 없이 의도적으로 느린 전송 thread를 모의한다. 기존8초 값을 바꾸지 않는다.
    release=threading.Event();finished=threading.Event();_,canonical,p=payload(case)
    class Late(OllamaCatalogProvider):
        def _post(self,body):
            try:
                assert release.wait(11)
                return envelope(p)
            finally:finished.set()
    async def scenario():
        started=time.perf_counter()
        try:
            response=await service.explain(ComparisonInput(before=case['before'],after=case['after']),provider=Late(MODEL))
            elapsed=time.perf_counter()-started;snapshot=response.model_dump_json()
            assert response.fallback_reason=='TIMEOUT' and response.document==canonical
            assert elapsed>=7.9 and service.TIMEOUT_SECONDS==8
            release.set();assert await asyncio.to_thread(finished.wait,1)
            await asyncio.sleep(0)
            assert response.model_dump_json()==snapshot and not response.ai_success
        finally:release.set()
    asyncio.run(scenario())

def test_request_binding_and_concurrent_provider_isolation(case):
    other=copy.deepcopy(case);other['after']['monthly_rent']=350000
    left,_,pl=payload(case);right,_,pr=payload(other);before=copy.deepcopy((left,right));barrier=threading.Barrier(2)
    class Concurrent(OllamaCatalogProvider):
        real_model=False;kind='test_double'
        def _post(self,body):
            barrier.wait(timeout=3);wire=json.loads(body);c=json.loads(wire['messages'][1]['content'])
            raw=dict(summary=c['summary_options'][1],policy_texts={k:v[1] for k,v in c['policy_options'].items()})
            return compact(dict(model=MODEL,message=dict(role='assistant',content=compact(raw).decode()),done=True,done_reason='stop'))
    provider=Concurrent(MODEL)
    async def run():return await asyncio.gather(provider.generate(left),provider.generate(right))
    a,b=map(json.loads,asyncio.run(run()))
    assert a['changed_facts']==left['template']['changed_facts'] and b['changed_facts']==right['template']['changed_facts']
    assert (left,right)==before
    checked=parse_catalog(json.loads(envelope(pl))['message']['content'],pl)
    with pytest.raises(NarrativeContractError):assemble_catalog(pr,checked)

def test_native_log_does_not_invent_eval_count_or_timestamps():
    text='time=2026-10-26T12:00:00+09:00 msg="starting llama-server" cmd="--port 123 --context-shift"\nnew prompt, task.n_tokens = 250\nstop processing: n_tokens = 342'
    result=log_events(text)
    assert result['runner_starts'][0]['context_shift']
    assert result['events'][0]['prompt_tokens']==250 and result['events'][0]['timestamp'] is None
    assert result['events'][1]['official_eval_count'] is None and result['events'][1]['slot_n_tokens']==342

def test_cli_refuses_existing_output_before_reading_sources(tmp_path):
    path=tmp_path/'unchanged.json';path.write_text('KEEP',encoding='utf-8')
    with pytest.raises(ValueError,match='REFUSE_OVERWRITE'):
        main(['--evidence',str(path),'--first',str(path),'--second',str(path),'--log',str(path),'--output',str(path)])
    assert path.read_text()=='KEEP'
