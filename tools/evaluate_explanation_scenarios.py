"""고정 합성30개 재현 도구. 실제 LLM이 아닌 fault injection을 명시적으로 구분한다."""
import argparse,asyncio,copy,hashlib,json
from pathlib import Path
from backend.web.comparison_schemas import ComparisonInput
from backend.web.comparison import compare_scenarios
from backend.explanation.facts import build_facts,deterministic_document
from backend.explanation.service import explain
from backend.explanation.provider import MAX_PROVIDER_BYTES

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/'data/synthetic/explanation-scenarios-v1.json'

class TestOnlyProvider:
    kind='test_double';real_model=False;configured=True
    def __init__(self,fault='valid'):self.fault=fault;self.calls=0;self.last_payload=None;self.output=None
    async def generate(self,payload):
        self.calls+=1;self.last_payload=copy.deepcopy(payload)
        if self.fault=='offline':raise ConnectionError('SIMULATED')
        if self.fault=='timeout':raise TimeoutError('SIMULATED')
        if self.fault=='failure':raise RuntimeError('SENSITIVE_VALUE_MUST_NOT_LEAK')
        obj=copy.deepcopy(payload['template'])
        obj['summary']='계산된 결과와 추가로 확인할 정보를 함께 살펴보세요.'
        for p in obj['policy_explanations']:p['text']='평가된 조건과 확인이 필요한 정보를 함께 살펴보세요.'
        if self.fault=='money':obj['changed_facts'][0]['after']+=1
        if self.fault=='status':obj['policy_explanations'][0]['after_status']='FAIL'
        if self.fault=='unknown':obj['unknown_information']=[]
        if self.fault=='deadline':obj['summary']='신청기한은 내일까지입니다.'
        if self.fault=='recommend':obj['summary']='이 상품을 추천합니다.'
        if self.fault=='action':obj['next_actions'].append({'policy_id':'FAKE','field':'FAKE','text':'확인해 주세요.'})
        self.output=('not JSON' if self.fault=='json' else 'x'*(MAX_PROVIDER_BYTES+1) if self.fault=='length' else json.dumps(obj,ensure_ascii=False))
        return self.output

def cases():
    data=json.loads(CASES.read_text(encoding='utf-8'))
    assert data['synthetic'] is True and data['test_only'] is True and len(data['cases'])==30
    return data['cases']

async def evaluate_case(case):
    data=ComparisonInput(before=case['before'],after=case['after'])
    comparison=compare_scenarios(data)
    facts=build_facts(comparison)
    deterministic=deterministic_document(comparison,facts)
    fault=case.get('fault','none')
    provider=TestOnlyProvider(fault) if fault!='none' else None
    result=await explain(data,provider=provider)
    if 'expected_policy' in case:
        pid,b,a=case['expected_policy'];p=next(p for p in facts.policy_facts if p.policy_id==pid)
        assert (p.before_status,p.after_status)==(b,a)
    for key,actual in [('expected_disposable_delta',comparison.numeric_deltas.disposable_after_policy),
      ('expected_savable_delta',comparison.numeric_deltas.savable_amount),('expected_after_disposable',comparison.after.cashflow['disposable_after_policy']),
      ('expected_after_savable',comparison.after.cashflow['savable_amount'])]:
        if key in case:assert actual==case[key],(case['case_id'],key,actual)
    if 'expected_fallback_reason' in case:assert result.fallback_reason==case['expected_fallback_reason']
    assert result.document.changed_facts==facts.money_facts
    assert result.document.policy_explanations==facts.policy_facts # every fixed30 case uses fallback
    assert result.document.unknown_information==facts.unknown_information
    assert result.fallback and not result.ai_success and not result.ai_executed
    return dict(case_id=case['case_id'],name=case['name'],synthetic=True,
        python_confirmed_result=comparison.model_dump(),deterministic_explanation=deterministic.model_dump(),
        actual_ai_output=None,actual_ai_executed=False,
        test_double_output=provider.output if provider else None,test_double_calls=provider.calls if provider else 0,
        status_match=True,amount_match=True,unknown_match=True,error_detected=fault not in ('none',),
        fallback=result.fallback,fallback_reason=result.fallback_reason,explanation_source=result.explanation_source)

async def run():
    results=[await evaluate_case(case) for case in cases()]
    return dict(evaluation_version='m3.6-fixed30-v1',synthetic=True,test_only=True,scenario_count=30,
        deterministic_evaluated=30,actual_llm_evaluated=0,test_double_cases=sum(r['test_double_calls']>0 for r in results),
        status_mismatches=0,amount_mismatches=0,unknown_mismatches=0,results=results,
        limitation='실제 LLM 충실성30건 또는 사용자 이해도 평가가 아니다. 구조·핵심 사실 및 제한된 표현 검증이며 자연어 전체 의미 보장 아님.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=asyncio.run(run());args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='results'},ensure_ascii=False,indent=2))
