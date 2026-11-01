"""Transport fixtures only. These tests do not execute a real model."""
import asyncio
import copy
import json
from pathlib import Path
import threading

import pytest

from backend.explanation import narrative_provider as module
from backend.explanation import service
from backend.explanation.contracts import ExplanationDocument
from backend.explanation.facts import build_facts, deterministic_document
from backend.explanation.provider import get_provider, NoProvider, OllamaLocalProvider, ProviderResponseTooLong
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

MODEL='qwen3:4b-instruct-2507-q4_K_M'
FIXTURE=Path(__file__).parent/'fixtures/narrative_response_v1.json'

def data(case=None):
    case=case or cases()[0]
    return ComparisonInput(before=case['before'],after=case['after'])

def payload(case=None):
    comparison=compare_scenarios(data(case));facts=build_facts(comparison);expected=deterministic_document(comparison,facts)
    return dict(facts=facts.model_dump(),template=expected.model_dump(),schema=ExplanationDocument.model_json_schema()),expected

def envelope(obj=None):
    return dict(model=MODEL,message=dict(role='assistant',content=json.dumps(obj or json.loads(FIXTURE.read_text(encoding='utf-8')),ensure_ascii=False)),
                done=True,done_reason='stop',eval_count=100,prompt_eval_count=500,total_duration=1000)

class FixtureProvider(module.OllamaNarrativeProvider):
    real_model=False
    kind='test_double'
    def __init__(self,fault=None):super().__init__(MODEL);self.calls=0;self.last_body=None;self.fault=fault
    def _post(self,body):
        self.calls+=1;self.last_body=json.loads(body)
        if self.fault in ('timeout','offline','internal'):
            raise {'timeout':TimeoutError,'offline':ConnectionError,'internal':RuntimeError}[self.fault]('PRIVATE_VALUE')
        obj=envelope()
        if self.fault:self.fault(obj)
        return json.dumps(obj,ensure_ascii=False).encode()

@pytest.mark.parametrize('case',cases(),ids=lambda c:c['case_id'])
def test_fixed30_through_existing_service_with_mocked_transport_only(case):
    provider=FixtureProvider();result=asyncio.run(service.explain(data(case),provider=provider))
    assert provider.calls==1 and result.validation_passed and not result.fallback
    assert result.explanation_source=='validated_test_double' and not result.ai_success and not result.ai_executed
    assert result.facts.money_facts==result.document.changed_facts
    assert result.facts.unknown_information==result.document.unknown_information
    assert result.facts.benefit_applied_krw==0

def test_wire_is_chat_compact_no_original_values_paths_template_or_legacy_prompt():
    provider=FixtureProvider();asyncio.run(service.explain(data(cases()[1]),provider=provider))
    obj=provider.last_body;text=json.dumps(obj,ensure_ascii=False)
    assert obj['model']==MODEL and obj['stream'] is False and obj['truncate'] is False and obj['shift'] is False
    assert obj['options']==dict(temperature=0,num_predict=256,num_ctx=16384)
    assert [m['role'] for m in obj['messages']]==['system','user']
    assert 'template JSON' not in text and '1500000' not in text and 'SAMPLE-001' not in text
    assert 'data/synthetic/' not in text and 'source_refs' not in text and 'changed_facts' not in text
    assert len(json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode())<=8192
    assert obj['format']['properties']['policy_texts']['required']==['p01','p02','p03']

@pytest.mark.parametrize('fault',[
    lambda x:x.update(done=False),lambda x:x.update(done_reason='length'),lambda x:x.pop('done_reason'),
    lambda x:x.update(model='OTHER'),lambda x:x.update(remote_host='https://remote'),lambda x:x.update(remote_model='remote'),
    lambda x:x.update(context=[]),lambda x:x.update(logprobs=[]),lambda x:x.update(_debug_info={}),
    lambda x:x['message'].update(role='user'),lambda x:x['message'].update(content={}),
    lambda x:x['message'].update(thinking='생각'),lambda x:x['message'].update(tool_calls=[{}]),
    lambda x:x['message'].update(images=['pixel']),lambda x:x.update(eval_count=True),
    lambda x:x.update(eval_count=-1),lambda x:x.update(eval_count=1.1),
    lambda x:x['message'].update(extra='untrusted'),lambda x:x.update(created_at=None),
],ids=[f'envelope-{i:02d}' for i in range(19)])
def test_incomplete_remote_tool_thinking_bad_metrics_or_envelope_falls_back(fault):
    provider=FixtureProvider(fault);result=asyncio.run(service.explain(data(),provider=provider))
    assert provider.calls==1 and result.fallback_reason=='INVALID_JSON'
    assert result.document==deterministic_document(compare_scenarios(data()),result.facts)

@pytest.mark.parametrize('raw',[
    b'not json',b'\xff',b'{"done":false,"done":true}',
    b'{"eval_count":NaN}',b'{"message":{"content":"a","content":"b"}}',
])
def test_strict_outer_parser_preserves_duplicate_and_nonfinite_rejection(raw):
    class Invalid(FixtureProvider):
        def _post(self,body):self.calls+=1;return raw
    p=Invalid();result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback_reason=='INVALID_JSON'

@pytest.mark.parametrize(('content','reason'),[
    ('{}','INVALID_JSON'),('{"summary":"가","summary":"나"}','INVALID_JSON'),
    (json.dumps({'summary':'자격이 충족됩니다.','policy_texts':{'p01':'가','p02':'나','p03':'다'}},ensure_ascii=False),'UNSUPPORTED_NARRATIVE'),
    ('가'*1400,'RESPONSE_TOO_LONG'),
])
def test_core_rejections_keep_existing_public_fallback_codes(content,reason):
    p=FixtureProvider(lambda x:x['message'].update(content=content))
    result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback_reason==reason
    assert result.document.changed_facts==result.facts.money_facts

@pytest.mark.parametrize(('fault','reason'),[('timeout','TIMEOUT'),('offline','PROVIDER_UNAVAILABLE'),('internal','GENERATION_FAILED')])
def test_failures_never_retry_or_echo_raw_exception(fault,reason):
    p=FixtureProvider(fault);result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==1 and result.fallback_reason==reason
    assert 'PRIVATE_VALUE' not in result.model_dump_json()

def test_transport_fixed_loopback_no_proxy_no_auth_six_seconds_and_bounded_read(monkeypatch):
    seen={}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):seen['limit']=limit;return json.dumps(envelope()).encode()
    class Opener:
        def open(self,request,timeout):seen.update(url=request.full_url,timeout=timeout,authorization=request.get_header('Authorization'));return Response()
    def build(*handlers):seen['handlers']=handlers;return Opener()
    monkeypatch.setattr(module,'build_opener',build)
    p=module.OllamaNarrativeProvider(MODEL)
    obj,_=payload();raw=asyncio.run(p.generate(obj))
    assert json.loads(raw)['policy_explanations'][0]['policy_id']=='SAMPLE-001'
    assert seen['url']=='http://127.0.0.1:11434/api/chat' and seen['timeout']==6 and seen['limit']==32769
    assert seen['authorization'] is None and seen['handlers'][0].proxies=={}

def test_envelope_limit_not_increased(monkeypatch):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):assert limit==32769;return b'x'*limit
    class Opener:
        def open(self,*args,**kwargs):return Response()
    monkeypatch.setattr(module,'build_opener',lambda *args:Opener())
    with pytest.raises(ProviderResponseTooLong):module.OllamaNarrativeProvider(MODEL)._post(b'{}')

def test_request_limit_rejects_before_post(monkeypatch):
    monkeypatch.setattr(module,'NARRATIVE_SYSTEM_PROMPT_V1','가'*8192)
    p=FixtureProvider();result=asyncio.run(service.explain(data(),provider=p))
    assert p.calls==0 and result.fallback_reason=='RESPONSE_TOO_LONG'

def test_explicit_contract_factory_and_legacy_default_are_preserved(monkeypatch):
    monkeypatch.setenv('AIX_EXPLANATION_PROVIDER','ollama_local');monkeypatch.setenv('AIX_OLLAMA_MODEL',MODEL)
    monkeypatch.delenv('AIX_EXPLANATION_CONTRACT',raising=False)
    assert type(get_provider()) is OllamaLocalProvider
    monkeypatch.setenv('AIX_EXPLANATION_CONTRACT','narrative_v1')
    assert type(get_provider()) is module.OllamaNarrativeProvider
    monkeypatch.setenv('AIX_EXPLANATION_CONTRACT','untrusted')
    assert isinstance(get_provider(),NoProvider)
    monkeypatch.delenv('AIX_EXPLANATION_PROVIDER')
    assert isinstance(get_provider(),NoProvider)

def test_existing_validator_runs_in_core_and_service_without_altering_core(monkeypatch):
    seen=[];original=service.validate_output
    def spy(raw,expected):seen.append(expected.model_dump());return original(raw,expected)
    monkeypatch.setattr(service,'validate_output',spy)
    result=asyncio.run(service.explain(data(),provider=FixtureProvider()))
    assert len(seen)==2 and seen[0]==seen[1]
    assert result.document.changed_facts==result.facts.money_facts

def test_one_shared_provider_keeps_concurrent_request_snapshots_isolated():
    a,expected_a=payload();b,expected_b=payload(cases()[6])
    for collection in ('policy_facts','unknown_information','next_actions'):
        for row in b['facts'][collection]:row['policy_id']='OTHER-'+row['policy_id']
    for collection in ('policy_explanations','unknown_information','next_actions'):
        for row in b['template'][collection]:row['policy_id']='OTHER-'+row['policy_id']
    barrier=threading.Barrier(2)
    class Concurrent(FixtureProvider):
        def _post(self,body):
            self.calls+=1;barrier.wait(timeout=2)
            return json.dumps(envelope()).encode()
    p=Concurrent()
    async def both():return await asyncio.gather(p.generate(a),p.generate(b))
    ra,rb=[json.loads(raw) for raw in asyncio.run(both())]
    assert p.calls==2
    assert ra['policy_explanations'][0]['policy_id']=='SAMPLE-001'
    assert rb['policy_explanations'][0]['policy_id']=='OTHER-SAMPLE-001'
    assert ra['changed_facts']==a['template']['changed_facts'] and rb['changed_facts']==b['template']['changed_facts']
