"""독립 출생일 구간 구조만 검증한다. 사용자 사실 비교·판정은 하지 않는다."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timezone
import json
from typing import get_args

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.loader import parse_policy_set
from backend.policy_engine.models import GroupOperator, Policy, RuleGroup, RuleNode
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.result_types import ReferenceDateSource


LOWER = date(1998, 1, 10)
UPPER = date(1999, 1, 9)
REF = "SYNTH-SOURCE-001#birth-date-range"


def rule(**changes):
    values = dict(rule_id="SYNTH-BIRTH", min_birth_date=LOWER,
                  max_birth_date=UPPER, evidence_refs=(REF,))
    values.update(changes)
    return BirthDateRule(**values)


@pytest.mark.parametrize(("lower", "upper"), [
    (LOWER, UPPER), (LOWER, LOWER), (date(2000, 2, 29), date(2000, 2, 29)),
    (date(2000, 2, 28), date(2000, 3, 1)), (date.min, date.max),
])
def test_valid_ranges_preserve_exact_dates_without_evaluation(lower, upper):
    result = rule(min_birth_date=lower, max_birth_date=upper)
    assert result.min_birth_date is lower and result.max_birth_date is upper
    assert not hasattr(result, "status") and not hasattr(result, "overall_status")


class DateSubclass(date):
    pass


@pytest.mark.parametrize("field", ["min_birth_date", "max_birth_date"])
@pytest.mark.parametrize("value", [
    None, "1998-01-10", 19980110, 0, 1.5, True, False, [], (), {},
    datetime(1998, 1, 10), datetime(1998, 1, 10, tzinfo=timezone.utc), DateSubclass(1998, 1, 10),
])
def test_date_fields_reject_wrong_types_instead_of_parsing(field, value):
    with pytest.raises(PolicyDataError, match=field) as error:
        rule(**{field: value})
    assert isinstance(error.value, EngineValidationError)


def test_reversed_range_is_policy_data_error():
    with pytest.raises(PolicyDataError, match="min_birth_date"):
        rule(min_birth_date=UPPER, max_birth_date=LOWER)


@pytest.mark.parametrize("field", ["rule_id", "min_birth_date", "max_birth_date"])
def test_identity_and_date_fields_have_no_defaults(field):
    values = dict(rule_id="SYNTH-BIRTH", min_birth_date=LOWER,
                  max_birth_date=UPPER, evidence_refs=(REF,))
    del values[field]
    with pytest.raises(TypeError, match=field):
        BirthDateRule(**values)


@pytest.mark.parametrize("value", ["", " ", "\t\n", None, 0, 1.0, True, [], {}])
def test_rule_id_is_required_nonblank_exact_string(value):
    with pytest.raises(PolicyDataError, match="rule_id"):
        rule(rule_id=value)


def test_valid_rule_id_is_preserved_without_strip_or_generation():
    result = rule(rule_id=" SYNTH-BIRTH ")
    assert result.rule_id == " SYNTH-BIRTH "


@pytest.mark.parametrize("refs", [(REF,), (REF, "SYNTH-SOURCE-002#birth-date-range"), (REF, REF)])
def test_nonempty_evidence_tuple_preserves_order_and_duplicates_like_existing_rule(refs):
    result = rule(evidence_refs=refs)
    assert result.evidence_refs is refs
    resident = ResidentRegistrationRule(
        "SYNTH-RESIDENT", RegionRef("GYEONGGI", "ANSAN"), ReferenceDateSource.APPLICATION_DATE, refs,
    )
    assert result.evidence_refs == resident.evidence_refs


@pytest.mark.parametrize("refs", [(), None, [], [REF], REF, {REF}, {"ref": REF}])
def test_empty_or_non_tuple_evidence_is_rejected_without_conversion(refs):
    with pytest.raises(PolicyDataError, match="evidence_refs"):
        rule(evidence_refs=refs)


@pytest.mark.parametrize("value", [None, "", " \t", 0, 1.5, False, [], {}, (REF,)])
def test_invalid_evidence_element_is_policy_data_error(value):
    with pytest.raises(PolicyDataError, match="evidence_refs"):
        rule(evidence_refs=(REF, value))


def test_omitted_evidence_uses_existing_specialized_default_but_is_rejected():
    with pytest.raises(PolicyDataError, match="evidence_refs"):
        BirthDateRule("SYNTH-BIRTH", LOWER, UPPER)


def test_evidence_syntax_and_existence_are_not_validated_by_structural_model():
    refs = (" synthetic local reference ",)
    assert rule(evidence_refs=refs).evidence_refs == refs


@pytest.mark.parametrize(("field", "value"), [
    ("rule_id", "OTHER"), ("min_birth_date", LOWER), ("max_birth_date", UPPER),
    ("evidence_refs", (REF, REF)),
])
def test_all_fields_are_frozen_and_cannot_be_deleted(field, value):
    result = rule()
    with pytest.raises(FrozenInstanceError):
        setattr(result, field, value)
    with pytest.raises(FrozenInstanceError):
        delattr(result, field)
    assert not hasattr(result, "__dict__")


def test_evidence_augmented_assignment_is_rejected():
    result = rule()
    with pytest.raises(FrozenInstanceError):
        result.evidence_refs += (REF,)
    assert result.evidence_refs == (REF,)


def test_equal_inputs_have_equal_values_and_replace_revalidates():
    first, second = rule(), rule()
    assert first == second and hash(first) == hash(second)
    assert replace(first) == first
    assert first != replace(first, rule_id="SYNTH-OTHER")
    with pytest.raises(PolicyDataError):
        replace(first, min_birth_date=UPPER, max_birth_date=LOWER)


def test_snapshot_is_json_friendly_and_fresh():
    result = rule()
    expected = dict(rule_id="SYNTH-BIRTH", min_birth_date="1998-01-10",
                    max_birth_date="1999-01-09", evidence_refs=[REF])
    snapshot = result.to_dict()
    assert snapshot == expected and json.loads(json.dumps(snapshot)) == expected
    snapshot["evidence_refs"].append("changed")
    snapshot["min_birth_date"] = "changed"
    assert result.to_dict() == expected


def test_fields_exclude_user_facts_age_quarter_and_inclusive_options():
    assert [field.name for field in fields(BirthDateRule)] == [
        "rule_id", "min_birth_date", "max_birth_date", "evidence_refs",
    ]


@pytest.mark.parametrize("extra", ["birth_fact", "age", "reference_age", "quarter", "reference_date", "inclusive_min", "inclusive_max"])
def test_unapproved_fields_are_not_accepted(extra):
    with pytest.raises(TypeError, match=extra):
        rule(**{extra: None})


def test_birth_rule_is_not_registered_as_rule_node_or_policy_root():
    # M1.16G 승인: 독립 모델의 임시 미편입 제한을 메모리 트리 지원으로 갱신한다.
    assert BirthDateRule in get_args(RuleNode)
    birth = rule()
    assert Policy("SYNTH-POLICY", "합성 정책", "synthetic-1", birth).root is birth
    assert RuleGroup("SYNTH-GROUP", GroupOperator.ALL, (birth,)).children == (birth,)


def test_m11_loader_does_not_accept_birth_date_rule():
    payload = dict(schema_version="m1.1", dataset_version="synthetic-birth-structure",
                   synthetic=True, test_only=True, policies=[dict(
                       policy_id="SYNTH-POLICY", policy_name="합성 정책", rule_version="synthetic-1",
                       synthetic=True, test_only=True,
                       root=dict(kind="rule", rule_type="birth_date", **rule().to_dict()),
                   )])
    # M1.16I 승인: 과거 미지원 기대를 m1.1 strict 로딩 계약으로 전환한다.
    loaded = parse_policy_set(payload).policies[0].root
    assert loaded == rule()
    assert type(loaded.min_birth_date) is date and type(loaded.max_birth_date) is date
