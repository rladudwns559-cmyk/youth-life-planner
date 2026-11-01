"""합성 ID mapping만 검증한다. 실제 inventory·트리 연결은 수행하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.models import Field, GroupOperator, Operator, PolicyRule, RuleGroup
from backend.policy_engine.policy_data import ConditionBinding, ConditionRequirement, RequiredCondition
from backend.policy_engine.policy_data import condition_binding as domain


def values(**changes):
    return {
        "condition_id": "SYNTH_CONDITION_A",
        "rule_root_id": "SYNTH_RULE_ROOT_A",
        "implementation_review_ref": "SYNTH-IMPLEMENTATION-REVIEW-A",
        **changes,
    }


class StringSubclass(str):
    pass


@pytest.mark.parametrize("condition_id,root", [
    ("SYNTH_CONDITION_A", "SYNTH_LEAF_A"),
    ("SYNTH_CONDITION_B", "SYNTH_ANY_GROUP_B"),
    ("SYNTH_CONDITIONAL_A", "SYNTH_CONDITIONAL_ROOT_A"),
    ("SYNTH_SAME_ID", "SYNTH_SAME_ID"),
])
def test_explicit_mapping_preserves_all_fields_and_value_equality(condition_id, root):
    payload = values(condition_id=condition_id, rule_root_id=root)
    binding = ConditionBinding(**payload)
    assert binding.to_dict() == payload
    assert binding.condition_id == condition_id
    assert binding.rule_root_id == root
    assert binding == ConditionBinding(**payload)
    assert hash(binding) == hash(ConditionBinding(**payload))
    assert json.loads(json.dumps(binding.to_dict())) == payload


@pytest.mark.parametrize("condition_id,valid", [
    ("SYNTH_CONDITION_A", True), ("SYNTH_001", True),
    ("", False), (" ", False), ("\t\n", False), ("synth_condition", False),
    ("SYNTH-CONDITION", False), (" SYNTH_A", False), ("SYNTH_A ", False),
    ("SYNTH_A\n", False), ("조건 표시문장", False), ("ＳＹＮＴＨ_A", False),
    (None, False), (1, False), (True, False), (1.0, False), ([], False), ({}, False),
    (StringSubclass("SYNTH_A"), False),
])
def test_condition_id_contract_matches_required_condition_without_changing_it(condition_id, valid):
    def condition():
        return RequiredCondition(condition_id, "합성 의미", ConditionRequirement.REQUIRED, ("SYN-DOC#test",))
    if valid:
        assert ConditionBinding(**values(condition_id=condition_id)).condition_id == condition().condition_id
    else:
        with pytest.raises(PolicyDataError):
            ConditionBinding(**values(condition_id=condition_id))
        with pytest.raises(PolicyDataError):
            condition()


@pytest.mark.parametrize("root,valid", [
    ("SYNTH_LEAF_A", True), ("SYNTH_GROUP_A", True), ("synth.root-a", True),
    ("  SYNTH_ROOT  ", True), ("합성 root", True),
    ("", False), (" ", False), ("\t\n", False), (None, False), (1, False),
    (True, False), (1.0, False), ([], False), ({}, False), ((), False),
    (StringSubclass("SYNTH_ROOT"), False),
])
def test_root_id_contract_matches_existing_leaf_and_group_text_validation(root, valid):
    # 기존 Rule·Group에 추가 형식 제한을 도입하지 않는다. 노드 존재 검증은 하지 않는다.
    child = PolicyRule("SYNTH_CHILD", Field.AGE, Operator.GTE, 1, evidence_refs=("synthetic-test",))
    constructors = [
        lambda: ConditionBinding(**values(rule_root_id=root)),
        lambda: PolicyRule(root, Field.AGE, Operator.GTE, 1, evidence_refs=("synthetic-test",)),
        lambda: RuleGroup(root, GroupOperator.ALL, (child,)),
    ]
    for construct in constructors:
        if valid:
            obj = construct()
            assert (obj.rule_root_id if type(obj) is ConditionBinding else obj.rule_id) == root
        else:
            with pytest.raises(PolicyDataError):
                construct()


@pytest.mark.parametrize("review", [
    "", " ", "\t\n", None, 1, True, 1.0, [], {}, (),
    StringSubclass("SYNTH-REVIEW"),
])
def test_review_is_required_exact_nonempty_string(review):
    with pytest.raises(PolicyDataError, match="implementation_review_ref"):
        ConditionBinding(**values(implementation_review_ref=review))


def test_no_whitespace_normalization_for_root_or_review_reference():
    binding = ConditionBinding(**values(rule_root_id="  SYNTH_ROOT  ", implementation_review_ref="  SYNTH-REVIEW  "))
    assert binding.to_dict() == values(rule_root_id="  SYNTH_ROOT  ", implementation_review_ref="  SYNTH-REVIEW  ")


@pytest.mark.parametrize("field,new_value", [
    ("condition_id", "SYNTH_CONDITION_B"),
    ("rule_root_id", "SYNTH_ROOT_B"),
    ("implementation_review_ref", "SYNTH-REVIEW-B"),
])
def test_each_field_is_part_of_value_equality(field, new_value):
    assert ConditionBinding(**values()) != ConditionBinding(**values(**{field: new_value}))


@pytest.mark.parametrize("field", ["condition_id", "rule_root_id", "implementation_review_ref"])
def test_fields_cannot_be_assigned_or_deleted(field):
    binding = ConditionBinding(**values())
    with pytest.raises(FrozenInstanceError):
        setattr(binding, field, "changed")
    with pytest.raises(FrozenInstanceError):
        delattr(binding, field)
    assert not hasattr(binding, "__dict__")


def test_repeated_snapshots_are_equal_and_independent():
    binding = ConditionBinding(**values())
    first, second = binding.to_dict(), binding.to_dict()
    assert first == second == values()
    assert first is not second
    first.clear()
    assert binding.to_dict() == second


@pytest.mark.parametrize("missing", ["condition_id", "rule_root_id", "implementation_review_ref"])
def test_all_fields_must_be_explicit(missing):
    payload = values()
    del payload[missing]
    with pytest.raises(TypeError):
        ConditionBinding(**payload)


@pytest.mark.parametrize("extra", [
    "scope", "edition_id", "quarter", "policy_id", "condition", "rule", "rule_ids",
    "implemented", "verified", "full", "coverage_status", "verification_status",
    "acceptance_status", "evidence_refs", "benefit_amount", "payment_cadence",
])
def test_only_mapping_fields_are_present(extra):
    binding = ConditionBinding(**values())
    assert [field.name for field in fields(binding)] == [
        "condition_id", "rule_root_id", "implementation_review_ref",
    ]
    assert not hasattr(binding, extra)
    with pytest.raises(TypeError):
        ConditionBinding(**values(**{extra: None}))


def test_single_bindings_do_not_validate_collection_duplicates_or_conflicts():
    first = ConditionBinding(**values())
    same = ConditionBinding(**values())
    same_condition = ConditionBinding(**values(rule_root_id="SYNTH_OTHER_ROOT"))
    same_root = ConditionBinding(**values(condition_id="SYNTH_OTHER_CONDITION"))
    assert first == same
    assert first != same_condition and first != same_root


def test_replace_revalidates_without_changing_original():
    binding = ConditionBinding(**values())
    changed = replace(binding, rule_root_id="SYNTH_ROOT_B")
    assert binding.rule_root_id == "SYNTH_RULE_ROOT_A"
    assert changed.rule_root_id == "SYNTH_ROOT_B"
    with pytest.raises(PolicyDataError):
        replace(binding, implementation_review_ref=None)


def test_mapping_does_not_lookup_inventory_tree_or_review_records(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Binding 값 생성에서 tree 또는 외부 기록을 조회했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("backend.policy_engine.models.walk_nodes", forbidden)
    monkeypatch.setattr(RequiredCondition, "__post_init__", forbidden)
    binding = ConditionBinding("SYNTH_UNREGISTERED", "SYNTH_NONEXISTENT_ROOT", "SYNTH-UNRESOLVED-REVIEW")
    assert binding.to_dict()["rule_root_id"] == "SYNTH_NONEXISTENT_ROOT"


def test_existing_error_hierarchy_does_not_echo_raw_values():
    secret = "private-invalid-id"
    with pytest.raises(PolicyDataError) as caught:
        ConditionBinding(**values(condition_id=secret))
    assert isinstance(caught.value, EngineValidationError)
    assert secret not in str(caught.value)


def test_model_has_no_inventory_tree_or_other_domain_dependencies():
    tree = ast.parse(inspect.getsource(domain))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {"dataclasses", "errors"}
    assert {node.name for node in tree.body if isinstance(node, ast.ClassDef)} == {"ConditionBinding"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {
        "Policy", "RuleGroup", "RuleNode", "RequiredCondition", "ConditionInventory", "ApplicabilityScope",
        "EligibilityCoverage", "PolicyBenefitAcceptance", "CashflowInput", "date", "datetime",
    }
