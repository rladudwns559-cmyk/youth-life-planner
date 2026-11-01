"""합성 Inventory/Binding의 로컬 정합성만 검증한다. tree·상태 판정 테스트는 아니다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.models import Field, GroupOperator, Operator, PolicyRule, RuleGroup
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement,
    EligibilityCoverage, RequiredCondition,
)
from backend.policy_engine.policy_data import coverage as domain


CONDITION_A = RequiredCondition(
    "SYNTH_CONDITION_A", "합성 공통 조건", ConditionRequirement.REQUIRED,
    ("SYN-DOC-A#test-a", "SYN-DOC-A#test-a"),
)
CONDITION_B = RequiredCondition(
    "SYNTH_CONDITION_B", "합성 조건부 조건", ConditionRequirement.CONDITIONAL,
    ("SYN-DOC-B#test-b",),
)
CONDITION_C = replace(CONDITION_A, condition_id="SYNTH_CONDITION_C")
BINDING_A = ConditionBinding("SYNTH_CONDITION_A", "SYNTH_RULE_A", "SYNTH-REVIEW-A")
BINDING_B = ConditionBinding("SYNTH_CONDITION_B", "SYNTH_GROUP_B", "SYNTH-REVIEW-B")
BINDING_C = ConditionBinding("SYNTH_CONDITION_C", "SYNTH_RULE_C", "SYNTH-REVIEW-C")


def inventory(quarter=3, review=None):
    return ConditionInventory(
        "SYNTH-POLICY", ApplicabilityScope("2026", quarter), "i0001",
        (CONDITION_A, CONDITION_B, CONDITION_C), review,
    )


class InventorySubclass(ConditionInventory):
    pass


class BindingSubclass(ConditionBinding):
    pass


class TupleSubclass(tuple):
    pass


@pytest.mark.parametrize("quarter", [3, None])
@pytest.mark.parametrize("review", [None, "SYNTH-COMPLETENESS-REVIEW"])
@pytest.mark.parametrize("bindings", [(), (BINDING_A,), (BINDING_B,), (BINDING_A, BINDING_B, BINDING_C)])
def test_valid_structure_preserves_original_inventory_tuple_and_bindings(quarter, review, bindings):
    supplied = inventory(quarter, review)
    model = EligibilityCoverage(supplied, bindings)
    assert model.inventory is supplied
    assert model.bindings is bindings
    assert all(actual is original for actual, original in zip(model.bindings, bindings))
    assert model.to_dict() == {
        "inventory": supplied.to_dict(), "bindings": [binding.to_dict() for binding in bindings],
    }
    assert model == EligibilityCoverage(supplied, bindings)
    assert hash(model) == hash(EligibilityCoverage(supplied, bindings))
    assert json.loads(json.dumps(model.to_dict())) == model.to_dict()


@pytest.mark.parametrize("supplied", [
    None, {}, [], (), "SYNTH-POLICY", object(), True,
    InventorySubclass("SYNTH-POLICY", ApplicabilityScope("2026", 3), "i0001", (CONDITION_A,)),
])
def test_inventory_must_have_exact_type(supplied):
    with pytest.raises(PolicyDataError, match="inventory"):
        EligibilityCoverage(supplied, ())


@pytest.mark.parametrize("bindings", [
    None, [], [BINDING_A], {BINDING_A}, {}, "SYNTH_CONDITION_A", iter((BINDING_A,)),
    (binding for binding in (BINDING_A,)), TupleSubclass((BINDING_A,)),
])
def test_bindings_must_be_exact_tuple_without_conversion(bindings):
    with pytest.raises(PolicyDataError, match="bindings"):
        EligibilityCoverage(inventory(), bindings)


LEAF = PolicyRule("SYNTH_LEAF", Field.AGE, Operator.GTE, 1, evidence_refs=("synthetic-test",))
GROUP = RuleGroup("SYNTH_GROUP", GroupOperator.ALL, (LEAF,))


@pytest.mark.parametrize("element", [
    None, {}, "SYNTH_CONDITION_A", CONDITION_A, LEAF, GROUP, 1, True, object(),
    BindingSubclass(BINDING_A.condition_id, BINDING_A.rule_root_id, BINDING_A.implementation_review_ref),
])
def test_each_element_must_be_exact_binding(element):
    with pytest.raises(PolicyDataError, match="bindings"):
        EligibilityCoverage(inventory(), (BINDING_A, element))


@pytest.mark.parametrize("second", [
    BINDING_A,
    replace(BINDING_A),
    replace(BINDING_A, rule_root_id="SYNTH_OTHER_ROOT"),
    replace(BINDING_A, implementation_review_ref="SYNTH-OTHER-REVIEW"),
])
def test_duplicate_condition_binding_is_constructor_error(second):
    with pytest.raises(PolicyDataError, match="중복"):
        EligibilityCoverage(inventory(), (BINDING_A, second))


@pytest.mark.parametrize("bindings", [
    (ConditionBinding("SYNTH_UNKNOWN", "SYNTH_ROOT_X", "SYNTH-REVIEW-X"),),
    (BINDING_A, ConditionBinding("SYNTH_UNKNOWN", "SYNTH_ROOT_X", "SYNTH-REVIEW-X")),
])
def test_unknown_condition_is_constructor_referential_integrity_error(bindings):
    with pytest.raises(PolicyDataError, match="inventory에 존재"):
        EligibilityCoverage(inventory(), bindings)


def test_missing_required_and_conditional_bindings_are_representable_without_status():
    model = EligibilityCoverage(inventory(), (BINDING_A,))
    assert model.inventory.conditions == (CONDITION_A, CONDITION_B, CONDITION_C)
    assert model.bindings == (BINDING_A,)
    assert set(model.to_dict()) == {"inventory", "bindings"}


def test_same_root_for_different_conditions_is_left_for_future_validator():
    same_root = replace(BINDING_B, rule_root_id=BINDING_A.rule_root_id)
    model = EligibilityCoverage(inventory(), (BINDING_A, same_root))
    assert model.bindings[0].rule_root_id == model.bindings[1].rule_root_id
    assert model.bindings[0].condition_id != model.bindings[1].condition_id


def test_missing_inventory_review_and_unresolved_implementation_refs_are_preserved():
    unknown_root = replace(BINDING_A, rule_root_id="SYNTH_NONEXISTENT_ROOT", implementation_review_ref="SYNTH-UNRESOLVED")
    model = EligibilityCoverage(inventory(review=None), (unknown_root,))
    assert model.inventory.completeness_review_ref is None
    assert model.bindings[0] is unknown_root


def test_input_order_is_preserved_and_affects_structural_equality():
    supplied = inventory()
    original = EligibilityCoverage(supplied, (BINDING_A, BINDING_B))
    reversed_model = EligibilityCoverage(supplied, (BINDING_B, BINDING_A))
    assert original != reversed_model
    assert [binding["condition_id"] for binding in reversed_model.to_dict()["bindings"]] == [
        "SYNTH_CONDITION_B", "SYNTH_CONDITION_A",
    ]
    assert original.bindings == (BINDING_A, BINDING_B)
    assert original.inventory.conditions[0].evidence_refs == CONDITION_A.evidence_refs


@pytest.mark.parametrize("field", ["inventory", "bindings"])
def test_field_assignment_and_deletion_are_rejected(field):
    model = EligibilityCoverage(inventory(), (BINDING_A,))
    with pytest.raises(FrozenInstanceError):
        setattr(model, field, None)
    with pytest.raises(FrozenInstanceError):
        delattr(model, field)
    assert not hasattr(model, "__dict__")


def test_nested_values_and_original_tuple_remain_immutable():
    supplied = inventory()
    bindings = (BINDING_A,)
    model = EligibilityCoverage(supplied, bindings)
    with pytest.raises(FrozenInstanceError):
        model.inventory.scope.quarter = None
    with pytest.raises(FrozenInstanceError):
        model.inventory.completeness_review_ref = "SYNTH-CHANGED"
    with pytest.raises(FrozenInstanceError):
        model.bindings[0].rule_root_id = "SYNTH_CHANGED"
    with pytest.raises(TypeError):
        model.bindings[0] = BINDING_B
    assert model.inventory is supplied and model.bindings is bindings
    assert model.inventory.scope.quarter == 3
    assert model.bindings[0] is BINDING_A


def test_returned_nested_snapshots_are_fresh_and_independent():
    supplied, bindings = inventory(), (BINDING_A, BINDING_B)
    model = EligibilityCoverage(supplied, bindings)
    inventory_before = supplied.to_dict()
    binding_before = BINDING_A.to_dict()
    first, second = model.to_dict(), model.to_dict()
    assert first == second and first is not second
    assert first["inventory"] is not second["inventory"]
    assert first["bindings"] is not second["bindings"]
    assert first["bindings"][0] is not second["bindings"][0]
    first["inventory"]["scope"]["quarter"] = None
    first["inventory"]["conditions"][0]["evidence_refs"].clear()
    first["inventory"]["conditions"].clear()
    first["bindings"][0]["rule_root_id"] = "SYNTH_CHANGED"
    first["bindings"].clear()
    assert model.to_dict() == second
    assert supplied.to_dict() == inventory_before
    assert BINDING_A.to_dict() == binding_before


@pytest.mark.parametrize("extra", [
    "policy_id", "scope", "inventory_version", "status", "coverage_status", "is_full", "is_slice",
    "implemented_condition_ids", "missing_condition_ids", "bound_condition_ids", "unbound_condition_ids",
    "policy", "review_context", "review_snapshot", "review_registry", "verification_status",
    "acceptance_status", "cashflow", "benefit_amount", "application_date",
])
def test_only_two_fields_exist_without_derived_properties_or_other_domain_inputs(extra):
    model = EligibilityCoverage(inventory(), ())
    assert [field.name for field in fields(model)] == ["inventory", "bindings"]
    assert not hasattr(model, extra)
    with pytest.raises(TypeError):
        EligibilityCoverage(inventory(), (), **{extra: None})


@pytest.mark.parametrize("missing", ["inventory", "bindings"])
def test_both_arguments_are_required(missing):
    payload = {"inventory": inventory(), "bindings": ()}
    del payload[missing]
    with pytest.raises(TypeError):
        EligibilityCoverage(**payload)


def test_replace_revalidates_local_references_without_modifying_original():
    model = EligibilityCoverage(inventory(), (BINDING_A,))
    changed = replace(model, bindings=())
    assert changed.inventory is model.inventory
    assert changed.bindings == () and model.bindings == (BINDING_A,)
    with pytest.raises(PolicyDataError):
        replace(model, bindings=(BINDING_A, BINDING_A))


def test_constructor_does_not_revalidate_nested_models_or_visit_tree_or_files(monkeypatch):
    supplied = inventory()
    before = supplied.to_dict()
    def forbidden(*args, **kwargs):
        pytest.fail("구조 모델에서 하위 재검증·tree·외부 작업을 호출했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("backend.policy_engine.models.walk_nodes", forbidden)
    for cls in (ConditionInventory, ConditionBinding, RequiredCondition, ApplicabilityScope):
        monkeypatch.setattr(cls, "__post_init__", forbidden)
    model = EligibilityCoverage(supplied, (BINDING_A,))
    assert model.to_dict()["inventory"] == before


def test_error_uses_existing_hierarchy_without_echoing_unknown_id():
    unknown = ConditionBinding("SYNTH_PRIVATE_UNKNOWN", "SYNTH_ROOT", "SYNTH-REVIEW")
    with pytest.raises(PolicyDataError) as caught:
        EligibilityCoverage(inventory(), (unknown,))
    assert isinstance(caught.value, EngineValidationError)
    assert unknown.condition_id not in str(caught.value)


def test_direct_dependencies_and_public_operations_remain_structural():
    tree = ast.parse(inspect.getsource(domain))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {
        "dataclasses", "errors", "condition_binding", "condition_inventory",
    }
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == ["EligibilityCoverage"]
    assert {node.name for node in classes[0].body if isinstance(node, ast.FunctionDef)} == {"__post_init__", "to_dict"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {
        "Policy", "RuleGroup", "RuleNode", "walk_nodes", "CoverageReviewContext", "EligibilityCoverageResult",
        "SourceRegistry", "PolicyEvaluation", "CashflowInput", "PolicyBenefitAcceptance", "date", "datetime",
    }
    assert not any(isinstance(node, ast.FunctionDef) for node in tree.body)
