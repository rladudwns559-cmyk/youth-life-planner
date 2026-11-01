"""합성 review collection의 구조만 검증한다. 실제 정책·검토·지문 계산은 사용하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.policy_data import (
    ApplicabilityScope, CoverageReviewContext, ImplementationBindingReview, InventoryCompletenessReview,
)
from backend.policy_engine.policy_data import coverage_review_context as domain


class TextSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class InventorySubclass(InventoryCompletenessReview):
    pass


class ImplementationSubclass(ImplementationBindingReview):
    pass


NAMES = ("policy_id", "scope", "dataset_version", "source_registry_fingerprint",
         "implementation_fingerprint", "inventory_reviews", "implementation_reviews")
COLLECTIONS = ("inventory_reviews", "implementation_reviews")
HASH_FIELDS = ("source_registry_fingerprint", "implementation_fingerprint")


def inventory(**changes):
    payload = dict(
        review_ref="SYNTH-INV-A", policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3),
        inventory_version="i0001", inventory_fingerprint="a1" * 32,
        dataset_version="SYNTH-DATASET", source_registry_fingerprint="b2" * 32,
        reviewed_at=date(2026, 10, 21), review_artifact_ref="SYNTH-NO-ARTIFACT",
    )
    payload.update(changes)
    return InventoryCompletenessReview(**payload)


def implementation(**changes):
    payload = dict(
        review_ref="SYNTH-IMPL-A", policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3),
        condition_id="SYNTH_CONDITION_A", rule_root_id="SYNTH_ROOT_A",
        inventory_version="i0001", inventory_fingerprint="a1" * 32, rule_version="r0001",
        policy_tree_fingerprint="c3" * 32, subtree_fingerprint="d4" * 32,
        dataset_version="SYNTH-DATASET", source_registry_fingerprint="b2" * 32,
        implementation_fingerprint="e5" * 32, reviewed_at=date(2026, 10, 21),
        review_artifact_ref="SYNTH-NO-ARTIFACT",
    )
    payload.update(changes)
    return ImplementationBindingReview(**payload)


def values(**changes):
    payload = dict(
        policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3), dataset_version="SYNTH-DATASET",
        source_registry_fingerprint="b2" * 32, implementation_fingerprint="e5" * 32,
        inventory_reviews=(), implementation_reviews=(),
    )
    payload.update(changes)
    return payload


@pytest.mark.parametrize("quarter", [3, None])
@pytest.mark.parametrize("with_inventory,with_implementation", [(False, False), (True, False), (False, True), (True, True)])
def test_empty_single_kind_and_mixed_context_preserve_explicit_scope(quarter, with_inventory, with_implementation):
    scope = ApplicabilityScope("2026", quarter)
    inv = (inventory(scope=scope),) if with_inventory else ()
    impl = (implementation(scope=scope),) if with_implementation else ()
    payload = values(scope=scope, inventory_reviews=inv, implementation_reviews=impl)
    context = CoverageReviewContext(**payload)
    assert context.scope is scope
    assert context.inventory_reviews is inv and context.implementation_reviews is impl
    assert context.to_dict() == {
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": quarter},
        "dataset_version": "SYNTH-DATASET", "source_registry_fingerprint": "b2" * 32,
        "implementation_fingerprint": "e5" * 32, "inventory_reviews": [r.to_dict() for r in inv],
        "implementation_reviews": [r.to_dict() for r in impl],
    }
    assert CoverageReviewContext(**payload) == context
    assert json.loads(json.dumps(context.to_dict())) == context.to_dict()


@pytest.mark.parametrize("bad", ["", " ", "synth-policy", "SYNTH_POLICY", "SYNTH--POLICY", "-SYNTH",
                                 "SYNTH-", " SYNTH", "SYNTH\n", None, True, 1, TextSubclass("SYNTH")])
def test_context_policy_id_matches_canonical_contract(bad):
    with pytest.raises(PolicyDataError, match="policy_id"):
        CoverageReviewContext(**values(policy_id=bad))


@pytest.mark.parametrize("bad", [None, {}, ("2026", 3), "2026-Q3", object(), ScopeSubclass("2026", 3)])
def test_context_scope_is_exact_value_type(bad):
    with pytest.raises(PolicyDataError, match="scope"):
        CoverageReviewContext(**values(scope=bad))


@pytest.mark.parametrize("bad", ["", " \t\n", None, 1, True, [], TextSubclass("SYNTH-DATASET")])
def test_context_dataset_is_exact_nonblank_string(bad):
    with pytest.raises(PolicyDataError, match="dataset_version"):
        CoverageReviewContext(**values(dataset_version=bad))


def test_context_dataset_does_not_strip_or_require_canonical_version_syntax():
    assert CoverageReviewContext(**values(dataset_version=" SYNTH data \n")).dataset_version == " SYNTH data \n"


@pytest.mark.parametrize("field", HASH_FIELDS)
@pytest.mark.parametrize("bad", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, " " + "a" * 64,
                                 "a" * 64 + "\n", "sha256:" + "a" * 64, None, 1, True, TextSubclass("a" * 64)])
def test_context_fingerprints_are_strict_metadata_only(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        CoverageReviewContext(**values(**{field: bad}))


@pytest.mark.parametrize("field", COLLECTIONS)
@pytest.mark.parametrize("bad", [[], set(), {}, None, "", iter(()), (x for x in ()), TupleSubclass()])
def test_collections_reject_nonexact_tuple_without_conversion(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        CoverageReviewContext(**values(**{field: bad}))


@pytest.mark.parametrize("field", COLLECTIONS)
@pytest.mark.parametrize("bad", [{}, None, "SYNTH-REF", 1, True, object()])
def test_collection_elements_reject_raw_values(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        CoverageReviewContext(**values(**{field: (bad,)}))


def test_two_review_kinds_cannot_be_swapped_or_subclassed():
    inv, impl = inventory(), implementation()
    wrong = (
        ("inventory_reviews", impl), ("implementation_reviews", inv),
        ("inventory_reviews", InventorySubclass(**{f.name: getattr(inv, f.name) for f in fields(inv)})),
        ("implementation_reviews", ImplementationSubclass(**{f.name: getattr(impl, f.name) for f in fields(impl)})),
    )
    for field, record in wrong:
        with pytest.raises(PolicyDataError, match=field):
            CoverageReviewContext(**values(**{field: (record,)}))


@pytest.mark.parametrize("field,factory", [("inventory_reviews", inventory), ("implementation_reviews", implementation)])
def test_other_policy_record_after_valid_record_is_rejected_without_filtering(field, factory):
    first = factory()
    wrong = factory(review_ref="SYNTH-OTHER", policy_id="SYNTH-OTHER-POLICY")
    with pytest.raises(PolicyDataError, match="policy_id"):
        CoverageReviewContext(**values(**{field: (first, wrong)}))


@pytest.mark.parametrize("field,factory", [("inventory_reviews", inventory), ("implementation_reviews", implementation)])
@pytest.mark.parametrize("scope", [ApplicabilityScope("2026", None), ApplicabilityScope("2026", 2), ApplicabilityScope("2027", 3)])
def test_scope_mismatch_rejects_annual_other_quarter_and_edition(field, factory, scope):
    wrong = factory(review_ref="SYNTH-OTHER", scope=scope)
    with pytest.raises(PolicyDataError, match="scope"):
        CoverageReviewContext(**values(**{field: (factory(), wrong)}))


def test_scope_equality_is_by_value_without_replacing_original_objects():
    scope = ApplicabilityScope("2026", 3)
    record = inventory()
    assert record.scope is not scope and record.scope == scope
    context = CoverageReviewContext(**values(scope=scope, inventory_reviews=(record,)))
    assert context.scope is scope and context.inventory_reviews[0] is record
    assert context.inventory_reviews[0].scope is record.scope


@pytest.mark.parametrize("field,factory", [("inventory_reviews", inventory), ("implementation_reviews", implementation)])
@pytest.mark.parametrize("duplicate_kind", ["same_object", "equal_object", "different_metadata"])
def test_duplicate_refs_within_kind_always_error(field, factory, duplicate_kind):
    first = factory()
    second = first if duplicate_kind == "same_object" else replace(first)
    if duplicate_kind == "different_metadata":
        second = replace(first, inventory_fingerprint="0" * 64)
    with pytest.raises(PolicyDataError, match="review_ref"):
        CoverageReviewContext(**values(**{field: (first, second)}))


def test_duplicate_ref_across_kinds_is_error():
    with pytest.raises(PolicyDataError, match="review_ref"):
        CoverageReviewContext(**values(inventory_reviews=(inventory(review_ref="SYNTH-SHARED"),),
                                      implementation_reviews=(implementation(review_ref="SYNTH-SHARED"),)))


def test_review_refs_remain_exact_without_strip_or_case_normalization():
    records = (inventory(review_ref="SYNTH-REF"), inventory(review_ref=" SYNTH-REF "), inventory(review_ref="synth-ref"))
    context = CoverageReviewContext(**values(inventory_reviews=records))
    assert context.inventory_reviews is records
    assert [r["review_ref"] for r in context.to_dict()["inventory_reviews"]] == [r.review_ref for r in records]


def test_historical_versions_datasets_dates_and_fingerprints_coexist_without_matching():
    inv = (inventory(), inventory(review_ref="SYNTH-INV-OLD", inventory_version="i0002",
                                 inventory_fingerprint="0" * 64, dataset_version="SYNTH-OLD",
                                 source_registry_fingerprint="1" * 64, reviewed_at=date(2024, 2, 29)))
    first = implementation()
    impl = (first, replace(first, review_ref="SYNTH-IMPL-OLD", inventory_version="i0002",
                           inventory_fingerprint="2" * 64, rule_version="r0002", policy_tree_fingerprint="3" * 64,
                           subtree_fingerprint="4" * 64, dataset_version="SYNTH-OLDER",
                           source_registry_fingerprint="5" * 64, implementation_fingerprint="6" * 64,
                           reviewed_at=date(2024, 2, 29)),
            replace(first, review_ref="SYNTH-IMPL-SAME-VERSION", subtree_fingerprint="7" * 64),
            replace(first, review_ref="SYNTH-IMPL-B", condition_id="SYNTH_CONDITION_B", rule_root_id="SYNTH_ROOT_B"))
    context = CoverageReviewContext(**values(inventory_reviews=inv, implementation_reviews=impl,
                                            dataset_version="SYNTH-CURRENT", source_registry_fingerprint="8" * 64,
                                            implementation_fingerprint="9" * 64))
    assert context.inventory_reviews is inv and context.implementation_reviews is impl
    assert context.to_dict()["implementation_reviews"] == [r.to_dict() for r in impl]
    # 현재 Coverage/tree가 없으므로 같은 version의 지문 모순조차 여기서 판정하지 않는다.


@pytest.mark.parametrize("field,factory", [("inventory_reviews", inventory), ("implementation_reviews", implementation)])
def test_input_order_is_preserved_and_part_of_value_equality(field, factory):
    first, second = factory(review_ref="SYNTH-Z"), factory(review_ref="SYNTH-A")
    original = (first, second)
    context = CoverageReviewContext(**values(**{field: original}))
    reverse = CoverageReviewContext(**values(**{field: tuple(reversed(original))}))
    assert context != reverse
    assert context == CoverageReviewContext(**values(**{field: original}))
    assert context.to_dict()[field] == [first.to_dict(), second.to_dict()]
    assert getattr(context, field) is original


@pytest.mark.parametrize("field", NAMES)
def test_all_seven_fields_are_explicit_and_frozen(field):
    payload = values()
    del payload[field]
    with pytest.raises(TypeError):
        CoverageReviewContext(**payload)
    context = CoverageReviewContext(**values())
    with pytest.raises(FrozenInstanceError):
        setattr(context, field, None)
    with pytest.raises(FrozenInstanceError):
        delattr(context, field)
    assert not hasattr(context, "__dict__")


@pytest.mark.parametrize("field,other", [
    ("policy_id", "SYNTH-OTHER"), ("scope", ApplicabilityScope("2026", None)),
    ("dataset_version", "SYNTH-OTHER"), ("source_registry_fingerprint", "0" * 64),
    ("implementation_fingerprint", "0" * 64), ("inventory_reviews", (inventory(),)),
    ("implementation_reviews", (implementation(),)),
])
def test_equality_includes_all_actual_fields(field, other):
    context = CoverageReviewContext(**values())
    assert replace(context, **{field: other}) != context


def test_nested_models_and_output_snapshots_are_independent_and_immutable():
    context = CoverageReviewContext(**values(inventory_reviews=(inventory(),), implementation_reviews=(implementation(),)))
    baseline = context.to_dict()
    for _ in range(3):
        snapshot = context.to_dict()
        assert snapshot == baseline and snapshot is not baseline
        snapshot["scope"]["quarter"] = None
        snapshot["inventory_reviews"][0]["scope"]["edition_id"] = "2027"
        snapshot["implementation_reviews"][0]["subtree_fingerprint"] = "0" * 64
        snapshot["inventory_reviews"].clear()
        snapshot["implementation_reviews"].append({})
    assert context.to_dict() == baseline
    for target, name in ((context.scope, "quarter"), (context.inventory_reviews[0], "review_ref"),
                         (context.implementation_reviews[0], "subtree_fingerprint")):
        with pytest.raises(FrozenInstanceError):
            setattr(target, name, None)
        with pytest.raises(FrozenInstanceError):
            delattr(target, name)


def test_only_seven_fields_without_lookup_cache_target_or_status_api():
    assert tuple(f.name for f in fields(CoverageReviewContext)) == NAMES
    context = CoverageReviewContext(**values())
    assert tuple(context.to_dict()) == NAMES
    for extra in ("coverage", "inventory", "binding", "policy", "status", "review_complete", "all_reviews_present",
                  "stale", "matched_reviews", "missing_reviews", "verification_status", "acceptance_status",
                  "policy_evaluation", "cashflow", "cache", "get_review", "get_inventory_review", "get_implementation_review"):
        assert not hasattr(context, extra)
        with pytest.raises(TypeError):
            CoverageReviewContext(**values(**{extra: None}))


def test_construction_and_serialization_do_not_revalidate_records_hash_or_access_external_state(monkeypatch):
    payload = values(inventory_reviews=(inventory(),), implementation_reviews=(implementation(),))
    before = [payload[key][0].to_dict() for key in COLLECTIONS]
    def forbidden(*args, **kwargs):
        pytest.fail("Context에서 하위 record 재검증·지문 계산·외부 조회를 호출했습니다")
    for target in (ApplicabilityScope, InventoryCompletenessReview, ImplementationBindingReview):
        monkeypatch.setattr(target, "__post_init__", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("hashlib.sha256", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    context = CoverageReviewContext(**payload)
    assert [context.to_dict()[key][0] for key in COLLECTIONS] == before
    assert [payload[key][0].to_dict() for key in COLLECTIONS] == before


def test_structure_errors_use_existing_hierarchy_without_raw_payload():
    private = "private-invalid-policy-payload"
    with pytest.raises(PolicyDataError) as caught:
        CoverageReviewContext(**values(policy_id=private))
    assert isinstance(caught.value, EngineValidationError)
    assert private not in str(caught.value)


def test_module_has_collection_dependencies_and_no_evaluation_or_time_io():
    tree = ast.parse(inspect.getsource(domain))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {
        "dataclasses", "errors", "coverage_review", "eligibility_coverage", "implementation_review",
    }
    assert {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} == {"re"}
    assert not any(isinstance(node, ast.FunctionDef) for node in tree.body)
    assert {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)} == {"__post_init__", "to_dict"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"EligibilityCoverage", "ConditionInventory", "ConditionBinding", "Policy", "RuleNode",
                        "CoverageResult", "PolicyEvaluation", "CashflowInput", "datetime", "date", "hashlib", "open"}
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"today", "now", "exists", "sha256"} for node in ast.walk(tree))
