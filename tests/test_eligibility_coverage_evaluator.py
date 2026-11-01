"""합성 Review/현재 지문으로 공개 Coverage API의 실제 전체 경로를 검증한다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
import inspect
from itertools import permutations
import textwrap

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import (
    Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, _jsonable, walk_nodes,
)
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, CoverageReviewContext,
    EligibilityCoverage, EligibilityCoverageResult, EligibilityCoverageStatus, ImplementationBindingReview,
    InventoryCompletenessReview, RequiredCondition, evaluate_eligibility_coverage,
    fingerprint_condition_inventory, fingerprint_policy_tree, fingerprint_rule_subtree,
)
from backend.policy_engine.policy_data import eligibility_coverage_evaluator as domain
from backend.policy_engine.policy_data import coverage_integration as integration
from backend.policy_engine.policy_data.coverage_review_match import (
    ReviewMatchStatus as Match, ReviewMissingReason as Missing, ReviewStaleReason as Stale,
)
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule


def atomic(rule_id="ROOT_A"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))


def group(rule_id, children, operator=GroupOperator.ALL):
    return RuleGroup(rule_id, operator, children)


def policy(root):
    return Policy("SYNTH-POLICY", "합성 정책", "r0001", root)


def coverage(current, declarations, pending=(), declared=True):
    bindings = tuple(ConditionBinding(cid, rid, "SYNTH-REVIEW-" + cid) for cid, rid in declarations)
    ids = tuple(binding.condition_id for binding in bindings) + tuple(pending)
    conditions = tuple(RequiredCondition(cid, "합성 자격조건", ConditionRequirement.CONDITIONAL if index % 2 else
                                        ConditionRequirement.REQUIRED, ("SYNTH-SRC#a",))
                       for index, cid in enumerate(ids))
    inventory = ConditionInventory(current.policy_id, ApplicabilityScope("2026", 3), "i0001", conditions,
                                   "SYNTH-INVENTORY-REVIEW" if declared else None)
    return EligibilityCoverage(inventory, bindings)


def matched_context(value, current):
    """실제 자료 없이 합성 현재 지문과 실제 타입의 검토 records를 명시적으로 준비한다."""
    inv = value.inventory
    inv_fp, tree_fp = fingerprint_condition_inventory(inv), fingerprint_policy_tree(current)
    roots = {node.rule_id: node for node in walk_nodes(current.root)}
    context = CoverageReviewContext(inv.policy_id, inv.scope, "SYNTH-DATASET", "a" * 64, "b" * 64, (), ())
    inventory_reviews = () if inv.completeness_review_ref is None else (InventoryCompletenessReview(
        inv.completeness_review_ref, inv.policy_id, inv.scope, inv.inventory_version, inv_fp,
        context.dataset_version, context.source_registry_fingerprint, date(2026, 1, 1), "SYNTH-ARTIFACT",
    ),)
    implementation_reviews = tuple(ImplementationBindingReview(
        binding.implementation_review_ref, inv.policy_id, inv.scope, binding.condition_id, binding.rule_root_id,
        inv.inventory_version, inv_fp, current.rule_version, tree_fp,
        fingerprint_rule_subtree(roots[binding.rule_root_id]), context.dataset_version,
        context.source_registry_fingerprint, context.implementation_fingerprint,
        date(2026, 1, 1), "SYNTH-ARTIFACT",
    ) for binding in value.bindings)
    return replace(context, inventory_reviews=inventory_reviews, implementation_reviews=implementation_reviews)


def standard(bound=("COND_C", "COND_B", "COND_A"), declared=True):
    resident = ResidentRegistrationRule("ROOT_B", RegionRef("SEOUL", "JONGNO"),
                                        ReferenceDateSource.APPLICATION_DATE, ("SYNTH-SRC#resident",))
    birth = BirthDateRule("ROOT_C", date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#birth",))
    current = policy(group("TOP_ALL", (atomic(), resident, birth)))
    value = coverage(current, tuple((cid, "ROOT_" + cid[-1]) for cid in bound),
                     pending=tuple(cid for cid in ("COND_C", "COND_B", "COND_A") if cid not in bound),
                     declared=declared)
    return value, current, matched_context(value, current)


def no_call(*args, **kwargs):
    pytest.fail("Gate 실패 후 Result factory가 호출됐습니다")


def test_real_synthetic_full_end_to_end_has_original_identity_current_baseline_and_no_approval():
    value, current, context = standard()
    result = evaluate_eligibility_coverage(value, current, context)
    assert type(result) is EligibilityCoverageResult
    assert result.status is EligibilityCoverageStatus.FULL_POLICY
    assert result.findings.missing_condition_ids == result.findings.unmapped_rule_ids == result.findings.composition_gap_group_ids == ()
    assert result.findings.inventory_review_match.status is Match.MATCHED
    assert all(item.review_match.status is Match.MATCHED for item in result.findings.implementation_findings)
    assert result.policy_id is value.inventory.policy_id and result.scope is value.inventory.scope
    assert result.inventory_version is value.inventory.inventory_version and result.rule_version is current.rule_version
    assert (result.dataset_version, result.source_registry_fingerprint, result.implementation_fingerprint) == (
        context.dataset_version, context.source_registry_fingerprint, context.implementation_fingerprint)
    assert not any(hasattr(result, name) for name in ("verification", "verified", "acceptance", "accepted", "cashflow"))
    assert "status" not in {item.name for item in fields(result)}
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        result.status = EligibilityCoverageStatus.CONDITION_SLICE
    with pytest.raises(TypeError):
        EligibilityCoverageResult(**{item.name: getattr(result, item.name) for item in fields(result)})


@pytest.mark.parametrize("declared", [False, True])
def test_omitted_and_explicit_none_context_return_equal_normal_slice(declared):
    value, current, _ = standard(declared=declared)
    result = evaluate_eligibility_coverage(value, current)
    assert result == evaluate_eligibility_coverage(value, current, None)
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert (result.dataset_version, result.source_registry_fingerprint, result.implementation_fingerprint) == (None,) * 3
    assert result.findings.inventory_review_match.status is Match.MISSING
    expected = Missing.NO_REVIEW_CONTEXT if declared else Missing.INVENTORY_REVIEW_NOT_DECLARED
    assert result.findings.inventory_review_match.missing_reasons == (expected,)
    assert all(item.review_match.missing_reasons == (Missing.NO_REVIEW_CONTEXT,)
               for item in result.findings.implementation_findings)


@pytest.mark.parametrize("bound", [(), ("COND_A",), ("COND_C", "COND_A")])
@pytest.mark.parametrize("context_present", [False, True])
def test_missing_bindings_and_unmapped_facts_are_normal_slice_without_fake_matches(bound, context_present):
    value, current, context = standard(bound=bound)
    result = evaluate_eligibility_coverage(value, current, context if context_present else None)
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    missing = tuple(cid for cid in ("COND_C", "COND_B", "COND_A") if cid not in bound)
    assert result.findings.missing_condition_ids == missing
    assert result.findings.unmapped_rule_ids == tuple("ROOT_" + letter for letter in "ABC" if "COND_" + letter not in bound)
    assert tuple(item.review_match.condition_id for item in result.findings.implementation_findings) == tuple(sorted(bound))


def test_undeclared_inventory_review_with_matched_implementations_is_slice():
    args = standard(declared=False)
    result = evaluate_eligibility_coverage(*args)
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert result.findings.inventory_review_match.missing_reasons == (Missing.INVENTORY_REVIEW_NOT_DECLARED,)
    assert all(item.review_match.status is Match.MATCHED for item in result.findings.implementation_findings)


@pytest.mark.parametrize("record_kind,field,value,reason", [
    ("inventory", "inventory_version", "i0002", Stale.INVENTORY_VERSION_CHANGED),
    ("inventory", "dataset_version", "SYNTH-OLD-DATASET", Stale.DATASET_VERSION_CHANGED),
    ("implementation", "inventory_version", "i0002", Stale.INVENTORY_VERSION_CHANGED),
    ("implementation", "rule_version", "r0002", Stale.RULE_VERSION_CHANGED),
    ("implementation", "dataset_version", "SYNTH-OLD-DATASET", Stale.DATASET_VERSION_CHANGED),
    ("implementation", "implementation_fingerprint", "c" * 64, Stale.IMPLEMENTATION_CHANGED),
])
def test_normal_stale_review_reasons_survive_public_api(record_kind, field, value, reason):
    cov, current, context = standard()
    if record_kind == "inventory":
        context = replace(context, inventory_reviews=(replace(context.inventory_reviews[0], **{field: value}),))
    else:
        context = replace(context, implementation_reviews=tuple(
            replace(record, **{field: value}) if record.condition_id == "COND_A" else record
            for record in context.implementation_reviews))
    result = evaluate_eligibility_coverage(cov, current, context)
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    match = result.findings.inventory_review_match if record_kind == "inventory" else result.findings.implementation_findings[0].review_match
    assert match.status is Match.STALE and match.stale_reasons == (reason,)
    if record_kind == "implementation":
        assert all(item.review_match.status is Match.MATCHED for item in result.findings.implementation_findings[1:])


@pytest.mark.parametrize("operator", [GroupOperator.ANY, GroupOperator.NOT])
@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize("missing", [False, True])
def test_composition_full_slice_and_errors_through_public_api(operator, owned, missing):
    children = (atomic("A"), atomic("B")) if operator is GroupOperator.ANY else (atomic("A"),)
    current = policy(group("BOUNDARY", children, operator))
    declarations = (("COND_ANY", "BOUNDARY"),) if owned else tuple(
        ("COND_" + child.rule_id, child.rule_id) for child in children)
    cov = coverage(current, declarations, pending=("COND_PENDING",) if missing else ())
    context = matched_context(cov, current)
    if not owned and not missing:
        with pytest.raises(PolicyDataError, match="^COVERAGE_COMPOSITION_GAP:"):
            evaluate_eligibility_coverage(cov, current, context)
    else:
        result = evaluate_eligibility_coverage(cov, current, context)
        assert result.status is (EligibilityCoverageStatus.CONDITION_SLICE if missing else EligibilityCoverageStatus.FULL_POLICY)
        assert result.findings.composition_gap_group_ids == (() if owned else ("BOUNDARY",))


def test_possible_multiple_incomplete_reasons_are_all_preserved():
    current = policy(group("TOP_ALL", (group("ANY", (atomic("A"), atomic("B")), GroupOperator.ANY), atomic("U"))))
    cov = coverage(current, (("COND_A", "A"), ("COND_B", "B")), pending=("COND_PENDING",))
    context = matched_context(cov, current)
    context = replace(context, inventory_reviews=(replace(context.inventory_reviews[0], inventory_version="i0002"),))
    result = evaluate_eligibility_coverage(cov, current, context)
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert result.findings.missing_condition_ids == ("COND_PENDING",)
    assert result.findings.unmapped_rule_ids == ("U",) and result.findings.composition_gap_group_ids == ("ANY",)
    assert result.findings.inventory_review_match.status is Match.STALE
    assert all(item.review_match.status is Match.MATCHED for item in result.findings.implementation_findings)


@pytest.mark.parametrize("problem,prefix", [
    ("policy", "COVERAGE_POLICY_MISMATCH"), ("root", "RULE_ROOT_NOT_FOUND"),
    ("overlap", "COVERAGE_OWNERSHIP_OVERLAP"), ("unmapped", "COVERAGE_UNMAPPED_RULE"),
    ("context_policy", "REVIEW_POLICY_MISMATCH"), ("context_scope", "REVIEW_SCOPE_MISMATCH"),
    ("broken_ref", "REVIEW_REF_NOT_FOUND"), ("wrong_review_type", "WRONG_REVIEW_TYPE"),
])
def test_existing_structural_target_and_reference_errors_prevent_factory(monkeypatch, problem, prefix):
    cov, current, context = standard()
    if problem == "policy":
        current = replace(current, policy_id="OTHER-POLICY")
    elif problem == "root":
        cov = replace(cov, bindings=(replace(cov.bindings[0], rule_root_id="ABSENT"),) + cov.bindings[1:])
    elif problem == "overlap":
        cov = replace(cov, bindings=(replace(cov.bindings[0], rule_root_id="TOP_ALL"),) + cov.bindings[1:])
    elif problem == "unmapped":
        # 현재 nonempty Inventory가 모두 bound지만 Policy의 두 leaf가 소유되지 않는다.
        cov = coverage(current, (("COND_A", "ROOT_A"),))
    elif problem in ("context_policy", "context_scope"):
        context = replace(context, inventory_reviews=(), implementation_reviews=(), **(
            dict(policy_id="OTHER-POLICY") if problem == "context_policy" else dict(scope=ApplicabilityScope("2026", None))))
    elif problem == "broken_ref":
        context = replace(context, inventory_reviews=())
    else:
        cov = replace(cov, inventory=replace(cov.inventory,
                      completeness_review_ref=context.implementation_reviews[0].review_ref))
    monkeypatch.setattr(domain, "_create_eligibility_coverage_result", no_call)
    with pytest.raises(PolicyDataError, match="^" + prefix + ":"):
        evaluate_eligibility_coverage(cov, current, context)


@pytest.mark.parametrize("kind,field,prefix", [
    ("inventory", "inventory_fingerprint", "INVENTORY_FINGERPRINT_CONFLICT"),
    ("inventory", "source_registry_fingerprint", "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
    ("implementation", "policy_tree_fingerprint", "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ("implementation", "subtree_fingerprint", "SUBTREE_FINGERPRINT_CONFLICT"),
])
def test_same_version_fingerprint_conflicts_are_errors_not_slice(monkeypatch, kind, field, prefix):
    cov, current, context = standard()
    if kind == "inventory":
        context = replace(context, inventory_reviews=(replace(context.inventory_reviews[0], **{field: "f" * 64}),))
    else:
        context = replace(context, implementation_reviews=tuple(
            replace(record, **{field: "f" * 64}) if record.condition_id == "COND_A" else record
            for record in context.implementation_reviews))
    monkeypatch.setattr(domain, "_create_eligibility_coverage_result", no_call)
    with pytest.raises(PolicyDataError, match="^" + prefix + ":"):
        evaluate_eligibility_coverage(cov, current, context)


def test_gate_success_then_factory_once_receives_original_findings_and_returns_same_result(monkeypatch):
    args = standard()
    original_gate, original_factory = domain._collect_coverage_integration_findings, domain._create_eligibility_coverage_result
    events, outputs = [], {}
    def gate(*received):
        assert all(got is expected for got, expected in zip(received, args))
        events.append("gate")
        outputs["facts"] = original_gate(*received)
        return outputs["facts"]
    def factory(cov, pol, ctx, facts):
        assert cov is args[0] and pol is args[1] and ctx is args[2] and facts is outputs["facts"]
        events.append("factory")
        outputs["result"] = original_factory(cov, pol, ctx, facts)
        return outputs["result"]
    monkeypatch.setattr(domain, "_collect_coverage_integration_findings", gate)
    monkeypatch.setattr(domain, "_create_eligibility_coverage_result", factory)
    result = evaluate_eligibility_coverage(*args)
    assert events == ["gate", "factory"]
    assert result is outputs["result"] and result.findings is outputs["facts"]


def test_wrapper_does_not_inspect_or_prevalidate_arguments_findings_or_result(monkeypatch):
    # 의도적으로 opaque 값을 쓰는 얇은 연결 계약 테스트. 정상 domain 결과 사례는 위에서 별도 검증한다.
    cov, pol, facts, returned = object(), object(), object(), object()
    events = []
    def gate(*args):
        assert args == (cov, pol, None)
        events.append("gate")
        return facts
    def factory(*args):
        assert args == (cov, pol, None, facts)
        events.append("factory")
        return returned
    monkeypatch.setattr(domain, "_collect_coverage_integration_findings", gate)
    monkeypatch.setattr(domain, "_create_eligibility_coverage_result", factory)
    assert evaluate_eligibility_coverage(cov, pol) is returned
    assert events == ["gate", "factory"]


@pytest.mark.parametrize("phase", ["gate", "factory"])
def test_errors_propagate_same_object_and_never_retry_or_return_partial(monkeypatch, phase):
    args = standard()
    original_gate = domain._collect_coverage_integration_findings
    failure = PolicyDataError("SYNTHETIC_" + phase.upper() + "_ERROR: fixed")
    events = []
    def gate(*received):
        events.append("gate")
        if phase == "gate":
            raise failure
        return original_gate(*received)
    def factory(*received):
        events.append("factory")
        raise failure
    monkeypatch.setattr(domain, "_collect_coverage_integration_findings", gate)
    monkeypatch.setattr(domain, "_create_eligibility_coverage_result", factory)
    with pytest.raises(PolicyDataError) as error:
        evaluate_eligibility_coverage(*args)
    assert error.value is failure
    assert events == (["gate"] if phase == "gate" else ["gate", "factory"])


def test_actual_factory_correspondence_error_from_injected_corrupt_gate_findings_is_preserved(monkeypatch):
    args = standard()
    original_gate = domain._collect_coverage_integration_findings
    events = []
    def corrupt_gate(*received):
        events.append("gate")
        return replace(original_gate(*received), implementation_findings=())
    monkeypatch.setattr(domain, "_collect_coverage_integration_findings", corrupt_gate)
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        evaluate_eligibility_coverage(*args)
    assert events == ["gate"]


def test_end_to_end_computation_counts_remain_single_per_existing_component(monkeypatch):
    args = standard()
    events = []
    names = ("_analyze_coverage_structure", "_find_composition_gap_group_ids", "fingerprint_condition_inventory",
             "fingerprint_policy_tree", "fingerprint_rule_subtree", "_match_inventory_review", "_match_implementation_review")
    for name in names:
        original = getattr(integration, name)
        def spy(*received, _name=name, _original=original, **kwargs):
            marker = received[0].rule_id if _name == "fingerprint_rule_subtree" else (
                received[1].condition_id if _name == "_match_implementation_review" else "")
            events.append((_name, marker))
            return _original(*received, **kwargs)
        monkeypatch.setattr(integration, name, spy)
    assert evaluate_eligibility_coverage(*args).status is EligibilityCoverageStatus.FULL_POLICY
    assert events == [(names[0], ""), (names[1], ""), (names[2], ""), (names[3], ""),
                      (names[4], "ROOT_A"), (names[4], "ROOT_B"), (names[4], "ROOT_C"), (names[5], ""),
                      (names[6], "COND_A"), (names[6], "COND_B"), (names[6], "COND_C")]


@pytest.mark.parametrize("slot,bad", [(slot, bad) for slot in ("coverage", "policy", "review_context")
    for bad in (None, {}, [], "raw", True) if not (slot == "review_context" and bad is None)])
def test_bad_input_uses_existing_gate_error_contract_without_conversion(monkeypatch, slot, bad):
    inputs = dict(zip(("coverage", "policy", "review_context"), standard()))
    inputs[slot] = bad
    monkeypatch.setattr(domain, "_create_eligibility_coverage_result", no_call)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: " + slot + ":"):
        evaluate_eligibility_coverage(**inputs)


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_binding_and_review_tuple_permutations_do_not_change_semantic_result(order):
    cov, current, context = standard()
    expected = evaluate_eligibility_coverage(cov, current, context)
    alternate = replace(cov, bindings=tuple(cov.bindings[index] for index in order))
    alternate_context = replace(context, implementation_reviews=tuple(context.implementation_reviews[index] for index in order))
    actual = evaluate_eligibility_coverage(alternate, current, alternate_context)
    assert actual == expected and actual.to_dict() == expected.to_dict()


def test_100_repeats_are_deterministic_and_all_inputs_records_and_nodes_are_unchanged():
    cov, current, context = standard()
    before = (cov.to_dict(), _jsonable(current), context.to_dict())
    nodes = tuple(walk_nodes(current.root))
    records = context.inventory_reviews + context.implementation_reviews
    expected = evaluate_eligibility_coverage(cov, current, context)
    for _ in range(100):
        actual = evaluate_eligibility_coverage(cov, current, context)
        assert actual == expected and actual.status is expected.status and actual.to_dict() == expected.to_dict()
    assert (cov.to_dict(), _jsonable(current), context.to_dict()) == before
    assert all(left is right for left, right in zip(nodes, walk_nodes(current.root)))
    assert all(left is right for left, right in zip(records, context.inventory_reviews + context.implementation_reviews))


@pytest.mark.parametrize("provided", [False, True])
def test_public_result_serialization_nine_keys_and_nested_mutation_isolation(provided):
    cov, current, context = standard()
    result = evaluate_eligibility_coverage(cov, current, context if provided else None)
    snapshot = result.to_dict()
    assert len(snapshot) == 9
    assert snapshot["status"] == ("FULL_POLICY" if provided else "CONDITION_SLICE")
    assert snapshot["scope"] == cov.inventory.scope.to_dict()
    for name in ("dataset_version", "source_registry_fingerprint", "implementation_fingerprint"):
        assert snapshot[name] == (getattr(context, name) if provided else None)
    before = result.to_dict()
    snapshot["scope"]["quarter"] = 1
    snapshot["findings"]["implementation_findings"].clear()
    assert result.to_dict() == before


def test_public_api_signature_exports_docstring_and_function_only_calls_gate_and_factory():
    from backend.policy_engine import policy_data
    signature = inspect.signature(evaluate_eligibility_coverage)
    assert tuple(signature.parameters) == ("coverage", "policy", "review_context")
    assert signature.parameters["coverage"].default is inspect.Parameter.empty
    assert signature.parameters["policy"].default is inspect.Parameter.empty
    assert signature.parameters["review_context"].default is None
    assert all(item.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for item in signature.parameters.values())
    assert signature.return_annotation is EligibilityCoverageResult
    assert policy_data.evaluate_eligibility_coverage is domain.evaluate_eligibility_coverage
    assert "evaluate_eligibility_coverage" in policy_data.__all__
    assert not hasattr(policy_data, "_collect_coverage_integration_findings")
    assert not hasattr(policy_data, "_create_eligibility_coverage_result")
    doc = inspect.getdoc(evaluate_eligibility_coverage)
    assert all(term in doc for term in ("완결성", "CONDITION_SLICE", "사용자", "행정", "VERIFIED", "PolicyDataError"))
    node = ast.parse(textwrap.dedent(inspect.getsource(evaluate_eligibility_coverage))).body[0]
    calls = [item for item in ast.walk(node) if isinstance(item, ast.Call)]
    assert len(calls) == 2
    assert [item.func.id for item in calls] == ["_collect_coverage_integration_findings", "_create_eligibility_coverage_result"]
    assert not any(isinstance(item, (ast.If, ast.Try, ast.For, ast.While, ast.Attribute, ast.Subscript))
                   for item in ast.walk(node))
    # 공개 함수 자체의 얇은 연결 계약만 검사하며 같은 모듈의 미래 독립 기능은 제한하지 않는다.
