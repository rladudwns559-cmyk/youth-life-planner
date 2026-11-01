"""합성 Binding 검토의 대상 결합·독립 버전/지문·오류 우선순위를 검증한다."""

import ast
from dataclasses import replace
from datetime import date
import inspect
from itertools import product

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.models import Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, CoverageReviewContext,
    ImplementationBindingReview, ImplementationReviewMatch, InventoryCompletenessReview,
    RequiredCondition, ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason,
    fingerprint_condition_inventory, fingerprint_policy_tree, fingerprint_rule_subtree,
)
from backend.policy_engine.policy_data import coverage_review_matching as domain


STALE_ORDER = (
    ReviewStaleReason.INVENTORY_VERSION_CHANGED, ReviewStaleReason.RULE_VERSION_CHANGED,
    ReviewStaleReason.DATASET_VERSION_CHANGED, ReviewStaleReason.IMPLEMENTATION_CHANGED,
)


def snapshot(root_kind="leaf", quarter=3, rule_version="SYNTH-RULE-CURRENT", binding_changes=None,
             review_changes=None, context_changes=None):
    condition = RequiredCondition("COND_A", "합성 자격조건의 의미", ConditionRequirement.REQUIRED, ("SYNTH-SRC#a",))
    inventory = ConditionInventory("SYNTH-POLICY", ApplicabilityScope("2026", quarter), "i0002", (condition,))
    leaf = PolicyRule("SYNTH-LEAF", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))
    root = leaf if root_kind == "leaf" else RuleGroup("SYNTH-GROUP", GroupOperator.ALL, (leaf,))
    policy = Policy(inventory.policy_id, "합성 정책", rule_version, root)
    values = dict(condition_id=condition.condition_id, rule_root_id=root.rule_id, implementation_review_ref="SYNTH-IMPL-EXPLICIT")
    values.update(binding_changes or {})
    binding = ConditionBinding(**values)
    current = dict(current_inventory_fingerprint=fingerprint_condition_inventory(inventory), current_rule_version=policy.rule_version,
                   current_policy_tree_fingerprint=fingerprint_policy_tree(policy), current_subtree_fingerprint=fingerprint_rule_subtree(root))
    values = dict(review_ref=binding.implementation_review_ref, policy_id=inventory.policy_id, scope=inventory.scope,
                  condition_id=binding.condition_id, rule_root_id=binding.rule_root_id, inventory_version=inventory.inventory_version,
                  inventory_fingerprint=current["current_inventory_fingerprint"], rule_version=policy.rule_version,
                  policy_tree_fingerprint=current["current_policy_tree_fingerprint"], subtree_fingerprint=current["current_subtree_fingerprint"],
                  dataset_version="SYNTH-DATASET-CURRENT", source_registry_fingerprint="a" * 64,
                  implementation_fingerprint="b" * 64, reviewed_at=date(2000, 1, 1), review_artifact_ref="SYNTH-NONEXISTENT-ARTIFACT")
    values.update(review_changes or {})
    review = ImplementationBindingReview(**values)
    values = dict(policy_id=review.policy_id, scope=review.scope, dataset_version="SYNTH-DATASET-CURRENT",
                  source_registry_fingerprint="a" * 64, implementation_fingerprint="b" * 64,
                  inventory_reviews=(), implementation_reviews=(review,))
    values.update(context_changes or {})
    return inventory, binding, CoverageReviewContext(**values), current, review


def match(values):
    inventory, binding, context, current, _ = values
    return domain._match_implementation_review(inventory, binding, context, **current)


def expected(binding, status, stale=(), missing=()):
    return ImplementationReviewMatch(binding.condition_id, binding.rule_root_id, binding.implementation_review_ref,
                                     status, stale, missing)


@pytest.mark.parametrize("root_kind", ["leaf", "group"])
@pytest.mark.parametrize("quarter", [None, 1, 3, 4])
def test_exact_snapshots_for_leaf_group_annual_and_quarters(root_kind, quarter):
    values = snapshot(root_kind, quarter)
    assert match(values) == expected(values[1], ReviewMatchStatus.MATCHED)


@pytest.mark.parametrize("ref", ["SYNTH-IMPL-EXPLICIT", " SYNTH-IMPL-EXPLICIT ", "synth-impl-explicit"])
def test_context_none_preserves_binding_identity_and_does_not_resolve(ref, monkeypatch):
    inventory, binding, _, current, review = snapshot(binding_changes={"condition_id": "COND_42", "rule_root_id": " SYNTH-ROOT ",
                                                                     "implementation_review_ref": ref})
    def forbidden(*args):
        pytest.fail("Context=None에서 resolver를 호출했습니다")
    monkeypatch.setattr(domain, "_resolve_implementation_review", forbidden)
    assert match((inventory, binding, None, current, review)) == expected(
        binding, ReviewMatchStatus.MISSING, missing=(ReviewMissingReason.NO_REVIEW_CONTEXT,))


@pytest.mark.parametrize("ref", ["SYNTH-IMPL-EXPLICIT", " SYNTH-IMPL-EXPLICIT ", "synth-impl-explicit"])
def test_existing_resolver_is_called_once_with_exact_context_and_ref(ref, monkeypatch):
    values = snapshot(binding_changes={"implementation_review_ref": ref})
    original = domain._resolve_implementation_review
    calls = []
    def observe(context, provided_ref):
        calls.append((context, provided_ref))
        review = original(context, provided_ref)
        assert review is values[4]
        return review
    monkeypatch.setattr(domain, "_resolve_implementation_review", observe)
    assert match(values).status is ReviewMatchStatus.MATCHED
    assert len(calls) == 1 and calls[0][0] is values[2] and calls[0][1] == ref


@pytest.mark.parametrize("other_ref", [None, "SYNTH-OTHER", "SYNTH-IMPL-EXPLICIT ", "synth-impl-explicit"])
def test_missing_explicit_ref_is_data_error_without_fallback(other_ref):
    inventory, binding, context, current, review = snapshot()
    records = () if other_ref is None else (replace(review, review_ref=other_ref),)
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        match((inventory, binding, replace(context, implementation_reviews=records), current, review))


def test_inventory_ref_is_wrong_review_type():
    inventory, binding, context, current, review = snapshot()
    wrong = InventoryCompletenessReview(review.review_ref, review.policy_id, review.scope, review.inventory_version,
                                        review.inventory_fingerprint, review.dataset_version, review.source_registry_fingerprint,
                                        review.reviewed_at, review.review_artifact_ref)
    context = replace(context, inventory_reviews=(wrong,), implementation_reviews=())
    with pytest.raises(PolicyDataError, match="^WRONG_REVIEW_TYPE:"):
        match((inventory, binding, context, current, review))


def test_resolver_error_is_propagated_as_original_exception(monkeypatch):
    values = snapshot()
    error = PolicyDataError("REVIEW_REF_NOT_FOUND: 합성 resolver 오류")
    def fail(*args):
        raise error
    monkeypatch.setattr(domain, "_resolve_implementation_review", fail)
    with pytest.raises(PolicyDataError) as caught:
        match(values)
    assert caught.value is error


TARGET_CASES = (
    ({"policy_id": "SYNTH-OTHER"}, "REVIEW_POLICY_MISMATCH"),
    ({"scope": ApplicabilityScope("2026", 2)}, "REVIEW_SCOPE_MISMATCH"),
    ({"scope": ApplicabilityScope("2026", None)}, "REVIEW_SCOPE_MISMATCH"),
    ({"scope": ApplicabilityScope("2025", 3)}, "REVIEW_SCOPE_MISMATCH"),
    ({"condition_id": "COND_OTHER"}, "REVIEW_CONDITION_MISMATCH"),
    ({"rule_root_id": "SYNTH-OTHER-ROOT"}, "REVIEW_RULE_ROOT_MISMATCH"),
    ({"rule_root_id": "SYNTH-LEAF "}, "REVIEW_RULE_ROOT_MISMATCH"),
)


@pytest.mark.parametrize("changes,code", TARGET_CASES)
@pytest.mark.parametrize("all_stale", [False, True])
def test_wrong_targets_are_data_error_even_when_versions_changed(changes, code, all_stale):
    review_changes = dict(changes)
    if all_stale:
        review_changes.update(inventory_version="i0001", rule_version="SYNTH-OLD", dataset_version="SYNTH-OLD",
                              implementation_fingerprint="0" * 64)
    with pytest.raises(PolicyDataError, match=f"^{code}:"):
        match(snapshot(review_changes=review_changes))


@pytest.mark.parametrize("inventory_changed,rule_changed,dataset_changed,implementation_changed", list(product([False, True], repeat=4)))
@pytest.mark.parametrize("changed_hashes_equal", [False, True])
def test_every_stale_subset_is_preserved_in_canonical_order(
    inventory_changed, rule_changed, dataset_changed, implementation_changed, changed_hashes_equal,
):
    changes = {}
    if inventory_changed:
        changes["inventory_version"] = "i0001"
        if not changed_hashes_equal:
            changes["inventory_fingerprint"] = "0" * 64
    if rule_changed:
        changes["rule_version"] = "SYNTH-OLD"
        if not changed_hashes_equal:
            changes.update(policy_tree_fingerprint="1" * 64, subtree_fingerprint="2" * 64)
    if dataset_changed:
        changes["dataset_version"] = "SYNTH-OLD"
        if not changed_hashes_equal:
            changes["source_registry_fingerprint"] = "3" * 64
    if implementation_changed:
        changes["implementation_fingerprint"] = "4" * 64
    values = snapshot(review_changes=changes)
    flags = (inventory_changed, rule_changed, dataset_changed, implementation_changed)
    reasons = tuple(reason for reason, changed in zip(STALE_ORDER, flags) if changed)
    assert match(values) == expected(values[1], ReviewMatchStatus.STALE if reasons else ReviewMatchStatus.MATCHED, reasons)


@pytest.mark.parametrize("field,code", [
    ("inventory_fingerprint", "INVENTORY_FINGERPRINT_CONFLICT"),
    ("policy_tree_fingerprint", "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ("subtree_fingerprint", "SUBTREE_FINGERPRINT_CONFLICT"),
    ("source_registry_fingerprint", "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
])
def test_same_version_content_conflict_is_error(field, code):
    with pytest.raises(PolicyDataError, match=f"^{code}:"):
        match(snapshot(review_changes={field: "0" * 64}))


@pytest.mark.parametrize("tree_same,subtree_same", list(product([False, True], repeat=2)))
def test_same_rule_version_guards_both_tree_and_subtree_in_fixed_order(tree_same, subtree_same):
    changes = {}
    if not tree_same:
        changes["policy_tree_fingerprint"] = "0" * 64
    if not subtree_same:
        changes["subtree_fingerprint"] = "1" * 64
    values = snapshot(review_changes=changes)
    if tree_same and subtree_same:
        assert match(values).status is ReviewMatchStatus.MATCHED
    else:
        code = "POLICY_TREE_FINGERPRINT_CONFLICT" if not tree_same else "SUBTREE_FINGERPRINT_CONFLICT"
        with pytest.raises(PolicyDataError, match=f"^{code}:"):
            match(values)


@pytest.mark.parametrize("changes,code", [
    ({"inventory_version": "i0001", "condition_id": "COND_OTHER"}, "REVIEW_CONDITION_MISMATCH"),
    ({"rule_version": "SYNTH-OLD", "policy_id": "SYNTH-OTHER"}, "REVIEW_POLICY_MISMATCH"),
    ({"inventory_version": "i0001", "policy_tree_fingerprint": "0" * 64}, "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ({"inventory_version": "i0001", "subtree_fingerprint": "0" * 64}, "SUBTREE_FINGERPRINT_CONFLICT"),
    ({"inventory_version": "i0001", "source_registry_fingerprint": "0" * 64}, "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
    ({"rule_version": "SYNTH-OLD", "inventory_fingerprint": "0" * 64}, "INVENTORY_FINGERPRINT_CONFLICT"),
    ({"rule_version": "SYNTH-OLD", "source_registry_fingerprint": "0" * 64}, "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
    ({"dataset_version": "SYNTH-OLD", "inventory_fingerprint": "0" * 64}, "INVENTORY_FINGERPRINT_CONFLICT"),
    ({"dataset_version": "SYNTH-OLD", "policy_tree_fingerprint": "0" * 64}, "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ({"dataset_version": "SYNTH-OLD", "subtree_fingerprint": "0" * 64}, "SUBTREE_FINGERPRINT_CONFLICT"),
    ({"implementation_fingerprint": "0" * 64, "inventory_fingerprint": "1" * 64}, "INVENTORY_FINGERPRINT_CONFLICT"),
    ({"implementation_fingerprint": "0" * 64, "policy_tree_fingerprint": "1" * 64}, "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ({"implementation_fingerprint": "0" * 64, "subtree_fingerprint": "1" * 64}, "SUBTREE_FINGERPRINT_CONFLICT"),
    ({"implementation_fingerprint": "0" * 64, "source_registry_fingerprint": "1" * 64}, "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
])
def test_independent_stale_cannot_hide_target_or_guarded_content_error(changes, code):
    with pytest.raises(PolicyDataError, match=f"^{code}:"):
        match(snapshot(review_changes=changes))


@pytest.mark.parametrize("first_field,code", [
    ("policy_id", "REVIEW_POLICY_MISMATCH"), ("scope", "REVIEW_SCOPE_MISMATCH"),
    ("condition_id", "REVIEW_CONDITION_MISMATCH"), ("rule_root_id", "REVIEW_RULE_ROOT_MISMATCH"),
    ("inventory_fingerprint", "INVENTORY_FINGERPRINT_CONFLICT"),
    ("policy_tree_fingerprint", "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ("subtree_fingerprint", "SUBTREE_FINGERPRINT_CONFLICT"),
    ("source_registry_fingerprint", "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
])
def test_multiple_errors_have_stable_target_then_content_precedence(first_field, code):
    errors = dict(policy_id="SYNTH-OTHER", scope=ApplicabilityScope("2025", None), condition_id="COND_OTHER",
                  rule_root_id="SYNTH-OTHER-ROOT", inventory_fingerprint="0" * 64, policy_tree_fingerprint="1" * 64,
                  subtree_fingerprint="2" * 64, source_registry_fingerprint="3" * 64)
    fields = list(errors)
    changes = {field: errors[field] for field in fields[fields.index(first_field):]}
    with pytest.raises(PolicyDataError, match=f"^{code}:"):
        match(snapshot(review_changes=changes))


@pytest.mark.parametrize("version", ["r0002", " SYNTH-RULE ", "정책 규칙 2판", "release/2026.3", "r0"])
def test_current_rule_version_uses_policy_text_contract_without_envelope_restriction(version):
    assert match(snapshot(rule_version=version)).status is ReviewMatchStatus.MATCHED


@pytest.mark.parametrize("different", ["synth-rule-current", "SYNTH-RULE-CURRENT ", " SYNTH-RULE-CURRENT", "r9999"])
def test_current_rule_version_preserves_case_padding_and_uses_exact_equality(different):
    values = snapshot()
    values[3]["current_rule_version"] = different
    assert match(values).stale_reasons == (ReviewStaleReason.RULE_VERSION_CHANGED,)


@pytest.mark.parametrize("field,value", [("inventory_version", "i9999"), ("dataset_version", "SYNTH-FUTURE")])
def test_version_labels_are_not_ordered_by_recency(field, value):
    result = match(snapshot(review_changes={field: value}))
    reason = ReviewStaleReason.INVENTORY_VERSION_CHANGED if field == "inventory_version" else ReviewStaleReason.DATASET_VERSION_CHANGED
    assert result.stale_reasons == (reason,)


@pytest.mark.parametrize("reviewed_at", [date.min, date(2000, 1, 1), date(2026, 10, 21), date.max])
@pytest.mark.parametrize("artifact", ["SYNTH-NONEXISTENT-ARTIFACT", "https://synthetic.invalid/review", "SYNTH-NONEXISTENT.txt"])
def test_review_date_and_artifact_reference_do_not_affect_exact_match(reviewed_at, artifact):
    assert match(snapshot(review_changes={"reviewed_at": reviewed_at, "review_artifact_ref": artifact})).status is ReviewMatchStatus.MATCHED


@pytest.mark.parametrize("select_old", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_historical_record_order_never_replaces_explicit_ref(select_old, reverse):
    inventory, binding, context, current, review = snapshot()
    older = replace(review, review_ref="SYNTH-OLD", inventory_version="i0001", rule_version="SYNTH-OLD",
                    dataset_version="SYNTH-OLD", implementation_fingerprint="0" * 64, reviewed_at=date.min)
    unrelated = replace(review, review_ref="SYNTH-NEWEST", policy_tree_fingerprint="1" * 64, reviewed_at=date.max)
    records = (older, review, unrelated)
    context = replace(context, implementation_reviews=tuple(reversed(records)) if reverse else records)
    if select_old:
        binding = replace(binding, implementation_review_ref=older.review_ref)
    assert match((inventory, binding, context, current, review)) == expected(
        binding, ReviewMatchStatus.STALE if select_old else ReviewMatchStatus.MATCHED, STALE_ORDER if select_old else ())


class InventorySubclass(ConditionInventory):
    pass


class BindingSubclass(ConditionBinding):
    pass


class ContextSubclass(CoverageReviewContext):
    pass


class TextSubclass(str):
    pass


class FakeObject:
    @property
    def implementation_review_ref(self):
        pytest.fail("잘못된 Binding의 속성을 읽었습니다")

    @property
    def policy_id(self):
        pytest.fail("잘못된 입력의 속성을 읽었습니다")


@pytest.mark.parametrize("input_name", ["inventory", "binding", "review_context"])
@pytest.mark.parametrize("bad", [{}, [], (), "SYNTH", 1, True, FakeObject()])
def test_domain_inputs_require_exact_model_types(input_name, bad):
    inventory, binding, context, current, _ = snapshot()
    args = dict(inventory=inventory, binding=binding, review_context=context)
    args[input_name] = bad
    with pytest.raises(PolicyDataError, match=f"^INVALID_MATCH_INPUT: {input_name}"):
        domain._match_implementation_review(**args, **current)


@pytest.mark.parametrize("input_name", ["inventory", "binding"])
def test_required_model_cannot_be_none_even_with_no_context(input_name):
    inventory, binding, _, current, _ = snapshot()
    args = dict(inventory=inventory, binding=binding, review_context=None)
    args[input_name] = None
    with pytest.raises(PolicyDataError, match=f"^INVALID_MATCH_INPUT: {input_name}"):
        domain._match_implementation_review(**args, **current)


@pytest.mark.parametrize("input_name", ["inventory", "binding", "review_context"])
def test_model_subclasses_are_rejected_without_conversion(input_name):
    inventory, binding, context, current, _ = snapshot()
    args = dict(inventory=inventory, binding=binding, review_context=context)
    if input_name == "inventory":
        args[input_name] = InventorySubclass(inventory.policy_id, inventory.scope, inventory.inventory_version, inventory.conditions)
    elif input_name == "binding":
        args[input_name] = BindingSubclass(binding.condition_id, binding.rule_root_id, binding.implementation_review_ref)
    else:
        args[input_name] = ContextSubclass(context.policy_id, context.scope, context.dataset_version, context.source_registry_fingerprint,
                                           context.implementation_fingerprint, context.inventory_reviews, context.implementation_reviews)
    with pytest.raises(PolicyDataError, match=f"^INVALID_MATCH_INPUT: {input_name}"):
        domain._match_implementation_review(**args, **current)


@pytest.mark.parametrize("has_context", [False, True])
@pytest.mark.parametrize("field", ["current_inventory_fingerprint", "current_policy_tree_fingerprint", "current_subtree_fingerprint"])
@pytest.mark.parametrize("bad", [None, True, 1, [], {}, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64,
                                  "0x" + "a" * 64, " " + "a" * 64, "a" * 64 + "\n", TextSubclass("a" * 64)])
def test_current_fingerprints_are_validated_before_any_missing_result(has_context, field, bad):
    inventory, binding, context, current, _ = snapshot()
    current[field] = bad
    with pytest.raises(PolicyDataError, match=f"^INVALID_MATCH_INPUT: {field}"):
        domain._match_implementation_review(inventory, binding, context if has_context else None, **current)


@pytest.mark.parametrize("has_context", [False, True])
@pytest.mark.parametrize("bad", [None, True, 1, [], {}, "", " \t\n", TextSubclass("SYNTH-RULE")])
def test_current_rule_version_is_exact_nonblank_text_before_missing_result(has_context, bad):
    inventory, binding, context, current, _ = snapshot()
    current["current_rule_version"] = bad
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: current_rule_version"):
        domain._match_implementation_review(inventory, binding, context if has_context else None, **current)


@pytest.mark.parametrize("state", ["matched", "stale", "missing"])
def test_100_calls_are_deterministic_and_preserve_all_inputs(state):
    inventory, binding, context, current, review = snapshot(review_changes={"implementation_fingerprint": "0" * 64} if state == "stale" else None)
    before = (inventory.to_dict(), binding.to_dict(), context.to_dict(), review.to_dict(), current.copy())
    records = context.implementation_reviews
    values = (inventory, binding, None if state == "missing" else context, current, review)
    result = match(values)
    for _ in range(100):
        assert match(values) == result
    assert (inventory.to_dict(), binding.to_dict(), context.to_dict(), review.to_dict(), current) == before
    assert context.implementation_reviews is records and records[0] is review


def test_error_is_deterministic_after_record_reordering_without_payload_echo():
    inventory, binding, context, current, review = snapshot(review_changes={"policy_tree_fingerprint": "0" * 64})
    unrelated = replace(review, review_ref="SYNTH-UNRELATED", rule_version="SYNTH-OLD")
    results = []
    for records in ((review, unrelated), (unrelated, review)):
        for _ in range(10):
            with pytest.raises(PolicyDataError) as caught:
                match((inventory, binding, replace(context, implementation_reviews=records), current, review))
            results.append((type(caught.value), str(caught.value)))
            assert inventory.conditions[0].meaning not in str(caught.value)
            assert current["current_policy_tree_fingerprint"] not in str(caught.value)
    assert len(set(results)) == 1


def test_only_binding_review_and_snapshot_fields_are_read(monkeypatch):
    values = snapshot()
    def guard(allowed):
        def access(value, name):
            if name not in allowed:
                pytest.fail("Implementation matcher 책임 밖 필드를 읽었습니다: " + name)
            return object.__getattribute__(value, name)
        return access
    monkeypatch.setattr(ConditionInventory, "__getattribute__", guard({"policy_id", "scope", "inventory_version"}))
    monkeypatch.setattr(ConditionBinding, "__getattribute__", guard({"condition_id", "rule_root_id", "implementation_review_ref"}))
    monkeypatch.setattr(CoverageReviewContext, "__getattribute__", guard(
        {"inventory_reviews", "implementation_reviews", "dataset_version", "source_registry_fingerprint", "implementation_fingerprint"}))
    monkeypatch.setattr(ImplementationBindingReview, "__getattribute__", guard(
        {"review_ref", "policy_id", "scope", "condition_id", "rule_root_id", "inventory_version", "inventory_fingerprint",
         "rule_version", "policy_tree_fingerprint", "subtree_fingerprint", "dataset_version", "source_registry_fingerprint",
         "implementation_fingerprint"}))
    assert match(values).status is ReviewMatchStatus.MATCHED


def test_no_calculation_traversal_model_revalidation_or_external_io(monkeypatch):
    values = snapshot()
    from backend.policy_engine import models
    from backend.policy_engine.policy_data import coverage_fingerprint
    def forbidden(*args, **kwargs):
        pytest.fail("matcher가 계산·순회·재검증·외부 상태에 접근했습니다")
    for model in (ConditionInventory, ConditionBinding, CoverageReviewContext, ImplementationBindingReview):
        monkeypatch.setattr(model, "__post_init__", forbidden)
        monkeypatch.setattr(model, "to_dict", forbidden)
    monkeypatch.setattr(models, "walk_nodes", forbidden)
    monkeypatch.setattr(domain, "_match_inventory_review", forbidden)
    for name in ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree"):
        monkeypatch.setattr(coverage_fingerprint, name, forbidden)
    for name in ("builtins.open", "hashlib.sha256", "socket.socket", "subprocess.run", "pathlib.Path.exists",
                 "pathlib.Path.read_text", "os.getenv", "time.time", "json.dumps"):
        monkeypatch.setattr(name, forbidden)
    assert match(values).status is ReviewMatchStatus.MATCHED


def test_declared_hash_matching_does_not_claim_condition_membership_or_root_existence():
    # 소속/존재는 상위 구조 검증 책임이다. 일치하는 선언값만으로 이 함수가 이를 증명하지 않는다.
    values = snapshot(binding_changes={"condition_id": "COND_NOT_IN_INVENTORY", "rule_root_id": "SYNTH-NOT-ACTUAL-ROOT"})
    assert match(values).status is ReviewMatchStatus.MATCHED


def test_private_api_has_scalar_snapshot_inputs_and_no_policy_or_lookup_dependency():
    from backend.policy_engine import policy_data
    signature = inspect.signature(domain._match_implementation_review)
    assert list(signature.parameters) == ["inventory", "binding", "review_context", "current_inventory_fingerprint",
                                         "current_rule_version", "current_policy_tree_fingerprint", "current_subtree_fingerprint"]
    assert all(signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY for name in list(signature.parameters)[3:])
    assert all(value.default is inspect.Parameter.empty for value in signature.parameters.values())
    assert "_match_implementation_review" not in policy_data.__all__
    assert not hasattr(policy_data, "_match_implementation_review")
    tree = ast.parse(inspect.getsource(domain._match_implementation_review))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"Policy", "RuleNode", "walk_nodes", "CoverageResult", "fingerprint_condition_inventory",
                        "fingerprint_policy_tree", "fingerprint_rule_subtree", "_match_inventory_review"}
