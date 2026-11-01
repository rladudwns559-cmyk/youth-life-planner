"""전송 모의시험만 실행한다. 실제 모델30평가와 별도다."""
import asyncio
import copy
import json
import threading

import pytest

from backend.explanation import catalog_provider as module, narrative_provider as transport, service
from backend.explanation.narrative_catalog import prepare_catalog
from backend.explanation.contracts import ExplanationDocument
from backend.explanation.facts import build_facts, deterministic_document
from backend.explanation.provider import get_provider, NoProvider, OllamaLocalProvider, ProviderResponseTooLong
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

MODEL='qwen3:4b-instruct-2507-q4_K_M'
def data(case=None):
    case=case or cases()[0];return ComparisonInput(before=case['before'],after=case['after'])
def payload(case=None):
    comparison=compare_scenarios(data(case));facts=build_facts(comparison);expected=deterministic_document(comparison,facts)
    return dict(facts=facts.model_dump(),template=expected.model_dump(),schema=ExplanationDocument.model_json_schema()),expected
def response_for(body):
    context=json.loads(json.loads(body)['messages'][1]['content'])
    return dict(summary=context['summary_options'][0],policy_texts={k:v[0] for k,v in context['policy_options'].items()})
def envelope(content):
    return dict(model=MODEL,message=dict(role='assistant',content=json.dumps(content,ensure_ascii=False)),done=True,done_reason='stop',eval_count=60,total_duration=10)
class FixtureProvider(module.OllamaCatalogProvider):
    real_model=False;kind='test_double'
    def __init__(self,fault=None):super().__init__(MODEL);self.calls=0;self.body=None;self.fault=fault
    def _post(self,body):
        self.calls+=1;self.body=body
        if self.fault in ('timeout','offline','internal'):
            raise {'timeout':TimeoutError,'offline':ConnectionError,'internal':RuntimeError}[self.fault]('PRIVATE_VALUE')
        obj=envelope(response_for(body))
        if self.fault:self.fault(obj)
        return json.dumps(obj,ensure_ascii=False).encode()

@pytest.mark.parametrize('case',cases(),ids=lambda c:c['case_id'])
def test_fixed30_through_unchanged_service_with_transport_fixture(case):
    p=FixtureProvider();result=asyncio.run(service.explain(data(case),provider=p))
    assert p.calls==1 and not result.fallback and result.validation_passed
    assert result.explanation_source=='validated_test_double' and not result.ai_success and not result.ai_executed
    comparison=compare_scenarios(data(case));expected=deterministic_document(comparison,build_facts(comparison))
    assert result.document.changed_facts==expected.changed_facts and result.document.unknown_information==expected.unknown_information
    assert result.document.next_actions==expected.next_actions
    assert [x.model_dump(exclude={'text'}) for x in result.document.policy_explanations]==[x.model_dump(exclude={'text'}) for x in expected.policy_explanations]

def test_wire_uses_only_candidate_context_and_exact_enum_with_same_limits():
    p=FixtureProvider();asyncio.run(service.explain(data(cases()[9]),provider=p));obj=json.loads(p.body);context=json.loads(obj['messages'][1]['content'])
    assert obj['options']==dict(temperature=0,num_predict=256,num_ctx=16384)
    assert obj['stream'] is False and obj['truncate'] is False and obj['shift'] is False
    assert [m['role'] for m in obj['messages']]==['system','user']
    assert set(context)=={'contract','summary_options','policy_options'}
    assert context['contract']=='narrative-catalog-v2'
    assert obj['format']['properties']['summary']['enum']==context['summary_options']
    for slot,texts in context['policy_options'].items():assert obj['format']['properties']['policy_texts']['properties'][slot]['enum']==texts
    assert len(p.body)<=8192 and len(obj['messages'][1]['content'].encode())<=4096
    assert all(marker not in p.body.decode() for marker in ('1500000','SAMPLE-001','source_refs','data/synthetic/','changed_facts','template'))

@pytest.mark.parametrize('change',[
 lambda c:c.update(summary='월세가 줄어서 소득이 늘었어요.'),
 lambda c:c.update(summary=c['summary']+' '),
 lambda c:c['policy_texts'].update(p03=c['policy_texts']['p01']),
 lambda c:c['policy_texts'].pop('p03'),
 lambda c:c['policy_texts'].update(p99='새 정책이에요.'),
 lambda c:c.update(changed_facts=[{'after':99999}]),
 lambda c:c.update(summary='모든 정책을 확정합니다.'),
 lambda c:c['policy_texts'].update(p03='추가 확인이 필요하지 않아요.'),
])
def test_invalid_or_non_exact_content_rejects_entire_document_without_retry(change):
    def fault(obj):
        content=json.loads(obj['message']['content']);change(content);obj['message']['content']=json.dumps(content,ensure_ascii=False)
    p=FixtureProvider(fault);result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback and not result.ai_success
    assert result.document==deterministic_document(compare_scenarios(data()),result.facts)

@pytest.mark.parametrize('fault',[
 lambda x:x.update(done=False),lambda x:x.update(done_reason='length'),lambda x:x.pop('done_reason'),
 lambda x:x.update(model='OTHER'),lambda x:x.update(remote_host='https://remote'),lambda x:x.update(remote_model='remote'),
 lambda x:x['message'].update(role='user'),lambda x:x['message'].update(thinking='생각'),lambda x:x['message'].update(tool_calls=[{}]),
 lambda x:x['message'].update(images=['pixel']),lambda x:x.update(context=[]),lambda x:x.update(eval_count=True),
])
def test_inherited_envelope_guard_is_unchanged(fault):
    p=FixtureProvider(fault);result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback_reason=='INVALID_JSON'

@pytest.mark.parametrize('raw',[b'not JSON',b'\xff',b'{"done":false,"done":true}',b'{"eval_count":NaN}'])
def test_outer_json_errors_fail_closed(raw):
    class Invalid(FixtureProvider):
        def _post(self,body):self.calls+=1;return raw
    p=Invalid();result=asyncio.run(service.explain(data(),provider=p));assert p.calls==1 and result.fallback_reason=='INVALID_JSON'

@pytest.mark.parametrize('raw,reason',[('not JSON','INVALID_JSON'),('{"summary":"가","summary":"나"}','INVALID_JSON'),('가'*1400,'RESPONSE_TOO_LONG')])
def test_inner_json_and_bytes_unchanged(raw,reason):
    p=FixtureProvider(lambda x:x['message'].update(content=raw));result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback_reason==reason

@pytest.mark.parametrize('fault,reason',[('timeout','TIMEOUT'),('offline','PROVIDER_UNAVAILABLE'),('internal','GENERATION_FAILED')])
def test_no_retry_or_exception_echo(fault,reason):
    p=FixtureProvider(fault);result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback_reason==reason and 'PRIVATE_VALUE' not in result.model_dump_json()

def test_inherited_fixed_transport_proxy_redirect_timeout_and_read_bound(monkeypatch):
    seen={};body=module.OllamaCatalogProvider(MODEL)._build_request(prepare_catalog(build_facts(compare_scenarios(data())),payload()[1]))
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):seen['limit']=limit;return json.dumps(envelope(response_for(body)),ensure_ascii=False).encode()
    class Opener:
        def open(self,request,timeout):seen.update(url=request.full_url,timeout=timeout,auth=request.get_header('Authorization'));return Response()
    def build(*handlers):seen['handlers']=handlers;return Opener()
    monkeypatch.setattr(transport,'build_opener',build)
    raw=asyncio.run(module.OllamaCatalogProvider(MODEL).generate(payload()[0]));assert json.loads(raw)['policy_explanations'][0]['policy_id']=='SAMPLE-001'
    assert seen['url']=='http://127.0.0.1:11434/api/chat' and seen['timeout']==6 and seen['limit']==32769 and seen['auth'] is None
    assert seen['handlers'][0].proxies=={} and type(seen['handlers'][1]).__name__=='_NoRedirect'

def test_oversize_envelope_and_http_failure(monkeypatch):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):assert limit==32769;return b'x'*limit
    class Opener:
        def open(self,*_,**__):return Response()
    monkeypatch.setattr(transport,'build_opener',lambda *args:Opener())
    p=module.OllamaCatalogProvider(MODEL);result=asyncio.run(service.explain(data(),provider=p));assert result.fallback_reason=='RESPONSE_TOO_LONG'
    def failed(*_,**__):raise OSError('PRIVATE_HTTP_FAILURE')
    monkeypatch.setattr(Opener,'open',failed)
    result=asyncio.run(service.explain(data(),provider=p));assert result.fallback_reason=='PROVIDER_UNAVAILABLE' and 'PRIVATE_HTTP' not in result.model_dump_json()

def test_request_limit_rejects_before_post(monkeypatch):
    monkeypatch.setattr(module,'CATALOG_SYSTEM_PROMPT_V2','가'*8192)
    p=FixtureProvider();result=asyncio.run(service.explain(data(),provider=p));assert p.calls==0 and result.fallback_reason=='RESPONSE_TOO_LONG'

def test_explicit_factory_preserves_no_provider_legacy_and_v1(monkeypatch):
    monkeypatch.setenv('AIX_EXPLANATION_PROVIDER','ollama_local');monkeypatch.setenv('AIX_OLLAMA_MODEL',MODEL)
    for flag,expected in [('',OllamaLocalProvider),('narrative_v1',transport.OllamaNarrativeProvider),('narrative_catalog_v2',module.OllamaCatalogProvider)]:
        monkeypatch.setenv('AIX_EXPLANATION_CONTRACT',flag);assert type(get_provider()) is expected
    monkeypatch.setenv('AIX_EXPLANATION_CONTRACT','untrusted');assert isinstance(get_provider(),NoProvider)
    monkeypatch.delenv('AIX_EXPLANATION_PROVIDER');assert isinstance(get_provider(),NoProvider)

def test_validator_runs_in_preflight_assembly_and_service_and_rejection_falls_back(monkeypatch):
    calls=[];original=service.validate_output
    def spy(raw,expected):calls.append(raw);return original(raw,expected)
    monkeypatch.setattr(service,'validate_output',spy)
    p=FixtureProvider();result=asyncio.run(service.explain(data(),provider=p));assert len(calls)>=3 and not result.fallback
    def rejected(*_):raise service.OutputRejected('UNSUPPORTED_NARRATIVE')
    monkeypatch.setattr(service,'validate_output',rejected)
    result=asyncio.run(service.explain(data(),provider=FixtureProvider()));assert result.fallback and result.fallback_reason=='UNSUPPORTED_NARRATIVE'

def test_shared_provider_concurrent_requests_do_not_mix_candidates_or_server_ids():
    a,da=payload(cases()[1]);b,db=payload(cases()[9]);barrier=threading.Barrier(2)
    for key in ('policy_facts','unknown_information','next_actions'):
        for row in b['facts'][key]:row['policy_id']='OTHER-'+row['policy_id']
    for key in ('policy_explanations','unknown_information','next_actions'):
        for row in b['template'][key]:row['policy_id']='OTHER-'+row['policy_id']
    class Concurrent(FixtureProvider):
        def _post(self,body):barrier.wait(timeout=3);return json.dumps(envelope(response_for(body)),ensure_ascii=False).encode()
    p=Concurrent()
    async def both():return await asyncio.gather(p.generate(a),p.generate(b))
    first,second=[json.loads(raw) for raw in asyncio.run(both())]
    assert first['summary'].startswith('취업상태') and second['summary'].startswith('월세')
    assert first['policy_explanations'][0]['policy_id']=='SAMPLE-001' and second['policy_explanations'][0]['policy_id']=='OTHER-SAMPLE-001'
    assert first['changed_facts']==a['template']['changed_facts'] and second['unknown_information']==b['template']['unknown_information']
