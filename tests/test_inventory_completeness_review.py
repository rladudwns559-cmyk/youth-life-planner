"""합성 review metadata의 값 계약만 검증한다. 실제 검토·Inventory 완결성 검증은 아니다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.policy_data import ApplicabilityScope, InventoryCompletenessReview
from backend.policy_engine.policy_data import coverage_review as domain


NAMES = [
    "review_ref", "policy_id", "scope", "inventory_version", "inventory_fingerprint",
    "dataset_version", "source_registry_fingerprint", "reviewed_at", "review_artifact_ref",
]


def values(**changes):
    return {
        "review_ref": "SYNTH_INVENTORY_REVIEW_001", "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "inventory_version": "i0001",
        "inventory_fingerprint": "a1" * 32, "dataset_version": "synthetic-review-dataset-001",
        "source_registry_fingerprint": "b2" * 32, "reviewed_at": date(2024, 2, 29),
        "review_artifact_ref": "SYNTH_REVIEW_ARTIFACT_001", **changes,
    }


class StringSubclass(str):
    pass


class DateSubclass(date):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


@pytest.mark.parametrize("scope", [ApplicabilityScope("2026", 3), ApplicabilityScope("2026", None), ApplicabilityScope("2027", 3)])
@pytest.mark.parametrize("reviewed_at", [date(2024, 2, 29), date.min, date.max])
def test_explicit_metadata_is_preserved_in_all_nine_fields(scope, reviewed_at):
    supplied = values(scope=scope, reviewed_at=reviewed_at)
    record = InventoryCompletenessReview(**supplied)
    expected = {**supplied, "scope": scope.to_dict(), "reviewed_at": reviewed_at.isoformat()}
    assert record.scope is scope
    assert record.reviewed_at is reviewed_at
    assert [field.name for field in fields(record)] == NAMES
    assert record.to_dict() == expected
    assert record == InventoryCompletenessReview(**supplied)
    assert hash(record) == hash(InventoryCompletenessReview(**supplied))
    assert json.loads(json.dumps(record.to_dict())) == expected


@pytest.mark.parametrize("name", ["review_ref", "dataset_version", "review_artifact_ref"])
@pytest.mark.parametrize("bad", ["", " ", "\t\n", None, 1, True, 1.0, [], {}, StringSubclass("SYNTH_VALUE")])
def test_text_fields_require_exact_nonempty_string(name, bad):
    with pytest.raises(PolicyDataError, match=name):
        InventoryCompletenessReview(**values(**{name: bad}))


@pytest.mark.parametrize("name", ["review_ref", "dataset_version", "review_artifact_ref"])
def test_valid_text_is_not_stripped_generated_or_interpreted_as_path(name):
    value = "  SYNTH_VALUE  "
    record = InventoryCompletenessReview(**values(**{name: value}))
    assert getattr(record, name) == record.to_dict()[name] == value


@pytest.mark.parametrize("policy_id", [
    "", " ", "SYNTH_POLICY", "synth-policy", "SYNTH--POLICY", " SYNTH-POLICY", "SYNTH-POLICY ",
    "SYNTH-POLICY\n", None, 1, True, 1.0, [], {}, StringSubclass("SYNTH-POLICY"),
])
def test_policy_id_uses_existing_inventory_canonical_contract(policy_id):
    with pytest.raises(PolicyDataError, match="policy_id"):
        InventoryCompletenessReview(**values(policy_id=policy_id))


@pytest.mark.parametrize("scope", [None, {}, ("2026", 3), "2026-Q3", [], 3, True, object(), ScopeSubclass("2026", 3)])
def test_scope_requires_exact_preconstructed_value(scope):
    with pytest.raises(PolicyDataError, match="scope"):
        InventoryCompletenessReview(**values(scope=scope))


@pytest.mark.parametrize("version", ["i0001", "i9999", "i10000", "i100000"])
def test_valid_inventory_version_is_preserved(version):
    record = InventoryCompletenessReview(**values(inventory_version=version))
    assert record.inventory_version == record.to_dict()["inventory_version"] == version


@pytest.mark.parametrize("version", [
    "", " ", None, 1, True, [], {}, "i0000", "i1", "I0001", "r0001", "i00001",
    " i0001", "i0001 ", "i0001\n", "i０００１", StringSubclass("i0001"),
])
def test_inventory_version_does_not_accept_aliases_or_normalization(version):
    with pytest.raises(PolicyDataError, match="inventory_version"):
        InventoryCompletenessReview(**values(inventory_version=version))


@pytest.mark.parametrize("name", ["inventory_fingerprint", "source_registry_fingerprint"])
@pytest.mark.parametrize("fingerprint", ["0" * 64, "0123456789abcdef" * 4, "f" * 64])
def test_canonical_fingerprint_is_only_a_preserved_explicit_value(name, fingerprint):
    record = InventoryCompletenessReview(**values(**{name: fingerprint}))
    assert getattr(record, name) == record.to_dict()[name] == fingerprint


@pytest.mark.parametrize("name", ["inventory_fingerprint", "source_registry_fingerprint"])
@pytest.mark.parametrize("bad", [
    "", "a" * 63, "a" * 65, "g" * 64, "A" * 64, " " + "a" * 64,
    "a" * 64 + " ", "a" * 64 + "\n", "sha256:" + "a" * 64,
    None, 1, True, [], {}, StringSubclass("a" * 64),
])
def test_fingerprint_requires_exact_lowercase_hex_without_conversion(name, bad):
    with pytest.raises(PolicyDataError, match=name):
        InventoryCompletenessReview(**values(**{name: bad}))


@pytest.mark.parametrize("reviewed_at", [
    datetime(2024, 2, 29), "2024-02-29", 20240229, True, None, [], {}, DateSubclass(2024, 2, 29),
])
def test_reviewed_at_requires_exact_date_without_conversion(reviewed_at):
    with pytest.raises(PolicyDataError, match="reviewed_at"):
        InventoryCompletenessReview(**values(reviewed_at=reviewed_at))


@pytest.mark.parametrize("field,new_value", [
    ("review_ref", "SYNTH_REVIEW_002"), ("policy_id", "SYNTH-POLICY-B"),
    ("scope", ApplicabilityScope("2026", None)), ("inventory_version", "i0002"),
    ("inventory_fingerprint", "c3" * 32), ("dataset_version", "synthetic-review-dataset-002"),
    ("source_registry_fingerprint", "d4" * 32), ("reviewed_at", date(2025, 1, 1)),
    ("review_artifact_ref", "SYNTH_ARTIFACT_002"),
])
def test_every_field_is_part_of_value_equality(field, new_value):
    assert InventoryCompletenessReview(**values()) != InventoryCompletenessReview(**values(**{field: new_value}))


@pytest.mark.parametrize("name", NAMES)
def test_all_fields_are_explicit_required_arguments(name):
    payload = values()
    del payload[name]
    with pytest.raises(TypeError):
        InventoryCompletenessReview(**payload)


@pytest.mark.parametrize("name", NAMES)
def test_every_field_is_frozen_against_assignment_and_deletion(name):
    record = InventoryCompletenessReview(**values())
    with pytest.raises(FrozenInstanceError):
        setattr(record, name, None)
    with pytest.raises(FrozenInstanceError):
        delattr(record, name)
    assert not hasattr(record, "__dict__")


def test_nested_scope_and_returned_snapshot_are_independent():
    scope = ApplicabilityScope("2026", 3)
    record = InventoryCompletenessReview(**values(scope=scope))
    first, second = record.to_dict(), record.to_dict()
    assert first == second and first is not second
    assert first["scope"] is not second["scope"]
    first["scope"]["quarter"] = None
    first["inventory_fingerprint"] = "0" * 64
    assert record.to_dict() == second
    assert record.scope is scope and scope.quarter == 3
    with pytest.raises(FrozenInstanceError):
        record.scope.quarter = None


def test_same_review_ref_with_other_metadata_is_not_a_single_record_conflict_check():
    first = InventoryCompletenessReview(**values())
    second = replace(first, inventory_fingerprint="0" * 64)
    assert first.review_ref == second.review_ref and first != second
    # Context 전체의 중복 review_ref 검증은 구현하지 않는다.


def test_replace_revalidates_without_changing_original():
    record = InventoryCompletenessReview(**values())
    with pytest.raises(PolicyDataError):
        replace(record, inventory_fingerprint="A" * 64)
    assert record.inventory_fingerprint == "a1" * 32


@pytest.mark.parametrize("extra", [
    "inventory", "condition_ids", "required_conditions", "rule_version", "rule_root_id", "tree_fingerprint",
    "subtree_fingerprint", "status", "coverage_status", "verification_status", "acceptance_status",
    "reviewed_by", "review_context", "policy_evaluation", "cashflow", "manifest", "is_full", "is_stale",
])
def test_record_has_no_inventory_tree_approval_or_reviewer_fields(extra):
    record = InventoryCompletenessReview(**values())
    assert not hasattr(record, extra)
    assert set(record.to_dict()) == set(NAMES)
    with pytest.raises(TypeError):
        InventoryCompletenessReview(**values(**{extra: None}))


def test_metadata_construction_performs_no_hashing_lookup_or_io(monkeypatch):
    payload = values()
    def forbidden(*args, **kwargs):
        pytest.fail("검토 metadata 값 처리에서 해시 계산·외부 조회·자동 시각을 호출했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("hashlib.sha256", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr(ApplicabilityScope, "__post_init__", forbidden)
    record = InventoryCompletenessReview(**payload)
    assert record.to_dict()["review_artifact_ref"] == "SYNTH_REVIEW_ARTIFACT_001"


def test_existing_error_hierarchy_does_not_echo_input_value():
    secret = "private-invalid-policy-payload"
    with pytest.raises(PolicyDataError) as caught:
        InventoryCompletenessReview(**values(policy_id=secret))
    assert isinstance(caught.value, EngineValidationError)
    assert secret not in str(caught.value)


def test_direct_dependencies_and_methods_only_describe_metadata():
    tree = ast.parse(inspect.getsource(domain))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {
        "dataclasses", "datetime", "errors", "eligibility_coverage",
    }
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == ["InventoryCompletenessReview"]
    assert {node.name for node in classes[0].body if isinstance(node, ast.FunctionDef)} == {"__post_init__", "to_dict"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {
        "ConditionInventory", "RequiredCondition", "Policy", "RuleNode", "DatasetManifest", "hashlib",
        "CoverageReviewContext", "ImplementationBindingReview", "CoverageResult", "PolicyEvaluation", "CashflowInput",
    }
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"today", "now", "exists", "sha256"} for node in ast.walk(tree))
    assert not any(isinstance(node, ast.FunctionDef) for node in tree.body)
