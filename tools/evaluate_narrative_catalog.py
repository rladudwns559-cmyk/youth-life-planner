"""고정30 후보 선택과 과거30응답의 오프라인 재생. 실제 모델 요청0."""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import sys

from backend.explanation.facts import build_facts, deterministic_document
from backend.explanation.narrative_catalog import prepare_catalog, parse_catalog, assemble_catalog, evaluate_synthetic_catalog
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/'docs/evidence/m3_8b_actual_evaluation.json'


def invariant(document, expected):
    assert document.changed_facts==expected.changed_facts
    assert document.unknown_information==expected.unknown_information
    assert document.next_actions==expected.next_actions
    assert [p.model_dump(exclude={'text'}) for p in document.policy_explanations]==[p.model_dump(exclude={'text'}) for p in expected.policy_explanations]


def evaluate():
    historical=json.loads(HISTORY.read_text(encoding='utf-8'))['actual_fixed30']['results']
    old={r['case_id']:r for r in historical};scenarios=cases();assert set(old)=={c['case_id'] for c in scenarios}
    rows=[]
    for case in scenarios:
        comparison=compare_scenarios(ComparisonInput(before=case['before'],after=case['after']))
        facts=build_facts(comparison);expected=deterministic_document(comparison,facts);prepared=prepare_catalog(facts,expected)
        combinations=(prepared.summary_options,)+tuple(p.texts for p in prepared.policy_options)
        count=0
        for selected in product(*combinations):
            raw=json.dumps(dict(summary=selected[0],policy_texts={p.slot:t for p,t in zip(prepared.policy_options,selected[1:],strict=True)}),ensure_ascii=False)
            document=assemble_catalog(prepared,parse_catalog(raw,prepared));invariant(document,expected);count+=1
        positive=evaluate_synthetic_catalog(facts,expected,raw)
        replay=evaluate_synthetic_catalog(facts,expected,old[case['case_id']]['actual_model_output'])
        assert not positive.fallback and positive.explanation_source=='validated_test_double' and not positive.ai_executed and not positive.ai_success
        assert replay.fallback and replay.document==expected
        rows.append(dict(case_id=case['case_id'],name=case['name'],original_fault_label_not_injected=case.get('fault'),
          summary_family=prepared.summary_family,policy_families=[dict(slot=p.slot,family=p.family,pending_before=p.pending_before,pending_after=p.pending_after) for p in prepared.policy_options],
          candidate_context=prepared.model_input(),context_bytes=len(prepared.model_input_json.encode('utf-8')),synthetic_combinations_accepted=count,
          canonical_document=expected.model_dump(),assembled_document=positive.document.model_dump(),rendered_core_preserved=True,
          explanation_source=positive.explanation_source,ai_executed=False,ai_success=False,
          historical_v1_passed=old[case['case_id']]['wire_validation']=='PASS',historical_replay=dict(fallback=replay.fallback,reason=replay.fallback_reason,diagnostic_code=replay.diagnostic_code,failure_stage=replay.failure_stage),
          actual_llm_calls=0))
    return dict(milestone='M3.8D',evaluation='fixed30-synthetic-catalog-and-historical-replay-v1',synthetic=True,test_only=True,
      actual_llm_calls=0,network_calls=0,provider_registered=False,human_semantic_reviews=0,
      historical_source=str(HISTORY),historical_source_sha256=hashlib.sha256(HISTORY.read_bytes()).hexdigest(),
      summary=dict(scenarios=len(rows),synthetic_candidate_combinations=sum(r['synthetic_combinations_accepted'] for r in rows),
        rendered_core_mismatches=0,historical_replays_rejected=sum(r['historical_replay']['fallback'] for r in rows),
        historical_v1_passed_now_membership_rejected=sum(r['historical_v1_passed'] and r['historical_replay']['diagnostic_code']=='TEXT_NOT_IN_REQUEST_CATALOG' for r in rows),
        historical_v1_rejected_still_rejected=sum(not r['historical_v1_passed'] for r in rows),
        context_min_bytes=min(r['context_bytes'] for r in rows),context_max_bytes=max(r['context_bytes'] for r in rows)),
      limitation='정해진 합성 후보 조립과 기존 실제응답의 오프라인 재생이다. 새 모델30 실행·자연어 전체 의미 정확도·사람 평가·사용자 효용 검증이 아니다.',results=rows)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=evaluate();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False,indent=2))
