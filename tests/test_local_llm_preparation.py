"""Transport doubles only: these tests provide NO actual-model evidence."""
import asyncio,copy,json
import pytest
from backend.explanation import provider as transport,service
from backend.explanation.contracts import ExplanationDocument
from backend.explanation.facts import build_facts,deterministic_document
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

MODEL='qwen3:4b-instruct-2507-q4_K_M'

def prepare(case=None):
    case=case or cases()[0]
    data=ComparisonInput(before=case['before'],after=case['after'])
    result=compare_scenarios(data);facts=build_facts(result);doc=deterministic_document(result,facts)
    return data,doc,{'facts':facts.model_dump(),'template':doc.model_dump(),'schema':ExplanationDocument.model_json_schema()}

def narrative(obj):
    obj['summary']='변경한 항목과 비교 내용을 함께 살펴보세요.'
    for policy in obj['policy_explanations']:policy['text']='평가된 조건과 추가 확인 항목을 함께 살펴보세요.'
    return obj

@pytest.mark.parametrize('case',cases(),ids=lambda c:c['case_id'])
def test_fixed30_wire_hides_internal_sources_and_roundtrip_retains_python_facts(case):
    _,expected,payload=prepare(case);before=copy.deepcopy(payload)
    wire,reverse=transport._wire_payload(payload)
    wire_json=json.dumps(wire,ensure_ascii=False)
    assert reverse
    for ref in reverse.values():assert ref not in wire_json
    assert 'data/synthetic/' not in wire_json and 'C:\\Users\\' not in wire_json
    assert wire['facts']['money_facts']==payload['facts']['money_facts']
    assert wire['facts']['unknown_information']==payload['facts']['unknown_information']
    raw=json.dumps(narrative(wire['template']),ensure_ascii=False)
    accepted=service.validate_output(transport._restore_sources(raw,reverse),expected)
    assert accepted.changed_facts==expected.changed_facts
    assert accepted.unknown_information==expected.unknown_information
    assert [p.model_dump(exclude={'text'}) for p in accepted.policy_explanations]==[p.model_dump(exclude={'text'}) for p in expected.policy_explanations]
    assert payload==before

@pytest.mark.parametrize('raw',[
    '{"summary":"가","summary":"나"}',
    '{"policy_explanations":[{"rules":[{"source_refs":[],"source_refs":[]}]}]}',
    '{"summary":NaN}', '{"summary":Infinity}', '{"summary":-Infinity}',
    'not json','[]','null','"text"', '가'*32769,
],ids=['duplicate-root','duplicate-nested','nan','positive-infinity','negative-infinity','invalid','array','null','string','over-limit'])
def test_alias_restore_never_masks_malformed_duplicate_or_nonfinite_json(raw):
    _,expected,payload=prepare();_,reverse=transport._wire_payload(payload)
    restored=transport._restore_sources(raw,reverse)
    assert restored==raw
    with pytest.raises(service.OutputRejected):service.validate_output(restored,expected)

def test_alias_mapping_deterministic_and_shared_between_facts_and_template():
    _,_,payload=prepare();wire,reverse=transport._wire_payload(payload)
    assert transport._wire_payload(copy.deepcopy(payload))==(wire,reverse)
    fact_refs=[r['source_refs'] for p in wire['facts']['policy_facts'] for r in p['rules']]
    doc_refs=[r['source_refs'] for p in wire['template']['policy_explanations'] for r in p['rules']]
    assert fact_refs==doc_refs
    assert all(ref.startswith('SOURCE-') for refs in fact_refs for ref in refs)

@pytest.mark.parametrize(('fault','code'),[
    ('source','POLICY_STATE_MISMATCH'),('policy','POLICY_STATE_MISMATCH'),
    ('money','NUMBER_MISMATCH'),('unknown','UNKNOWN_MISSING'),
    ('maturity','UNSUPPORTED_NARRATIVE'),('deadline','UNSUPPORTED_NARRATIVE'),
    ('bad_json','INVALID_JSON'),('offline','PROVIDER_UNAVAILABLE'),
    ('timeout','TIMEOUT'),('internal','GENERATION_FAILED'),
    ('long','RESPONSE_TOO_LONG'),('outer','INVALID_JSON'),
    ('success',None),
])
def test_mocked_adapter_one_call_validates_or_falls_back_without_changing_core(monkeypatch,capsys,fault,code):
    data,expected,_=prepare();original=data.model_dump_json();seen=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):
            assert limit==32769
            if fault=='long':return b'x'*32769
            if fault=='outer':return b'{"done":false,"response":"{}"}'
            obj=narrative(copy.deepcopy(seen[0]['template']))
            if fault=='source':obj['policy_explanations'][0]['rules'][0]['source_refs']=['SOURCE-999']
            if fault=='policy':obj['policy_explanations'][0]['policy_id']='INVENTED'
            if fault=='money':obj['changed_facts'][0]['after']=999999
            if fault=='unknown':obj['unknown_information']=[]
            if fault=='maturity':obj['summary']='실제 상품 만기금액은 999999원입니다.'
            if fault=='deadline':obj['summary']='내일이 신청 마감입니다.'
            raw='{"summary":"가","summary":"나"}' if fault=='bad_json' else json.dumps(obj,ensure_ascii=False)
            return json.dumps({'done':True,'response':raw},ensure_ascii=False).encode()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url=='http://127.0.0.1:11434/api/generate' and timeout==6
            body=json.loads(request.data)
            assert body['model']==MODEL and body['stream'] is False
            assert body['options']=={'temperature':0,'num_predict':4096}
            wire=json.loads(body['prompt']);seen.append(wire)
            assert body['format']==wire['schema']
            assert 'data/synthetic/' not in body['prompt']
            if fault=='offline':raise ConnectionError('PRIVATE_DO_NOT_ECHO')
            if fault=='timeout':raise TimeoutError('PRIVATE_DO_NOT_ECHO')
            if fault=='internal':raise RuntimeError('PRIVATE_DO_NOT_ECHO')
            return Response()
    monkeypatch.setattr(transport,'build_opener',lambda *args:Opener())
    class ProtocolDouble(transport.OllamaLocalProvider):
        real_model=False
        kind='test_double'
    result=asyncio.run(service.explain(data,provider=ProtocolDouble(MODEL)))
    assert len(seen)==1 and result.fallback_reason==code
    assert result.fallback==(code is not None)
    assert not result.ai_executed and not result.ai_success
    assert result.facts.money_facts==expected.changed_facts
    assert result.facts.unknown_information==expected.unknown_information
    assert result.facts.benefit_applied_krw==0 and data.model_dump_json()==original
    if code is None:assert result.explanation_source=='validated_test_double'
    else:assert result.document==expected
    assert 'PRIVATE_DO_NOT_ECHO' not in result.model_dump_json()
    captured=capsys.readouterr();assert 'PRIVATE_DO_NOT_ECHO' not in captured.out+captured.err
