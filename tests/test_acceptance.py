import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from backend.policy_engine import Status, evaluate_policies


@pytest.mark.acceptance
def test_three_synthetic_policies_for_same_user(policy_set, profile, context):
    results = evaluate_policies(profile, policy_set, context)
    assert [(r.policy_id, r.overall_status) for r in results] == [
        ("SAMPLE-001", Status.PASS),
        ("SAMPLE-002", Status.FAIL),
        ("SAMPLE-003", Status.UNKNOWN),
    ]
    assert results[0].missing_fields == ()
    assert results[1].missing_fields == ()
    assert results[2].missing_fields == ("household_income",)
    income = next(r for r in results[2].rule_results if r.rule_id == "S003-INCOME")
    assert income.reason_code == "MISSING_FIELD"
    assert income.evaluated_value is None
    assert income.expected_condition.value == 3000000
    assert income.evidence_refs == ("data/synthetic/README.md#sample-003",)
    assert [r.display_status for r in results] == ["이용 가능성 높음", "현재 조건과 맞지 않음", "추가 확인 필요"]
    assert all(p.synthetic and p.test_only for p in policy_set.policies)


def test_result_contract_and_json_serialization(policy_set, profile, context):
    output = [r.to_dict() for r in evaluate_policies(profile, policy_set, context)]
    encoded = json.dumps(output, ensure_ascii=False, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded[2]["context"] == {
        "as_of": "2026-10-20", "dataset_version": "synthetic-v1", "engine_version": "m1.0",
    }
    assert decoded[2]["overall_status"] == "UNKNOWN"
    assert decoded[2]["missing_fields"] == ["household_income"]
    assert decoded[2]["rule_results"][-1]["expected_condition"]["fact_basis"]["unit"] == "KRW"
    assert "monthly_income" not in encoded
    assert "1500000" not in encoded
    assert context.as_of == date(2026, 10, 20)


@pytest.mark.acceptance
@pytest.mark.parametrize("args", [[], ["--summary"]])
def test_readme_sample_command(args):
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run(
        [sys.executable, "-m", "backend.policy_engine", *args], cwd=root,
        capture_output=True, text=True, encoding="utf-8", env=env, check=True,
    )
    result = json.loads(run.stdout)
    assert result["synthetic"] is True
    assert result["test_only"] is True
    assert [r["overall_status"] for r in result["results"]] == ["PASS", "FAIL", "UNKNOWN"]
