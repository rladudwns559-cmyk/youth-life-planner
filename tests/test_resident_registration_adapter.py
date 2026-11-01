"""M1.6E: 표현 변환 단위 테스트와 Fact→Resolver→Adapter 작은 통합 테스트."""

from dataclasses import asdict, FrozenInstanceError, replace
from datetime import date
from itertools import permutations
import json

import pytest

from backend.policy_engine.adapters import adapt_resident_registration_resolution as adapt
from backend.policy_engine.facts import (
    RegionRef, RegistrationSource, ResidentRegistrationFact, ResidentRegistrationValidationError,
)
from backend.policy_engine.models import Status
from backend.policy_engine.resolvers.resident_registration import (
    ResidentRegistrationReasonCode as Reason,
    ResidentRegistrationResolution, resolve_resident_registration,
)
from backend.policy_engine.result_types import (
    EvidenceFactType, ReferenceDateSource, RegionSnapshot, ResidentRegistrationCondition,
    ResultValidationError,
)


DAY = date(2026, 11, 10)
ANSAN = RegionRef("GYEONGGI", "ANSAN")
SUWON = RegionRef("GYEONGGI", "SUWON")
CONDITION = ResidentRegistrationCondition(RegionSnapshot("GYEONGGI", "ANSAN"), ReferenceDateSource.APPLICATION_DATE)
REFS = ("synthetic:document#resident", "synthetic:rule-version-1")


def fact(region=ANSAN, day=DAY, source=RegistrationSource.SELF_REPORTED):
    return ResidentRegistrationFact(region, day, source)


def resolution():
    # 공개 dataclass 생성자는 의미 검증이 없으므로 구조 불일치도 replace로 실제 생성 가능하다.
    return ResidentRegistrationResolution(
        Status.PASS, Reason.RESIDENT_REGION_MATCH, ANSAN, DAY, DAY,
        ANSAN, DAY, (), (fact(),),
    )


def convert(value, **changes):
    args = dict(rule_id="TEST_RESIDENT", resolution=value, policy_condition=CONDITION, evidence_refs=REFS)
    args.update(changes)
    return adapt(**args)


@pytest.mark.parametrize(("status", "reason", "region"), [
    (Status.PASS, Reason.RESIDENT_REGION_MATCH, ANSAN),
    (Status.FAIL, Reason.RESIDENT_REGION_MISMATCH, SUWON),
])
def test_decided_status_reason_and_structured_values(status, reason, region):
    value = replace(resolution(), status=status, reason_code=reason, resolved_region=region, used_facts=(fact(region),))
    output = convert(value)
    assert output.status is status and output.reason_code is reason
    assert output.evaluated_value == RegionSnapshot(region.sido, region.sigungu)
    assert output.expected_condition == CONDITION
    assert output.rule_id == "TEST_RESIDENT"
    assert output.evidence_refs is REFS
    assert output.details.reference_date == DAY
    e = output.details.evidence[0]
    assert e.fact_as_of_date == DAY and e.source is RegistrationSource.SELF_REPORTED
    assert e.region == output.evaluated_value
    assert e.fact_type is EvidenceFactType.RESIDENT_REGISTRATION
    assert e.field_path == "resident_registration.region"


@pytest.mark.parametrize(("reason", "missing", "reference", "used", "fact_day"), [
    (Reason.RESIDENT_REGISTRATION_MISSING, ("resident_registration",), DAY, (), None),
    (Reason.RESIDENT_REGION_MISSING, ("resident_registration.region",), DAY, (fact(None),), DAY),
    (Reason.RESIDENT_REGISTRATION_DATE_MISSING, ("resident_registration.as_of_date",), DAY, (), None),
    (Reason.RESIDENT_REGISTRATION_DATE_UNPROVEN, (), DAY, (), None),
    (Reason.RESIDENT_REFERENCE_DATE_MISSING, ("reference_date",), None, (), None),
    (Reason.RESIDENT_REFERENCE_DATE_IN_FUTURE, (), date(2026, 11, 11), (), None),
])
def test_unknown_reason_missing_reference_and_absence_preserved(reason, missing, reference, used, fact_day):
    value = replace(resolution(), status=Status.UNKNOWN, reason_code=reason, resolved_region=None,
                    reference_date=reference, fact_as_of_date=fact_day, missing_fields=missing, used_facts=used)
    output = convert(value)
    assert output.status is Status.UNKNOWN
    assert output.reason_code is reason
    assert output.missing_fields is missing
    assert output.evaluated_value is None
    assert output.details.reference_date == reference
    assert len(output.details.evidence) == len(used)
    if not used:
        assert output.details.evidence == ()
    else:
        assert output.details.evidence[0].region is None
        assert output.details.evidence[0].fact_as_of_date == DAY


@pytest.mark.parametrize("source", list(RegistrationSource))
def test_source_metadata_does_not_change_result(source):
    output = convert(replace(resolution(), used_facts=(fact(source=source),)))
    assert output.status is Status.PASS
    assert output.reason_code is Reason.RESIDENT_REGION_MATCH
    assert output.details.evidence[0].source is source


def test_no_eligibility_recalculation_even_when_observed_region_known():
    # 직접 생성 가능한 결과의 상태를 변환기가 다시 판정하지 않는다.
    value = replace(resolution(), status=Status.UNKNOWN, reason_code=Reason.RESIDENT_REGISTRATION_DATE_UNPROVEN)
    output = convert(value)
    assert output.status is Status.UNKNOWN
    assert output.reason_code is Reason.RESIDENT_REGISTRATION_DATE_UNPROVEN
    assert output.evaluated_value == CONDITION.required_region


def test_no_region_comparison_to_recompute_status():
    # 의미적으로 잘못 만들어진 결과라도 Adapter는 자격 판정을 다시 수행하지 않는다.
    value = replace(resolution(), resolved_region=SUWON, used_facts=(fact(SUWON),))
    output = convert(value)
    assert output.status is Status.PASS
    assert output.reason_code is Reason.RESIDENT_REGION_MATCH
    assert output.evaluated_value == RegionSnapshot("GYEONGGI", "SUWON")


def test_empty_policy_evidence_allowed_and_user_evidence_separate():
    output = adapt(rule_id="R", resolution=resolution(), policy_condition=CONDITION)
    assert output.evidence_refs == ()
    assert output.details.evidence[0].source is RegistrationSource.SELF_REPORTED


@pytest.mark.parametrize("value", [None, {}, "resolution", RuntimeError("not a result")])
def test_invalid_resolution_type(value):
    with pytest.raises(ResultValidationError) as err:
        convert(value)
    assert (err.value.code, err.value.field) == ("INVALID_RESOLUTION", "resolution")


@pytest.mark.parametrize("bad", [None, {}, "resident_condition"])
def test_invalid_condition_type(bad):
    with pytest.raises(ResultValidationError, match="INVALID_POLICY_CONDITION"):
        convert(resolution(), policy_condition=bad)


@pytest.mark.parametrize("bad", [None, "", "   ", 24])
def test_invalid_rule_id_uses_existing_result_validation(bad):
    with pytest.raises(ResultValidationError, match="INVALID_RESULT_RULE_ID"):
        convert(resolution(), rule_id=bad)


def test_mismatched_policy_requirement_is_contract_error():
    other = ResidentRegistrationCondition(RegionSnapshot("GYEONGGI", "SUWON"), ReferenceDateSource.APPLICATION_DATE)
    with pytest.raises(ResultValidationError) as err:
        convert(resolution(), policy_condition=other)
    assert (err.value.code, err.value.field) == ("RESOLUTION_CONDITION_MISMATCH", "required_region")


@pytest.mark.parametrize(("changes", "code"), [
    ({"status": "PASS"}, "INVALID_RESULT_STATUS"),
    ({"status": "DATA_ERROR"}, "INVALID_RESULT_STATUS"),
    ({"reason_code": "RESIDENT_REGION_MATCH"}, "INVALID_RESULT_REASON"),
    ({"status": Status.UNKNOWN}, "RESULT_REASON_STATUS_MISMATCH"),
    ({"used_facts": [fact()]}, "INVALID_RESOLUTION_EVIDENCE"),
    ({"used_facts": (object(),)}, "INVALID_RESOLUTION_EVIDENCE"),
    ({"used_facts": ()}, "RESOLUTION_EVIDENCE_MISMATCH"),
    ({"fact_as_of_date": None}, "RESOLUTION_EVIDENCE_MISMATCH"),
    ({"resolved_region": None}, "RESOLUTION_EVIDENCE_MISMATCH"),
    ({"resolved_region": "ANSAN", "used_facts": (), "fact_as_of_date": None}, "RESOLUTION_EVIDENCE_MISMATCH"),
    ({"reference_date": None}, "RESULT_EVIDENCE_DATE_MISMATCH"),
    ({"required_region": "ANSAN"}, "INVALID_RESOLUTION_REGION"),
])
def test_directly_constructible_resolution_contract_errors(changes, code):
    value = replace(resolution(), **changes)
    with pytest.raises(ResultValidationError) as err:
        convert(value)
    assert err.value.code == code


def test_resolution_region_wrong_type_with_evidence_rejected():
    # 공통 메타데이터와 evidence의 정합성 오류가 자격 UNKNOWN으로 감춰지지 않는다.
    with pytest.raises(ResultValidationError):
        convert(replace(resolution(), resolved_region="ANSAN"))


def test_selected_evidence_order_is_preserved_not_ranked():
    selected = (fact(source=RegistrationSource.SELF_REPORTED), fact(source=RegistrationSource.OFFICIAL_DATA))
    output = convert(replace(resolution(), used_facts=selected))
    assert tuple(e.source for e in output.details.evidence) == tuple(f.source for f in selected)


def test_repeatability_immutability_and_minimal_evidence():
    value = resolution()
    before = (asdict(value), asdict(CONDITION))
    first, second = convert(value), convert(value)
    assert first == second
    assert first.to_dict() == second.to_dict()
    assert repr(first) == repr(second)
    assert json.dumps(first.to_dict(), ensure_ascii=False) == json.dumps(second.to_dict(), ensure_ascii=False)
    assert before == (asdict(value), asdict(CONDITION))
    assert first.expected_condition is CONDITION
    with pytest.raises(FrozenInstanceError):
        first.details.evidence[0].region.sigungu = "SUWON"
    serialized = first.to_dict()
    serialized["details"]["evidence"].clear()
    assert first.details.evidence
    assert set(first.to_dict()["details"]["evidence"][0]) == {
        "source", "fact_as_of_date", "region", "fact_type", "field_path",
    }


@pytest.mark.parametrize(("facts", "status", "reason"), [
    ((fact(),), Status.PASS, Reason.RESIDENT_REGION_MATCH),
    ((fact(SUWON),), Status.FAIL, Reason.RESIDENT_REGION_MISMATCH),
    ((), Status.UNKNOWN, Reason.RESIDENT_REGISTRATION_MISSING),
])
def test_fact_resolver_adapter_integration(facts, status, reason):
    result = resolve_resident_registration(facts, required_region=ANSAN, reference_date=DAY, evaluation_date=DAY)
    output = convert(result)
    assert output.status is status and output.reason_code is reason
    assert output.details.reference_date == DAY
    assert len(output.details.evidence) == len(result.used_facts)


def test_resolver_error_stops_pipeline_before_adapter():
    called = []

    def next_stage(value):
        called.append(value)
        return convert(value)

    with pytest.raises(ResidentRegistrationValidationError) as err:
        next_stage(resolve_resident_registration(
            (fact(), fact(SUWON)), required_region=ANSAN, reference_date=DAY, evaluation_date=DAY,
        ))
    assert err.value.code == "CONFLICTING_RESIDENT_REGISTRATION_FACTS"
    assert called == []


def test_unrelated_historical_conflict_still_errors():
    old = date(2026, 1, 1)
    with pytest.raises(ResidentRegistrationValidationError, match="CONFLICTING_RESIDENT_REGISTRATION_FACTS"):
        convert(resolve_resident_registration(
            (fact(), fact(ANSAN, old), fact(SUWON, old)),
            required_region=ANSAN, reference_date=DAY, evaluation_date=DAY,
        ))


def test_resolver_adapter_order_and_duplicates_integration():
    facts = (fact(), fact(source=RegistrationSource.MANUALLY_VERIFIED), fact())
    outputs = [convert(resolve_resident_registration(
        order, required_region=ANSAN, reference_date=DAY, evaluation_date=DAY,
    )) for order in permutations(facts)]
    assert all(output == outputs[0] for output in outputs)
    assert len(outputs[0].details.evidence) == 2


def test_distinct_evaluation_and_policy_dates_not_mixed():
    output = convert(resolve_resident_registration(
        (fact(),), required_region=ANSAN, reference_date=DAY, evaluation_date=date(2026, 11, 20),
    ))
    assert output.details.reference_date == DAY
    assert output.details.evidence[0].fact_as_of_date == DAY
    assert "evaluation_date" not in output.to_dict()["details"]
