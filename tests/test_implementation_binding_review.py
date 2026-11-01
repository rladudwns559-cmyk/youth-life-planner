"""합성 metadata 전용. 실제 정책·구현 검토 또는 지문 계산을 수행하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.models import require_text
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ImplementationBindingReview,
    InventoryCompletenessReview,
)
from backend.policy_engine.policy_data import implementation_review as domain


class TextSubclass(str):
    pass


class DateSubclass(date):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


NAMES = (
    "review_ref", "policy_id", "scope", "condition_id", "rule_root_id",
    "inventory_version", "inventory_fingerprint", "rule_version", "policy_tree_fingerprint",
    "subtree_fingerprint", "dataset_version", "source_registry_fingerprint",
    "implementation_fingerprint", "reviewed_at", "review_artifact_ref",
)
TEXT_FIELDS = ("review_ref", "rule_root_id", "rule_version", "dataset_version", "review_artifact_ref")
HASH_FIELDS = ("inventory_fingerprint", "policy_tree_fingerprint", "subtree_fingerprint",
               "source_registry_fingerprint", "implementation_fingerprint")


def values(**changes):
    payload = dict(
        review_ref="SYNTH-IMPL-REVIEW", policy_id="SYNTH-POLICY",
        scope=ApplicabilityScope("2026", 3), condition_id="SYNTH_CONDITION_A",
        rule_root_id="SYNTH_RULE_A", inventory_version="i0001",
        inventory_fingerprint="a1" * 32, rule_version="r0001",
        policy_tree_fingerprint="b2" * 32, subtree_fingerprint="c3" * 32,
        dataset_version="SYNTH-DATASET", source_registry_fingerprint="d4" * 32,
        implementation_fingerprint="e5" * 32, reviewed_at=date(2026, 10, 21),
        review_artifact_ref="SYNTH-ARTIFACT-NOT-LOOKED-UP",
    )
    payload.update(changes)
    return payload


@pytest.mark.parametrize("root", ["SYNTH_RULE_A", "SYNTH_RULE_GROUP_A"])
@pytest.mark.parametrize("quarter", [3, None])
def test_leaf_and_group_claims_with_explicit_quarter_or_annual_scope(root, quarter):
    payload = values(rule_root_id=root, scope=ApplicabilityScope("2026", quarter))
    record = ImplementationBindingReview(**payload)
    expected = {**payload, "scope": {"edition_id": "2026", "quarter": quarter}, "reviewed_at": "2026-10-21"}
    assert record.to_dict() == expected
    assert tuple(record.to_dict()) == NAMES
    assert json.loads(json.dumps(record.to_dict())) == expected
    assert record == ImplementationBindingReview(**payload)
    assert record.scope is payload["scope"]


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("bad", ["", " \t\n", None, 1, True, [], TextSubclass("SYNTH")])
def test_exact_nonblank_text_contract(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        ImplementationBindingReview(**values(**{field: bad}))


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_text_is_preserved_without_strip_or_external_ref_resolution(field):
    original = " \tSYNTH://nonexistent/artifact\n"
    record = ImplementationBindingReview(**values(**{field: original}))
    assert getattr(record, field) == original
    assert record.to_dict()[field] == original


@pytest.mark.parametrize("bad", ["", " ", "synth-policy", "SYNTH_POLICY", "-SYNTH", "SYNTH--POLICY",
                                 "SYNTH-", " SYNTH", "SYNTH\n", "정책", None, True, 2, TextSubclass("SYNTH")])
def test_policy_id_is_canonical_without_normalization(bad):
    with pytest.raises(PolicyDataError, match="policy_id"):
        ImplementationBindingReview(**values(policy_id=bad))


@pytest.mark.parametrize("bad", [None, {}, ("2026", 3), "2026-Q3", object(), ScopeSubclass("2026", 3)])
def test_scope_requires_exact_existing_value_model(bad):
    with pytest.raises(PolicyDataError, match="scope"):
        ImplementationBindingReview(**values(scope=bad))


@pytest.mark.parametrize("bad", ["", " ", "synth_a", "SYNTH-A", "SYNTH.A", " SYNTH", "SYNTH\n",
                                 "조건", None, 1, True, TextSubclass("SYNTH")])
def test_condition_id_matches_binding_rejection(bad):
    with pytest.raises(PolicyDataError):
        ConditionBinding(bad, "SYNTH_ROOT", "SYNTH_REF")
    with pytest.raises(PolicyDataError, match="condition_id"):
        ImplementationBindingReview(**values(condition_id=bad))


@pytest.mark.parametrize("condition_id", ["A", "123", "_", "SYNTH_CONDITION_A"])
@pytest.mark.parametrize("root", ["SYNTH_LEAF", "SYNTH_GROUP", " padded root "])
def test_binding_id_contract_preserves_accepted_values(condition_id, root):
    binding = ConditionBinding(condition_id, root, "SYNTH_REF")
    record = ImplementationBindingReview(**values(condition_id=condition_id, rule_root_id=root))
    assert (record.condition_id, record.rule_root_id) == (binding.condition_id, binding.rule_root_id)


@pytest.mark.parametrize("version", ["r0001", "r0002", "custom-policy-version", " r0001 ", "r0000"])
def test_rule_version_uses_policy_text_contract_without_new_envelope_restriction(version):
    require_text(version, "rule_version", PolicyDataError)
    assert ImplementationBindingReview(**values(rule_version=version)).rule_version == version


@pytest.mark.parametrize("version", ["i0001", "i9999", "i10000"])
def test_inventory_version_matches_inventory_review(version):
    payload = values(inventory_version=version)
    inventory = InventoryCompletenessReview(**{key: payload[key] for key in (
        "review_ref", "policy_id", "scope", "inventory_version", "inventory_fingerprint",
        "dataset_version", "source_registry_fingerprint", "reviewed_at", "review_artifact_ref",
    )})
    assert ImplementationBindingReview(**payload).inventory_version == inventory.inventory_version


@pytest.mark.parametrize("bad", ["", "i0000", "i001", "i00001", "i-001", "I0001", " i0001", "i0001\n",
                                 "i１２３４", None, 1, True, TextSubclass("i0001")])
def test_inventory_version_rejects_malformed_or_coerced_values(bad):
    with pytest.raises(PolicyDataError, match="inventory_version"):
        ImplementationBindingReview(**values(inventory_version=bad))


@pytest.mark.parametrize("field", HASH_FIELDS)
@pytest.mark.parametrize("bad", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, " " + "a" * 64,
                                 "a" * 64 + "\n", "sha256:" + "a" * 64, None, 1, True, TextSubclass("a" * 64)])
def test_each_fingerprint_requires_exact_lowercase_sha256(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        ImplementationBindingReview(**values(**{field: bad}))


@pytest.mark.parametrize("field", HASH_FIELDS)
def test_each_fingerprint_is_independent_and_explicit(field):
    original = ImplementationBindingReview(**values())
    changed = replace(original, **{field: "0123456789abcdef" * 4})
    assert changed != original and changed.review_ref == original.review_ref
    assert {name for name in NAMES if getattr(changed, name) != getattr(original, name)} == {field}


@pytest.mark.parametrize("bad", [datetime(2026, 10, 21), "2026-10-21", 20261021, True, None,
                                 DateSubclass(2026, 10, 21)])
def test_reviewed_at_requires_exact_date_without_conversion(bad):
    with pytest.raises(PolicyDataError, match="reviewed_at"):
        ImplementationBindingReview(**values(reviewed_at=bad))


def test_leap_date_is_explicit_and_serializes_iso():
    record = ImplementationBindingReview(**values(reviewed_at=date(2024, 2, 29)))
    assert record.to_dict()["reviewed_at"] == "2024-02-29"


@pytest.mark.parametrize("name", NAMES)
def test_every_field_is_required_without_generated_defaults(name):
    payload = values()
    del payload[name]
    with pytest.raises(TypeError):
        ImplementationBindingReview(**payload)


@pytest.mark.parametrize("name", NAMES)
def test_every_field_participates_in_value_equality_and_is_frozen(name):
    record = ImplementationBindingReview(**values())
    if name == "scope":
        other = ApplicabilityScope("2026", None)
    elif name == "reviewed_at":
        other = date(2024, 2, 29)
    elif name in HASH_FIELDS:
        other = "0" * 64
    elif name == "inventory_version":
        other = "i0002"
    else:
        other = "SYNTH2"
    assert replace(record, **{name: other}) != record
    with pytest.raises(FrozenInstanceError):
        setattr(record, name, other)
    with pytest.raises(FrozenInstanceError):
        delattr(record, name)
    assert not hasattr(record, "__dict__")


def test_snapshots_are_independent_and_nested_scope_stays_immutable():
    record = ImplementationBindingReview(**values())
    before = record.to_dict()
    for _ in range(3):
        snapshot = record.to_dict()
        assert snapshot == before and snapshot is not before
        assert snapshot["scope"] is not before["scope"]
        snapshot["scope"]["quarter"] = None
        snapshot["subtree_fingerprint"] = "0" * 64
    assert record.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        record.scope.quarter = None


def test_fields_exclude_objects_statuses_and_candidate_aliases():
    assert tuple(field.name for field in fields(ImplementationBindingReview)) == NAMES
    record = ImplementationBindingReview(**values())
    for extra in ("binding", "inventory", "policy", "root", "rule_node", "status", "implementation_valid",
                  "coverage_status", "verification_status", "acceptance_status", "reviewed_by",
                  "policy_evaluation", "cashflow", "review_context", "tree_fingerprint", "engine_artifact_hash"):
        assert not hasattr(record, extra)
        with pytest.raises(TypeError):
            ImplementationBindingReview(**values(**{extra: None}))


def test_claimed_metadata_does_not_hash_resolve_revalidate_or_access_external_resources(monkeypatch):
    payload = values(rule_root_id="SYNTH_NONEXISTENT_ROOT", review_artifact_ref="file:///SYNTH-NO-ARTIFACT")
    def forbidden(*args, **kwargs):
        pytest.fail("값 모델에서 외부 조회·지문 계산·하위 객체 재검증을 호출했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("hashlib.sha256", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr(ApplicabilityScope, "__post_init__", forbidden)
    record = ImplementationBindingReview(**payload)
    assert record.to_dict()["rule_root_id"] == "SYNTH_NONEXISTENT_ROOT"
    assert record.scope is payload["scope"]


def test_errors_use_existing_hierarchy_without_echoing_raw_payload():
    private = "private-invalid-policy-payload"
    with pytest.raises(PolicyDataError) as caught:
        ImplementationBindingReview(**values(policy_id=private))
    assert isinstance(caught.value, EngineValidationError)
    assert private not in str(caught.value)


def test_module_dependencies_are_only_value_metadata_without_matching_or_traversal():
    tree = ast.parse(inspect.getsource(domain))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {
        "dataclasses", "datetime", "errors", "eligibility_coverage",
    }
    assert {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} == {"re"}
    assert not any(isinstance(node, ast.FunctionDef) for node in tree.body)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert methods == {"__post_init__", "to_dict"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"Policy", "RuleNode", "RuleGroup", "ConditionBinding", "ConditionInventory",
                        "InventoryCompletenessReview", "CoverageReviewContext", "CoverageResult",
                        "PolicyEvaluation", "CashflowInput", "walk_nodes", "open", "hashlib"}
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"today", "now", "exists", "sha256"} for node in ast.walk(tree))
