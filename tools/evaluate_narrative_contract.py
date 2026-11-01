"""고정30+합성 fixture만 평가. 실제 모델/네트워크/Provider를 호출하지 않는다."""
import argparse
import json
import sys
from pathlib import Path

from backend.explanation.facts import build_facts, deterministic_document
from backend.explanation.narrative_contract import project_facts, evaluate_synthetic_narrative
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from tools.evaluate_explanation_scenarios import cases

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/narrative_response_v1.json'


def evaluate():
    raw = FIXTURE.read_text(encoding='utf-8')
    rows = []
    for case in cases():
        comparison = compare_scenarios(ComparisonInput(before=case['before'], after=case['after']))
        facts = build_facts(comparison)
        expected = deterministic_document(comparison, facts)
        projection = project_facts(facts)
        result = evaluate_synthetic_narrative(facts, expected, raw)
        assert not result.fallback and result.validation_passed and not result.ai_executed and not result.ai_success
        assert result.document.changed_facts == expected.changed_facts
        assert result.document.unknown_information == expected.unknown_information
        assert result.document.next_actions == expected.next_actions
        assert [p.model_dump(exclude={'text'}) for p in result.document.policy_explanations] == [p.model_dump(exclude={'text'}) for p in expected.policy_explanations]
        rows.append(dict(case_id=case['case_id'], name=case['name'], model_input=projection.model_input(),
                         projection_bytes=len(projection.model_input_json.encode('utf-8')),
                         fixture_bytes=len(raw.encode('utf-8')), server_slots=[dict(slot=s.slot, policy_id=s.policy_id) for s in projection.slots],
                         canonical_document=expected.model_dump(), assembled_document=result.document.model_dump(),
                         core_preserved=True, unknown_preserved=True, validator_passed=result.validation_passed,
                         explanation_source=result.explanation_source, actual_llm_output=None, actual_llm_calls=0))
    sizes = [r['projection_bytes'] for r in rows]
    return dict(evaluation='m3.8a-fixed30-synthetic-fixture-v1', synthetic=True, test_only=True,
                scenario_count=len(rows), fixture_passed=len(rows), actual_llm_calls=0, llm_quality_evaluation=False,
                projection_min_bytes=min(sizes), projection_max_bytes=max(sizes), fixture_bytes=len(raw.encode('utf-8')),
                limitation='구조/서버 원본 불변/기존 validator의 합성 시험. 실제 LLM 성능·한국어 의미 정확성 증거가 아니다.', results=rows)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'results'}, ensure_ascii=False, indent=2))
