"""합성 Inventory 검토 matching: 미검토·정상 변경·같은 버전 모순의 경계를 검증한다."""

import ast
from dataclasses import replace
from datetime import date
import inspect
from itertools import product

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionInventory, ConditionRequirement, CoverageReviewContext,
    ImplementationBindingReview, InventoryCompletenessReview, InventoryReviewMatch,
    RequiredCondition, ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason,
    fingerprint_condition_inventory,
)
from backend.policy_engine.policy_data import coverage_review_matching as domain


def inventory(**changes):
    values = dict(policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3), inventory_version="i0002",
                  conditions=(RequiredCondition("COND_A", "소득과 거주 조건의 합성 의미", ConditionRequirement.REQUIRED,
                                                ("SYNTH-SRC#a",)),), completeness_review_ref="SYNTH-INV-EXPLICIT")
    values.update(changes)
    return ConditionInventory(**values)


def snapshot(current=None, review_changes=None, context_changes=None):
    current = inventory() if current is None else current
    fingerprint = fingerprint_condition_inventory(current)
    values = dict(review_ref=current.completeness_review_ref or "SYNTH-UNREFERENCED",
                  policy_id=current.policy_id, scope=current.scope, inventory_version=current.inventory_version,
                  inventory_fingerprint=fingerprint, dataset_version="SYNTH-DATASET-CURRENT",
                  source_registry_fingerprint="a" * 64, reviewed_at=date(2000, 1, 1),
                  review_artifact_ref="SYNTH-NONEXISTENT-ARTIFACT")
    values.update(review_changes or {})
    review = InventoryCompletenessReview(**values)
    values = dict(policy_id=review.policy_id, scope=review.scope, dataset_version="SYNTH-DATASET-CURRENT",
                  source_registry_fingerprint="a" * 64, implementation_fingerprint="b" * 64,
                  inventory_reviews=(review,), implementation_reviews=())
    values.update(context_changes or {})
    return current, CoverageReviewContext(**values), fingerprint, review


def match(current, context, fingerprint):
    return domain._match_inventory_review(current, context, current_inventory_fingerprint=fingerprint)


def expected(ref, status, stale=(), missing=()):
    return InventoryReviewMatch(ref, status, stale, missing)


@pytest.mark.parametrize("quarter", [None, 1, 3, 4])
def test_exact_snapshot_including_annual_quarter_and_korean_meaning(quarter):
    current, context, fingerprint, _ = snapshot(inventory(scope=ApplicabilityScope("2026", quarter)))
    assert match(current, context, fingerprint) == expected(current.completeness_review_ref, ReviewMatchStatus.MATCHED)


@pytest.mark.parametrize("context_shape", ["none", "empty", "populated", "different_target"])
def test_undeclared_review_has_priority_over_missing_context_and_does_not_resolve(context_shape, monkeypatch):
    current, context, fingerprint, _ = snapshot(inventory(completeness_review_ref=None))
    if context_shape == "none":
        context = None
    elif context_shape == "empty":
        context = replace(context, inventory_reviews=())
    elif context_shape == "different_target":
        context = replace(context, policy_id="SYNTH-OTHER", scope=ApplicabilityScope("2025", None), inventory_reviews=())
    def forbidden(*args):
        pytest.fail("미선언 분기에서 resolver를 호출했습니다")
    monkeypatch.setattr(domain, "_resolve_inventory_review", forbidden)
    assert match(current, context, fingerprint) == expected(
        None, ReviewMatchStatus.MISSING, missing=(ReviewMissingReason.INVENTORY_REVIEW_NOT_DECLARED,))


@pytest.mark.parametrize("ref", ["SYNTH-INV-EXPLICIT", " SYNTH-INV-EXPLICIT ", "synth-inv-explicit"])
def test_declared_ref_without_context_preserves_exact_ref_and_does_not_resolve(ref, monkeypatch):
    current = inventory(completeness_review_ref=ref)
    fingerprint = fingerprint_condition_inventory(current)
    def forbidden(*args):
        pytest.fail("Context=None 분기에서 resolver를 호출했습니다")
    monkeypatch.setattr(domain, "_resolve_inventory_review", forbidden)
    assert match(current, None, fingerprint) == expected(ref, ReviewMatchStatus.MISSING,
                                                       missing=(ReviewMissingReason.NO_REVIEW_CONTEXT,))


@pytest.mark.parametrize("ref", ["SYNTH-INV-EXPLICIT", " SYNTH-INV-EXPLICIT ", "synth-inv-explicit"])
def test_success_calls_existing_resolver_once_with_unmodified_ref(ref, monkeypatch):
    current, context, fingerprint, review = snapshot(inventory(completeness_review_ref=ref))
    original = domain._resolve_inventory_review
    calls = []
    def observe(provided_context, provided_ref):
        calls.append((provided_context, provided_ref))
        resolved = original(provided_context, provided_ref)
        assert resolved is review
        return resolved
    monkeypatch.setattr(domain, "_resolve_inventory_review", observe)
    assert match(current, context, fingerprint).status is ReviewMatchStatus.MATCHED
    assert len(calls) == 1 and calls[0][0] is context and calls[0][1] == ref


@pytest.mark.parametrize("other_ref", [None, "SYNTH-OTHER", "SYNTH-INV-EXPLICIT ", "synth-inv-explicit"])
def test_missing_explicit_ref_stays_data_error(other_ref):
    current, context, fingerprint, review = snapshot()
    context = replace(context, inventory_reviews=() if other_ref is None else (replace(review, review_ref=other_ref),))
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        match(current, context, fingerprint)


def test_explicit_implementation_ref_stays_wrong_type_error():
    current, context, fingerprint, review = snapshot()
    wrong = ImplementationBindingReview(
        review.review_ref, review.policy_id, review.scope, "COND_A", "SYNTH-ROOT", review.inventory_version,
        review.inventory_fingerprint, "SYNTH-RULE-VERSION", "c" * 64, "d" * 64,
        review.dataset_version, review.source_registry_fingerprint, "e" * 64,
        review.reviewed_at, review.review_artifact_ref,
    )
    context = replace(context, inventory_reviews=(), implementation_reviews=(wrong,))
    with pytest.raises(PolicyDataError, match="^WRONG_REVIEW_TYPE:"):
        match(current, context, fingerprint)


def test_resolver_exception_is_propagated_without_wrapping_or_state_conversion(monkeypatch):
    current, context, fingerprint, _ = snapshot()
    error = PolicyDataError("REVIEW_REF_NOT_FOUND: 합성 resolver 오류")
    def fail(*args):
        raise error
    monkeypatch.setattr(domain, "_resolve_inventory_review", fail)
    with pytest.raises(PolicyDataError) as caught:
        match(current, context, fingerprint)
    assert caught.value is error


@pytest.mark.parametrize("changes,code", [
    ({"policy_id": "SYNTH-OTHER"}, "REVIEW_POLICY_MISMATCH"),
    ({"scope": ApplicabilityScope("2026", 2)}, "REVIEW_SCOPE_MISMATCH"),
    ({"scope": ApplicabilityScope("2026", None)}, "REVIEW_SCOPE_MISMATCH"),
    ({"scope": ApplicabilityScope("2025", 3)}, "REVIEW_SCOPE_MISMATCH"),
])
@pytest.mark.parametrize("stale", [False, True])
def test_resolved_record_target_mismatch_is_error_even_with_stale_versions(changes, code, stale):
    review_changes = dict(changes)
    if stale:
        review_changes.update(inventory_version="i0001", dataset_version="SYNTH-OLD", inventory_fingerprint="0" * 64)
    current, context, fingerprint, _ = snapshot(review_changes=review_changes)
    # Context는 record와 같은 대상으로 구성하므로 현재 Inventory와의 차이를 검출한다.
    with pytest.raises(PolicyDataError, match=f"^{code}:"):
        match(current, context, fingerprint)


@pytest.mark.parametrize("inventory_same,inventory_fp_same,dataset_same,source_same", list(product([False, True], repeat=4)))
def test_all_independent_version_and_guarded_fingerprint_combinations(
    inventory_same, inventory_fp_same, dataset_same, source_same,
):
    current = inventory()
    fingerprint = fingerprint_condition_inventory(current)
    current, context, fingerprint, _ = snapshot(current, review_changes=dict(
        inventory_version=current.inventory_version if inventory_same else "i0001",
        inventory_fingerprint=fingerprint if inventory_fp_same else "0" * 64,
        dataset_version="SYNTH-DATASET-CURRENT" if dataset_same else "SYNTH-OLD",
        source_registry_fingerprint="a" * 64 if source_same else "1" * 64,
    ))
    if inventory_same and not inventory_fp_same:
        with pytest.raises(PolicyDataError, match="^INVENTORY_FINGERPRINT_CONFLICT:"):
            match(current, context, fingerprint)
    elif dataset_same and not source_same:
        with pytest.raises(PolicyDataError, match="^SOURCE_REGISTRY_FINGERPRINT_CONFLICT:"):
            match(current, context, fingerprint)
    else:
        reasons = ((ReviewStaleReason.INVENTORY_VERSION_CHANGED,) if not inventory_same else ())
        reasons += ((ReviewStaleReason.DATASET_VERSION_CHANGED,) if not dataset_same else ())
        status = ReviewMatchStatus.STALE if reasons else ReviewMatchStatus.MATCHED
        assert match(current, context, fingerprint) == expected(current.completeness_review_ref, status, reasons)


@pytest.mark.parametrize("review_version", ["i0001", "i0003", "i9999"])
def test_version_change_uses_equality_not_numeric_recency(review_version):
    current, context, fingerprint, _ = snapshot(review_changes={"inventory_version": review_version})
    assert match(current, context, fingerprint).stale_reasons == (ReviewStaleReason.INVENTORY_VERSION_CHANGED,)


@pytest.mark.parametrize("changed_field", ["meaning", "evidence_refs", "requirement"])
def test_real_synthetic_content_change_requires_new_inventory_version(changed_field):
    old, context, _, _ = snapshot()
    changes = {"meaning": "변경된 합성 조건", "evidence_refs": ("SYNTH-SRC#changed",),
               "requirement": ConditionRequirement.CONDITIONAL}
    changed = replace(old, conditions=(replace(old.conditions[0], **{changed_field: changes[changed_field]}),))
    with pytest.raises(PolicyDataError, match="^INVENTORY_FINGERPRINT_CONFLICT:"):
        match(changed, context, fingerprint_condition_inventory(changed))
    versioned = replace(changed, inventory_version="i0003")
    assert match(versioned, context, fingerprint_condition_inventory(versioned)).stale_reasons == (
        ReviewStaleReason.INVENTORY_VERSION_CHANGED,)


@pytest.mark.parametrize("reviewed_at", [date.min, date(2000, 1, 1), date(2026, 10, 21), date.max])
@pytest.mark.parametrize("artifact", ["SYNTH-NONEXISTENT-ARTIFACT", "https://synthetic.invalid/review", "SYNTH-MISSING-FILE.txt"])
def test_review_date_and_artifact_reference_do_not_affect_matching(reviewed_at, artifact):
    current, context, fingerprint, _ = snapshot(review_changes={"reviewed_at": reviewed_at, "review_artifact_ref": artifact})
    assert match(current, context, fingerprint).status is ReviewMatchStatus.MATCHED


@pytest.mark.parametrize("implementation_fingerprint", ["0" * 64, "f" * 64])
def test_context_implementation_fingerprint_is_not_an_inventory_gate(implementation_fingerprint):
    current, context, fingerprint, _ = snapshot(context_changes={"implementation_fingerprint": implementation_fingerprint})
    assert match(current, context, fingerprint).status is ReviewMatchStatus.MATCHED


@pytest.mark.parametrize("declared_old", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_historical_records_order_cannot_replace_explicit_ref(declared_old, reverse):
    current, context, fingerprint, selected = snapshot()
    older = replace(selected, review_ref="SYNTH-OLDER", inventory_version="i0001", inventory_fingerprint="0" * 64,
                    dataset_version="SYNTH-OLD", reviewed_at=date.min)
    unrelated = replace(selected, review_ref="SYNTH-NEWEST-UNREFERENCED", inventory_fingerprint="1" * 64,
                        reviewed_at=date.max)
    records = (older, selected, unrelated)
    context = replace(context, inventory_reviews=tuple(reversed(records)) if reverse else records)
    if declared_old:
        current = replace(current, completeness_review_ref=older.review_ref)
    status = ReviewMatchStatus.STALE if declared_old else ReviewMatchStatus.MATCHED
    reasons = (ReviewStaleReason.INVENTORY_VERSION_CHANGED, ReviewStaleReason.DATASET_VERSION_CHANGED) if declared_old else ()
    assert match(current, context, fingerprint) == expected(current.completeness_review_ref, status, reasons)


class InventorySubclass(ConditionInventory):
    pass


class ContextSubclass(CoverageReviewContext):
    pass


class TextSubclass(str):
    pass


class FakeObject:
    @property
    def completeness_review_ref(self):
        pytest.fail("잘못된 입력 객체의 속성을 읽었습니다")

    @property
    def inventory_reviews(self):
        pytest.fail("잘못된 Context의 collection을 읽었습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "SYNTH", 1, True, FakeObject()])
def test_inventory_exact_type_is_required(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: inventory"):
        match(bad, None, "0" * 64)


def test_inventory_subclass_is_not_converted():
    current = inventory()
    bad = InventorySubclass(current.policy_id, current.scope, current.inventory_version, current.conditions)
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: inventory"):
        match(bad, None, "0" * 64)


@pytest.mark.parametrize("declared", [False, True])
@pytest.mark.parametrize("bad", [{}, [], (), "SYNTH", 1, True, FakeObject()])
def test_context_exact_type_is_validated_before_missing_branches(declared, bad):
    current = inventory(completeness_review_ref="SYNTH-REF" if declared else None)
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: review_context"):
        match(current, bad, "0" * 64)


def test_context_subclass_is_rejected():
    current, context, fingerprint, _ = snapshot()
    bad = ContextSubclass(context.policy_id, context.scope, context.dataset_version, context.source_registry_fingerprint,
                          context.implementation_fingerprint, context.inventory_reviews, context.implementation_reviews)
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: review_context"):
        match(current, bad, fingerprint)


@pytest.mark.parametrize("branch", ["undeclared", "no_context", "provided"])
@pytest.mark.parametrize("bad", [None, True, 1, [], {}, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64,
                                  "0x" + "a" * 64, " " + "a" * 64, "a" * 64 + "\n", TextSubclass("a" * 64)])
def test_supplied_fingerprint_is_validated_even_before_missing_result(branch, bad):
    current, context, _, _ = snapshot(inventory(completeness_review_ref=None) if branch == "undeclared" else None)
    if branch != "provided":
        context = None
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: current_inventory_fingerprint"):
        match(current, context, bad)


@pytest.mark.parametrize("branch", ["matched", "stale", "undeclared", "no_context"])
def test_100_calls_are_deterministic_and_do_not_mutate_inputs(branch):
    current, context, fingerprint, review = snapshot(
        inventory(completeness_review_ref=None) if branch == "undeclared" else None,
        review_changes={"inventory_version": "i0001", "dataset_version": "SYNTH-OLD"} if branch == "stale" else None,
    )
    before = (current.to_dict(), context.to_dict(), review.to_dict())
    records = context.inventory_reviews
    result = match(current, None if branch == "no_context" else context, fingerprint)
    for _ in range(100):
        assert match(current, None if branch == "no_context" else context, fingerprint) == result
    assert (current.to_dict(), context.to_dict(), review.to_dict()) == before
    assert context.inventory_reviews is records and records[0] is review


def test_error_class_prefix_message_are_deterministic_without_payload_echo():
    current, context, fingerprint, review = snapshot(review_changes={"inventory_fingerprint": "0" * 64})
    other = replace(review, review_ref="SYNTH-OTHER", inventory_version="i0001")
    results = []
    for records in ((review, other), (other, review)):
        for _ in range(10):
            with pytest.raises(PolicyDataError) as caught:
                match(current, replace(context, inventory_reviews=records), fingerprint)
            results.append((type(caught.value), str(caught.value)))
            assert current.conditions[0].meaning not in str(caught.value)
            assert fingerprint not in str(caught.value)
    assert len(set(results)) == 1


def test_only_inventory_matching_fields_are_read(monkeypatch):
    current, context, fingerprint, review = snapshot()
    def guard(allowed):
        def access(value, name):
            if name not in allowed:
                pytest.fail("Inventory matcher 책임 밖의 필드를 읽었습니다: " + name)
            return object.__getattribute__(value, name)
        return access
    monkeypatch.setattr(ConditionInventory, "__getattribute__", guard(
        {"completeness_review_ref", "policy_id", "scope", "inventory_version"}))
    monkeypatch.setattr(CoverageReviewContext, "__getattribute__", guard(
        {"inventory_reviews", "implementation_reviews", "dataset_version", "source_registry_fingerprint"}))
    monkeypatch.setattr(InventoryCompletenessReview, "__getattribute__", guard(
        {"review_ref", "policy_id", "scope", "inventory_version", "inventory_fingerprint", "dataset_version",
         "source_registry_fingerprint"}))
    assert match(current, context, fingerprint).status is ReviewMatchStatus.MATCHED


def test_no_fingerprint_calculation_revalidation_serialization_or_external_io(monkeypatch):
    current, context, fingerprint, _ = snapshot()
    from backend.policy_engine.policy_data import coverage_fingerprint
    def forbidden(*args, **kwargs):
        pytest.fail("matcher가 지문 재계산·모델 재검증·외부 상태에 접근했습니다")
    for model in (ConditionInventory, CoverageReviewContext, InventoryCompletenessReview):
        monkeypatch.setattr(model, "__post_init__", forbidden)
        monkeypatch.setattr(model, "to_dict", forbidden)
    for name in ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree"):
        monkeypatch.setattr(coverage_fingerprint, name, forbidden)
    for name in ("builtins.open", "hashlib.sha256", "socket.socket", "subprocess.run", "pathlib.Path.exists",
                 "pathlib.Path.read_text", "os.getenv", "time.time", "json.dumps"):
        monkeypatch.setattr(name, forbidden)
    assert match(current, context, fingerprint).status is ReviewMatchStatus.MATCHED


def test_private_api_and_current_dependency_boundary():
    from backend.policy_engine import policy_data
    signature = inspect.signature(domain._match_inventory_review)
    assert list(signature.parameters) == ["inventory", "review_context", "current_inventory_fingerprint"]
    assert signature.parameters["current_inventory_fingerprint"].kind is inspect.Parameter.KEYWORD_ONLY
    assert all(p.default is inspect.Parameter.empty for p in signature.parameters.values())
    assert "_match_inventory_review" not in policy_data.__all__
    assert not hasattr(policy_data, "_match_inventory_review")
    # Inventory 함수 자체의 책임만 고정한다. 후속 별도 matcher의 모듈 확장을 막지 않는다.
    tree = ast.parse(inspect.getsource(domain._match_inventory_review))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not imports & {"coverage_fingerprint", "models", "condition_binding", "implementation_review"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"Policy", "RuleNode", "ConditionBinding", "ImplementationReviewMatch", "CoverageResult",
                        "fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree"}
