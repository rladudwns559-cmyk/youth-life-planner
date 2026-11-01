"""M1.6A 입력 모델만 검증한다. 주민등록 상태 판정이나 resolver는 호출하지 않는다."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, time

import pytest

from backend.policy_engine import EngineValidationError
from backend.policy_engine.facts import (
    CANONICAL_REGION_PAIRS,
    INTERNAL_REGION_NAMESPACE,
    RegionRef,
    RegistrationSource,
    ResidentRegistrationFact,
    ResidentRegistrationValidationError,
)


@pytest.mark.parametrize(("sido", "sigungu"), [
    ("GYEONGGI", "ANSAN"),
    ("GYEONGGI", "SUWON"),
    ("SEOUL", "JONGNO"),
])
def test_complete_canonical_region(sido, sigungu):
    region = RegionRef(sido=sido, sigungu=sigungu)
    assert region.sido == sido
    assert region.sigungu == sigungu


@pytest.mark.parametrize(("sido", "sigungu"), [
    ("SEOUL", "ANSAN"),
    ("SEOUL", "SUWON"),
    ("GYEONGGI", "JONGNO"),
])
def test_individually_valid_keys_cannot_form_wrong_pair(sido, sigungu):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        RegionRef(sido, sigungu)
    assert caught.value.code == "INVALID_REGION"
    assert caught.value.field == "region"


@pytest.mark.parametrize("field", ["sido", "sigungu"])
@pytest.mark.parametrize("value", [None, "", " ", "???", 0, 1, False, True, 1.0, [], {}])
def test_invalid_region_key(field, value):
    args = {"sido": "GYEONGGI", "sigungu": "ANSAN", field: value}
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        RegionRef(**args)
    assert isinstance(caught.value, EngineValidationError)
    assert caught.value.code == "INVALID_REGION"
    assert caught.value.field == f"region.{field}"


@pytest.mark.parametrize(("sido", "sigungu"), [
    ("경기도", "안산시"), ("GYEONGGI", "안산"), ("GYEONGGI", "안산시"),
    ("GYEONGGI", "경기도 안산시"), ("gyeonggi", "ANSAN"), ("GYEONGGI", "ansan"),
    (" GYEONGGI", "ANSAN"), ("GYEONGGI", "ANSAN "),
])
def test_region_does_not_normalize_alias_case_or_whitespace(sido, sigungu):
    with pytest.raises(ResidentRegistrationValidationError):
        RegionRef(sido, sigungu)


def test_both_region_keys_are_required():
    with pytest.raises(TypeError):
        RegionRef(sido="GYEONGGI")
    with pytest.raises(TypeError):
        RegionRef(sigungu="ANSAN")
    with pytest.raises(ResidentRegistrationValidationError):
        RegionRef(None, None)


def test_catalog_is_explicitly_internal_minimal_and_immutable():
    assert INTERNAL_REGION_NAMESPACE == "MVP_INTERNAL_REGION_V1"
    assert CANONICAL_REGION_PAIRS == frozenset({
        ("GYEONGGI", "ANSAN"), ("GYEONGGI", "SUWON"), ("SEOUL", "JONGNO"),
    })
    with pytest.raises(AttributeError):
        CANONICAL_REGION_PAIRS.add(("OTHER", "OTHER"))


@pytest.mark.parametrize(("member", "expected"), [
    (RegistrationSource.SELF_REPORTED, "SELF_REPORTED"),
    (RegistrationSource.MANUALLY_VERIFIED, "MANUALLY_VERIFIED"),
    (RegistrationSource.OFFICIAL_DATA, "OFFICIAL_DATA"),
])
def test_source_enum_has_stable_explicit_values(member, expected):
    assert member.value == expected
    assert RegistrationSource(expected) is member
    fact = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), date(2026, 11, 10), member)
    assert fact.source is member
    assert fact.to_dict()["source"] == expected


@pytest.mark.parametrize("value", ["whatever", "self_reported", " SELF_REPORTED", "SELF_REPORTED ", "", None, 0, False])
def test_invalid_source_enum_value_is_not_fixed(value):
    with pytest.raises(ValueError):
        RegistrationSource(value)


@pytest.mark.parametrize(("region", "as_of_date"), [
    (RegionRef("GYEONGGI", "ANSAN"), date(2026, 11, 10)),
    (None, date(2026, 11, 10)),
    (RegionRef("GYEONGGI", "ANSAN"), None),
    (None, None),
])
def test_fact_allows_missing_information_without_creating_status(region, as_of_date):
    fact = ResidentRegistrationFact(region, as_of_date, RegistrationSource.SELF_REPORTED)
    assert fact.region is region
    assert fact.as_of_date is as_of_date
    assert fact.source is RegistrationSource.SELF_REPORTED
    assert not hasattr(fact, "status")
    assert not hasattr(fact, "overall_status")


@pytest.mark.parametrize("region", ["안산시", "ANSAN", 123, False, True, [], {"sido": "GYEONGGI", "sigungu": "ANSAN"}])
def test_fact_rejects_invalid_region_instead_of_treating_it_as_missing(region):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        ResidentRegistrationFact(region, None, RegistrationSource.SELF_REPORTED)
    assert caught.value.code == "INVALID_REGION"
    assert caught.value.field == "resident_registration.region"


@pytest.mark.parametrize("value", [
    "2026-11-10", "abc", "2026-02-30", datetime(2026, 11, 10), time(12, 0),
    0, False, True, 20261110, 1.0, [], {},
])
def test_fact_rejects_invalid_date_without_implicit_parsing(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        ResidentRegistrationFact(None, value, RegistrationSource.SELF_REPORTED)
    assert caught.value.code == "INVALID_DATE"
    assert caught.value.field == "resident_registration.as_of_date"


@pytest.mark.parametrize("value", [None, "whatever", "SELF_REPORTED", 0, False, True, [], {}])
def test_fact_requires_explicit_source_enum(value):
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        ResidentRegistrationFact(None, None, value)
    assert caught.value.code == "INVALID_SOURCE"
    assert caught.value.field == "resident_registration.source"


def test_source_cannot_be_omitted():
    with pytest.raises(TypeError, match="source"):
        ResidentRegistrationFact(region=None, as_of_date=None)


@pytest.mark.parametrize(("field", "value"), [
    ("region", None), ("as_of_date", None), ("source", RegistrationSource.OFFICIAL_DATA),
])
def test_fact_is_frozen(field, value):
    fact = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), date(2026, 11, 10), RegistrationSource.SELF_REPORTED)
    with pytest.raises(FrozenInstanceError):
        setattr(fact, field, value)


@pytest.mark.parametrize("field", ["sido", "sigungu"])
def test_nested_region_is_frozen(field):
    fact = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), None, RegistrationSource.SELF_REPORTED)
    with pytest.raises(FrozenInstanceError):
        setattr(fact.region, field, "OTHER")


def test_identical_inputs_create_equal_value_objects():
    first = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), date(2026, 11, 10), RegistrationSource.SELF_REPORTED)
    second = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), date(2026, 11, 10), RegistrationSource.SELF_REPORTED)
    assert first is not second
    assert first == second
    assert hash(first) == hash(second)


def test_dataclass_replace_still_validates_new_input():
    region = RegionRef("GYEONGGI", "ANSAN")
    fact = ResidentRegistrationFact(region, None, RegistrationSource.SELF_REPORTED)
    with pytest.raises(ResidentRegistrationValidationError):
        replace(region, sido="SEOUL")
    with pytest.raises(ResidentRegistrationValidationError):
        replace(fact, as_of_date="2026-11-10")
    with pytest.raises(ResidentRegistrationValidationError):
        replace(fact, source="OFFICIAL_DATA")
    assert fact.region == RegionRef("GYEONGGI", "ANSAN")
    assert fact.as_of_date is None


def test_explicit_json_representation_and_boundary_conversion():
    fact = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), date(2026, 11, 10), RegistrationSource.SELF_REPORTED)
    expected = {
        "region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "as_of_date": "2026-11-10",
        "source": "SELF_REPORTED",
    }
    payload = json.loads(json.dumps(fact.to_dict()))
    assert payload == expected
    # 명시적인 외부 변환 예시. 도메인 생성자의 암묵 파싱이 아니다.
    recreated = ResidentRegistrationFact(
        RegionRef(**payload["region"]),
        date.fromisoformat(payload["as_of_date"]),
        RegistrationSource(payload["source"]),
    )
    assert recreated == fact
    payload["region"]["sigungu"] = "SUWON"
    assert fact.to_dict() == expected


def test_serialization_preserves_null_instead_of_inventing_values():
    fact = ResidentRegistrationFact(None, None, RegistrationSource.MANUALLY_VERIFIED)
    assert json.loads(json.dumps(fact.to_dict())) == {
        "region": None, "as_of_date": None, "source": "MANUALLY_VERIFIED",
    }


def test_validation_message_does_not_echo_input_value():
    private_input = "사용자의 원문 정보가 포함된 잘못된 지역"
    with pytest.raises(ResidentRegistrationValidationError) as caught:
        RegionRef("GYEONGGI", private_input)
    assert private_input not in str(caught.value)
    assert caught.value.code == "INVALID_REGION"
