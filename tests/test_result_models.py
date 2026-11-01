"""M1.6D 결과 표현 계약. Resolver 호출/Adapter 변환은 하지 않는다."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime
import json

import pytest

from backend.policy_engine.models import (
    EvaluationContext, ExpectedCondition, Field, GroupCondition, GroupOperator,
    Operator, PolicyEvaluation, ReasonCode, RuleEvaluation, Status, UserProfile,
)
from backend.policy_engine.facts import RegionRef, RegistrationSource, ResidentRegistrationFact
from backend.policy_engine.resolvers.resident_registration import ResidentRegistrationReasonCode as RR
from backend.policy_engine.result_types import (
    EvaluationEvidence, EvidenceFactType, ReferenceDateSource, RegionSnapshot,
    ResidentRegistrationCondition, ResidentRegistrationDetails, ResultValidationError,
)


DAY = date(2026, 11, 10)
ANSAN = RegionSnapshot("GYEONGGI", "ANSAN")
SUWON = RegionSnapshot("GYEONGGI", "SUWON")
CONDITION = ResidentRegistrationCondition(ANSAN, ReferenceDateSource.APPLICATION_DATE)


def atomic(value=24, missing=()):
    return RuleEvaluation("A", Status.PASS, ReasonCode.CONDITION_MET, value,
                          ExpectedCondition(Field.AGE, Operator.EQ, 24, None),
                          missing, ("synthetic:A",))


def evidence(source=RegistrationSource.SELF_REPORTED, region=ANSAN):
    return EvaluationEvidence(source, DAY, region)


def resident(**changes):
    args = dict(rule_id="R", status=Status.PASS, reason_code=RR.RESIDENT_REGION_MATCH,
                evaluated_value=ANSAN, expected_condition=CONDITION, missing_fields=(),
                evidence_refs=("synthetic:R",),
                details=ResidentRegistrationDetails(DAY, (evidence(),)))
    args.update(changes)
    return RuleEvaluation(**args)


def policy(result, reasons=None):
    return PolicyEvaluation("P", result.status, (result,), result.missing_fields,
                            reasons if reasons is not None else (result.reason_code,),
                            EvaluationContext(date(2026, 11, 20), "synthetic-v1"), "1")


def test_legacy_positional_keyword_equality_and_repr():
    a = atomic()
    b = RuleEvaluation(rule_id="A", status=Status.PASS, reason_code=ReasonCode.CONDITION_MET,
                       evaluated_value=24, expected_condition=ExpectedCondition(Field.AGE, Operator.EQ, 24, None),
                       missing_fields=(), evidence_refs=("synthetic:A",))
    assert a == b == replace(a, details=None)
    assert a.details is None
    assert repr(a) == (
        "RuleEvaluation(rule_id='A', status=<Status.PASS: 'PASS'>, "
        "reason_code=<ReasonCode.CONDITION_MET: 'CONDITION_MET'>, evaluated_value=24, "
        "expected_condition=ExpectedCondition(field=<Field.AGE: 'age'>, operator=<Operator.EQ: 'eq'>, "
        "value=24, fact_basis=None), missing_fields=(), evidence_refs=('synthetic:A',))"
    )


@pytest.mark.parametrize("value", [0, 24, False, True, "안산시", None])
def test_legacy_scalar_values_remain_exact(value):
    result = atomic(value)
    assert type(result.evaluated_value) is type(value)
    assert result.to_dict()["evaluated_value"] == value


def test_legacy_serialization_golden_and_missing_paths():
    r = atomic(missing=("household_income", "region"))
    assert r.to_dict() == {
        "rule_id": "A", "status": "PASS", "reason_code": "CONDITION_MET",
        "evaluated_value": 24,
        "expected_condition": {"field": "age", "operator": "eq", "value": 24, "fact_basis": None},
        "missing_fields": ["household_income", "region"], "evidence_refs": ["synthetic:A"],
    }
    assert policy(r).to_dict() == {
        "policy_id": "P", "overall_status": "PASS", "rule_results": [r.to_dict()],
        "missing_fields": ["household_income", "region"], "reason_codes": ["CONDITION_MET"],
        "context": {"as_of": "2026-11-20", "dataset_version": "synthetic-v1", "engine_version": "m1.0"},
        "rule_version": "1", "display_status": "이용 가능성 높음",
    }


def test_legacy_group_result_unchanged():
    condition = GroupCondition(GroupOperator.ALL, ("A",))
    r = RuleEvaluation("G", Status.PASS, ReasonCode.ALL_PASS, None, condition, (), ())
    assert r.expected_condition is condition
    assert r.to_dict()["expected_condition"] == {"operator": "ALL", "child_ids": ["A"]}
    assert "details" not in r.to_dict()


@pytest.mark.parametrize("source", list(RegistrationSource))
def test_structured_serialization_with_all_sources(source):
    r = resident(details=ResidentRegistrationDetails(DAY, (evidence(source),)))
    body = policy(r).to_dict()
    leaf = body["rule_results"][0]
    assert leaf["evaluated_value"] == {"sido": "GYEONGGI", "sigungu": "ANSAN"}
    assert leaf["expected_condition"] == {
        "required_region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "reference_date_source": "APPLICATION_DATE",
    }
    assert leaf["details"] == {"reference_date": "2026-11-10", "evidence": [{
        "source": source.value, "fact_as_of_date": "2026-11-10",
        "region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "fact_type": "RESIDENT_REGISTRATION", "field_path": "resident_registration.region",
    }]}
    assert body["context"]["as_of"] == "2026-11-20"
    assert "evaluation_date" not in leaf["details"]
    assert json.loads(json.dumps(body, ensure_ascii=False)) == body


@pytest.mark.parametrize(("reason", "status", "value", "missing"), [
    (RR.RESIDENT_REGION_MATCH, Status.PASS, ANSAN, ()),
    (RR.RESIDENT_REGION_MISMATCH, Status.FAIL, SUWON, ()),
    (RR.RESIDENT_REGISTRATION_MISSING, Status.UNKNOWN, None, ("resident_registration",)),
    (RR.RESIDENT_REGION_MISSING, Status.UNKNOWN, None, ("resident_registration.region",)),
    (RR.RESIDENT_REGISTRATION_DATE_MISSING, Status.UNKNOWN, None, ("resident_registration.as_of_date",)),
    (RR.RESIDENT_REGISTRATION_DATE_UNPROVEN, Status.UNKNOWN, None, ()),
    (RR.RESIDENT_REFERENCE_DATE_MISSING, Status.UNKNOWN, None, ("reference_date",)),
    (RR.RESIDENT_REFERENCE_DATE_IN_FUTURE, Status.UNKNOWN, None, ()),
])
def test_resolver_reasons_and_missing_paths_survive(reason, status, value, missing):
    r = resident(reason_code=reason, status=status, evaluated_value=value, missing_fields=missing, details=None)
    assert r.reason_code is reason
    assert r.missing_fields == missing
    body = policy(r).to_dict()
    assert body["reason_codes"] == [reason.value]
    assert body["rule_results"][0]["missing_fields"] == list(missing)


def test_mixed_reason_enums_in_policy_result():
    r = resident()
    reasons = (ReasonCode.ALL_PASS, RR.RESIDENT_REGION_MATCH)
    assert policy(r, reasons).to_dict()["reason_codes"] == ["ALL_PASS", "RESIDENT_REGION_MATCH"]


def test_optional_detail_reference_and_evidence():
    assert resident(details=None).details is None
    detail = ResidentRegistrationDetails()
    assert detail.reference_date is None and detail.evidence == ()
    r = resident(status=Status.UNKNOWN, reason_code=RR.RESIDENT_REFERENCE_DATE_MISSING,
                 evaluated_value=None, details=detail, missing_fields=("reference_date",))
    assert r.to_dict()["details"] == {"reference_date": None, "evidence": []}


def test_date_only_selected_evidence_and_null_observation():
    r = resident(status=Status.UNKNOWN, reason_code=RR.RESIDENT_REGION_MISSING,
                 evaluated_value=None, missing_fields=("resident_registration.region",),
                 details=ResidentRegistrationDetails(DAY, (evidence(region=None),)))
    e = r.to_dict()["details"]["evidence"][0]
    assert e["region"] is None and e["fact_as_of_date"] == "2026-11-10"


@pytest.mark.parametrize(("sido", "sigungu"), [
    (None, "ANSAN"), ("GYEONGGI", None), ("SEOUL", "ANSAN"),
    ("GYEONGGI", "OTHER"), ([], "ANSAN"), ("경기도", "안산시"),
])
def test_invalid_region_snapshot(sido, sigungu):
    with pytest.raises(ResultValidationError) as err:
        RegionSnapshot(sido, sigungu)
    assert err.value.code == "INVALID_RESULT_REGION"


@pytest.mark.parametrize("bad", [None, "SELF_REPORTED", "OFFICIAL_DATA", {}, UserProfile()])
def test_invalid_evidence_source(bad):
    with pytest.raises(ResultValidationError, match="INVALID_EVIDENCE_SOURCE"):
        EvaluationEvidence(bad, DAY, ANSAN)


@pytest.mark.parametrize("bad", ["2026-11-10", datetime(2026, 11, 10), 0, True, []])
@pytest.mark.parametrize("target", ["reference", "fact"])
def test_invalid_date_types(bad, target):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_DATE"):
        if target == "reference":
            ResidentRegistrationDetails(bad)
        else:
            EvaluationEvidence(RegistrationSource.SELF_REPORTED, bad, ANSAN)


@pytest.mark.parametrize("bad", [[evidence()], {"fact": evidence()}, (UserProfile(),), (object(),)])
def test_mutable_or_untyped_evidence_rejected(bad):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_EVIDENCE"):
        ResidentRegistrationDetails(DAY, bad)


@pytest.mark.parametrize(("field", "bad"), [
    ("evaluated_value", {"sido": "GYEONGGI", "sigungu": "ANSAN"}),
    ("evaluated_value", RegionRef("GYEONGGI", "ANSAN")),
    ("evaluated_value", UserProfile()), ("evaluated_value", []),
    ("details", {}), ("details", UserProfile()),
    ("missing_fields", ["resident_registration"]),
    ("missing_fields", ("주민등록 지역을 입력해주세요",)),
    ("missing_fields", ("resident_registration..region",)),
    ("evidence_refs", ["synthetic:R"]),
    ("reason_code", "RESIDENT_REGION_MATCH"), ("reason_code", "DATA_ERROR"),
    ("status", "UNKNOWN"), ("status", "DATA_ERROR"),
])
def test_invalid_rule_result_fields(field, bad):
    with pytest.raises(ResultValidationError):
        resident(**{field: bad})


@pytest.mark.parametrize("bad", [RegionRef("GYEONGGI", "ANSAN"), {}, None])
def test_expected_region_requires_snapshot(bad):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_REGION"):
        ResidentRegistrationCondition(bad, ReferenceDateSource.APPLICATION_DATE)


def test_reference_binding_requires_enum():
    with pytest.raises(ResultValidationError, match="INVALID_REFERENCE_DATE_SOURCE"):
        ResidentRegistrationCondition(ANSAN, "APPLICATION_DATE")


@pytest.mark.parametrize(("field", "bad"), [
    ("fact_type", "RESIDENT_REGISTRATION"), ("fact_type", "BIRTH"),
    ("field_path", "source_document_id"), ("field_path", "주민등록 지역"),
    ("region", ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), DAY, RegistrationSource.SELF_REPORTED)),
])
def test_invalid_evidence_contract(field, bad):
    with pytest.raises(ResultValidationError):
        replace(evidence(), **{field: bad})


@pytest.mark.parametrize("reference", [None, date(2026, 10, 1)])
def test_evidence_must_match_policy_reference_date(reference):
    with pytest.raises(ResultValidationError, match="RESULT_EVIDENCE_DATE_MISMATCH"):
        ResidentRegistrationDetails(reference, (evidence(),))


def test_conflicting_result_evidence_is_error_not_unknown():
    with pytest.raises(ResultValidationError, match="CONFLICTING_RESULT_EVIDENCE"):
        ResidentRegistrationDetails(DAY, (evidence(), evidence(region=SUWON)))


def test_observed_value_must_match_selected_evidence():
    with pytest.raises(ResultValidationError, match="RESULT_EVIDENCE_VALUE_MISMATCH"):
        resident(evaluated_value=SUWON)


def test_reason_status_and_condition_must_agree():
    with pytest.raises(ResultValidationError, match="RESULT_REASON_STATUS_MISMATCH"):
        resident(status=Status.UNKNOWN)
    with pytest.raises(ResultValidationError, match="RESULT_REASON_CONDITION_MISMATCH"):
        resident(reason_code=ReasonCode.CONDITION_MET)
    with pytest.raises(ResultValidationError, match="RESULT_DETAIL_CONDITION_MISMATCH"):
        replace(atomic(), details=ResidentRegistrationDetails())


@pytest.mark.parametrize(("status", "reason"), [
    (Status.PASS, RR.RESIDENT_REGION_MATCH), (Status.FAIL, RR.RESIDENT_REGION_MISMATCH),
])
def test_decided_resident_result_requires_observed_region(status, reason):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_VALUE"):
        resident(status=status, reason_code=reason, evaluated_value=None, details=None)


def test_policy_rejects_free_text_reasons_and_mutable_results():
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_REASON"):
        policy(resident(), ("RESIDENT_REGION_MATCH",))
    with pytest.raises(ResultValidationError, match="INVALID_RULE_RESULTS"):
        replace(policy(atomic()), rule_results=[atomic()])


@pytest.mark.parametrize("obj", [ANSAN, CONDITION, evidence(), ResidentRegistrationDetails(DAY, (evidence(),)), resident()])
def test_all_new_layers_are_frozen(obj):
    with pytest.raises(FrozenInstanceError):
        setattr(obj, fields(obj)[0].name, None)


def test_serialized_mutation_cannot_change_result():
    r = resident()
    body = r.to_dict()
    body["details"]["evidence"][0]["region"]["sigungu"] = "SUWON"
    body["details"]["evidence"].clear()
    assert r.details.evidence == (evidence(),)
    assert r.evaluated_value == ANSAN


def test_minimal_evidence_contains_no_profile_or_fact_object():
    e = evidence()
    assert {f.name for f in fields(e)} == {"source", "fact_as_of_date", "region", "fact_type", "field_path"}
    assert not hasattr(e, "__dict__")
    with pytest.raises(TypeError):
        EvaluationEvidence(RegistrationSource.SELF_REPORTED, DAY, ANSAN, user_profile=UserProfile())
    data = resident().to_dict()
    assert "monthly_income" not in json.dumps(data)
    assert not isinstance(e.region, (RegionRef, ResidentRegistrationFact))


def test_future_extension_boundary_without_future_resolvers():
    # 날짜/기간은 원시 불변 date/int로 표현 가능하다. 미래 의미 타입은 아직 등록하지 않는다.
    assert type(evidence().fact_as_of_date) is date
    assert atomic(36).evaluated_value == 36
    assert atomic(120).evaluated_value == 120
    assert [v.value for v in EvidenceFactType] == ["RESIDENT_REGISTRATION"]
    with pytest.raises(ResultValidationError):
        resident(details={"income": 100, "basis": "arbitrary"})


def test_error_does_not_echo_sensitive_values():
    with pytest.raises(ResultValidationError) as err:
        RegionSnapshot("private-region-value", "private-city-value")
    assert "private" not in str(err.value)
