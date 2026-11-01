"""독립 birth evaluator의 실제 비교와 결과 계약을 확인한다. 정책 트리는 실행하지 않는다."""

from dataclasses import replace
from datetime import date
import inspect
import json

import pytest

from backend.policy_engine import evaluate_birth_date_rule
from backend.policy_engine.errors import PolicyDataError, ProfileValidationError
from backend.policy_engine.facts import BirthFact, BirthSource
from backend.policy_engine.result_types import BirthDateCondition, BirthDateDetails, BirthDateReasonCode as BR
from backend.policy_engine.models import Status, UserProfile, EvaluationContext
from backend.policy_engine.evaluation_inputs import PolicyReferenceContext
from backend.policy_engine.specialized_rules import BirthDateRule


LOWER, UPPER = date(1998, 1, 10), date(1999, 1, 9)
REFS = ("SYNTH-SOURCE-002#birth-range", "SYNTH-SOURCE-001#birth-range", "SYNTH-SOURCE-002#birth-range")


def rule(lower=LOWER, upper=UPPER):
    return BirthDateRule("SYNTH-BIRTH", lower, upper, REFS)


@pytest.mark.parametrize(("day", "status", "reason"), [
    (date(1998, 1, 9), Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
    (date(1900, 1, 1), Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
    (LOWER, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (date(1998, 6, 15), Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (UPPER, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (date(1999, 1, 10), Status.FAIL, BR.BIRTH_DATE_AFTER_RANGE),
    (date(2100, 1, 1), Status.FAIL, BR.BIRTH_DATE_AFTER_RANGE),
])
@pytest.mark.parametrize("source", list(BirthSource))
def test_actual_comparison_boundaries_and_source_variants(day, status, reason, source):
    requirement = rule()
    output = evaluate_birth_date_rule(requirement, BirthFact(day, source))
    assert output.status is status and output.reason_code is reason
    assert output.evaluated_value is day
    assert output.expected_condition == BirthDateCondition(LOWER, UPPER)
    assert output.details == BirthDateDetails(source)
    assert output.rule_id == requirement.rule_id and output.evidence_refs is REFS
    assert output.missing_fields == ()


@pytest.mark.parametrize(("day", "status", "reason"), [
    (date(2000, 12, 31), Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
    (date(2001, 1, 1), Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (date(2001, 1, 2), Status.FAIL, BR.BIRTH_DATE_AFTER_RANGE),
])
def test_single_day_range(day, status, reason):
    output = evaluate_birth_date_rule(rule(date(2001, 1, 1), date(2001, 1, 1)), BirthFact(day, BirthSource.SELF_REPORTED))
    assert output.status is status and output.reason_code is reason


def test_leap_day_uses_native_date_and_alternative_rule_values():
    day = date(2000, 2, 29)
    output = evaluate_birth_date_rule(rule(day, day), BirthFact(day, BirthSource.SELF_REPORTED))
    assert output.status is Status.PASS and output.reason_code is BR.BIRTH_DATE_WITHIN_RANGE
    assert output.to_dict()["evaluated_value"] == "2000-02-29"


@pytest.mark.parametrize("source", [None, *list(BirthSource)])
def test_unknown_preserves_absent_fact_or_known_provenance(source):
    fact = None if source is None else BirthFact(None, source)
    output = evaluate_birth_date_rule(rule(), fact)
    assert output.status is Status.UNKNOWN and output.reason_code is BR.BIRTH_DATE_MISSING
    assert output.evaluated_value is None
    assert output.missing_fields == ("birth.birth_date",)
    assert output.details.birth_source is source
    assert output.evidence_refs is REFS
    assert output.expected_condition == BirthDateCondition(LOWER, UPPER)
    value = output.to_dict()
    assert value["evaluated_value"] is None and value["missing_fields"] == ["birth.birth_date"]
    assert value["details"] == {"birth_source": source.value if source is not None else None}
    assert json.loads(json.dumps(value)) == value


@pytest.mark.parametrize("day", [date(1990, 1, 1), date(1998, 6, 15), date(2010, 1, 1), None])
def test_source_only_changes_provenance(day):
    outputs = [evaluate_birth_date_rule(rule(), BirthFact(day, source)).to_dict() for source in BirthSource]
    for output, source in zip(outputs, BirthSource):
        assert output.pop("details") == {"birth_source": source.value}
    assert outputs[0] == outputs[1] == outputs[2]


def test_evaluator_generated_golden_json_and_determinism_without_input_mutation():
    requirement, fact = rule(), BirthFact(date(1998, 6, 15), BirthSource.SELF_REPORTED)
    before = (requirement.to_dict(), fact.to_dict())
    output = evaluate_birth_date_rule(requirement, fact)
    expected = {
        "rule_id": "SYNTH-BIRTH", "status": "PASS", "reason_code": "BIRTH_DATE_WITHIN_RANGE",
        "evaluated_value": "1998-06-15",
        "expected_condition": {"min_birth_date": "1998-01-10", "max_birth_date": "1999-01-09"},
        "details": {"birth_source": "SELF_REPORTED"}, "missing_fields": [], "evidence_refs": list(REFS),
    }
    assert output.to_dict() == expected
    repeated = evaluate_birth_date_rule(requirement, fact)
    assert output == repeated
    assert json.dumps(output.to_dict(), sort_keys=True) == json.dumps(repeated.to_dict(), sort_keys=True)
    snapshot = output.to_dict()
    snapshot["evidence_refs"].append("changed")
    snapshot["expected_condition"]["min_birth_date"] = "changed"
    assert output.to_dict() == expected
    assert (requirement.to_dict(), fact.to_dict()) == before


@pytest.mark.parametrize("value", [None, "rule", {}, [], BirthFact(None, BirthSource.SELF_REPORTED)])
def test_wrong_rule_is_data_error_even_with_missing_fact(value):
    with pytest.raises(PolicyDataError):
        evaluate_birth_date_rule(value, None)


@pytest.mark.parametrize("value", ["1998-06-15", {}, [], (), date(1998, 6, 15), rule(), UserProfile(age=24)])
def test_wrong_fact_type_is_error_not_unknown(value):
    with pytest.raises(ProfileValidationError):
        evaluate_birth_date_rule(rule(), value)


def test_api_has_only_rule_and_birth_fact_and_no_age_or_context_fallback():
    assert list(inspect.signature(evaluate_birth_date_rule).parameters) == ["rule", "birth_fact"]
    profile = UserProfile(age=24)
    context = EvaluationContext(date(2026, 10, 20), "synthetic-birth")
    reference = PolicyReferenceContext("SYNTH-POLICY", date(2026, 9, 1))
    for extra in [dict(profile=profile), dict(context=context), dict(reference_context=reference)]:
        with pytest.raises(TypeError):
            evaluate_birth_date_rule(rule(), None, **extra)
    assert evaluate_birth_date_rule(rule(), None).status is Status.UNKNOWN
    assert replace(profile, age=25).age == 25  # 어느 age 값도 함수에 전달하지 않는다.


def test_evaluation_does_not_access_file_or_network(monkeypatch):
    import builtins
    import socket
    import urllib.request

    requirement, fact = rule(), BirthFact(LOWER, BirthSource.SELF_REPORTED)

    def unexpected(*args, **kwargs):
        raise AssertionError("순수 평가에서 외부 I/O를 호출했습니다")

    monkeypatch.setattr(builtins, "open", unexpected)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    assert evaluate_birth_date_rule(requirement, fact).status is Status.PASS
