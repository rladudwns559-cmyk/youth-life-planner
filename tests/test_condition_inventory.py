"""합성 목록으로 inventory 구조·중복·불변성을 검증한다. 정책 구현범위는 판정하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionInventory, ConditionRequirement, RequiredCondition,
)
from backend.policy_engine.policy_data import condition_inventory as domain
from backend.policy_engine.sources import SourceRegistry


FIRST = RequiredCondition(
    "SYNTH_CONDITION_A", "합성 공통 자격조건", ConditionRequirement.REQUIRED,
    ("SYN-DOC-A#test-a", "SYN-DOC-A#test-a"),
)
SECOND = RequiredCondition(
    "SYNTH_CONDITION_B", "합성 조건부 자격조건", ConditionRequirement.CONDITIONAL,
    ("SYN-DOC-B#test-b",),
)


def values(**changes):
    return {
        "policy_id": "SYN-POLICY-A", "scope": ApplicabilityScope("2026", 3),
        "inventory_version": "i0001", "conditions": (FIRST, SECOND),
        "completeness_review_ref": None, **changes,
    }


class StringSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class ConditionSubclass(RequiredCondition):
    pass


@pytest.mark.parametrize("quarter", [3, None])
@pytest.mark.parametrize("conditions", [(FIRST,), (FIRST, SECOND)])
@pytest.mark.parametrize("review", [None, "SYN-REVIEW-001"])
def test_valid_inventory_keeps_original_objects_and_expected_nested_snapshot(quarter, conditions, review):
    scope = ApplicabilityScope("2026", quarter)
    inventory = ConditionInventory(**values(scope=scope, conditions=conditions, completeness_review_ref=review))
    assert inventory.scope is scope
    assert inventory.conditions is conditions
    assert all(actual is supplied for actual, supplied in zip(inventory.conditions, conditions))
    expected = {
        "policy_id": "SYN-POLICY-A", "scope": {"edition_id": "2026", "quarter": quarter},
        "inventory_version": "i0001", "conditions": [condition.to_dict() for condition in conditions],
        "completeness_review_ref": review,
    }
    assert inventory.to_dict() == expected
    assert json.loads(json.dumps(inventory.to_dict())) == expected
    repeated = ConditionInventory(**values(scope=scope, conditions=conditions, completeness_review_ref=review))
    assert inventory == repeated and hash(inventory) == hash(repeated)


@pytest.mark.parametrize("other", [
    FIRST,
    replace(FIRST, meaning="합성 의미 변경"),
    replace(FIRST, requirement=ConditionRequirement.CONDITIONAL),
    replace(FIRST, evidence_refs=("SYN-DOC-C#test-c",)),
])
def test_same_id_is_rejected_even_for_identical_object_or_metadata_conflict(other):
    with pytest.raises(PolicyDataError, match="condition_id"):
        ConditionInventory(**values(conditions=(FIRST, other)))


def test_different_ids_with_same_meaning_are_not_natural_language_deduplicated():
    other = replace(FIRST, condition_id="SYNTH_CONDITION_C")
    inventory = ConditionInventory(**values(conditions=(FIRST, other)))
    assert inventory.conditions == (FIRST, other)
    assert len(inventory.conditions) == 2


@pytest.mark.parametrize("scope", [
    None, {}, {"edition_id": "2026", "quarter": 3}, ("2026", 3), "2026-Q3",
    3, True, object(), ScopeSubclass("2026", 3),
])
def test_scope_is_exact_prevalidated_value(scope):
    with pytest.raises(PolicyDataError, match="scope"):
        ConditionInventory(**values(scope=scope))


@pytest.mark.parametrize("conditions", [None, [], [FIRST], (), "SYNTH_CONDITION_A", {}, {FIRST}, TupleSubclass((FIRST,))])
def test_conditions_are_nonempty_exact_tuple(conditions):
    with pytest.raises(PolicyDataError, match="conditions"):
        ConditionInventory(**values(conditions=conditions))


@pytest.mark.parametrize("element", [
    None, {}, "SYNTH_CONDITION_A", 1, True, object(), ApplicabilityScope("2026", 3),
    ConditionSubclass(FIRST.condition_id, FIRST.meaning, FIRST.requirement, FIRST.evidence_refs),
])
def test_elements_are_exact_required_conditions(element):
    with pytest.raises(PolicyDataError, match="conditions"):
        ConditionInventory(**values(conditions=(FIRST, element)))


@pytest.mark.parametrize("review", ["", " ", "\t\n", 1, True, 1.0, [], {}, StringSubclass("SYN-REVIEW")])
def test_review_reference_is_nonempty_exact_string_or_none(review):
    with pytest.raises(PolicyDataError, match="completeness_review_ref"):
        ConditionInventory(**values(completeness_review_ref=review))


def test_review_is_optional_and_not_stripped_or_resolved():
    omitted = values()
    del omitted["completeness_review_ref"]
    assert ConditionInventory(**omitted).completeness_review_ref is None
    inventory = ConditionInventory(**values(completeness_review_ref="  SYN-REVIEW-001  "))
    assert inventory.completeness_review_ref == inventory.to_dict()["completeness_review_ref"] == "  SYN-REVIEW-001  "


@pytest.mark.parametrize("policy_id", [
    "", " ", "SYN_POLICY", "syn-policy", " SYN-POLICY", "SYN-POLICY ", "SYN-POLICY\n",
    "SYN--POLICY", "정책 표시문장", None, 1, True, [], {}, StringSubclass("SYN-POLICY"),
])
def test_policy_identity_uses_existing_canonical_format(policy_id):
    with pytest.raises(PolicyDataError, match="policy_id"):
        ConditionInventory(**values(policy_id=policy_id))


@pytest.mark.parametrize("version", ["i0001", "i9999", "i10000", "i100000"])
def test_inventory_version_is_explicit_and_not_limited_to_four_digits(version):
    inventory = ConditionInventory(**values(inventory_version=version))
    assert inventory.inventory_version == inventory.to_dict()["inventory_version"] == version


@pytest.mark.parametrize("version", [
    None, 1, True, [], {}, "", "i0000", "i1", "I0001", "r0001", "i00001", "i-0001",
    " i0001", "i0001 ", "i0001\n", "i０００１", StringSubclass("i0001"),
])
def test_invalid_inventory_versions_are_not_inferred_or_normalized(version):
    with pytest.raises(PolicyDataError, match="inventory_version"):
        ConditionInventory(**values(inventory_version=version))


def test_tuple_order_is_preserved_and_part_of_value_equality():
    first = ConditionInventory(**values())
    reversed_inventory = ConditionInventory(**values(conditions=(SECOND, FIRST)))
    assert first != reversed_inventory
    assert [item["condition_id"] for item in reversed_inventory.to_dict()["conditions"]] == [
        "SYNTH_CONDITION_B", "SYNTH_CONDITION_A",
    ]
    assert reversed_inventory.conditions == (SECOND, FIRST)
    assert FIRST.evidence_refs == ("SYN-DOC-A#test-a", "SYN-DOC-A#test-a")


@pytest.mark.parametrize("change", [
    {"policy_id": "SYN-POLICY-B"}, {"scope": ApplicabilityScope("2027", 3)},
    {"scope": ApplicabilityScope("2026", None)}, {"inventory_version": "i0002"},
    {"completeness_review_ref": "SYN-REVIEW-001"},
])
def test_identity_scope_version_and_review_values_affect_equality(change):
    assert ConditionInventory(**values()) != ConditionInventory(**values(**change))


@pytest.mark.parametrize("field", ["policy_id", "scope", "inventory_version", "conditions", "completeness_review_ref"])
def test_inventory_fields_cannot_be_assigned_or_deleted(field):
    inventory = ConditionInventory(**values())
    with pytest.raises(FrozenInstanceError):
        setattr(inventory, field, None)
    with pytest.raises(FrozenInstanceError):
        delattr(inventory, field)
    assert not hasattr(inventory, "__dict__")


def test_nested_values_and_collection_are_immutable():
    inventory = ConditionInventory(**values())
    with pytest.raises(FrozenInstanceError):
        inventory.scope.quarter = 4
    with pytest.raises(FrozenInstanceError):
        inventory.conditions[0].meaning = "합성 변경"
    with pytest.raises(TypeError):
        inventory.conditions[0] = SECOND
    assert inventory.scope == ApplicabilityScope("2026", 3)
    assert inventory.conditions[0] is FIRST


def test_nested_serialization_is_fresh_and_cannot_change_inputs():
    inventory = ConditionInventory(**values())
    scope_before, condition_before = inventory.scope.to_dict(), FIRST.to_dict()
    first, second = inventory.to_dict(), inventory.to_dict()
    assert first == second and first is not second
    assert first["scope"] is not second["scope"]
    assert first["conditions"] is not second["conditions"]
    assert first["conditions"][0] is not second["conditions"][0]
    assert first["conditions"][0]["evidence_refs"] is not second["conditions"][0]["evidence_refs"]
    first["scope"]["quarter"] = None
    first["conditions"][0]["evidence_refs"].clear()
    first["conditions"][0]["meaning"] = "합성 변경"
    first["conditions"].clear()
    assert inventory.to_dict() == second
    assert inventory.scope.to_dict() == scope_before
    assert FIRST.to_dict() == condition_before


@pytest.mark.parametrize("missing", ["policy_id", "scope", "inventory_version", "conditions"])
def test_identity_scope_version_and_conditions_are_required(missing):
    payload = values()
    del payload[missing]
    with pytest.raises(TypeError):
        ConditionInventory(**payload)


@pytest.mark.parametrize("extra", [
    "edition_id", "rule_id", "rule_root_id", "group_id", "implemented", "implemented_count",
    "coverage_status", "verification_status", "accepted", "benefit_amount", "inventory_evidence_refs",
    "eligibility_coverage", "policy_evaluation", "application_date",
])
def test_inventory_has_no_binding_coverage_verification_or_benefit_fields(extra):
    assert [field.name for field in fields(ConditionInventory)] == [
        "policy_id", "scope", "inventory_version", "conditions", "completeness_review_ref",
    ]
    inventory = ConditionInventory(**values())
    assert not hasattr(inventory, extra)
    with pytest.raises(TypeError):
        ConditionInventory(**values(**{extra: None}))


def test_replace_revalidates_duplicates_and_does_not_modify_input():
    inventory = ConditionInventory(**values())
    changed = replace(inventory, completeness_review_ref="SYN-REVIEW-001")
    assert inventory.completeness_review_ref is None
    assert changed.conditions is inventory.conditions
    with pytest.raises(PolicyDataError):
        replace(inventory, conditions=(FIRST, FIRST))


def test_constructor_and_snapshot_do_not_lookup_refs_or_revalidate_condition_evidence(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("inventory 값 처리에서 I/O·조회·조건 재검증을 호출했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(SourceRegistry, "get_source", forbidden)
    monkeypatch.setattr(RequiredCondition, "__post_init__", forbidden)
    inventory = ConditionInventory(**values(completeness_review_ref="SYN-UNRESOLVED-REVIEW"))
    assert inventory.to_dict()["completeness_review_ref"] == "SYN-UNRESOLVED-REVIEW"
    assert inventory.conditions[0] is FIRST


def test_validation_uses_existing_error_hierarchy_without_raw_payload():
    secret = "private-invalid-policy-payload"
    with pytest.raises(PolicyDataError) as caught:
        ConditionInventory(**values(policy_id=secret))
    assert isinstance(caught.value, EngineValidationError)
    assert secret not in str(caught.value)


def test_direct_dependencies_exclude_evaluation_binding_and_acceptance():
    tree = ast.parse(inspect.getsource(domain))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports == {"dataclasses", "errors", "eligibility_coverage", "required_condition"}
    assert {node.name for node in tree.body if isinstance(node, ast.ClassDef)} == {"ConditionInventory"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {
        "date", "datetime", "PolicyEvaluation", "PolicyEnvelope", "ConditionBinding",
        "EligibilityCoverage", "PolicyBenefitAcceptance", "CashflowInput", "UserProfile",
    }
