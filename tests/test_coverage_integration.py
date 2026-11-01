"""합성 입력만 사용하는 findings orchestration 계약과 실제 helper 간 통합 검증."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
import inspect
from itertools import permutations

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import (
    Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, _jsonable, walk_nodes,
)
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, EligibilityCoverage,
    RequiredCondition, CoverageReviewContext, InventoryCompletenessReview, ImplementationBindingReview,
)
from backend.policy_engine.policy_data import coverage_integration as domain
from backend.policy_engine.policy_data.coverage_integration_findings import (
    _CoverageIntegrationFindings as CoverageFindings, _ImplementationIntegrationFinding as BindingFinding,
)
from backend.policy_engine.policy_data.coverage_review_match import (
    ImplementationReviewMatch, ReviewMatchStatus as Status, ReviewMissingReason as Missing,
    ReviewStaleReason as Stale,
)
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule


def atomic(rule_id="A"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))


def resident(rule_id="RESIDENT"):
    return ResidentRegistrationRule(rule_id, RegionRef("SEOUL", "JONGNO"),
                                    ReferenceDateSource.APPLICATION_DATE, ("SYNTH-SRC#resident",))


def birth(rule_id="BIRTH"):
    return BirthDateRule(rule_id, date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#birth",))


def group(rule_id, children, operator=GroupOperator.ALL):
    return RuleGroup(rule_id, operator, children)


def policy(root):
    return Policy("SYNTH-POLICY", "합성 정책", "r0001", root)


def coverage(current, declarations=(), pending=(), declared=True):
    bindings = tuple(ConditionBinding(cid, rid, "SYNTH-REVIEW-" + cid) for cid, rid in declarations)
    ids = tuple(binding.condition_id for binding in bindings) + tuple(pending)
    conditions = tuple(RequiredCondition(cid, "합성 조건", ConditionRequirement.REQUIRED,
                                         ("SYNTH-SRC#a",)) for cid in ids)
    inventory = ConditionInventory(current.policy_id, ApplicabilityScope("2026", 3), "i0001", conditions,
                                   "SYNTH-INVENTORY-REVIEW" if declared else None)
    return EligibilityCoverage(inventory, bindings)


def empty_context(value, **overrides):
    result = CoverageReviewContext(value.inventory.policy_id, value.inventory.scope,
                                   "SYNTH-DATASET-1", "a" * 64, "b" * 64, (), ())
    return replace(result, **overrides)


def matched_context(value, current):
    """합성 tree의 현재 지문으로만 검토 fixture를 준비한다. 실제 자료는 읽지 않는다."""
    context = empty_context(value)
    inv = value.inventory
    inventory_fp = domain.fingerprint_condition_inventory(inv)
    tree_fp = domain.fingerprint_policy_tree(current)
    roots = {node.rule_id: node for node in walk_nodes(current.root)}
    inventory_reviews = () if inv.completeness_review_ref is None else (InventoryCompletenessReview(
        inv.completeness_review_ref, inv.policy_id, inv.scope, inv.inventory_version, inventory_fp,
        context.dataset_version, context.source_registry_fingerprint, date(2026, 1, 1), "SYNTH-ARTIFACT",
    ),)
    implementation_reviews = tuple(ImplementationBindingReview(
        binding.implementation_review_ref, inv.policy_id, inv.scope, binding.condition_id, binding.rule_root_id,
        inv.inventory_version, inventory_fp, current.rule_version, tree_fp,
        domain.fingerprint_rule_subtree(roots[binding.rule_root_id]), context.dataset_version,
        context.source_registry_fingerprint, context.implementation_fingerprint,
        date(2026, 1, 1), "SYNTH-ARTIFACT",
    ) for binding in value.bindings)
    return replace(context, inventory_reviews=inventory_reviews, implementation_reviews=implementation_reviews)


def standard(count=3, declared=True):
    roots = tuple(atomic("ROOT_" + letter) for letter in "ABC"[:count])
    current = policy(group("TOP_ALL", roots))
    declarations = tuple(("COND_" + letter, "ROOT_" + letter) for letter in "CBA" if letter in "ABC"[:count])
    value = coverage(current, declarations, declared=declared)
    return value, current, matched_context(value, current)


def call(value, current, context):
    return domain._collect_coverage_integration_findings(value, current, context)


def no_call(*args, **kwargs):
    pytest.fail("오류 이후 또는 허용되지 않은 단계가 실행됐습니다")


def test_matched_complete_returns_exact_immutable_findings_without_final_status():
    value, current, context = standard()
    result = call(value, current, context)
    assert type(result) is CoverageFindings
    assert result.missing_condition_ids == result.unmapped_rule_ids == result.composition_gap_group_ids == ()
    assert result.inventory_review_match.status is Status.MATCHED
    assert all(type(item) is BindingFinding and item.review_match.status is Status.MATCHED
               for item in result.implementation_findings)
    assert tuple(item.review_match.condition_id for item in result.implementation_findings) == (
        "COND_A", "COND_B", "COND_C")
    assert len(fields(result)) == 7 and not hasattr(result, "status")
    with pytest.raises(FrozenInstanceError):
        result.inventory_fingerprint = "c" * 64
    with pytest.raises(FrozenInstanceError):
        result.implementation_findings[0].subtree_fingerprint = "c" * 64


@pytest.mark.parametrize("declared", [False, True])
def test_context_none_is_normal_and_all_existing_slots_missing(declared):
    value, current, _ = standard(declared=declared)
    result = call(value, current, None)
    reason = Missing.NO_REVIEW_CONTEXT if declared else Missing.INVENTORY_REVIEW_NOT_DECLARED
    assert result.inventory_review_match.status is Status.MISSING
    assert result.inventory_review_match.missing_reasons == (reason,)
    assert result.inventory_fingerprint == domain.fingerprint_condition_inventory(value.inventory)
    for item in result.implementation_findings:
        assert item.review_match.status is Status.MISSING
        assert item.review_match.missing_reasons == (Missing.NO_REVIEW_CONTEXT,)


def test_undeclared_inventory_review_does_not_stop_matched_implementation_reviews():
    value, current, context = standard(declared=False)
    result = call(value, current, context)
    assert result.inventory_review_match.missing_reasons == (Missing.INVENTORY_REVIEW_NOT_DECLARED,)
    assert all(item.review_match.status is Status.MATCHED for item in result.implementation_findings)


@pytest.mark.parametrize("declared", [False, True])
@pytest.mark.parametrize("provided", [False, True])
def test_zero_bindings_keeps_all_missing_and_unmapped_facts_and_skips_implementation(monkeypatch, declared, provided):
    current = policy(group("ANY_Z", (atomic("A"), birth("B")), GroupOperator.ANY))
    value = coverage(current, pending=("COND_Z", "COND_A"), declared=declared)
    context = matched_context(value, current) if provided else None
    events = []
    original = domain._match_inventory_review
    def match(*args, **kwargs):
        events.append("inventory")
        return original(*args, **kwargs)
    monkeypatch.setattr(domain, "_match_inventory_review", match)
    monkeypatch.setattr(domain, "_match_implementation_review", no_call)
    monkeypatch.setattr(domain, "fingerprint_rule_subtree", no_call)
    result = call(value, current, context)
    assert result.missing_condition_ids == ("COND_Z", "COND_A")
    assert result.unmapped_rule_ids == ("A", "B")
    assert result.composition_gap_group_ids == ("ANY_Z",)
    assert result.implementation_findings == () and events == ["inventory"]


@pytest.mark.parametrize("nested", [False, True])
def test_unowned_all_groups_do_not_prevent_matched_findings(nested):
    pair = (resident(), birth())
    current = policy(group("TOP", (group("INNER", pair),) if nested else pair))
    value = coverage(current, (("CURRENT_RESIDENCE", "RESIDENT"), ("BIRTH", "BIRTH")))
    result = call(value, current, matched_context(value, current))
    assert result.composition_gap_group_ids == result.unmapped_rule_ids == result.missing_condition_ids == ()


def test_current_ansan_shape_is_synthetic_only_and_has_no_fake_duration_review():
    current = policy(group("TOP", (resident(), birth())))
    value = coverage(current, (("CURRENT_RESIDENCE", "RESIDENT"), ("BIRTH", "BIRTH")),
                     pending=("RESIDENCE_DURATION",))
    result = call(value, current, matched_context(value, current))
    assert result.missing_condition_ids == ("RESIDENCE_DURATION",)
    assert result.unmapped_rule_ids == result.composition_gap_group_ids == ()
    assert tuple(item.review_match.condition_id for item in result.implementation_findings) == ("BIRTH", "CURRENT_RESIDENCE")


@pytest.mark.parametrize("operator", [GroupOperator.ANY, GroupOperator.NOT])
@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize("incomplete", [False, True])
def test_composition_ownership_and_conditional_error_promotion(operator, owned, incomplete):
    branches = (atomic("3Y"), atomic("10Y")) if operator is GroupOperator.ANY else (atomic("3Y"),)
    duration = group("DURATION_GROUP", branches, operator)
    current = policy(group("TOP", (resident(), birth(), duration)))
    declarations = (("CURRENT_RESIDENCE", "RESIDENT"), ("BIRTH", "BIRTH")) + (
        (("DURATION", "DURATION_GROUP"),) if owned else
        tuple(("DURATION_" + str(index), child.rule_id) for index, child in enumerate(branches)))
    value = coverage(current, declarations, pending=("PENDING",) if incomplete else ())
    if not owned and not incomplete:
        with pytest.raises(PolicyDataError, match="^COVERAGE_COMPOSITION_GAP:"):
            call(value, current, None)
    else:
        result = call(value, current, matched_context(value, current))
        assert result.composition_gap_group_ids == (() if owned else ("DURATION_GROUP",))
        assert result.missing_condition_ids == (("PENDING",) if incomplete else ())
        assert result.unmapped_rule_ids == ()


def test_complete_gap_payload_is_fixed_two_fields_in_preorder_and_precedes_context(monkeypatch):
    current = policy(group("TOP", (
        group("한글_Z", (atomic("A"),), GroupOperator.ANY),
        group("ANY_A", (birth("B"),), GroupOperator.NOT),
    )))
    value = coverage(current, (("COND_A", "A"), ("COND_B", "B")))
    context = empty_context(value, policy_id="OTHER-POLICY")
    monkeypatch.setattr(domain, "fingerprint_condition_inventory", no_call)
    monkeypatch.setattr(domain, "_CoverageIntegrationFindings", no_call)
    with pytest.raises(PolicyDataError) as error:
        call(value, current, context)
    assert str(error.value) == ('COVERAGE_COMPOSITION_GAP: {"composition_gap_count":2,'
                                '"first_composition_gap_group_id":"\\ud55c\\uae00_Z"}')


class CoverageSubclass(EligibilityCoverage):
    pass


class PolicySubclass(Policy):
    pass


class ContextSubclass(CoverageReviewContext):
    pass


class FakeInput:
    @property
    def inventory(self):
        pytest.fail("exact type 확인 전에 속성을 읽었습니다")


@pytest.mark.parametrize("slot,bad", [
    (slot, bad) for slot in ("coverage", "policy", "review_context")
    for bad in (None, {}, [], "raw", 1, True, FakeInput())
    if not (slot == "review_context" and bad is None)
])
def test_exact_input_types_reject_raw_values_before_structure(monkeypatch, slot, bad):
    value, current, context = standard()
    inputs = dict(coverage=value, policy=current, review_context=context)
    inputs[slot] = bad
    monkeypatch.setattr(domain, "_analyze_coverage_structure", no_call)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: " + slot + ":"):
        domain._collect_coverage_integration_findings(**inputs)


@pytest.mark.parametrize("slot", ["coverage", "policy", "review_context"])
def test_subclasses_are_not_exact_input(monkeypatch, slot):
    value, current, context = standard()
    inputs = dict(coverage=value, policy=current, review_context=context)
    if slot == "coverage":
        inputs[slot] = CoverageSubclass(value.inventory, value.bindings)
    elif slot == "policy":
        inputs[slot] = PolicySubclass(current.policy_id, current.policy_name, current.rule_version, current.root)
    else:
        inputs[slot] = ContextSubclass(**{item.name: getattr(context, item.name) for item in fields(context)})
    monkeypatch.setattr(domain, "_analyze_coverage_structure", no_call)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: " + slot + ":"):
        domain._collect_coverage_integration_findings(**inputs)


def test_input_validation_order_coverage_policy_context_and_context_type_before_structure(monkeypatch):
    value, current, _ = standard()
    monkeypatch.setattr(domain, "_analyze_coverage_structure", no_call)
    for inputs, field in [((None, None, {}), "coverage"), ((value, None, {}), "policy"),
                          ((value, replace(current, policy_id="OTHER-POLICY"), {}), "review_context")]:
        with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: " + field + ":"):
            call(*inputs)


@pytest.mark.parametrize("failure", ["policy", "root", "overlap", "unmapped"])
def test_real_structural_errors_precede_context_mismatch_and_stop_composition(monkeypatch, failure):
    current = policy(group("TOP", (atomic("A"), birth("B"))))
    declarations = {
        "policy": (("COND_A", "TOP"),), "root": (("COND_A", "ABSENT"),),
        "overlap": (("COND_A", "TOP"), ("COND_B", "A")), "unmapped": (("COND_A", "A"),),
    }[failure]
    value = coverage(current, declarations)
    target = replace(current, policy_id="OTHER-POLICY") if failure == "policy" else current
    context = empty_context(value, policy_id="OTHER-CONTEXT")
    expected = {"policy": "COVERAGE_POLICY_MISMATCH", "root": "RULE_ROOT_NOT_FOUND",
                "overlap": "COVERAGE_OWNERSHIP_OVERLAP", "unmapped": "COVERAGE_UNMAPPED_RULE"}[failure]
    monkeypatch.setattr(domain, "_find_composition_gap_group_ids", no_call)
    monkeypatch.setattr(domain, "fingerprint_condition_inventory", no_call)
    with pytest.raises(PolicyDataError, match="^" + expected + ":"):
        call(value, target, context)


@pytest.mark.parametrize("code", ["DUPLICATE_RULE_NODE_ID", "UNSUPPORTED_RULE_NODE"])
def test_defensive_structural_errors_propagate_original_exception_without_forging_nodes(monkeypatch, code):
    value, current, context = standard()
    failure = PolicyDataError(code + ": synthetic defensive failure")
    def fail(*args):
        raise failure
    monkeypatch.setattr(domain, "_analyze_coverage_structure", fail)
    monkeypatch.setattr(domain, "_find_composition_gap_group_ids", no_call)
    with pytest.raises(PolicyDataError) as error:
        call(value, current, context)
    assert error.value is failure


@pytest.mark.parametrize("declared", [False, True])
@pytest.mark.parametrize("bindings", [False, True])
@pytest.mark.parametrize("mismatch", ["policy", "annual", "quarter", "edition", "both"])
def test_context_identity_checked_even_without_review_lookup(monkeypatch, declared, bindings, mismatch):
    current = policy(atomic())
    value = coverage(current, (("COND_A", "A"),) if bindings else (),
                     pending=() if bindings else ("COND_A",), declared=declared)
    overrides = {
        "policy": {"policy_id": "OTHER-POLICY"}, "annual": {"scope": ApplicabilityScope("2026", None)},
        "quarter": {"scope": ApplicabilityScope("2026", 4)}, "edition": {"scope": ApplicabilityScope("2027", 3)},
        "both": {"policy_id": "OTHER-POLICY", "scope": ApplicabilityScope("2026", None)},
    }[mismatch]
    context = empty_context(value, **overrides)
    monkeypatch.setattr(domain, "fingerprint_condition_inventory", no_call)
    monkeypatch.setattr(domain, "_match_inventory_review", no_call)
    prefix = "REVIEW_POLICY_MISMATCH" if mismatch in ("policy", "both") else "REVIEW_SCOPE_MISMATCH"
    with pytest.raises(PolicyDataError, match="^" + prefix + ": Context와 현재 Inventory의"):
        call(value, current, context)


def test_empty_context_explicit_ref_is_data_error_but_no_ref_and_zero_binding_is_normal():
    value, current, _ = standard()
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        call(value, current, empty_context(value))
    value = coverage(current, pending=("COND_PENDING",), declared=False)
    result = call(value, current, empty_context(value))
    assert result.inventory_review_match.missing_reasons == (Missing.INVENTORY_REVIEW_NOT_DECLARED,)
    assert result.implementation_findings == ()


def test_actual_helper_pipeline_order_counts_original_roots_and_association(monkeypatch):
    value, current, context = standard()
    expected_inv = domain.fingerprint_condition_inventory(value.inventory)
    expected_tree = domain.fingerprint_policy_tree(current)
    root_map = {node.rule_id: node for node in walk_nodes(current.root)}
    expected_subtrees = {cid: domain.fingerprint_rule_subtree(root_map["ROOT_" + cid[-1]])
                         for cid in ("COND_A", "COND_B", "COND_C")}
    events, structure_pairs = [], []
    originals = {name: getattr(domain, name) for name in (
        "_analyze_coverage_structure", "_find_composition_gap_group_ids", "fingerprint_condition_inventory",
        "fingerprint_policy_tree", "fingerprint_rule_subtree", "_match_inventory_review",
        "_match_implementation_review", "_ImplementationIntegrationFinding", "_CoverageIntegrationFindings")}
    def structure(cov, pol):
        assert cov is value and pol is current
        events.append("structure")
        result = originals["_analyze_coverage_structure"](cov, pol)
        structure_pairs.append(result[1])
        return result
    def composition(pol, pairs):
        assert pol is current and pairs is structure_pairs[0]
        events.append("composition")
        return originals["_find_composition_gap_group_ids"](pol, pairs)
    def inventory_fp(inv):
        assert inv is value.inventory
        events.append("inventory_fp")
        return originals["fingerprint_condition_inventory"](inv)
    def tree_fp(pol):
        assert pol is current
        events.append("tree_fp")
        return originals["fingerprint_policy_tree"](pol)
    def subtree_fp(root):
        assert root is root_map[root.rule_id]
        events.append("subtree:" + root.rule_id)
        return originals["fingerprint_rule_subtree"](root)
    def inventory_match(inv, ctx, **kwargs):
        assert inv is value.inventory and ctx is context
        assert kwargs == {"current_inventory_fingerprint": expected_inv}
        events.append("inventory_match")
        return originals["_match_inventory_review"](inv, ctx, **kwargs)
    def implementation_match(inv, binding, ctx, **kwargs):
        assert inv is value.inventory and ctx is context
        assert binding is next(item for item in value.bindings if item.condition_id == binding.condition_id)
        assert kwargs == dict(current_inventory_fingerprint=expected_inv, current_rule_version=current.rule_version,
                              current_policy_tree_fingerprint=expected_tree,
                              current_subtree_fingerprint=expected_subtrees[binding.condition_id])
        events.append("implementation_match:" + binding.condition_id)
        return originals["_match_implementation_review"](inv, binding, ctx, **kwargs)
    def binding_finding(**kwargs):
        events.append("binding_finding:" + kwargs["review_match"].condition_id)
        return originals["_ImplementationIntegrationFinding"](**kwargs)
    def coverage_finding(**kwargs):
        events.append("coverage_finding")
        return originals["_CoverageIntegrationFindings"](**kwargs)
    for name, wrapper in zip(originals, (structure, composition, inventory_fp, tree_fp, subtree_fp,
                                        inventory_match, implementation_match, binding_finding, coverage_finding)):
        monkeypatch.setattr(domain, name, wrapper)
    result = call(value, current, context)
    assert events == ["structure", "composition", "inventory_fp", "tree_fp",
                      "subtree:ROOT_A", "subtree:ROOT_B", "subtree:ROOT_C", "inventory_match",
                      "implementation_match:COND_A", "implementation_match:COND_B", "implementation_match:COND_C",
                      "binding_finding:COND_A", "binding_finding:COND_B", "binding_finding:COND_C", "coverage_finding"]
    assert len(set(expected_subtrees.values())) == 3
    for item in result.implementation_findings:
        assert item.subtree_fingerprint == expected_subtrees[item.review_match.condition_id]
        assert item.review_match.rule_root_id == "ROOT_" + item.review_match.condition_id[-1]


@pytest.mark.parametrize("phase", ["_find_composition_gap_group_ids", "fingerprint_condition_inventory",
    "fingerprint_policy_tree", "fingerprint_rule_subtree", "_match_inventory_review", "_match_implementation_review"])
def test_helper_error_propagates_same_object_and_stops_later_phases(monkeypatch, phase):
    value, current, context = standard()
    stages = ["_find_composition_gap_group_ids", "fingerprint_condition_inventory", "fingerprint_policy_tree",
              "fingerprint_rule_subtree", "_match_inventory_review", "_match_implementation_review",
              "_ImplementationIntegrationFinding", "_CoverageIntegrationFindings"]
    failure = PolicyDataError("SYNTHETIC_HELPER_FAILURE: " + phase)
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(domain, phase, fail)
    for later in stages[stages.index(phase) + 1:]:
        monkeypatch.setattr(domain, later, no_call)
    with pytest.raises(PolicyDataError) as error:
        call(value, current, context)
    assert error.value is failure


def test_real_utf8_fingerprint_failure_precedes_broken_review_ref(monkeypatch):
    # 정상 생성자는 자유 ID를 허용한다. strict UTF-8 부호화 오류는 기존 지문 함수 책임이다.
    current = policy(atomic("ROOT_\ud800"))
    value = coverage(current, (("COND_A", "ROOT_\ud800"),))
    monkeypatch.setattr(domain, "_match_inventory_review", no_call)
    with pytest.raises(PolicyDataError, match="^policy tree fingerprint: canonical JSON/UTF-8"):
        call(value, current, empty_context(value))


@pytest.mark.parametrize("version_field,reason", [
    ("inventory_version", Stale.INVENTORY_VERSION_CHANGED), ("dataset_version", Stale.DATASET_VERSION_CHANGED)])
def test_inventory_stale_is_preserved_and_implementation_matching_continues(version_field, reason):
    value, current, context = standard()
    old = "i0002" if version_field == "inventory_version" else "SYNTH-OLD-DATASET"
    record = replace(context.inventory_reviews[0], **{version_field: old})
    result = call(value, current, replace(context, inventory_reviews=(record,)))
    assert result.inventory_review_match.status is Status.STALE
    assert result.inventory_review_match.stale_reasons == (reason,)
    assert all(item.review_match.status is Status.MATCHED for item in result.implementation_findings)


@pytest.mark.parametrize("field,old,reason", [
    ("inventory_version", "i0002", Stale.INVENTORY_VERSION_CHANGED),
    ("rule_version", "r0002", Stale.RULE_VERSION_CHANGED),
    ("dataset_version", "SYNTH-OLD-DATASET", Stale.DATASET_VERSION_CHANGED),
    ("implementation_fingerprint", "c" * 64, Stale.IMPLEMENTATION_CHANGED),
])
def test_one_implementation_stale_does_not_stop_later_matched_bindings(field, old, reason):
    value, current, context = standard()
    records = tuple(replace(record, **{field: old}) if record.condition_id == "COND_A" else record
                    for record in context.implementation_reviews)
    result = call(value, current, replace(context, implementation_reviews=records))
    first, *later = result.implementation_findings
    assert first.review_match.status is Status.STALE and first.review_match.stale_reasons == (reason,)
    assert all(item.review_match.status is Status.MATCHED for item in later)


def test_supplied_current_rule_version_is_used_not_historical_review_version():
    value, current, context = standard()
    result = call(value, replace(current, rule_version="r0002"), context)
    assert all(item.review_match.stale_reasons == (Stale.RULE_VERSION_CHANGED,)
               for item in result.implementation_findings)


def test_multiple_stale_reasons_and_different_stale_bindings_are_all_preserved():
    value, current, context = standard()
    old = dict(inventory_version="i0002", rule_version="r0002", dataset_version="SYNTH-OLD",
               implementation_fingerprint="c" * 64)
    records = tuple(replace(record, **old) if record.condition_id != "COND_C" else record
                    for record in context.implementation_reviews)
    result = call(value, current, replace(context, implementation_reviews=records))
    for item in result.implementation_findings[:2]:
        assert item.review_match.stale_reasons == (Stale.INVENTORY_VERSION_CHANGED, Stale.RULE_VERSION_CHANGED,
                                                 Stale.DATASET_VERSION_CHANGED, Stale.IMPLEMENTATION_CHANGED)
    assert result.implementation_findings[2].review_match.status is Status.MATCHED


def test_orchestration_preserves_mixed_normal_match_outcomes_without_interpreting_them(monkeypatch):
    # 실제 Context 유무 계약상 implementation MISSING/STALE 혼합은 직접 구성되지 않는다.
    # 이 테스트는 matcher 반환값에 대한 orchestration의 비해석 계약만 주입 검증한다.
    value, current, context = standard()
    def match(inv, binding, ctx, **kwargs):
        status = {"COND_A": Status.MISSING, "COND_B": Status.STALE, "COND_C": Status.MATCHED}[binding.condition_id]
        return ImplementationReviewMatch(binding.condition_id, binding.rule_root_id, binding.implementation_review_ref,
                                         status, (Stale.RULE_VERSION_CHANGED,) if status is Status.STALE else (),
                                         (Missing.NO_REVIEW_CONTEXT,) if status is Status.MISSING else ())
    monkeypatch.setattr(domain, "_match_implementation_review", match)
    result = call(value, current, context)
    assert tuple(item.review_match.status for item in result.implementation_findings) == (
        Status.MISSING, Status.STALE, Status.MATCHED)


def test_inventory_conflict_precedes_implementation_broken_ref_and_creates_no_findings(monkeypatch):
    value, current, context = standard()
    context = replace(context, inventory_reviews=(replace(context.inventory_reviews[0], inventory_fingerprint="c" * 64),),
                      implementation_reviews=())
    monkeypatch.setattr(domain, "_match_implementation_review", no_call)
    monkeypatch.setattr(domain, "_ImplementationIntegrationFinding", no_call)
    monkeypatch.setattr(domain, "_CoverageIntegrationFindings", no_call)
    with pytest.raises(PolicyDataError, match="^INVENTORY_FINGERPRINT_CONFLICT:"):
        call(value, current, context)


@pytest.mark.parametrize("inventory_state", ["stale", "missing"])
def test_normal_inventory_outcomes_do_not_hide_implementation_data_error(inventory_state):
    value, current, context = standard(declared=inventory_state != "missing")
    if inventory_state == "stale":
        context = replace(context, inventory_reviews=(replace(context.inventory_reviews[0], inventory_version="i0002"),))
    context = replace(context, implementation_reviews=())
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        call(value, current, context)


def test_second_implementation_error_stops_third_and_precedes_all_findings_construction(monkeypatch):
    value, current, context = standard()
    context = replace(context, implementation_reviews=tuple(
        record for record in context.implementation_reviews if record.condition_id != "COND_B"))
    original, events = domain._match_implementation_review, []
    def match(inv, binding, ctx, **kwargs):
        events.append(binding.condition_id)
        return original(inv, binding, ctx, **kwargs)
    monkeypatch.setattr(domain, "_match_implementation_review", match)
    monkeypatch.setattr(domain, "_ImplementationIntegrationFinding", no_call)
    monkeypatch.setattr(domain, "_CoverageIntegrationFindings", no_call)
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        call(value, current, context)
    assert events == ["COND_A", "COND_B"]


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_multiple_implementation_errors_always_use_canonical_condition_order(order):
    value, current, context = standard()
    # A의 root 모순과 B의 condition 모순을 동시에 두어 먼저 선택된 slot을 확인한다.
    records = tuple(replace(record, rule_root_id="OTHER") if record.condition_id == "COND_A" else
                    replace(record, condition_id="OTHER") if record.condition_id == "COND_B" else record
                    for record in context.implementation_reviews)
    context = replace(context, implementation_reviews=records)
    value = replace(value, bindings=tuple(value.bindings[index] for index in order))
    with pytest.raises(PolicyDataError, match="^REVIEW_RULE_ROOT_MISMATCH:"):
        call(value, current, context)


def test_explicit_refs_do_not_select_newer_unselected_reviews_or_depend_on_record_order():
    value, current, context = standard()
    newer_inv = replace(context.inventory_reviews[0], review_ref="SYNTH-NEWER-INV",
                        reviewed_at=date(2026, 12, 31), inventory_fingerprint="c" * 64)
    newer_impl = replace(context.implementation_reviews[0], review_ref="SYNTH-NEWER-IMPL",
                         reviewed_at=date(2026, 12, 31), policy_tree_fingerprint="c" * 64)
    expected = call(value, current, context)
    context = replace(context, inventory_reviews=(newer_inv,) + context.inventory_reviews,
                      implementation_reviews=(newer_impl,) + context.implementation_reviews)
    assert call(value, current, context) == expected
    assert call(value, current, replace(context, inventory_reviews=context.inventory_reviews[::-1],
                                      implementation_reviews=context.implementation_reviews[::-1])) == expected


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_binding_permutations_have_same_results_and_keep_subtree_association(order):
    value, current, context = standard()
    expected = call(value, current, context)
    rearranged = replace(value, bindings=tuple(value.bindings[index] for index in order))
    assert call(rearranged, current, context) == expected
    assert call(rearranged, current, context).to_dict() == expected.to_dict()


def test_100_calls_deterministic_and_all_nested_inputs_unchanged():
    value, current, context = standard()
    snapshots = (value.to_dict(), _jsonable(current), context.to_dict())
    original_bindings = value.bindings
    original_nodes = tuple(walk_nodes(current.root))
    original_records = context.inventory_reviews + context.implementation_reviews
    first = call(value, current, context)
    for _ in range(100):
        assert call(value, current, context) == first
    assert (value.to_dict(), _jsonable(current), context.to_dict()) == snapshots
    assert value.bindings is original_bindings
    assert all(before is after for before, after in zip(original_nodes, walk_nodes(current.root)))
    assert all(before is after for before, after in zip(original_records,
               context.inventory_reviews + context.implementation_reviews))
    exported = first.to_dict()
    exported["implementation_findings"][0]["review_match"]["condition_id"] = "CHANGED"
    assert first.implementation_findings[0].review_match.condition_id == "COND_A"


def test_private_api_has_three_required_arguments_and_function_scoped_dependencies_only():
    from backend.policy_engine import policy_data
    function = domain._collect_coverage_integration_findings
    signature = inspect.signature(function)
    assert tuple(signature.parameters) == ("coverage", "policy", "review_context")
    assert all(parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and
               parameter.default is inspect.Parameter.empty for parameter in signature.parameters.values())
    assert signature.return_annotation is CoverageFindings
    assert not hasattr(policy_data, function.__name__)
    tree = ast.parse(inspect.getsource(function))
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert calls <= {"type", "PolicyDataError", "len", "tuple", "_analyze_coverage_structure",
                     "_find_composition_gap_group_ids", "fingerprint_condition_inventory", "fingerprint_policy_tree",
                     "fingerprint_rule_subtree", "_match_inventory_review", "_match_implementation_review",
                     "_ImplementationIntegrationFinding", "_CoverageIntegrationFindings"}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert attributes <= {"inventory", "policy_id", "scope", "rule_version", "dumps"}
    # 현재 함수의 의존 경계만 고정한다. 같은 모듈의 미래 기능 추가를 금지하지 않는다.
