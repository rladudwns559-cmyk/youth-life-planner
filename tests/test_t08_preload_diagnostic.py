"""승인된 실행 도구의 합성 gate/관측 시험. 실제 모델 호출 없음."""
import asyncio,json
from pathlib import Path
import pytest
from tools import run_t08_preload_diagnostic as module
from tools.diagnose_t08 import prepare
from backend.explanation.catalog_provider import OllamaCatalogProvider
from backend.explanation import narrative_provider as transport

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def case():return json.loads((ROOT/'docs/experiments/m3_8f/evidence/m38f-combined-actual.json').read_text(encoding='utf-8'))['case']
def load_response():return dict(model=module.MODEL,done=True,done_reason='load',message=dict(role='assistant',content=''))
def state():return dict(launch_context=16384,launch_parallel=1,runner_starts=[dict(port=1,context_shift=False)],events=[dict(event='runner_ready',runner_port=1)])
def ps():return dict(models=[dict(name=module.MODEL,digest=module.DIGEST)])
def test_preload_only_removes_messages_retains_exact_configuration_and_enum(case):
    _,_,_,prepared=prepare(case);actual=json.loads(OllamaCatalogProvider(module.MODEL)._build_request(prepared));empty=json.loads(module.preload_body(prepared))
    assert empty.pop('messages')==[];actual.pop('messages');assert empty==actual
    assert empty['shift'] is False and empty['truncate'] is False and empty['options']['num_ctx']==16384

@pytest.mark.parametrize('change',[
 lambda x:x.update(done=False),lambda x:x.update(model='other'),lambda x:x.update(done_reason='stop'),
 lambda x:x['message'].update(content='설명'),lambda x:x.update(eval_count=1),lambda x:x.update(remote_host='remote'),
])
def test_preload_bad_response_never_confirms(change):
    value=load_response();change(value)
    with pytest.raises(ValueError):module.valid_preload(json.dumps(value).encode())
def test_preload_duplicate_json_rejected():
    with pytest.raises(ValueError):module.valid_preload(b'{"done":false,"done":true}')
def test_preload_exact_load_accepted():assert module.valid_preload(json.dumps(load_response()).encode())['done_reason']=='load'

@pytest.mark.parametrize('fault',['digest','shift','context','parallel','not_ready','no_model'])
def test_same_name_only_is_not_ready(fault):
    n=state();p=ps()
    if fault=='digest':p['models'][0]['digest']='OTHER'
    elif fault=='shift':n['runner_starts'][0]['context_shift']=True
    elif fault=='context':n['launch_context']=4096
    elif fault=='parallel':n['launch_parallel']=2
    elif fault=='not_ready':n['events']=[]
    elif fault=='no_model':p['models']=[]
    assert not module.compatible_ready(p,n)
def test_loaded_matching_settings_is_ready():assert module.compatible_ready(ps(),state())

def test_actual_transport_wrapper_preserves_timeout_read_limit_and_records_error_phase(monkeypatch):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):assert limit==32769;raise TimeoutError('PRIVATE')
    class Opener:
        def open(self,request,timeout):assert timeout==6;return Response()
    factory=lambda *handlers:Opener()
    monkeypatch.setattr(transport,'build_opener',factory);provider=module.TimedRecordingProvider()
    with pytest.raises(TimeoutError):provider._post(b'{}')
    assert transport.build_opener is factory and provider.posts==1
    assert [e['stage'] for e in provider.transport_trace]==['open_started','headers_received','read_started','read_error','transport_wrapper_finished']
    assert all('PRIVATE' not in str(e) for e in provider.transport_trace)

@pytest.mark.parametrize('kind',['timeout','invalid_load','gate'])
def test_failed_preload_stops_without_diagnostic_calls(case,tmp_path,monkeypatch,kind):
    calls=[]
    def metadata(route):
        if route=='/api/version':return dict(version='0.40.11')
        if route=='/api/tags':return dict(models=[dict(name=module.MODEL,digest=module.DIGEST,details=dict(quantization_level='Q4_K_M'))])
        return ps()
    def post(self,body):
        calls.append('preload')
        if kind=='timeout':raise TimeoutError()
        value=load_response()
        if kind=='invalid_load':value['done_reason']='stop'
        return json.dumps(value).encode()
    async def forbidden(*a):raise AssertionError('NO_GENERATION_ON_PRELOAD_FAILURE')
    monkeypatch.setattr(module.evaluation,'metadata',metadata);monkeypatch.setattr(module.TimedRecordingProvider,'_post',post)
    monkeypatch.setattr(module,'native_state',lambda path:state());monkeypatch.setattr(module,'evaluate_one',forbidden)
    if kind=='gate':monkeypatch.setattr(module,'compatible_ready',lambda *a:False)
    result=asyncio.run(module.run(tmp_path/'evidence.json',tmp_path/'unused.log',case))
    assert result['status']=='STOPPED_PRELOAD_FAILED' and result['results']==[] and calls==['preload']
def test_existing_output_prevents_any_call(case,tmp_path):
    output=tmp_path/'old.json';output.write_text('KEEP')
    with pytest.raises(ValueError):asyncio.run(module.run(output,tmp_path/'log',case))
    assert output.read_text()=='KEEP'

STUDY=ROOT/'docs/experiments/m3_8f_r2/study_v2'
def test_saved_actual_diagnostic_honors_budget_no_reload_and_exact_validation():
    d=json.loads((STUDY.parent/'actual_diagnostics.json').read_text(encoding='utf-8'))
    assert d['preload']['attempts']==1 and d['preload']['success'] and d['preload']['request']['shift'] is False
    assert [r['case_id'] for r in d['results']]==['FU01','EX06']
    assert sum(r['provider_post_attempts'] for r in d['results'])==2
    for r in d['results']:
        assert r['api_result']['ai_success'] and r['exact_candidate_match'] and r['existing_validator_passed']
        assert not r['runner_reload_observed'] and r['envelope_bytes']<=32768

def test_v2_only_adds_valid_T08_B_keeps_questions_and_previous_seven():
    old=json.loads((ROOT/'docs/experiments/m3_8f/private/study_key.json').read_text(encoding='utf-8'))
    new=json.loads((STUDY/'private/study_key.json').read_text(encoding='utf-8'))
    assert new['ready'] and new['version']=='m38f-study-v2-r2' and not old['ready']
    assert old['tasks'][:7]==new['tasks'][:7] and old['allocations']==new['allocations']
    for key in ('input','facts','questions','disclaimer'):assert old['tasks'][7][key]==new['tasks'][7][key]
    assert old['tasks'][7]['variants']['A']==new['tasks'][7]['variants']['A']
    actual=json.loads((STUDY.parent/'t08_accepted_for_study.json').read_text(encoding='utf-8'))
    assert new['tasks'][7]['variants']['B']==actual['results'][0]['api_result']['document']
    assert new['tasks'][7]['source']['source_milestone']=='M3.8F-R2'

@pytest.mark.parametrize('slot',range(1,21))
def test_all_planned_v2_sessions_ready_and_blind(slot):
    session=json.loads((STUDY/f'participant/sessions/P{slot:02}.json').read_text(encoding='utf-8'))
    assert session['ready'] and session['version']=='m38f-study-v2-r2' and len(session['tasks'])==8
    assert all('condition' not in t and 'variants' not in t and 'source' not in t for t in session['tasks'])
    assert all('correct' not in q for t in session['tasks'] for q in t['questions'])

def test_v2_real_summary_no_humans_or_measured_scores():
    d=json.loads((STUDY/'results/initial_summary_real.json').read_text(encoding='utf-8'))
    assert d['actual_participants']==d['real_response_rows']==0
    assert d['verdict']=='M3_EXPLANATION_EVALUATION_READY_PARTICIPANTS_PENDING'
    assert all(c['accuracy_assigned'] is None and c['ratings']['ease']['mean'] is None for c in d['conditions'].values())

def test_v2_preview_remains_synthetic_and_covers_optional_preference():
    q=json.loads((STUDY/'participant/sessions/QA_SYN001.json').read_text(encoding='utf-8'))
    assert q['data_kind']=='synthetic' and q['preview_only'] and len(q['tasks'])==8
    assert q['preference']['task_id']=='T08'
    assert '현재 복합 변경 과제의 실제 AI 문장 미확보' not in (STUDY/'participant/index.html').read_text(encoding='utf-8')
