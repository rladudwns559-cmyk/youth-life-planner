"""사람이 명시한 기대값으로 독립 주민등록 resolver를 검증한다."""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from itertools import permutations

import pytest

from backend.policy_engine import Status, UserProfile
from backend.policy_engine.facts import (
    RegionRef,
    RegistrationSource,
    ResidentRegistrationFact,
    ResidentRegistrationValidationError,
)
from backend.policy_engine.resolvers import (
    ResidentRegistrationReasonCode,
    resolve_resident_registration,
)

ANSAN = RegionRef("GYEONGGI", "ANSAN")
SUWON = RegionRef("GYEONGGI", "SUWON")
REFERENCE = date(2026, 11, 10)
PAST = date(2026, 10, 1)
FUTURE = date(2026, 12, 1)


def fact(region=ANSAN, when=REFERENCE, source=RegistrationSource.SELF_REPORTED):
    return ResidentRegistrationFact(region, when, source)


def resolve(facts, *, reference_date=REFERENCE, evaluation_date=REFERENCE, required_region=ANSAN):
    return resolve_resident_registration(
        facts,
        required_region=required_region,
        reference_date=reference_date,
        evaluation_date=evaluation_date,
    )


@pytest.mark.parametrize(("region", "status", "reason"), [
    (ANSAN, Status.PASS, "RESIDENT_REGION_MATCH"),
    (SUWON, Status.FAIL, "RESIDENT_REGION_MISMATCH"),
    (None, Status.UNKNOWN, "RESIDENT_REGION_MISSING"),
])
def test_exact_date_region(region, status, reason):
    input_fact = fact(region)
    result = resolve([input_fact])
    assert result.status is status
    assert result.reason_code.value == reason
    assert result.reference_date == REFERENCE
    assert result.evaluation_date == REFERENCE
    assert result.required_region == ANSAN
    assert result.resolved_region == region
    assert result.fact_as_of_date == REFERENCE
    assert result.used_facts == (input_fact,)
    assert result.sources == (RegistrationSource.SELF_REPORTED,)
    assert result.missing_fields == (("resident_registration.region",) if region is None else ())


@pytest.mark.parametrize("facts", [[], ()])
def test_no_facts_is_unknown(facts):
    result = resolve(facts)
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_MISSING"
    assert result.missing_fields == ("resident_registration",)
    assert result.used_facts == ()
    assert result.sources == ()


@pytest.mark.parametrize("when", [
    date(2026, 11, 9), PAST, date(2025, 11, 10), date(2026, 11, 11), FUTURE,
])
def test_different_date_never_proves_reference_date(when):
    result = resolve([fact(when=when)])
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_DATE_UNPROVEN"
    assert result.missing_fields == ()
    assert result.used_facts == ()
    assert result.resolved_region is None
    assert result.fact_as_of_date is None


def test_date_missing_is_distinct_from_wrong_date():
    result = resolve([fact(when=None)])
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_DATE_MISSING"
    assert result.missing_fields == ("resident_registration.as_of_date",)
    assert result.used_facts == ()


def test_undated_fact_is_not_assumed_to_be_for_today():
    result = resolve([fact(when=None), fact(SUWON, PAST)])
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_DATE_MISSING"
    assert result.missing_fields == ("resident_registration.as_of_date",)


def test_reference_date_is_not_defaulted_to_evaluation_date():
    result = resolve([fact()], reference_date=None)
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REFERENCE_DATE_MISSING"
    assert result.reference_date is None
    assert result.missing_fields == ("reference_date",)
    assert result.used_facts == ()


@pytest.mark.parametrize("facts", [
    [], [fact(when=PAST)], [fact(when=REFERENCE)],
    [fact(when=REFERENCE, source=RegistrationSource.OFFICIAL_DATA)],
])
def test_future_reference_date_is_unknown_even_if_future_fact_matches(facts):
    result = resolve(facts, evaluation_date=PAST)
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REFERENCE_DATE_IN_FUTURE"
    assert result.missing_fields == ()
    assert result.used_facts == ()
    assert result.fact_as_of_date is None


def test_exact_historical_fact_can_be_reviewed_later():
    historical = fact(when=PAST)
    result = resolve([historical], reference_date=PAST)
    assert result.status is Status.PASS
    assert result.reason_code == "RESIDENT_REGION_MATCH"
    assert result.fact_as_of_date == PAST
    assert result.evaluation_date == REFERENCE


def test_current_fact_does_not_prove_past_reference_date():
    result = resolve([fact()], reference_date=PAST)
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_DATE_UNPROVEN"


def test_exact_date_wins_over_other_dates_without_source_priority():
    exact = fact()
    result = resolve([
        fact(SUWON, PAST, RegistrationSource.OFFICIAL_DATA), exact,
        fact(SUWON, FUTURE, RegistrationSource.MANUALLY_VERIFIED),
    ])
    assert result.status is Status.PASS
    assert result.used_facts == (exact,)
    assert result.sources == (RegistrationSource.SELF_REPORTED,)
    assert result.missing_fields == ()


def test_exact_region_missing_does_not_fall_back_to_past_or_undated_fact():
    exact = fact(region=None)
    result = resolve([fact(when=PAST), exact, fact(when=None)])
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGION_MISSING"
    assert result.missing_fields == ("resident_registration.region",)
    assert result.used_facts == (exact,)


def test_exact_complete_fact_does_not_inherit_other_missing_fields():
    exact = fact()
    result = resolve([fact(region=None), fact(when=None), exact])
    assert result.status is Status.PASS
    assert result.missing_fields == ()
    assert result.used_facts == (exact,)


def test_identical_fact_duplicates_are_idempotent():
    first = fact()
    same_value = fact()
    assert first is not same_value
    assert resolve([first]) == resolve([first, first, same_value])


def test_same_date_region_different_sources_preserve_metadata():
    result = resolve([
        fact(source=RegistrationSource.SELF_REPORTED),
        fact(source=RegistrationSource.OFFICIAL_DATA),
        fact(source=RegistrationSource.MANUALLY_VERIFIED),
        fact(source=RegistrationSource.SELF_REPORTED),
    ])
    assert result.status is Status.PASS
    assert result.reason_code == "RESIDENT_REGION_MATCH"
    assert result.sources == (
        RegistrationSource.MANUALLY_VERIFIED,
        RegistrationSource.OFFICIAL_DATA,
        RegistrationSource.SELF_REPORTED,
    )
    assert len(result.used_facts) == 3


@pytest.mark.parametrize("source", [
    RegistrationSource.SELF_REPORTED,
    RegistrationSource.MANUALLY_VERIFIED,
    RegistrationSource.OFFICIAL_DATA,
])
@pytest.mark.parametrize(("region", "expected"), [(ANSAN, Status.PASS), (SUWON, Status.FAIL)])
def test_source_does_not_change_status(source, region, expected):
    result = resolve([fact(region, source=source)])
    assert result.status is expected
    assert result.reason_code == ("RESIDENT_REGION_MATCH" if region == ANSAN else "RESIDENT_REGION_MISMATCH")


@pytest.mark.parametrize("reverse", [False, True])
def test_same_date_conflict_is_error_even_with_official_source(reverse):
    inputs = [fact(), fact(SUWON, source=RegistrationSource.OFFICIAL_DATA)]
    if reverse:
        inputs.reverse()
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve(inputs)
    assert caught.value.code == "CONFLICTING_RESIDENT_REGISTRATION_FACTS"
    assert caught.value.field == "resident_registration_facts"


@pytest.mark.parametrize("when", [PAST, FUTURE])
def test_conflicts_outside_selected_date_are_not_silently_hidden(when):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([fact(), fact(when=when), fact(SUWON, when)])
    assert caught.value.code == "CONFLICTING_RESIDENT_REGISTRATION_FACTS"


@pytest.mark.parametrize(("reference_date", "evaluation_date"), [(None, REFERENCE), (REFERENCE, PAST)])
def test_conflict_error_precedes_missing_or_future_reference(reference_date, evaluation_date):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([fact(), fact(SUWON)], reference_date=reference_date, evaluation_date=evaluation_date)
    assert caught.value.code == "CONFLICTING_RESIDENT_REGISTRATION_FACTS"


def test_missing_region_is_not_a_conflicting_region_or_verified_evidence():
    useful = fact()
    result = resolve([fact(region=None, source=RegistrationSource.OFFICIAL_DATA), useful])
    assert result.status is Status.PASS
    assert result.used_facts == (useful,)
    assert result.sources == (RegistrationSource.SELF_REPORTED,)


def test_unknown_dates_do_not_prove_two_region_claims_conflict():
    result = resolve([fact(when=None), fact(SUWON, None)])
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_DATE_MISSING"


def test_different_dates_and_regions_are_not_inherently_a_conflict():
    selected = fact(SUWON)
    result = resolve([fact(when=PAST), selected])
    assert result.status is Status.FAIL
    assert result.used_facts == (selected,)


@pytest.mark.parametrize("value", [None, "ANSAN", False, 0, {"sido": "GYEONGGI", "sigungu": "ANSAN"}, UserProfile(region="안산시")])
def test_invalid_required_region_is_data_error(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([], required_region=value)
    assert caught.value.code == "INVALID_REQUIRED_REGION"
    assert caught.value.field == "required_region"


@pytest.mark.parametrize("value", ["2026-11-10", "abc", datetime(2026, 11, 10), 20261110, False, [], {}])
def test_invalid_reference_date_reuses_existing_date_error(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([fact()], reference_date=value)
    assert caught.value.code == "INVALID_DATE"
    assert caught.value.field == "reference_date"


@pytest.mark.parametrize("value", [None, "2026-11-10", datetime(2026, 11, 10), 20261110, False, [], {}])
def test_invalid_evaluation_date_is_data_error(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([fact()], evaluation_date=value)
    assert caught.value.code == "INVALID_EVALUATION_DATE"
    assert caught.value.field == "evaluation_date"


@pytest.mark.parametrize("value", [None, "", b"", bytearray(), {}, {"facts": []}, fact(), 0])
def test_invalid_fact_container_is_not_missing_information(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve(value)
    assert caught.value.code == "INVALID_RESIDENT_REGISTRATION_FACT"


def test_generator_is_rejected_instead_of_being_consumed_implicitly():
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve(iter([fact()]))
    assert caught.value.code == "INVALID_RESIDENT_REGISTRATION_FACT"


@pytest.mark.parametrize("value", [None, {}, "안산시", False, UserProfile(region="안산시")])
def test_invalid_fact_member_is_rejected_before_unknown(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([value], reference_date=None)
    assert caught.value.code == "INVALID_RESIDENT_REGISTRATION_FACT"


def test_every_candidate_is_validated_even_when_exact_match_already_exists():
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([fact(), "invalid additional fact"])
    assert caught.value.code == "INVALID_RESIDENT_REGISTRATION_FACT"


def test_legacy_region_is_not_implicitly_promoted():
    user = UserProfile(region="안산시")
    result = resolve([])
    assert user.region == "안산시"
    assert result.status is Status.UNKNOWN
    assert result.reason_code == "RESIDENT_REGISTRATION_MISSING"


def test_required_region_is_generic_not_hardcoded_to_ansan():
    result = resolve([fact(SUWON)], required_region=SUWON)
    assert result.status is Status.PASS
    assert result.reason_code == "RESIDENT_REGION_MATCH"


def test_input_list_fact_and_result_are_immutable_or_preserved():
    inputs = [fact(source=RegistrationSource.OFFICIAL_DATA), fact(), fact(when=PAST)]
    before = deepcopy(inputs)
    original_ids = [id(item) for item in inputs]
    result = resolve(inputs)
    assert inputs == before
    assert [id(item) for item in inputs] == original_ids
    with pytest.raises(FrozenInstanceError):
        result.status = Status.FAIL
    with pytest.raises(FrozenInstanceError):
        result.used_facts = ()
    with pytest.raises(FrozenInstanceError):
        result.used_facts[0].region.sigungu = "SUWON"


def test_same_input_repeated_has_identical_result():
    inputs = [fact(), fact(source=RegistrationSource.OFFICIAL_DATA)]
    assert resolve(inputs) == resolve(inputs)
    assert resolve(inputs).to_dict() == resolve(inputs).to_dict()


def test_permutations_and_duplicates_produce_identical_full_result():
    self_reported = fact()
    official = fact(source=RegistrationSource.OFFICIAL_DATA)
    old = fact(SUWON, PAST)
    expected = resolve([self_reported, official])
    for ordering in permutations((old, official, self_reported, self_reported)):
        assert resolve(ordering) == expected


def test_missing_region_evidence_is_also_deterministic():
    first = fact(region=None)
    second = fact(region=None, source=RegistrationSource.MANUALLY_VERIFIED)
    assert resolve([first, second, first]) == resolve([second, first])
    assert resolve([first, second]).reason_code == "RESIDENT_REGION_MISSING"


def test_result_serialization_contains_only_selected_evidence():
    result = resolve([fact(), fact(SUWON, PAST, RegistrationSource.OFFICIAL_DATA)])
    expected = {
        "status": "PASS",
        "reason_code": "RESIDENT_REGION_MATCH",
        "required_region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "reference_date": "2026-11-10",
        "evaluation_date": "2026-11-10",
        "resolved_region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "fact_as_of_date": "2026-11-10",
        "missing_fields": [],
        "used_facts": [{
            "region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
            "as_of_date": "2026-11-10", "source": "SELF_REPORTED",
        }],
        "sources": ["SELF_REPORTED"],
    }
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload == expected
    assert "SUWON" not in json.dumps(payload)
    payload["used_facts"][0]["region"]["sigungu"] = "SUWON"
    assert result.to_dict() == expected


def test_unknown_result_can_be_serialized_without_inventing_fact_date():
    result = resolve([], reference_date=None)
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["status"] == "UNKNOWN"
    assert payload["reference_date"] is None
    assert payload["fact_as_of_date"] is None
    assert payload["resolved_region"] is None
    assert payload["used_facts"] == []


def test_error_message_does_not_echo_unrelated_input():
    private_text = "사용자가 입력한 상세 개인정보"
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        resolve([private_text])
    assert private_text not in str(caught.value)


def test_reason_enum_retains_approved_future_reference_name():
    assert ResidentRegistrationReasonCode.RESIDENT_REFERENCE_DATE_IN_FUTURE.value == "RESIDENT_REFERENCE_DATE_IN_FUTURE"
    assert "POLICY_REFERENCE_DATE_IN_FUTURE" not in {reason.value for reason in ResidentRegistrationReasonCode}
