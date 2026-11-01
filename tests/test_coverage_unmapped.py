"""합성 Policy의 leaf target/미매핑 사실 분석. 완결성이나 오류 승격은 다루지 않는다."""

import ast
from dataclasses import replace
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
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, EligibilityCoverage, RequiredCondition,
)
from backend.policy_engine.policy_data import coverage_unmapped as domain
from backend.policy_engine.policy_data.coverage_ownership import _validate_binding_ownership_no_overlap
from backend.policy_engine.policy_data.rule_root_resolution import _resolve_rule_root
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
    deep = group("G_ANY", (resident(), group("G_NOT", (birth(),), GroupOperator.NOT)), GroupOperator.ANY)
    return policy(group("ROOT", (atomic(), group("G_NEST", (deep, atomic("C"))), resident("D"))))


def prepared(current, declarations, extra_conditions=()):
    bindings = tuple(ConditionBinding(condition, root, "SYNTH-REVIEW-" + condition) for condition, root in declarations)
    ids = tuple(binding.condition_id for binding in bindings) + extra_conditions
    # 빈 Binding도 정상적인 비어 있지 않은 Inventory에서 준비한다.
    ids = ids or ("COND_PLANNED",)
    conditions = tuple(RequiredCondition(condition, "합성 조건", ConditionRequirement.REQUIRED, ("SYNTH-SRC#a",))
                       for condition in ids)
    inventory = ConditionInventory(current.policy_id, ApplicabilityScope("2026", 3), "i0001", conditions)
    coverage = EligibilityCoverage(inventory, bindings)
    resolved = tuple((binding, _resolve_rule_root(current, binding.rule_root_id)) for binding in coverage.bindings)
    _validate_binding_ownership_no_overlap(resolved)
    return coverage, resolved


def entries(current, declarations):
    return prepared(current, declarations)[1]


@pytest.mark.parametrize("factory", [atomic, resident, birth])
def test_each_leaf_policy_root_is_single_target_and_can_be_owned(factory):
    current = policy(factory("SELF"))
    assert domain._collect_policy_coverage_target_rule_ids(current) == ("SELF",)
    assert domain._find_unmapped_rule_ids(current, ()) == ("SELF",)
    assert domain._find_unmapped_rule_ids(current, entries(current, (("COND", "SELF"),))) == ()


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_groups_are_not_targets_but_keep_traversing_children(operator):
    children = (atomic(),) if operator is GroupOperator.NOT else (atomic(), resident(), birth())
    current = policy(group("GROUP", children, operator))
    assert domain._collect_policy_coverage_target_rule_ids(current) == tuple(child.rule_id for child in children)
    assert domain._find_unmapped_rule_ids(current, ()) == tuple(child.rule_id for child in children)


def test_preorder_excludes_all_middle_groups_and_retains_leaf_order():
    assert domain._collect_policy_coverage_target_rule_ids(tree()) == ("Z", "A", "B", "C", "D")


@pytest.mark.parametrize("depth", [5, 12, 30])
def test_deep_nested_tree_reaches_leaf(depth):
    root = birth("LEAF")
    for index in range(depth):
        root = group(f"G_{index}", (root,), GroupOperator.NOT)
    current = policy(root)
    assert domain._collect_policy_coverage_target_rule_ids(current) == ("LEAF",)
    assert domain._find_unmapped_rule_ids(current, ()) == ("LEAF",)


@pytest.mark.parametrize("ids", [
    ("Z", " A ", "a"), ("한글", "é", "e\u0301"), ('quote"', "line\nID", "tab\tID"),
])
def test_original_free_ids_are_not_sorted_or_normalized(ids):
    current = policy(group("GROUP", tuple(atomic(rule_id) for rule_id in ids)))
    assert domain._collect_policy_coverage_target_rule_ids(current) == ids
    assert domain._find_unmapped_rule_ids(current, entries(current, (("COND", ids[-1]),))) == ids[:-1]


class PolicySubclass(Policy):
    pass


class AtomicSubclass(PolicyRule):
    pass


class ResidentSubclass(ResidentRegistrationRule):
    pass


class BirthSubclass(BirthDateRule):
    pass


class GroupSubclass(RuleGroup):
    pass


class BindingSubclass(ConditionBinding):
    pass


class TupleSubclass(tuple):
    pass


class FakePolicy:
    @property
    def root(self):
        pytest.fail("정확한 Policy 확인 전에 root에 접근했습니다")


class FakeRoot:
    @property
    def rule_id(self):
        pytest.fail("정확한 node 확인 전에 ID에 접근했습니다")


BAD_POLICIES = [None, {}, [], (), "POLICY", 1, True, atomic(), resident(), birth(),
                group("GROUP", (atomic(),)), FakePolicy(), PolicySubclass("SYNTH-POLICY", "합성", "r0001", atomic())]


@pytest.mark.parametrize("bad", BAD_POLICIES)
@pytest.mark.parametrize("helper", [domain._collect_policy_coverage_target_rule_ids, domain._find_unmapped_rule_ids])
def test_exact_policy_checked_before_tree_or_other_inputs(bad, helper, monkeypatch):
    def forbidden(*args):
        pytest.fail("Policy 입력 검사 전에 계산했습니다")
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: policy:"):
        helper(bad) if helper is domain._collect_policy_coverage_target_rule_ids else helper(bad, None)


def test_target_collector_calls_existing_walk_once_and_consumes_entire_tree(monkeypatch):
    current = tree()
    calls, visited, exhausted = [], [], []
    def observe(root):
        calls.append(root)
        for node in walk_nodes(root):
            visited.append(node)
            yield node
        exhausted.append(True)
    monkeypatch.setattr(domain, "walk_nodes", observe)
    assert domain._collect_policy_coverage_target_rule_ids(current) == ("Z", "A", "B", "C", "D")
    assert len(calls) == 1 and calls[0] is current.root
    assert tuple(visited) == tuple(walk_nodes(current.root)) and exhausted == [True]


@pytest.mark.parametrize("root_ids,expected", [
    ((), ("Z", "A", "B", "C", "D")),
    (("Z",), ("A", "B", "C", "D")),
    (("B",), ("Z", "A", "C", "D")),
    (("G_ANY",), ("Z", "C", "D")),
    (("G_NEST",), ("Z", "D")),
    (("ROOT",), ()),
    (("Z", "G_NEST", "D"), ()),
    (("Z", "A", "B", "C", "D"), ()),
    (("G_NOT", "Z"), ("A", "C", "D")),
])
def test_zero_single_many_leaf_and_group_roots_return_facts_only(root_ids, expected):
    current = tree()
    resolved = entries(current, tuple((f"COND_{index}", root_id) for index, root_id in enumerate(root_ids)))
    result = domain._find_unmapped_rule_ids(current, resolved)
    assert type(result) is tuple and result == expected
    assert all(type(rule_id) is str for rule_id in result)


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_unowned_composition_group_is_not_unmapped_when_leaves_owned(operator):
    children = (atomic(),) if operator is GroupOperator.NOT else (atomic(), resident())
    current = policy(group("TOP", (group("INNER", children, operator),)))
    resolved = entries(current, tuple((f"COND_{index}", child.rule_id) for index, child in enumerate(children)))
    assert domain._find_unmapped_rule_ids(current, resolved) == ()


@pytest.mark.parametrize("count", [1, 2, 4])
def test_extra_deep_leaves_are_returned_in_preorder_without_error_promotion(count):
    extra_ids = tuple(f"EXTRA_{index}" for index in reversed(range(count)))
    current = policy(group("ROOT", (atomic("BOUND"), group("DEEP", tuple(birth(rid) for rid in extra_ids)))))
    resolved = entries(current, (("COND_BOUND", "BOUND"),))
    assert domain._find_unmapped_rule_ids(current, resolved) == extra_ids


def test_binding_permutations_do_not_change_unmapped_order():
    current = tree()
    resolved = entries(current, (("COND_Z", "Z"), ("COND_A", "B"), ("COND_C", "D")))
    for permutation in permutations(resolved):
        assert domain._find_unmapped_rule_ids(current, permutation) == ("A", "C")


def test_policy_child_order_changes_output_order_only():
    first = policy(group("ROOT", (atomic("Z"), resident("A"), birth("B"))))
    second = policy(group("ROOT", (birth("B"), resident("A"), atomic("Z"))))
    assert domain._find_unmapped_rule_ids(first, entries(first, (("COND", "A"),))) == ("Z", "B")
    assert domain._find_unmapped_rule_ids(second, entries(second, (("COND", "A"),))) == ("B", "Z")


@pytest.mark.parametrize("bad", [None, [], {}, set(), "pairs", 1, True, TupleSubclass(), iter(())])
def test_resolved_bindings_must_be_exact_tuple(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: resolved_bindings:"):
        domain._find_unmapped_rule_ids(tree(), bad)


@pytest.mark.parametrize("bad", [None, [], {}, (), (None,), (None, None, None), TupleSubclass((None, None))])
def test_entries_must_be_exact_pairs(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: entry:"):
        domain._find_unmapped_rule_ids(tree(), (bad,))


@pytest.mark.parametrize("bad", [None, {}, "COND", FakeRoot(), BindingSubclass("COND", "Z", "REVIEW")])
def test_binding_must_be_exact_model(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: binding:"):
        domain._find_unmapped_rule_ids(tree(), ((bad, atomic()),))


BAD_ROOTS = [None, {}, "Z", FakeRoot(),
             AtomicSubclass("Z", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",)),
             ResidentSubclass("Z", RegionRef("SEOUL", "JONGNO"), ReferenceDateSource.APPLICATION_DATE, ("SYNTH-SRC#a",)),
             BirthSubclass("Z", date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#a",)),
             GroupSubclass("Z", GroupOperator.ALL, (atomic("CHILD"),))]


@pytest.mark.parametrize("bad", BAD_ROOTS)
def test_resolved_root_must_be_exact_supported_node_before_id_access(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: root:"):
        domain._find_unmapped_rule_ids(tree(), ((ConditionBinding("COND", "Z", "REVIEW"), bad),))


@pytest.mark.parametrize("root_id", ["z", "Z ", " Z", "OLD_ID"])
def test_binding_and_supplied_root_ids_must_match_exactly(root_id):
    current = tree()
    root = _resolve_rule_root(current, "Z")
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: rule_root_id:"):
        domain._find_unmapped_rule_ids(current, ((ConditionBinding("COND", root_id, "REVIEW"), root),))


@pytest.mark.parametrize("same_object", [True, False])
def test_duplicate_condition_is_local_input_error_as_spec_requires(same_object):
    current = tree()
    binding = ConditionBinding("COND", "Z", "REVIEW")
    root = _resolve_rule_root(current, "Z")
    other = binding if same_object else replace(binding, rule_root_id="A")
    other_root = root if same_object else _resolve_rule_root(current, "A")
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: condition_id:"):
        domain._find_unmapped_rule_ids(current, ((binding, root), (other, other_root)))


def test_all_pair_types_then_duplicates_then_links_before_computation(monkeypatch):
    current = tree()
    pair = (ConditionBinding("COND", "WRONG", "REVIEW"), _resolve_rule_root(current, "Z"))
    def forbidden(*args):
        pytest.fail("입력 검사를 마치기 전에 계산했습니다")
    monkeypatch.setattr(domain, "_collect_policy_coverage_target_rule_ids", forbidden)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    for resolved, field in [((pair, pair, []), "entry"), ((pair, pair), "condition_id"), ((pair,), "rule_root_id")]:
        with pytest.raises(PolicyDataError, match=f"^INVALID_STRUCTURE_INPUT: {field}:"):
            domain._find_unmapped_rule_ids(current, resolved)


def test_targets_once_then_existing_ownership_once_per_entry_in_condition_order(monkeypatch):
    current = tree()
    resolved = entries(current, (("COND_Z", "D"), ("COND_A", "G_NEST"), ("COND_B", "Z")))
    original_targets = domain._collect_policy_coverage_target_rule_ids
    original_owned = domain._collect_owned_rule_ids
    calls = []
    def targets(provided):
        assert provided is current
        calls.append("targets")
        return original_targets(provided)
    def owned(root):
        calls.append(root.rule_id)
        assert any(root is provided_root for _, provided_root in resolved)
        return original_owned(root)
    monkeypatch.setattr(domain, "_collect_policy_coverage_target_rule_ids", targets)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", owned)
    assert domain._find_unmapped_rule_ids(current, resolved) == ()
    assert calls == ["targets", "G_NEST", "Z", "D"]


@pytest.mark.parametrize("dependency", ["_collect_policy_coverage_target_rule_ids", "_collect_owned_rule_ids"])
def test_existing_collector_errors_propagate_without_wrapping(dependency, monkeypatch):
    current = tree()
    resolved = entries(current, (("COND", "Z"),))
    error = PolicyDataError("SYNTHETIC_COLLECTOR_FAILURE")
    def fail(*args):
        raise error
    monkeypatch.setattr(domain, dependency, fail)
    with pytest.raises(PolicyDataError) as caught:
        domain._find_unmapped_rule_ids(current, resolved)
    assert caught.value is error


def test_zero_bindings_still_collects_targets_and_never_calls_ownership(monkeypatch):
    current = tree()
    def forbidden(*args):
        pytest.fail("빈 Binding에 ownership을 호출했습니다")
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    assert domain._find_unmapped_rule_ids(current, ()) == ("Z", "A", "B", "C", "D")


def test_current_group_child_addition_and_removal_use_current_ownership():
    for child_ids in [("L1",), ("L1", "L2"), ("L2",)]:
        current = policy(group("ROOT", (group("BOUND", tuple(atomic(rid) for rid in child_ids)), birth("EXTRA"))))
        assert domain._collect_policy_coverage_target_rule_ids(current) == child_ids + ("EXTRA",)
        assert domain._find_unmapped_rule_ids(current, entries(current, (("COND", "BOUND"),))) == ("EXTRA",)


def test_moved_leaf_uses_current_resolved_original_root():
    leaf = atomic("MOVED")
    first = policy(group("ROOT", (group("LEFT", (leaf, birth("X"))), resident("Y"))))
    second = policy(group("ROOT", (birth("X"), group("RIGHT", (resident("Y"), leaf)))))
    for current in (first, second):
        resolved = entries(current, (("COND", "MOVED"),))
        assert resolved[0][1] is leaf
        assert domain._find_unmapped_rule_ids(current, resolved) == ("X", "Y")


def test_renamed_root_is_rejected_by_preceding_resolver_not_finder():
    current = policy(atomic("NEW_ID"))
    with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
        prepared(current, (("COND", "OLD_ID"),))


def test_inventory_not_consulted_or_interpreted_by_finder():
    current = tree()
    coverage, resolved = prepared(current, (("COND", "Z"),), ("COND_NOT_BOUND",))
    before = coverage.to_dict()
    assert domain._find_unmapped_rule_ids(current, resolved) == ("A", "B", "C", "D")
    assert coverage.to_dict() == before


def test_100_calls_are_deterministic_and_keep_every_input_value_and_identity():
    current = tree()
    coverage, resolved = prepared(current, (("COND_Z", "D"), ("COND_A", "G_ANY")))
    before = (_jsonable(current), coverage.to_dict(), tuple((binding.to_dict(), _jsonable(root)) for binding, root in resolved))
    nodes = tuple(walk_nodes(current.root))
    children = tuple(node.children for node in nodes if type(node) is RuleGroup)
    for _ in range(100):
        assert domain._collect_policy_coverage_target_rule_ids(current) == ("Z", "A", "B", "C", "D")
        assert domain._find_unmapped_rule_ids(current, resolved) == ("Z", "C")
    after = (_jsonable(current), coverage.to_dict(), tuple((binding.to_dict(), _jsonable(root)) for binding, root in resolved))
    assert before == after
    assert all(old is new for old, new in zip(nodes, walk_nodes(current.root), strict=True))
    assert all(old is new for old, new in zip(children, (n.children for n in nodes if type(n) is RuleGroup), strict=True))
    assert all(binding is original for (binding, _), original in zip(resolved, coverage.bindings, strict=True))
    assert all(root is _resolve_rule_root(current, binding.rule_root_id) for binding, root in resolved)


@pytest.mark.parametrize("factory", [
    lambda: group("G", (atomic("DUP"), birth("DUP"))),
    lambda: group("DUP", (atomic("DUP"),)),
    lambda: group("ROOT", (group("DUP", (atomic("L"),)), resident("DUP"))),
    lambda: group("EMPTY", ()),
    lambda: policy(None),
    lambda: policy(FakeRoot()),
    lambda: group("G", (FakeRoot(),)),
])
def test_normal_constructors_block_invalid_trees_without_immutable_hacking(factory):
    with pytest.raises(PolicyDataError):
        factory()


@pytest.mark.parametrize("helper", [domain._collect_policy_coverage_target_rule_ids, domain._find_unmapped_rule_ids])
def test_private_function_dependencies_do_not_cross_analysis_boundary(helper):
    source = ast.parse(inspect.getsource(helper))
    forbidden = {"_resolve_rule_root", "_validate_binding_ownership_no_overlap", "_validate_no_unmapped_rules",
                 "open", "getattr", "setattr", "eval", "exec", "__import__", "print"}
    called = {node.func.id for node in ast.walk(source) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not called & forbidden
    allowed = {"type", "PolicyDataError", "tuple", "set", "len", "sorted", "walk_nodes",
               "_collect_policy_coverage_target_rule_ids", "_collect_owned_rule_ids"}
    assert called <= allowed
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Try)) for node in ast.walk(source))
    # 함수 범위만 검사해 같은 모듈의 미래 기능을 금지하지 않는다.
    referenced = {node.id for node in ast.walk(source) if isinstance(node, ast.Name)}
    assert not referenced & {"ConditionInventory", "CoverageResult", "UserProfile", "EvaluationFacts", "Status"}


def test_apis_have_only_required_inputs_and_are_not_package_public_exports():
    from backend.policy_engine import policy_data
    for helper, names in [(domain._collect_policy_coverage_target_rule_ids, ("policy",)),
                          (domain._find_unmapped_rule_ids, ("policy", "resolved_bindings"))]:
        signature = inspect.signature(helper)
        assert tuple(signature.parameters) == names
        assert all(p.default is inspect.Parameter.empty for p in signature.parameters.values())
        assert signature.return_annotation == tuple[str, ...]
        assert helper.__name__ not in policy_data.__all__
        assert not hasattr(policy_data, helper.__name__)
