"""생년월일 사실 모델만 검증한다. 정책 범위 비교나 상태 판정은 하지 않는다."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, time, timezone
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, ProfileValidationError
from backend.policy_engine.facts import BirthFact, BirthFactValidationError, BirthSource, RegistrationSource
from backend.policy_engine.models import UserProfile


@pytest.mark.parametrize(("source", "value"), [
    (BirthSource.SELF_REPORTED, "SELF_REPORTED"),
    (BirthSource.MANUALLY_VERIFIED, "MANUALLY_VERIFIED"),
    (BirthSource.OFFICIAL_DATA, "OFFICIAL_DATA"),
])
def test_all_explicit_source_values(source, value):
    assert source.value == value
    assert BirthSource(value) is source
    fact = BirthFact(date(2000, 1, 15), source)
    assert fact.source is source
    assert fact.to_dict()["source"] == value


def test_source_enum_is_separate_and_has_no_additional_members_or_aliases():
    assert BirthSource is not RegistrationSource
    assert set(BirthSource.__members__) == {"SELF_REPORTED", "MANUALLY_VERIFIED", "OFFICIAL_DATA"}


@pytest.mark.parametrize("value", [
    "", "self_reported", "Self_Reported", " SELF_REPORTED", "SELF_REPORTED ",
    "manual", "official", "사용자입력", "UNKNOWN", None, 0, 1, True,
])
def test_source_enum_does_not_normalize_case_alias_or_whitespace(value):
    with pytest.raises(ValueError):
        BirthSource(value)


@pytest.mark.parametrize("source", list(BirthSource))
@pytest.mark.parametrize("birth_date", [None, date(2000, 2, 29), date(1999, 12, 31), date.min, date.max])
def test_valid_date_or_missing_information_preserved_without_policy_result(birth_date, source):
    fact = BirthFact(birth_date, source)
    assert fact.birth_date is birth_date
    assert fact.source is source
    assert not hasattr(fact, "status") and not hasattr(fact, "overall_status")
    assert [field.name for field in fields(fact)] == ["birth_date", "source"]


class DateSubclass(date):
    pass


@pytest.mark.parametrize("value", [
    "2001-07-02", "2001-02-29", "", datetime(2000, 1, 15),
    datetime(2000, 1, 15, tzinfo=timezone.utc), DateSubclass(2000, 1, 15), time(12, 0),
    20000115, 0, 1.5, True, False, [], [date(2000, 1, 15)], (), {},
])
def test_invalid_date_types_are_errors_without_parsing_or_truncation(value):
    with pytest.raises(BirthFactValidationError) as caught:
        BirthFact(value, BirthSource.SELF_REPORTED)
    assert caught.value.code == "INVALID_DATE"
    assert caught.value.field == "birth.birth_date"
    assert isinstance(caught.value, ProfileValidationError)
    assert isinstance(caught.value, EngineValidationError)


@pytest.mark.parametrize("value", [
    None, "SELF_REPORTED", "self_reported", "OFFICIAL_DATA", "manual", "", 0, 1, 1.5,
    True, False, [], {}, *list(RegistrationSource),
])
def test_fact_requires_exact_birth_source_even_when_date_missing(value):
    with pytest.raises(BirthFactValidationError) as caught:
        BirthFact(None, value)
    assert caught.value.code == "INVALID_SOURCE"
    assert caught.value.field == "birth.source"


def test_required_fields_cannot_be_omitted():
    with pytest.raises(TypeError, match="source"):
        BirthFact(birth_date=None)
    with pytest.raises(TypeError, match="birth_date"):
        BirthFact(source=BirthSource.SELF_REPORTED)


def test_nonexistent_leap_day_is_rejected_by_python_date_before_fact_creation():
    with pytest.raises(ValueError):
        BirthFact(date(2001, 2, 29), BirthSource.SELF_REPORTED)


@pytest.mark.parametrize(("field", "value"), [
    ("birth_date", None), ("source", BirthSource.OFFICIAL_DATA),
])
def test_fact_fields_cannot_be_modified_or_deleted(field, value):
    fact = BirthFact(date(2000, 1, 15), BirthSource.SELF_REPORTED)
    with pytest.raises(FrozenInstanceError):
        setattr(fact, field, value)
    with pytest.raises(FrozenInstanceError):
        delattr(fact, field)
    assert not hasattr(fact, "__dict__")


def test_equality_hash_and_repr_have_stable_value_semantics():
    first = BirthFact(date(2000, 1, 15), BirthSource.SELF_REPORTED)
    second = BirthFact(date(2000, 1, 15), BirthSource.SELF_REPORTED)
    assert first == second and hash(first) == hash(second)
    assert first != replace(first, source=BirthSource.OFFICIAL_DATA)
    assert "BirthFact" in repr(first) and "SELF_REPORTED" in repr(first)
    assert replace(first) == first
    with pytest.raises(BirthFactValidationError):
        replace(first, birth_date="2000-01-15")


@pytest.mark.parametrize("birth_date", [None, date(2000, 2, 29)])
def test_json_friendly_snapshot_is_fresh_and_does_not_mutate_fact(birth_date):
    fact = BirthFact(birth_date, BirthSource.MANUALLY_VERIFIED)
    expected = {"birth_date": birth_date.isoformat() if birth_date else None, "source": "MANUALLY_VERIFIED"}
    snapshot = fact.to_dict()
    assert snapshot == expected
    assert json.loads(json.dumps(snapshot)) == expected
    snapshot["birth_date"] = "changed"
    snapshot["source"] = "changed"
    assert fact.to_dict() == expected
    assert fact.birth_date is birth_date


def test_changes_to_callers_input_mapping_do_not_change_fact():
    inputs = {"birth_date": date(2000, 1, 15), "source": BirthSource.SELF_REPORTED}
    fact = BirthFact(**inputs)
    inputs.update(birth_date=None, source=BirthSource.OFFICIAL_DATA)
    assert fact == BirthFact(date(2000, 1, 15), BirthSource.SELF_REPORTED)


def test_age_never_populates_birth_date_and_profile_is_not_modified():
    profile = UserProfile(age=24)
    fact = BirthFact(None, BirthSource.SELF_REPORTED)
    assert profile.age == 24 and fact.birth_date is None
    assert not hasattr(profile, "birth_date") and not hasattr(fact, "age")
    with pytest.raises(TypeError, match="age"):
        BirthFact(birth_date=None, source=BirthSource.SELF_REPORTED, age=profile.age)


def test_error_message_does_not_include_raw_birth_input():
    value = "private-date-input-2001-07-02"
    with pytest.raises(BirthFactValidationError) as caught:
        BirthFact(value, BirthSource.SELF_REPORTED)
    assert value not in str(caught.value)
