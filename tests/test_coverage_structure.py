"""합성 Coverage의 구조 phase·incomplete 해석·오류 승격 계약."""

import ast
from dataclasses import replace
from datetime import date
import inspect
from itertools import permutations
import json

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import (
    Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, RuleNode, _jsonable, walk_nodes,
)
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, EligibilityCoverage, RequiredCondition,
)
from backend.policy_engine.policy_data import coverage_structure as domain
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule


def atomic(rule_id="Z"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))


def resident(rule_id="A"):
    return ResidentRegistrationRule(rule_id, RegionRef("SEOUL", "JONGNO"), ReferenceDateSource.APPLICATION_DATE,
                                    ("SYNTH-SRC#resident",))


def birth(rule_id="B"):
    return BirthDateRule(rule_id, date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#birth",))


def group(rule_id, children, operator=GroupOperator.ALL):
    return RuleGroup(rule_id, operator, children)


def policy(root):
    return Policy("SYNTH-POLICY", "합성 정책", "r0001", root)


def tree():
    deep = group("DEEP", (resident(), group("NEGATED", (birth(),), GroupOperator.NOT)), GroupOperator.ANY)
    return policy(group("ROOT", (atomic(), deep, atomic("C"))))


def coverage(current, condition_ids, declarations=(), requirement=ConditionRequirement.REQUIRED):
    conditions = tuple(RequiredCondition(cid, "합성 조건", requirement, ("SYNTH-SRC#a",)) for cid in condition_ids)
    inventory = ConditionInventory(current.policy_id, ApplicabilityScope("2026", 3), "i0001", conditions)
    bindings = tuple(ConditionBinding(cid, root, "SYNTH-REVIEW-" + cid) for cid, root in declarations)
    return EligibilityCoverage(inventory, bindings)


def analyze(current, condition_ids, declarations=(), requirement=ConditionRequirement.REQUIRED):
    return domain._analyze_coverage_structure(coverage(current, condition_ids, declarations, requirement), current)


def unmapped_error(current, condition_ids, declarations):
    with pytest.raises(PolicyDataError, match="^COVERAGE_UNMAPPED_RULE: ") as caught:
        analyze(current, condition_ids, declarations)
    message = str(caught.value)
    payload = json.loads(message.split(": ", 1)[1])
    assert set(payload) == {"unmapped_count", "first_unmapped_rule_id"}
    assert type(payload["unmapped_count"]) is int
    assert type(payload["first_unmapped_rule_id"]) is str
    return message, payload


@pytest.mark.parametrize("factory", [atomic, resident, birth])
def test_one_condition_and_leaf_root_return_original_pair(factory):
    current = policy(factory("SELF"))
    value = coverage(current, ("COND",), (("COND", "SELF"),))
    missing, resolved, unmapped = domain._analyze_coverage_structure(value, current)
    assert missing == unmapped == ()
    assert type(resolved) is tuple and type(resolved[0]) is tuple and len(resolved[0]) == 2
    assert resolved[0][0] is value.bindings[0] and resolved[0][1] is current.root


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_whole_policy_group_root_binding_covers_entire_subtree(operator):
    children = (atomic(),) if operator is GroupOperator.NOT else (atomic(), resident(), birth())
    current = policy(group("ROOT", children, operator))
    missing, resolved, unmapped = analyze(current, ("COND",), (("COND", "ROOT"),))
    assert missing == unmapped == () and resolved[0][1] is current.root


@pytest.mark.parametrize("declarations", [
    (("COND_Z", "Z"), ("COND_A", "DEEP"), ("COND_C", "C")),
    (("COND_Z", "Z"), ("COND_A", "A"), ("COND_B", "NEGATED"), ("COND_C", "C")),
    (("COND_Z", "Z"), ("COND_A", "A"), ("COND_B", "B"), ("COND_C", "C")),
])
def test_nested_group_and_disjoint_leaf_bindings_cover_all_targets(declarations):
    current = tree()
    missing, resolved, unmapped = analyze(current, tuple(cid for cid, _ in declarations), declarations)
    assert missing == unmapped == ()
    assert tuple(binding.condition_id for binding, _ in resolved) == tuple(sorted(cid for cid, _ in declarations))
    assert all(root is next(node for node in walk_nodes(current.root) if node.rule_id == binding.rule_root_id)
               for binding, root in resolved)


@pytest.mark.parametrize("requirement", list(ConditionRequirement))
@pytest.mark.parametrize("with_unmapped", [False, True])
def test_missing_both_requirement_kinds_is_normal_with_or_without_unmapped(requirement, with_unmapped):
    current = policy(group("ROOT", (atomic("BOUND"), birth("LEFT")))) if with_unmapped else policy(atomic("BOUND"))
    missing, resolved, unmapped = analyze(current, ("COND_MISSING", "COND_BOUND"), (("COND_BOUND", "BOUND"),), requirement)
    assert missing == ("COND_MISSING",)
    assert tuple(binding.condition_id for binding, _ in resolved) == ("COND_BOUND",)
    assert unmapped == (("LEFT",) if with_unmapped else ())


def test_many_missing_and_ambiguous_extra_leaves_remain_separate_facts():
    current = policy(group("ROOT", (atomic("BOUND"), group("INNER", (birth("Z_LEFT"), atomic("A_EXTRA"))))))
    missing, _, unmapped = analyze(current, ("MISSING_Z", "BOUND", "MISSING_A"), (("BOUND", "BOUND"),))
    assert missing == ("MISSING_Z", "MISSING_A")
    assert unmapped == ("Z_LEFT", "A_EXTRA")


@pytest.mark.parametrize("root", [atomic("SELF"), group("ROOT", (resident("Z"), birth("A")))])
def test_zero_bindings_returns_entire_inventory_and_entire_target_tuple(root):
    current = policy(root)
    result = analyze(current, ("COND_B", "COND_A"))
    assert type(result) is tuple and len(result) == 3
    assert result == (("COND_B", "COND_A"), (), ("SELF",) if type(root) is PolicyRule else ("Z", "A"))


def test_required_and_conditional_are_both_missing_in_same_inventory():
    current = policy(atomic())
    value = coverage(current, ("REQUIRED", "CONDITIONAL"))
    conditional = replace(value.inventory.conditions[1], requirement=ConditionRequirement.CONDITIONAL)
    value = replace(value, inventory=replace(value.inventory, conditions=(value.inventory.conditions[0], conditional)))
    assert domain._analyze_coverage_structure(value, current) == (("REQUIRED", "CONDITIONAL"), (), ("Z",))


def test_inventory_order_and_canonical_resolved_order_are_distinct():
    current = policy(group("ROOT", (atomic("Z"), resident("A"), birth("B"))))
    declarations = (("COND_C", "Z"), ("COND_A", "A"), ("COND_B", "B"))
    value = coverage(current, ("MISSING_Z", "COND_C", "COND_A", "MISSING_A", "COND_B"), declarations)
    before = value.bindings
    for permutation in permutations(before):
        missing, resolved, unmapped = domain._analyze_coverage_structure(replace(value, bindings=permutation), current)
        assert missing == ("MISSING_Z", "MISSING_A") and unmapped == ()
        assert tuple(binding.condition_id for binding, _ in resolved) == ("COND_A", "COND_B", "COND_C")
        assert all(any(binding is original for original in before) for binding, _ in resolved)
    assert value.bindings is before and tuple(b.condition_id for b in before) == ("COND_C", "COND_A", "COND_B")


def test_ascii_condition_order_is_lexical_not_natural_number_order():
    current = policy(group("ROOT", (atomic("ONE"), resident("TWO"))))
    _, resolved, _ = analyze(current, ("COND_2", "COND_10"), (("COND_2", "TWO"), ("COND_10", "ONE")))
    assert tuple(binding.condition_id for binding, _ in resolved) == ("COND_10", "COND_2")


@pytest.mark.parametrize("count", [1, 2, 4])
def test_complete_with_extra_rules_promotes_exact_count_and_preorder_first(count):
    ids = tuple(f"EXTRA_{index}" for index in reversed(range(count)))
    current = policy(group("ROOT", (atomic("BOUND"), group("INNER", tuple(birth(rid) for rid in ids)))))
    message, payload = unmapped_error(current, ("COND",), (("COND", "BOUND"),))
    assert payload == {"unmapped_count": count, "first_unmapped_rule_id": ids[0]}
    assert message == "COVERAGE_UNMAPPED_RULE: " + json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


@pytest.mark.parametrize("first_id", ["RULE_Z", " 한글 ", 'quote"', "line\nID", "e\u0301"])
def test_unmapped_error_escapes_original_id_and_never_chooses_ascii_minimum(first_id):
    current = policy(group("ROOT", (atomic("BOUND"), resident(first_id), birth("AAA_OTHER"))))
    message, payload = unmapped_error(current, ("COND",), (("COND", "BOUND"),))
    assert payload == {"first_unmapped_rule_id": first_id, "unmapped_count": 2}
    assert message == "COVERAGE_UNMAPPED_RULE: " + json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    assert all(ord(char) < 128 for char in message) and "\n" not in message


def test_unmapped_error_has_literal_fixed_message():
    current = policy(group("ROOT", (atomic("BOUND"), resident("RULE_Z"), birth("RULE_A"))))
    message, _ = unmapped_error(current, ("COND",), (("COND", "BOUND"),))
    assert message == 'COVERAGE_UNMAPPED_RULE: {"first_unmapped_rule_id":"RULE_Z","unmapped_count":2}'


def test_unmapped_preorder_is_preserved_in_incomplete_results_and_changes_with_tree_order():
    roots = [(atomic("BOUND"), resident("Z"), birth("A")), (birth("A"), atomic("BOUND"), resident("Z"))]
    results = []
    for children in roots:
        current = policy(group("ROOT", children))
        results.append(analyze(current, ("BOUND", "MISSING"), (("BOUND", "BOUND"),))[2])
    assert results == [("Z", "A"), ("A", "Z")]


class CoverageSubclass(EligibilityCoverage):
    pass


class PolicySubclass(Policy):
    pass


class FakeCoverage:
    @property
    def inventory(self):
        pytest.fail("정확한 Coverage 검사 전에 inventory에 접근했습니다")


class FakePolicy:
    @property
    def policy_id(self):
        pytest.fail("정확한 Policy 검사 전에 ID에 접근했습니다")


def forbid(*args, **kwargs):
    pytest.fail("실행하면 안 되는 후속 phase를 호출했습니다")


def forbid_helpers(monkeypatch):
    for name in ("_resolve_rule_root", "_validate_binding_ownership_no_overlap", "_find_unmapped_rule_ids"):
        monkeypatch.setattr(domain, name, forbid)


_VALID_POLICY = policy(atomic())
_VALID_COVERAGE = coverage(_VALID_POLICY, ("COND",))


@pytest.mark.parametrize("bad", [None, {}, (), [], "coverage", True, 1, FakeCoverage(),
                                 CoverageSubclass(_VALID_COVERAGE.inventory, ())])
def test_exact_coverage_checked_first_without_other_input_access(bad, monkeypatch):
    forbid_helpers(monkeypatch)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: coverage:"):
        domain._analyze_coverage_structure(bad, FakePolicy())


@pytest.mark.parametrize("bad", [None, {}, (), [], "policy", True, 1, atomic(), group("GROUP", (birth(),)),
                                 FakePolicy(), PolicySubclass("SYNTH-POLICY", "합성", "r0001", atomic())])
def test_exact_policy_checked_before_any_calculation(bad, monkeypatch):
    forbid_helpers(monkeypatch)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: policy:"):
        domain._analyze_coverage_structure(_VALID_COVERAGE, bad)


@pytest.mark.parametrize("root_exists", [False, True])
def test_policy_identity_mismatch_precedes_root_lookup_even_for_identical_rule_ids(root_exists, monkeypatch):
    current = policy(atomic("SAME_ID"))
    value = coverage(current, ("COND", "MISSING"), (("COND", "SAME_ID" if root_exists else "ABSENT"),))
    other_policy = replace(current, policy_id="OTHER-POLICY")
    forbid_helpers(monkeypatch)
    with pytest.raises(PolicyDataError) as caught:
        domain._analyze_coverage_structure(value, other_policy)
    assert str(caught.value) == "COVERAGE_POLICY_MISMATCH: Coverage와 Policy의 policy_id가 일치해야 합니다"


@pytest.mark.parametrize("incomplete", [False, True])
def test_missing_root_is_not_hidden_by_missing_condition_and_stops_later_phases(incomplete, monkeypatch):
    current = tree()
    condition_ids = ("COND", "MISSING") if incomplete else ("COND",)
    value = coverage(current, condition_ids, (("COND", "ABSENT"),))
    monkeypatch.setattr(domain, "_validate_binding_ownership_no_overlap", forbid)
    monkeypatch.setattr(domain, "_find_unmapped_rule_ids", forbid)
    with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
        domain._analyze_coverage_structure(value, current)


def test_multiple_missing_roots_always_fail_at_same_canonical_binding(monkeypatch):
    current = tree()
    value = coverage(current, ("COND_Z", "COND_A", "COND_B"),
                     (("COND_Z", "ABSENT_Z"), ("COND_A", "Z"), ("COND_B", "ABSENT_B")))
    original = domain._resolve_rule_root
    calls = []
    def observe(provided_policy, root_id):
        calls.append(root_id)
        return original(provided_policy, root_id)
    monkeypatch.setattr(domain, "_resolve_rule_root", observe)
    monkeypatch.setattr(domain, "_validate_binding_ownership_no_overlap", forbid)
    monkeypatch.setattr(domain, "_find_unmapped_rule_ids", forbid)
    for permutation in permutations(value.bindings):
        calls.clear()
        with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
            domain._analyze_coverage_structure(replace(value, bindings=permutation), current)
        assert calls == ["Z", "ABSENT_B"]


def test_missing_last_root_wins_over_earlier_potential_overlap(monkeypatch):
    current = tree()
    value = coverage(current, ("COND_A", "COND_B", "COND_Z"),
                     (("COND_A", "DEEP"), ("COND_B", "A"), ("COND_Z", "ABSENT")))
    monkeypatch.setattr(domain, "_validate_binding_ownership_no_overlap", forbid)
    monkeypatch.setattr(domain, "_find_unmapped_rule_ids", forbid)
    with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
        domain._analyze_coverage_structure(value, current)


@pytest.mark.parametrize("roots", [("A", "A"), ("DEEP", "A"), ("ROOT", "B"), ("DEEP", "NEGATED")])
@pytest.mark.parametrize("incomplete", [False, True])
def test_overlap_is_data_error_even_when_incomplete_and_precedes_unmapped(roots, incomplete, monkeypatch):
    current = tree()
    ids = ("COND_A", "COND_B", "MISSING") if incomplete else ("COND_A", "COND_B")
    value = coverage(current, ids, (("COND_B", roots[1]), ("COND_A", roots[0])))
    monkeypatch.setattr(domain, "_find_unmapped_rule_ids", forbid)
    messages = []
    for permutation in permutations(value.bindings):
        with pytest.raises(PolicyDataError, match="^COVERAGE_OWNERSHIP_OVERLAP:") as caught:
            domain._analyze_coverage_structure(replace(value, bindings=permutation), current)
        messages.append(str(caught.value))
    assert len(set(messages)) == 1
    assert json.loads(messages[0].split(": ", 1)[1])["condition_a"] == "COND_A"


@pytest.mark.parametrize("count", [0, 1, 3])
def test_exact_phase_order_call_counts_and_same_original_pair_tuple(count, monkeypatch):
    current = policy(group("ROOT", (atomic("L0"), resident("L1"), birth("L2"))))
    declarations = tuple((f"COND_{index}", f"L{index}") for index in reversed(range(count)))
    value = coverage(current, ("MISSING", "COND_0", "COND_1", "COND_2"), declarations)
    original_resolve = domain._resolve_rule_root
    original_overlap = domain._validate_binding_ownership_no_overlap
    original_unmapped = domain._find_unmapped_rule_ids
    events, pair_tuples = [], []
    def resolve(provided_policy, root_id):
        assert provided_policy is current
        events.append(("root", root_id))
        return original_resolve(provided_policy, root_id)
    def overlap(resolved):
        events.append(("overlap",))
        pair_tuples.append(resolved)
        return original_overlap(resolved)
    def unmapped(provided_policy, resolved):
        assert provided_policy is current
        assert len(pair_tuples) == 1 and resolved is pair_tuples[0]
        events.append(("unmapped",))
        return original_unmapped(provided_policy, resolved)
    monkeypatch.setattr(domain, "_resolve_rule_root", resolve)
    monkeypatch.setattr(domain, "_validate_binding_ownership_no_overlap", overlap)
    monkeypatch.setattr(domain, "_find_unmapped_rule_ids", unmapped)
    result = domain._analyze_coverage_structure(value, current)
    assert events == [("root", f"L{index}") for index in range(count)] + [("overlap",), ("unmapped",)]
    assert result[1] is pair_tuples[0]
    assert all(any(binding is original for original in value.bindings) for binding, _ in result[1])


@pytest.mark.parametrize("dependency", ["_resolve_rule_root", "_validate_binding_ownership_no_overlap", "_find_unmapped_rule_ids"])
@pytest.mark.parametrize("incomplete", [False, True])
def test_helper_policy_data_errors_propagate_as_same_object(dependency, incomplete, monkeypatch):
    current = policy(atomic("SELF"))
    ids = ("COND", "MISSING") if incomplete else ("COND",)
    value = coverage(current, ids, (("COND", "SELF"),))
    error = PolicyDataError("SYNTHETIC_DEPENDENCY_ERROR")
    def fail(*args):
        raise error
    monkeypatch.setattr(domain, dependency, fail)
    order = ("_resolve_rule_root", "_validate_binding_ownership_no_overlap", "_find_unmapped_rule_ids")
    for later in order[order.index(dependency) + 1:]:
        monkeypatch.setattr(domain, later, forbid)
    with pytest.raises(PolicyDataError) as caught:
        domain._analyze_coverage_structure(value, current)
    assert caught.value is error


def test_current_policy_concept_is_synthetic_incomplete_even_without_unmapped_leaves():
    current = policy(group("ROOT", (resident("SYNTH_RESIDENT"), birth("SYNTH_BIRTH"))))
    value = coverage(current, ("CURRENT_RESIDENCE", "BIRTH", "RESIDENCE_DURATION"),
                     (("CURRENT_RESIDENCE", "SYNTH_RESIDENT"), ("BIRTH", "SYNTH_BIRTH")))
    missing, resolved, unmapped = domain._analyze_coverage_structure(value, current)
    assert missing == ("RESIDENCE_DURATION",) and unmapped == ()
    assert tuple(binding.condition_id for binding, _ in resolved) == ("BIRTH", "CURRENT_RESIDENCE")


def test_future_group_shape_concept_uses_generic_atomic_rules_and_has_no_duration_evaluator():
    # 두 AGE atomic은 순수 합성 tree 모양이다. 실제 거주기간 산식·Rule을 표현하지 않는다.
    shape = group("SYNTH_DURATION_SHAPE", (atomic("SYNTH_PATH_A"), atomic("SYNTH_PATH_B")), GroupOperator.ANY)
    current = policy(group("ROOT", (resident("SYNTH_RESIDENT"), birth("SYNTH_BIRTH"), shape)))
    value = coverage(current, ("CURRENT_RESIDENCE", "BIRTH", "RESIDENCE_DURATION"),
                     (("CURRENT_RESIDENCE", "SYNTH_RESIDENT"), ("BIRTH", "SYNTH_BIRTH"),
                      ("RESIDENCE_DURATION", "SYNTH_DURATION_SHAPE")))
    missing, resolved, unmapped = domain._analyze_coverage_structure(value, current)
    assert missing == unmapped == () and len(resolved) == 3
    assert resolved[-1][1] is shape


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_unowned_composition_group_does_not_add_an_unapproved_whole_composition_gate(operator):
    children = (atomic("Z"),) if operator is GroupOperator.NOT else (atomic("Z"), birth("A"))
    current = policy(group("OUTER", (group("INNER", children, operator),)))
    declarations = tuple((f"COND_{index}", child.rule_id) for index, child in enumerate(children))
    missing, _, unmapped = analyze(current, tuple(cid for cid, _ in declarations), declarations)
    assert missing == unmapped == ()


@pytest.mark.parametrize("quarter", [None, 1, 3, 4])
@pytest.mark.parametrize("version", ["r0001", "r9999", " custom version "])
def test_scope_and_rule_version_are_not_inferred_or_used_for_freshness(quarter, version):
    current = replace(policy(atomic()), rule_version=version)
    value = coverage(current, ("COND", "MISSING"), (("COND", "Z"),))
    scope = ApplicabilityScope("2099", quarter)
    value = replace(value, inventory=replace(value.inventory, scope=scope))
    missing, _, unmapped = domain._analyze_coverage_structure(value, current)
    assert missing == ("MISSING",) and unmapped == ()
    assert value.inventory.scope is scope


def test_100_calls_and_binding_permutations_preserve_all_values_and_identities():
    current = tree()
    value = coverage(current, ("MISSING_Z", "COND_Z", "COND_A", "MISSING_A"),
                     (("COND_Z", "Z"), ("COND_A", "DEEP")))
    before = (_jsonable(current), value.to_dict())
    bindings, inventory, conditions = value.bindings, value.inventory, value.inventory.conditions
    nodes = tuple(walk_nodes(current.root))
    children = tuple(node.children for node in nodes if type(node) is RuleGroup)
    evidence = tuple(node.evidence_refs for node in nodes if type(node) is not RuleGroup)
    expected = None
    for index in range(100):
        provided = value if index % 2 == 0 else replace(value, bindings=tuple(reversed(bindings)))
        result = domain._analyze_coverage_structure(provided, current)
        assert type(result) is tuple and len(result) == 3
        assert all(type(part) is tuple for part in result)
        assert result[0] == ("MISSING_Z", "MISSING_A") and result[2] == ("C",)
        if expected is None:
            expected = result
        assert result == expected
        assert all(any(binding is original for original in bindings) for binding, _ in result[1])
        assert all(any(root is original for original in nodes) for _, root in result[1])
    assert before == (_jsonable(current), value.to_dict())
    assert value.bindings is bindings and value.inventory is inventory and inventory.conditions is conditions
    assert all(old is new for old, new in zip(nodes, walk_nodes(current.root), strict=True))
    assert all(old is new for old, new in zip(children, (n.children for n in nodes if type(n) is RuleGroup), strict=True))
    assert all(old is new for old, new in zip(evidence, (n.evidence_refs for n in nodes if type(n) is not RuleGroup), strict=True))


def test_complete_unmapped_error_is_deterministic_across_100_calls_and_binding_orders():
    current = tree()
    value = coverage(current, ("COND_Z", "COND_A"), (("COND_Z", "Z"), ("COND_A", "A")))
    messages = []
    for index in range(100):
        provided = value if index % 2 == 0 else replace(value, bindings=tuple(reversed(value.bindings)))
        with pytest.raises(PolicyDataError) as caught:
            domain._analyze_coverage_structure(provided, current)
        messages.append(str(caught.value))
    assert set(messages) == {'COVERAGE_UNMAPPED_RULE: {"first_unmapped_rule_id":"B","unmapped_count":2}'}


def test_generated_model_invariants_are_trusted_without_reconstructing_inputs(monkeypatch):
    current = policy(atomic())
    value = coverage(current, ("COND",), (("COND", "Z"),))
    for model in (EligibilityCoverage, ConditionInventory, ConditionBinding, RequiredCondition, Policy, PolicyRule):
        monkeypatch.setattr(model, "__post_init__", forbid)
    assert domain._analyze_coverage_structure(value, current)[0::2] == ((), ())


def test_function_dependencies_stay_within_mapping_analysis_without_future_module_lock():
    source = ast.parse(inspect.getsource(domain._analyze_coverage_structure))
    called = {node.func.id for node in ast.walk(source) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert called <= {"type", "PolicyDataError", "tuple", "sorted", "len", "_resolve_rule_root",
                      "_validate_binding_ownership_no_overlap", "_find_unmapped_rule_ids"}
    attribute_calls = {(node.func.value.id, node.func.attr) for node in ast.walk(source)
                       if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                       and isinstance(node.func.value, ast.Name)}
    assert attribute_calls == {("json", "dumps")}
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Try)) for node in ast.walk(source))
    names = {node.id for node in ast.walk(source) if isinstance(node, ast.Name)}
    assert not names & {"CoverageResult", "CoverageStructureAnalysis", "ReviewContext", "UserProfile", "EvaluationFacts",
                        "PolicyEvaluation", "Status", "datetime", "date", "os", "pathlib"}
    attributes = {node.attr for node in ast.walk(source) if isinstance(node, ast.Attribute)}
    assert not attributes & {"scope", "rule_version", "requirement", "completeness_review_ref", "implementation_review_ref"}


def test_api_is_private_exactly_two_required_inputs_and_three_tuple_parts():
    from backend.policy_engine import policy_data
    signature = inspect.signature(domain._analyze_coverage_structure)
    assert tuple(signature.parameters) == ("coverage", "policy")
    assert all(p.default is inspect.Parameter.empty for p in signature.parameters.values())
    assert signature.parameters["coverage"].annotation is EligibilityCoverage
    assert signature.parameters["policy"].annotation is Policy
    assert signature.return_annotation == tuple[tuple[str, ...], tuple[tuple[ConditionBinding, RuleNode], ...], tuple[str, ...]]
    assert "_analyze_coverage_structure" not in policy_data.__all__
    assert not hasattr(policy_data, "_analyze_coverage_structure")
