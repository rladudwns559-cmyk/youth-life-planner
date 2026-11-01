"""합성 tree의 unowned ANY/NOT 사실 분석. 오류 승격·최종 상태는 검사하지 않는다."""

import ast
from dataclasses import replace
from datetime import date
import inspect
from itertools import permutations

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import (
    Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, RuleNode, _jsonable, walk_nodes,
)
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, EligibilityCoverage, RequiredCondition,
)
from backend.policy_engine.policy_data import coverage_composition as domain
from backend.policy_engine.policy_data.coverage_structure import _analyze_coverage_structure
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule


def atomic(rule_id="A"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))


def resident(rule_id="B"):
    return ResidentRegistrationRule(rule_id, RegionRef("SEOUL", "JONGNO"), ReferenceDateSource.APPLICATION_DATE,
                                    ("SYNTH-SRC#resident",))


def birth(rule_id="C"):
    return BirthDateRule(rule_id, date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#birth",))


def group(rule_id, children, operator=GroupOperator.ALL):
    return RuleGroup(rule_id, operator, children)


def policy(root):
    return Policy("SYNTH-POLICY", "합성 정책", "r0001", root)


def tree():
    first = group("ANY_Z", (atomic("L_Z"), resident("L_A")), GroupOperator.ANY)
    last = group("ANY_Y", (atomic("L_C"), group("NOT_B", (resident("L_D"),), GroupOperator.NOT)), GroupOperator.ANY)
    middle = group("G_ALL", (group("NOT_A", (birth("L_B"),), GroupOperator.NOT), last))
    return policy(group("ROOT_ALL", (first, middle)))


def prepared(current, declarations=(), pending=True):
    bindings = tuple(ConditionBinding(cid, rid, "SYNTH-REVIEW-" + cid) for cid, rid in declarations)
    ids = tuple(binding.condition_id for binding in bindings) + (("COND_PENDING",) if pending else ())
    conditions = tuple(RequiredCondition(cid, "합성 조건", ConditionRequirement.REQUIRED, ("SYNTH-SRC#a",)) for cid in ids)
    inventory = ConditionInventory(current.policy_id, ApplicabilityScope("2026", 3), "i0001", conditions)
    coverage = EligibilityCoverage(inventory, bindings)
    # 선행 structure 성공으로 같은 현재 Policy의 원본 roots·비겹침 전제를 준비한다.
    return coverage, _analyze_coverage_structure(coverage, current)[1]


def entries(current, root_ids=()):
    return prepared(current, tuple((f"COND_{index}", rid) for index, rid in enumerate(root_ids)))[1]


@pytest.mark.parametrize("factory", [atomic, resident, birth])
@pytest.mark.parametrize("owned", [False, True])
def test_three_leaf_types_never_produce_composition_gaps(factory, owned):
    current = policy(factory("SELF"))
    assert domain._find_composition_gap_group_ids(current, entries(current, ("SELF",) if owned else ())) == ()


@pytest.mark.parametrize("operator", list(GroupOperator))
@pytest.mark.parametrize("mode", ["zero", "children", "root"])
def test_owned_and_unowned_group_operator_matrix(operator, mode):
    children = (atomic("LEAF_A"),) if operator is GroupOperator.NOT else (atomic("LEAF_A"), birth("LEAF_B"))
    current = policy(group("GROUP", children, operator))
    roots = () if mode == "zero" else (("GROUP",) if mode == "root" else tuple(child.rule_id for child in children))
    result = domain._find_composition_gap_group_ids(current, entries(current, roots))
    expected = ("GROUP",) if mode != "root" and operator is not GroupOperator.ALL else ()
    assert type(result) is tuple and result == expected


@pytest.mark.parametrize("nested", [False, True])
def test_unowned_top_and_nested_all_groups_are_allowed_with_leaf_bindings(nested):
    children = (atomic("L1"), group("INNER_ALL", (resident("L2"), birth("L3")))) if nested else (resident("L1"), birth("L2"))
    current = policy(group("ROOT_ALL", children))
    leaf_ids = tuple(node.rule_id for node in walk_nodes(current.root) if type(node) is not RuleGroup)
    assert domain._find_composition_gap_group_ids(current, entries(current, leaf_ids)) == ()
    assert domain._find_composition_gap_group_ids(current, ()) == ()


@pytest.mark.parametrize("roots,expected", [
    ((), ("ANY_Z", "NOT_A", "ANY_Y", "NOT_B")),
    (("ANY_Z",), ("NOT_A", "ANY_Y", "NOT_B")),
    (("NOT_A",), ("ANY_Z", "ANY_Y", "NOT_B")),
    (("ANY_Y",), ("ANY_Z", "NOT_A")),
    (("NOT_B",), ("ANY_Z", "NOT_A", "ANY_Y")),
    (("G_ALL",), ("ANY_Z",)),
    (("ROOT_ALL",), ()),
    (("L_Z", "L_A"), ("ANY_Z", "NOT_A", "ANY_Y", "NOT_B")),
    (("ANY_Z", "NOT_A", "ANY_Y"), ()),
    (("ANY_Z", "NOT_A", "NOT_B"), ("ANY_Y",)),
])
def test_mixed_groups_all_gaps_and_parent_ownership(roots, expected):
    current = tree()
    assert domain._find_composition_gap_group_ids(current, entries(current, roots)) == expected


@pytest.mark.parametrize("parent_operator", list(GroupOperator))
def test_parent_owns_nested_any_and_not_without_separate_group_bindings(parent_operator):
    inner = group("INNER_ANY", (atomic("L1"), group("INNER_NOT", (birth("L2"),), GroupOperator.NOT)), GroupOperator.ANY)
    parent = group("PARENT", (inner,), parent_operator)
    current = policy(group("ROOT_ALL", (parent,)))
    assert domain._find_composition_gap_group_ids(current, entries(current, ("PARENT",))) == ()


@pytest.mark.parametrize("root_ids", [("A",), ("A", "B")])
def test_any_remains_gap_when_some_or_all_children_are_individually_owned(root_ids):
    current = policy(group("ANY", (atomic("A"), birth("B")), GroupOperator.ANY))
    assert domain._find_composition_gap_group_ids(current, entries(current, root_ids)) == ("ANY",)


def test_mapping_complete_any_split_returns_gap_fact_without_promoting_error():
    current = policy(group("ANY", (atomic("A"), birth("B")), GroupOperator.ANY))
    value, resolved = prepared(current, (("COND_A", "A"), ("COND_B", "B")), pending=False)
    missing, _, unmapped = _analyze_coverage_structure(value, current)
    assert missing == unmapped == ()
    assert domain._find_composition_gap_group_ids(current, resolved) == ("ANY",)


def test_mapping_complete_not_child_binding_still_returns_not_gap():
    current = policy(group("NOT", (atomic("A"),), GroupOperator.NOT))
    _, resolved = prepared(current, (("COND", "A"),), pending=False)
    assert domain._find_composition_gap_group_ids(current, resolved) == ("NOT",)


@pytest.mark.parametrize("depth", [5, 12, 30])
def test_deep_nested_gaps_include_ancestors_and_descendants_in_preorder(depth):
    root = atomic("LEAF")
    for index in range(depth):
        root = group(f"NOT_{index}", (root,), GroupOperator.NOT)
    current = policy(root)
    expected = tuple(f"NOT_{index}" for index in reversed(range(depth)))
    assert domain._find_composition_gap_group_ids(current, entries(current, ("LEAF",))) == expected


@pytest.mark.parametrize("ids", [("ANY_Z", "NOT_A"), (" 한글 ", "é"), ("é", "e\u0301"), ('quote"', "line\nID")])
def test_gap_ids_preserve_original_text_and_tree_order(ids):
    current = policy(group("ROOT", (group(ids[0], (atomic("A"),), GroupOperator.ANY),
                                    group(ids[1], (birth("B"),), GroupOperator.NOT))))
    assert domain._find_composition_gap_group_ids(current, entries(current, ("A", "B"))) == ids


def test_policy_child_order_changes_gap_order_without_ascii_sort():
    any_group = group("Z_ANY", (atomic(),), GroupOperator.ANY)
    not_group = group("A_NOT", (birth(),), GroupOperator.NOT)
    first = policy(group("ROOT", (any_group, not_group)))
    second = policy(group("ROOT", (not_group, any_group)))
    assert domain._find_composition_gap_group_ids(first, ()) == ("Z_ANY", "A_NOT")
    assert domain._find_composition_gap_group_ids(second, ()) == ("A_NOT", "Z_ANY")


def test_binding_permutations_do_not_change_gap_tuple():
    current = tree()
    resolved = entries(current, ("ANY_Z", "L_B", "NOT_B"))
    for permutation in permutations(resolved):
        assert domain._find_composition_gap_group_ids(current, permutation) == ("NOT_A", "ANY_Y")


class PolicySubclass(Policy):
    pass


class BindingSubclass(ConditionBinding):
    pass


class AtomicSubclass(PolicyRule):
    pass


class ResidentSubclass(ResidentRegistrationRule):
    pass


class BirthSubclass(BirthDateRule):
    pass


class GroupSubclass(RuleGroup):
    pass


class TupleSubclass(tuple):
    pass


class FakePolicy:
    @property
    def root(self):
        pytest.fail("정확한 Policy 검사 전에 root를 읽었습니다")


class FakeRoot:
    @property
    def rule_id(self):
        pytest.fail("정확한 root 검사 전에 ID를 읽었습니다")


def forbidden(*args, **kwargs):
    pytest.fail("입력 검사 전에 계산하거나 책임 밖 함수를 호출했습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "policy", 1, True, FakePolicy(), atomic(), resident(), birth(),
                                 group("GROUP", (atomic(),)), PolicySubclass("SYNTH-POLICY", "합성", "r0001", atomic())])
def test_exact_policy_is_checked_before_other_inputs_or_traversal(bad, monkeypatch):
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: policy:"):
        domain._find_composition_gap_group_ids(bad, None)


@pytest.mark.parametrize("bad", [None, [], {}, set(), "pairs", 1, True, TupleSubclass(), iter(())])
def test_resolved_bindings_requires_exact_tuple(bad, monkeypatch):
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: resolved_bindings:"):
        domain._find_composition_gap_group_ids(tree(), bad)


@pytest.mark.parametrize("bad", [None, [], {}, (), (None,), (None, None, None), TupleSubclass((None, None))])
def test_entries_require_exact_length_two_tuple(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: entry:"):
        domain._find_composition_gap_group_ids(tree(), (bad,))


@pytest.mark.parametrize("bad", [None, {}, "COND", FakeRoot(), BindingSubclass("COND", "A", "REVIEW")])
def test_binding_requires_exact_type(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: binding:"):
        domain._find_composition_gap_group_ids(tree(), ((bad, atomic()),))


@pytest.mark.parametrize("bad", [None, {}, (), "A", FakeRoot(),
    AtomicSubclass("A", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",)),
    ResidentSubclass("A", RegionRef("SEOUL", "JONGNO"), ReferenceDateSource.APPLICATION_DATE, ("SYNTH-SRC#a",)),
    BirthSubclass("A", date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#a",)),
    GroupSubclass("A", GroupOperator.ALL, (atomic("L"),)),
])
def test_root_requires_exact_supported_node_before_id_access(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: root:"):
        domain._find_composition_gap_group_ids(tree(), ((ConditionBinding("COND", "A", "REVIEW"), bad),))


@pytest.mark.parametrize("declared", ["a", " A", "A ", "RENAMED"])
def test_binding_root_id_connection_is_exact_and_never_remapped(declared):
    current = policy(atomic("A"))
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: rule_root_id:"):
        domain._find_composition_gap_group_ids(current, ((ConditionBinding("COND", declared, "REVIEW"), current.root),))


@pytest.mark.parametrize("same_object", [False, True])
def test_duplicate_condition_rejected_as_explicit_spec_requires(same_object):
    current = policy(group("ROOT", (atomic("A"), birth("B"))))
    first = ConditionBinding("COND", "A", "REVIEW")
    second = first if same_object else replace(first, rule_root_id="B")
    roots = current.root.children
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: condition_id:"):
        domain._find_composition_gap_group_ids(current, ((first, roots[0]), (second, roots[0] if same_object else roots[1])))


def test_all_pair_types_then_duplicate_then_links_precede_traversal_and_ownership(monkeypatch):
    current = policy(atomic())
    pair = (ConditionBinding("COND", "WRONG", "REVIEW"), current.root)
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    for resolved, field in [((pair, pair, []), "entry"), ((pair, pair), "condition_id"), ((pair,), "rule_root_id")]:
        with pytest.raises(PolicyDataError, match=f"^INVALID_STRUCTURE_INPUT: {field}:"):
            domain._find_composition_gap_group_ids(current, resolved)


def test_walk_once_exhausted_before_canonical_ownership_once_per_entry(monkeypatch):
    current = tree()
    _, prepared_pairs = prepared(current, (("COND_Z", "NOT_B"), ("COND_A", "ANY_Z"), ("COND_B", "L_B")))
    supplied = tuple(reversed(prepared_pairs))
    original_owned = domain._collect_owned_rule_ids
    events, visited, roots = [], [], []
    def observe_walk(root):
        events.append("walk")
        roots.append(root)
        for node in walk_nodes(root):
            visited.append(node)
            yield node
        events.append("walk_done")
    def observe_owned(root):
        events.append(root.rule_id)
        assert any(root is original for _, original in supplied)
        return original_owned(root)
    monkeypatch.setattr(domain, "walk_nodes", observe_walk)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", observe_owned)
    assert domain._find_composition_gap_group_ids(current, supplied) == ("NOT_A", "ANY_Y")
    assert events == ["walk", "walk_done", "ANY_Z", "L_B", "NOT_B"]
    assert len(roots) == 1 and roots[0] is current.root
    assert tuple(visited) == tuple(walk_nodes(current.root))


def test_zero_bindings_still_walks_tree_without_collecting_ownership(monkeypatch):
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    assert domain._find_composition_gap_group_ids(tree(), ()) == ("ANY_Z", "NOT_A", "ANY_Y", "NOT_B")


def test_policy_traversal_error_propagates_before_any_ownership(monkeypatch):
    current = tree()
    resolved = entries(current, ("ROOT_ALL",))
    error = PolicyDataError("SYNTHETIC_TRAVERSAL_ERROR")
    def fail(root):
        raise error
    monkeypatch.setattr(domain, "walk_nodes", fail)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    with pytest.raises(PolicyDataError) as caught:
        domain._find_composition_gap_group_ids(current, resolved)
    assert caught.value is error


def test_ownership_collector_error_is_propagated_without_wrapping(monkeypatch):
    current = tree()
    resolved = entries(current, ("ANY_Z",))
    error = PolicyDataError("SYNTHETIC_OWNERSHIP_ERROR")
    def fail(root):
        raise error
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", fail)
    with pytest.raises(PolicyDataError) as caught:
        domain._find_composition_gap_group_ids(current, resolved)
    assert caught.value is error


@pytest.mark.parametrize("factory", [
    lambda: group("DUP", (atomic("DUP"),)),
    lambda: group("ROOT", (group("DUP", (atomic("L"),)), birth("DUP"))),
    lambda: group("ROOT", (atomic("DUP"), resident("DUP"))),
    lambda: group("EMPTY", ()),
    lambda: group("UNSUPPORTED", (FakeRoot(),)),
    lambda: policy(FakeRoot()),
    lambda: group("RAW", (atomic(),), "ANY"),
    lambda: group("FUTURE", (atomic(),), "XOR"),
])
def test_normal_constructors_reject_invalid_tree_or_operator_without_object_hacking(factory):
    with pytest.raises(PolicyDataError):
        factory()


def test_current_resident_birth_shape_is_synthetic_and_has_no_composition_gap():
    current = policy(group("SYNTH_ROOT", (resident("SYNTH_RESIDENT"), birth("SYNTH_BIRTH"))))
    _, resolved = prepared(current, (("COND_RESIDENT", "SYNTH_RESIDENT"), ("COND_BIRTH", "SYNTH_BIRTH")), pending=False)
    assert domain._find_composition_gap_group_ids(current, resolved) == ()


@pytest.mark.parametrize("split", [False, True])
def test_duration_any_shape_owned_whole_or_split_into_two_conditions(split):
    # AGE leaf는 합성 tree 경계만 검증한다. 실제 거주기간 의미/산식/Rule은 구현하지 않는다.
    duration = group("DURATION_ANY", (atomic("RULE_3Y"), atomic("RULE_10Y")), GroupOperator.ANY)
    current = policy(group("ROOT", (resident("RESIDENT"), birth("BIRTH"), duration)))
    duration_bindings = (("COND_3Y", "RULE_3Y"), ("COND_10Y", "RULE_10Y")) if split else (("COND_DURATION", "DURATION_ANY"),)
    declarations = (("COND_RESIDENT", "RESIDENT"), ("COND_BIRTH", "BIRTH")) + duration_bindings
    _, resolved = prepared(current, declarations, pending=False)
    assert domain._find_composition_gap_group_ids(current, resolved) == (("DURATION_ANY",) if split else ())


def test_not_sibling_shape_only_reports_unowned_negation():
    current = policy(group("ROOT", (atomic("A"), group("NOT_X", (birth("B"),), GroupOperator.NOT))))
    assert domain._find_composition_gap_group_ids(current, entries(current, ("A", "B"))) == ("NOT_X",)


def test_100_repetitions_preserve_all_original_values_and_identities():
    current = tree()
    value, resolved = prepared(current, (("COND_Z", "NOT_B"), ("COND_A", "ANY_Z"), ("COND_B", "L_B")))
    before = (_jsonable(current), value.to_dict(), tuple((binding.to_dict(), _jsonable(root)) for binding, root in resolved))
    original_pairs = tuple(resolved)
    nodes = tuple(walk_nodes(current.root))
    children = tuple(node.children for node in nodes if type(node) is RuleGroup)
    evidence = tuple(node.evidence_refs for node in nodes if type(node) is not RuleGroup)
    for index in range(100):
        supplied = resolved if index % 2 == 0 else tuple(reversed(resolved))
        result = domain._find_composition_gap_group_ids(current, supplied)
        assert type(result) is tuple and result == ("NOT_A", "ANY_Y")
    after = (_jsonable(current), value.to_dict(), tuple((binding.to_dict(), _jsonable(root)) for binding, root in resolved))
    assert before == after and all(a is b for a, b in zip(original_pairs, resolved, strict=True))
    assert all(a is b for a, b in zip(nodes, walk_nodes(current.root), strict=True))
    assert all(a is b for a, b in zip(children, (n.children for n in nodes if type(n) is RuleGroup), strict=True))
    assert all(a is b for a, b in zip(evidence, (n.evidence_refs for n in nodes if type(n) is not RuleGroup), strict=True))


def test_function_dependencies_are_analysis_only_without_future_module_lock():
    source = ast.parse(inspect.getsource(domain._find_composition_gap_group_ids))
    called = {node.func.id for node in ast.walk(source) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert called <= {"type", "PolicyDataError", "tuple", "set", "len", "sorted", "walk_nodes", "_collect_owned_rule_ids"}
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Try)) for node in ast.walk(source))
    names = {node.id for node in ast.walk(source) if isinstance(node, ast.Name)}
    assert not names & {"ConditionInventory", "EligibilityCoverage", "CoverageReviewContext", "CoverageResult",
                        "UserProfile", "EvaluationFacts", "Status", "datetime", "os", "pathlib", "json"}
    string_constants = {node.value for node in ast.walk(source) if isinstance(node, ast.Constant) and type(node.value) is str}
    assert not any(value.startswith("COVERAGE_COMPOSITION_GAP") for value in string_constants)


def test_api_is_exactly_two_required_inputs_and_is_not_publicly_exported():
    from backend.policy_engine import policy_data
    signature = inspect.signature(domain._find_composition_gap_group_ids)
    assert tuple(signature.parameters) == ("policy", "resolved_bindings")
    assert all(p.default is inspect.Parameter.empty for p in signature.parameters.values())
    assert signature.parameters["policy"].annotation is Policy
    assert signature.parameters["resolved_bindings"].annotation == tuple[tuple[ConditionBinding, RuleNode], ...]
    assert signature.return_annotation == tuple[str, ...]
    assert "_find_composition_gap_group_ids" not in policy_data.__all__
    assert not hasattr(policy_data, "_find_composition_gap_group_ids")
