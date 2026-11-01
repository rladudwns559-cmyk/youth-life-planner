"""birth 결과를 수동 생성해 타입/조합/직렬화만 확인한다. evaluator는 없다."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timezone
from itertools import product
import json

import pytest

from backend.policy_engine import BirthDateCondition, BirthDateDetails, BirthDateReasonCode as BR
from backend.policy_engine.facts import BirthSource, RegistrationSource
from backend.policy_engine.models import (
    EvaluationContext, ExpectedCondition, Field, Operator, PolicyEvaluation,
    ReasonCode, RuleEvaluation, Status,
)
from backend.policy_engine.resolvers.resident_registration import ResidentRegistrationReasonCode as RR
from backend.policy_engine.result_types import (
    ReferenceDateSource, RegionSnapshot, ResidentRegistrationCondition,
    ResidentRegistrationDetails, ResultValidationError,
)


LOWER, UPPER = date(1998, 1, 10), date(1999, 1, 9)
CONDITION = BirthDateCondition(LOWER, UPPER)
REFS = ("SYNTH-SOURCE-001#birth-date-range",)
SOURCE = BirthSource.SELF_REPORTED


def result(**changes):
    values = dict(rule_id="SYNTH-BIRTH", status=Status.PASS, reason_code=BR.BIRTH_DATE_WITHIN_RANGE,
                  evaluated_value=date(1998, 6, 15), expected_condition=CONDITION,
                  missing_fields=(), evidence_refs=REFS, details=BirthDateDetails(SOURCE))
    values.update(changes)
    return RuleEvaluation(**values)


class DateSubclass(date):
    pass


@pytest.mark.parametrize(("lower", "upper"), [
    (LOWER, UPPER), (LOWER, LOWER), (date(2000, 2, 29), date(2000, 2, 29)), (date.min, date.max),
])
def test_valid_condition_ranges(lower, upper):
    condition = BirthDateCondition(lower, upper)
    assert condition.min_birth_date is lower and condition.max_birth_date is upper


@pytest.mark.parametrize("field", ["min_birth_date", "max_birth_date"])
@pytest.mark.parametrize("value", [
    None, "1998-01-10", 19980110, 0, 1.5, True, [], {},
    datetime(1998, 1, 10), datetime(1998, 1, 10, tzinfo=timezone.utc), DateSubclass(1998, 1, 10),
])
def test_condition_rejects_inexact_dates(field, value):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_DATE"):
        BirthDateCondition(**({"min_birth_date": LOWER, "max_birth_date": UPPER} | {field: value}))


def test_condition_rejects_reversed_range():
    with pytest.raises(ResultValidationError, match="INVALID_BIRTH_DATE_RANGE"):
        BirthDateCondition(UPPER, LOWER)


@pytest.mark.parametrize("source", [None, *list(BirthSource)])
def test_details_allow_only_known_birth_provenance_or_missing(source):
    assert BirthDateDetails(source).birth_source is source
    assert [field.name for field in fields(BirthDateDetails)] == ["birth_source"]


@pytest.mark.parametrize("value", ["SELF_REPORTED", 0, True, [], {}, *list(RegistrationSource)])
def test_details_reject_wrong_source_type(value):
    with pytest.raises(ResultValidationError, match="INVALID_BIRTH_SOURCE"):
        BirthDateDetails(value)


@pytest.mark.parametrize(("reason", "value", "status"), [
    (BR.BIRTH_DATE_WITHIN_RANGE, LOWER, Status.PASS),
    (BR.BIRTH_DATE_WITHIN_RANGE, UPPER, Status.PASS),
    (BR.BIRTH_DATE_BEFORE_RANGE, date(1998, 1, 9), Status.FAIL),
    (BR.BIRTH_DATE_AFTER_RANGE, date(1999, 1, 10), Status.FAIL),
])
@pytest.mark.parametrize("source", list(BirthSource))
def test_manual_known_results_with_all_sources(reason, value, status, source):
    leaf = result(status=status, reason_code=reason, evaluated_value=value, details=BirthDateDetails(source))
    assert leaf.status is status and leaf.reason_code is reason
    assert leaf.evaluated_value is value and leaf.details.birth_source is source
    assert leaf.missing_fields == ()


@pytest.mark.parametrize("source", [None, *list(BirthSource)])
def test_manual_unknown_preserves_missing_or_known_source(source):
    leaf = result(status=Status.UNKNOWN, reason_code=BR.BIRTH_DATE_MISSING,
                  evaluated_value=None, missing_fields=("birth.birth_date",), details=BirthDateDetails(source))
    assert leaf.evaluated_value is None
    assert leaf.to_dict()["details"] == {"birth_source": source.value if source is not None else None}


EXPECTED_STATUS = {
    BR.BIRTH_DATE_WITHIN_RANGE: Status.PASS,
    BR.BIRTH_DATE_BEFORE_RANGE: Status.FAIL,
    BR.BIRTH_DATE_AFTER_RANGE: Status.FAIL,
    BR.BIRTH_DATE_MISSING: Status.UNKNOWN,
}


@pytest.mark.parametrize(("status", "reason"), [
    (status, reason) for status, reason in product(Status, BR) if status is not EXPECTED_STATUS[reason]
])
def test_incompatible_status_reason_is_rejected(status, reason):
    with pytest.raises(ResultValidationError, match="RESULT_REASON_STATUS_MISMATCH"):
        result(status=status, reason_code=reason)


@pytest.mark.parametrize("value", [None, "1998-06-15", 19980615, True, datetime(1998, 6, 15), DateSubclass(1998, 6, 15)])
def test_known_birth_result_requires_exact_observed_date(value):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_VALUE"):
        result(evaluated_value=value)


@pytest.mark.parametrize("reason", [BR.BIRTH_DATE_BEFORE_RANGE, BR.BIRTH_DATE_AFTER_RANGE])
def test_fail_requires_observation_and_source(reason):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_VALUE"):
        result(status=Status.FAIL, reason_code=reason, evaluated_value=None)
    with pytest.raises(ResultValidationError, match="INVALID_BIRTH_SOURCE"):
        result(status=Status.FAIL, reason_code=reason, details=BirthDateDetails(None))


def test_pass_requires_provenance():
    with pytest.raises(ResultValidationError, match="INVALID_BIRTH_SOURCE"):
        result(details=BirthDateDetails(None))


@pytest.mark.parametrize("missing", [("birth.birth_date",), ("age",), ("birth",)])
@pytest.mark.parametrize(("status", "reason"), [
    (Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE), (Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
])
def test_known_result_cannot_have_missing_fields(missing, status, reason):
    with pytest.raises(ResultValidationError, match="INVALID_MISSING_FIELDS"):
        result(status=status, reason_code=reason, missing_fields=missing)


@pytest.mark.parametrize("missing", [(), ("birth",), ("birth_date",), ("birth.birth_date", "age"), ("birth.birth_date", "birth.birth_date")])
def test_unknown_requires_exact_canonical_missing_path(missing):
    with pytest.raises(ResultValidationError, match="INVALID_MISSING_FIELDS"):
        result(status=Status.UNKNOWN, reason_code=BR.BIRTH_DATE_MISSING,
               evaluated_value=None, missing_fields=missing)


def test_unknown_cannot_have_observed_date():
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_VALUE"):
        result(status=Status.UNKNOWN, reason_code=BR.BIRTH_DATE_MISSING, missing_fields=("birth.birth_date",))


@pytest.mark.parametrize("details", [None, {}, ResidentRegistrationDetails()])
def test_birth_requires_its_own_typed_details(details):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_DETAILS"):
        result(details=details)


@pytest.mark.parametrize("reason", [ReasonCode.CONDITION_MET, RR.RESIDENT_REGION_MATCH, "BIRTH_DATE_WITHIN_RANGE"])
def test_birth_requires_typed_birth_reason(reason):
    with pytest.raises(ResultValidationError):
        result(reason_code=reason)


@pytest.mark.parametrize("refs", [(), [], (None,), ("",)])
def test_birth_requires_nonempty_structural_policy_evidence(refs):
    with pytest.raises(ResultValidationError, match="INVALID_EVIDENCE_REFS"):
        result(evidence_refs=refs)


def test_birth_preserves_evidence_order_and_duplicates_without_registry_lookup():
    refs = ("synthetic:second", "synthetic:first", "synthetic:second")
    assert result(evidence_refs=refs).evidence_refs is refs


@pytest.mark.parametrize(("reason", "value"), [
    (BR.BIRTH_DATE_BEFORE_RANGE, date(2000, 1, 1)),
    (BR.BIRTH_DATE_AFTER_RANGE, date(1990, 1, 1)),
    (BR.BIRTH_DATE_WITHIN_RANGE, date(1990, 1, 1)),
])
def test_model_does_not_recompute_the_evaluators_date_comparison(reason, value):
    # M1.16C 기준: 구조 유효성이 실제 범위 비교의 정답을 보증하지 않는다.
    leaf = result(reason_code=reason, status=EXPECTED_STATUS[reason], evaluated_value=value)
    assert leaf.reason_code is reason and leaf.evaluated_value is value


def test_birth_additions_do_not_allow_date_or_birth_details_in_atomic_or_resident_results():
    atomic = dict(rule_id="A", status=Status.PASS, reason_code=ReasonCode.CONDITION_MET,
                  evaluated_value=24, expected_condition=ExpectedCondition(Field.AGE, Operator.EQ, 24, None),
                  missing_fields=(), evidence_refs=("synthetic:A",))
    for changes in [dict(evaluated_value=LOWER), dict(details=BirthDateDetails(SOURCE)), dict(reason_code=BR.BIRTH_DATE_WITHIN_RANGE)]:
        with pytest.raises(ResultValidationError):
            RuleEvaluation(**(atomic | changes))
    resident = dict(atomic, reason_code=RR.RESIDENT_REGION_MATCH,
                    expected_condition=ResidentRegistrationCondition(RegionSnapshot("GYEONGGI", "ANSAN"), ReferenceDateSource.APPLICATION_DATE),
                    evaluated_value=RegionSnapshot("GYEONGGI", "ANSAN"))
    for changes in [dict(evaluated_value=LOWER), dict(details=BirthDateDetails(SOURCE)), dict(reason_code=BR.BIRTH_DATE_WITHIN_RANGE)]:
        with pytest.raises(ResultValidationError):
            RuleEvaluation(**(resident | changes))


def test_golden_serialization_and_fresh_nested_values():
    leaf = result()
    expected = dict(rule_id="SYNTH-BIRTH", status="PASS", reason_code="BIRTH_DATE_WITHIN_RANGE",
                    evaluated_value="1998-06-15", expected_condition=dict(min_birth_date="1998-01-10", max_birth_date="1999-01-09"),
                    missing_fields=[], evidence_refs=list(REFS), details=dict(birth_source="SELF_REPORTED"))
    assert leaf.to_dict() == expected
    assert json.loads(json.dumps(leaf.to_dict())) == expected
    assert json.dumps(leaf.to_dict(), sort_keys=True) == json.dumps(result().to_dict(), sort_keys=True)
    snapshot = leaf.to_dict()
    snapshot["expected_condition"]["min_birth_date"] = "changed"
    snapshot["details"]["birth_source"] = "changed"
    snapshot["evidence_refs"].append("changed")
    assert leaf.to_dict() == expected


def test_policy_evaluation_preserves_birth_result_and_typed_reason():
    leaf = result()
    policy = PolicyEvaluation("SYNTH-POLICY", leaf.status, (leaf,), (), (leaf.reason_code,),
                              EvaluationContext(date(2026, 10, 20), "synthetic-birth-result"), "synthetic-1")
    assert policy.rule_results[0] is leaf
    value = policy.to_dict()
    assert value["rule_results"] == [leaf.to_dict()]
    assert value["reason_codes"] == ["BIRTH_DATE_WITHIN_RANGE"]
    assert value["context"]["as_of"] == "2026-10-20"
    assert json.loads(json.dumps(value)) == value


@pytest.mark.parametrize(("obj", "field", "value"), [
    (CONDITION, "min_birth_date", LOWER), (CONDITION, "max_birth_date", UPPER),
    (BirthDateDetails(SOURCE), "birth_source", None), (result(), "evaluated_value", None),
])
def test_birth_result_values_are_frozen(obj, field, value):
    with pytest.raises(FrozenInstanceError):
        setattr(obj, field, value)
    assert not hasattr(obj, "__dict__")


def test_result_schema_has_no_extra_birth_top_level_fields_or_duplicate_dates():
    assert [f.name for f in fields(BirthDateCondition)] == ["min_birth_date", "max_birth_date"]
    assert set(result().to_dict()) == {"rule_id", "status", "reason_code", "evaluated_value", "expected_condition", "missing_fields", "evidence_refs", "details"}
    assert replace(result()) == result()
