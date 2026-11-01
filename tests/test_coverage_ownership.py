"""같은 합성 Policy에서 resolve한 원본 root의 소유 범위와 canonical overlap 계약."""

import ast
from dataclasses import replace
from datetime import date
import inspect
from itertools import permutations
import json

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, _jsonable
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, EligibilityCoverage, RequiredCondition,
)
from backend.policy_engine.policy_data import coverage_ownership as domain
from backend.policy_engine.policy_data.rule_root_resolution import _resolve_rule_root
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule


def atomic(rule_id="A1"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))


def resident(rule_id="A2"):
    return ResidentRegistrationRule(rule_id, RegionRef("SEOUL", "JONGNO"), ReferenceDateSource.APPLICATION_DATE,
                                    ("SYNTH-SRC#resident",))


def birth(rule_id="A3"):
    return BirthDateRule(rule_id, date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#birth",))


def group(rule_id, children, operator=GroupOperator.ALL):
    return RuleGroup(rule_id, operator, children)


def tree():
    negation = group("G_NOT", (birth(),), GroupOperator.NOT)
    deep = group("G_DEEP", (resident(), negation), GroupOperator.ANY)
    root = group("ROOT", (group("G_A", (atomic(), deep)), group("G_B", (atomic("B1"),), GroupOperator.ANY),
                          group("G_C", (resident("C1"),))))
    return Policy("SYNTH-POLICY", "합성 정책", "r0001", root)


def prepared(current, declarations, extra_conditions=()):
    bindings = tuple(ConditionBinding(condition, root, "SYNTH-REVIEW-" + condition) for condition, root in declarations)
    conditions = tuple(RequiredCondition(condition, "합성 조건", ConditionRequirement.REQUIRED, ("SYNTH-SRC#a",))
                       for condition in tuple(binding.condition_id for binding in bindings) + extra_conditions)
    inventory = ConditionInventory(current.policy_id, ApplicabilityScope("2026", 3), "i0001", conditions)
    coverage = EligibilityCoverage(inventory, bindings)
    resolved = tuple((binding, _resolve_rule_root(current, binding.rule_root_id)) for binding in coverage.bindings)
    return coverage, resolved


def entries(current, declarations):
    return prepared(current, declarations)[1]


def overlap_message(resolved):
    with pytest.raises(PolicyDataError) as caught:
        domain._validate_binding_ownership_no_overlap(resolved)
    prefix, payload = str(caught.value).split(": ", 1)
    assert prefix == "COVERAGE_OWNERSHIP_OVERLAP"
    return str(caught.value), json.loads(payload)


@pytest.mark.parametrize("factory,rule_id", [(atomic, "A1"), (resident, "A2"), (birth, "A3")])
def test_leaf_owns_exactly_its_own_id(factory, rule_id):
    result = domain._collect_owned_rule_ids(factory())
    assert type(result) is tuple and result == (rule_id,)


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_all_any_not_include_root_and_original_child_order(operator):
    children = (atomic("Z"),) if operator is GroupOperator.NOT else (atomic("Z"), birth("A"))
    root = group("GROUP", children, operator)
    assert domain._collect_owned_rule_ids(root) == (("GROUP", "Z") if operator is GroupOperator.NOT else ("GROUP", "Z", "A"))
    assert root.children is children


def test_complete_preorder_includes_middle_groups_and_every_leaf():
    current = tree()
    assert domain._collect_owned_rule_ids(current.root) == (
        "ROOT", "G_A", "A1", "G_DEEP", "A2", "G_NOT", "A3", "G_B", "B1", "G_C", "C1",
    )
    inner = _resolve_rule_root(current, "G_DEEP")
    assert domain._collect_owned_rule_ids(inner) == ("G_DEEP", "A2", "G_NOT", "A3")


@pytest.mark.parametrize("depth", [5, 12])
def test_deep_nested_groups_are_not_omitted(depth):
    root = atomic("LEAF")
    for index in range(depth):
        root = group(f"G_{index}", (root,), GroupOperator.NOT)
    expected = tuple(f"G_{index}" for index in reversed(range(depth))) + ("LEAF",)
    assert domain._collect_owned_rule_ids(root) == expected


def test_preorder_preserves_free_ids_and_never_sorts_or_normalizes():
    root = group("그룹", (atomic("Z"), resident(" A "), birth("a")))
    assert domain._collect_owned_rule_ids(root) == ("그룹", "Z", " A ", "a")


class AtomicSubclass(PolicyRule):
    pass


class BindingSubclass(ConditionBinding):
    pass


class TupleSubclass(tuple):
    pass


class FakeRoot:
    @property
    def rule_id(self):
        pytest.fail("미지원 root의 ID를 읽었습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "A", 1, True, FakeRoot(), AtomicSubclass(
    "SUBCLASS", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))])
def test_collector_requires_exact_supported_root_before_traversal(bad, monkeypatch):
    def forbidden(*args):
        pytest.fail("입력 검사 전에 순회했습니다")
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: root:"):
        domain._collect_owned_rule_ids(bad)


def test_collector_reuses_existing_walk_once_and_exhausts_it(monkeypatch):
    from backend.policy_engine.models import walk_nodes
    root = tree().root
    calls, visited, exhausted = [], [], []
    def observe(provided_root):
        calls.append(provided_root)
        for node in walk_nodes(provided_root):
            visited.append(node.rule_id)
            yield node
        exhausted.append(True)
    monkeypatch.setattr(domain, "walk_nodes", observe)
    result = domain._collect_owned_rule_ids(root)
    assert len(calls) == 1 and calls[0] is root and tuple(visited) == result and exhausted == [True]


@pytest.mark.parametrize("declarations", [
    (("COND_A", "ROOT"),), (("COND_A", "A1"),),
    (("COND_A", "A1"), ("COND_B", "A2")),
    (("COND_A", "G_A"), ("COND_B", "G_B")),
    (("COND_A", "G_A"), ("COND_B", "G_B"), ("COND_C", "G_C")),
    (("COND_A", "G_DEEP"), ("COND_B", "B1"), ("COND_C", "C1")),
])
def test_single_sibling_and_deep_disjoint_ownership_returns_none(declarations):
    assert domain._validate_binding_ownership_no_overlap(entries(tree(), declarations)) is None


def test_empty_input_returns_none_without_collection(monkeypatch):
    def forbidden(*args):
        pytest.fail("빈 입력에서 수집했습니다")
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    assert domain._validate_binding_ownership_no_overlap(()) is None


@pytest.mark.parametrize("root_a,root_b,shared", [
    ("A1", "A1", ("A1",)),
    ("G_A", "G_A", ("G_A", "A1", "G_DEEP", "A2", "G_NOT", "A3")),
    ("G_A", "A1", ("A1",)),
    ("G_A", "G_DEEP", ("G_DEEP", "A2", "G_NOT", "A3")),
    ("ROOT", "G_B", ("G_B", "B1")),
    ("ROOT", "A3", ("A3",)),
    ("G_NOT", "A3", ("A3",)),
    ("A1", "G_A", ("A1",)),
])
def test_same_root_parent_child_and_policy_root_have_exact_json_contract(root_a, root_b, shared):
    resolved = entries(tree(), (("COND_A", root_a), ("COND_B", root_b)))
    message, payload = overlap_message(resolved)
    expected = dict(condition_a="COND_A", rule_root_a=root_a, condition_b="COND_B", rule_root_b=root_b,
                    overlap_count=len(shared), first_overlap_rule_id=min(shared))
    assert payload == expected
    assert message == "COVERAGE_OWNERSHIP_OVERLAP: " + json.dumps(expected, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


@pytest.mark.parametrize("declarations,first_pair", [
    ((("COND_A", "G_A"), ("COND_B", "A1"), ("COND_C", "A3")), ("COND_A", "COND_B")),
    ((("COND_A", "G_A"), ("COND_B", "G_B"), ("COND_C", "G_DEEP")), ("COND_A", "COND_C")),
    ((("COND_A", "B1"), ("COND_B", "G_A"), ("COND_C", "A1")), ("COND_B", "COND_C")),
    ((("COND_A", "G_A"), ("COND_B", "G_A"), ("COND_C", "G_A")), ("COND_A", "COND_B")),
])
def test_every_input_permutation_has_same_first_canonical_conflict(declarations, first_pair):
    resolved = entries(tree(), declarations)
    messages = []
    for variant in permutations(resolved):
        message, payload = overlap_message(variant)
        messages.append(message)
        assert (payload["condition_a"], payload["condition_b"]) == first_pair
    assert len(set(messages)) == 1


def test_condition_order_is_ascii_lexical_not_numeric_or_parent_first():
    resolved = entries(tree(), (("COND_2", "G_A"), ("COND_10", "A1")))
    _, payload = overlap_message(resolved)
    assert payload == dict(condition_a="COND_10", rule_root_a="A1", condition_b="COND_2", rule_root_b="G_A",
                           overlap_count=1, first_overlap_rule_id="A1")


@pytest.mark.parametrize("ids", [("Z", "A"), ("한글", "é"), ("한글", " A ")])
def test_overlap_evidence_is_unicode_min_not_preorder_or_set_iteration(ids):
    root = group("ZZZ_ROOT", tuple(atomic(rule_id) for rule_id in ids))
    current = Policy("SYNTH-POLICY", "합성 정책", "r0001", root)
    resolved = entries(current, (("COND_A", root.rule_id), ("COND_B", root.rule_id)))
    _, payload = overlap_message(resolved)
    assert payload["first_overlap_rule_id"] == min((root.rule_id,) + ids)
    assert payload["overlap_count"] == 3


def test_json_keys_escaping_and_root_condition_mapping_are_exact():
    root_id = '한국어 "ROOT"\n'
    root = atomic(root_id)
    current = Policy("SYNTH-POLICY", "합성 정책", "r0001", root)
    message, payload = overlap_message(entries(current, (("COND_Z", root_id), ("COND_A", root_id))))
    assert list(payload) == ["condition_a", "condition_b", "first_overlap_rule_id", "overlap_count", "rule_root_a", "rule_root_b"]
    assert payload["condition_a"] == "COND_A" and payload["rule_root_a"] == root_id
    assert payload["condition_b"] == "COND_Z" and payload["rule_root_b"] == root_id
    assert payload["first_overlap_rule_id"] == root_id
    assert message.isascii() and "\\n" in message and '\\"' in message


def test_child_order_changes_tuple_but_not_overlap_message():
    first = group("ROOT", (atomic("Z"), atomic("A")))
    second = replace(first, children=tuple(reversed(first.children)))
    assert domain._collect_owned_rule_ids(first) == ("ROOT", "Z", "A")
    assert domain._collect_owned_rule_ids(second) == ("ROOT", "A", "Z")
    messages = []
    for root in (first, second):
        current = Policy("SYNTH-POLICY", "합성 정책", "r0001", root)
        messages.append(overlap_message(entries(current, (("COND_A", "ROOT"), ("COND_B", "ROOT"))))[0])
    assert messages[0] == messages[1]


@pytest.mark.parametrize("bad", [None, [], {}, "SYNTH", 1, True, TupleSubclass(())])
def test_validator_requires_exact_outer_tuple(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: resolved_bindings:"):
        domain._validate_binding_ownership_no_overlap(bad)


@pytest.mark.parametrize("shape", ["list", "empty", "one", "three", "subclass", "none"])
def test_validator_requires_exact_two_tuple_entries(shape):
    pair = entries(tree(), (("COND_A", "A1"),))[0]
    bad = {"list": list(pair), "empty": (), "one": pair[:1], "three": pair + ("EXTRA",),
           "subclass": TupleSubclass(pair), "none": None}[shape]
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: entry:"):
        domain._validate_binding_ownership_no_overlap((bad,))


@pytest.mark.parametrize("bad", [None, {}, [], "COND_A", 1, True,
                                  BindingSubclass("COND_A", "A1", "SYNTH-REVIEW")])
def test_validator_requires_exact_binding(bad):
    root = atomic()
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: binding:"):
        domain._validate_binding_ownership_no_overlap(((bad, root),))


@pytest.mark.parametrize("bad", [None, {}, [], (), ("A1",), ("ROOT", "A1", "A1"), "A1", 1, True, FakeRoot(),
                                  AtomicSubclass("A1", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))])
def test_validator_accepts_original_root_not_fabricated_owned_id_tuple(bad):
    binding = ConditionBinding("COND_A", "A1", "SYNTH-REVIEW")
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: root:"):
        domain._validate_binding_ownership_no_overlap(((binding, bad),))


@pytest.mark.parametrize("different_root", [False, True])
def test_duplicate_condition_is_input_error_not_overlap(different_root):
    current = tree()
    root_a = _resolve_rule_root(current, "A1")
    root_b = _resolve_rule_root(current, "B1") if different_root else root_a
    first = ConditionBinding("COND_A", root_a.rule_id, "SYNTH-REF-A")
    second = ConditionBinding("COND_A", root_b.rule_id, "SYNTH-REF-B")
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: condition_id:"):
        domain._validate_binding_ownership_no_overlap(((first, root_a), (second, root_b)))


@pytest.mark.parametrize("binding_root", ["ABSENT", "A1 ", "a1"])
def test_root_binding_link_requires_exact_id_before_collection(binding_root, monkeypatch):
    binding = ConditionBinding("COND_A", binding_root, "SYNTH-REVIEW")
    def forbidden(*args):
        pytest.fail("ID 연결 확인보다 먼저 수집했습니다")
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: rule_root_id:"):
        domain._validate_binding_ownership_no_overlap(((binding, atomic()),))


def test_every_input_is_checked_before_early_overlap_and_before_collection(monkeypatch):
    current = tree()
    collision = entries(current, (("COND_A", "G_A"), ("COND_B", "G_A")))
    invalid = (ConditionBinding("COND_C", "B1", "SYNTH-REVIEW-C"), ("B1",))
    def forbidden(*args):
        pytest.fail("전체 입력 형식 검사가 끝나기 전에 수집했습니다")
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: root:"):
        domain._validate_binding_ownership_no_overlap(collision + (invalid,))


def test_duplicate_condition_precedes_root_link_error():
    root = atomic()
    binding = ConditionBinding("COND_A", "WRONG", "SYNTH-REVIEW")
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: condition_id:"):
        domain._validate_binding_ownership_no_overlap(((binding, root), (binding, root)))


def test_collections_are_prepared_once_per_entry_in_condition_order_before_overlap(monkeypatch):
    resolved = entries(tree(), (("COND_C", "G_C"), ("COND_B", "G_A"), ("COND_A", "G_A")))
    original = domain._collect_owned_rule_ids
    calls = []
    def observe(root):
        calls.append(root.rule_id)
        return original(root)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", observe)
    overlap_message(resolved)
    assert calls == ["G_A", "G_A", "G_C"]


def test_later_collection_error_precedes_earlier_overlap_and_is_not_wrapped(monkeypatch):
    resolved = entries(tree(), (("COND_A", "G_A"), ("COND_B", "G_A"), ("COND_C", "G_C")))
    original = domain._collect_owned_rule_ids
    error = PolicyDataError("UNSUPPORTED_RULE_NODE: 합성 수집 실패")
    def fail_later(root):
        if root.rule_id == "G_C":
            raise error
        return original(root)
    monkeypatch.setattr(domain, "_collect_owned_rule_ids", fail_later)
    with pytest.raises(PolicyDataError) as caught:
        domain._validate_binding_ownership_no_overlap(resolved)
    assert caught.value is error


@pytest.mark.parametrize("collision", [False, True])
def test_100_calls_preserve_bindings_tree_tuple_identity_and_results(collision):
    current = tree()
    declarations = (("COND_A", "G_A"), ("COND_B", "G_A" if collision else "G_B"))
    coverage, resolved = prepared(current, declarations)
    before = (_jsonable(current), coverage.to_dict())
    roots = tuple(root for _, root in resolved)
    bindings = coverage.bindings
    child_tuples = tuple(root.children for root in roots)
    expected = overlap_message(resolved)[0] if collision else None
    expected_ids = domain._collect_owned_rule_ids(current.root)
    for _ in range(100):
        assert domain._collect_owned_rule_ids(current.root) == expected_ids
        if collision:
            assert overlap_message(resolved)[0] == expected
        else:
            assert domain._validate_binding_ownership_no_overlap(resolved) is None
    assert (_jsonable(current), coverage.to_dict()) == before
    assert coverage.bindings is bindings
    assert all(binding is original for (binding, _), original in zip(resolved, bindings))
    assert all(root is original for (_, root), original in zip(resolved, roots))
    assert all(root.children is children for root, children in zip(roots, child_tuples))


def test_missing_inventory_binding_and_unowned_tree_nodes_are_outside_scope():
    current = tree()
    coverage, resolved = prepared(current, (("COND_A", "A1"),), extra_conditions=("COND_MISSING",))
    assert len(coverage.inventory.conditions) == 2
    assert domain._validate_binding_ownership_no_overlap(resolved) is None
    # G_B/G_C 등 미매핑 node가 있어도 이 helper는 전체 구조 상태를 만들지 않는다.


def test_binding_review_ref_changes_do_not_affect_ownership():
    resolved = entries(tree(), (("COND_A", "G_A"), ("COND_B", "G_A")))
    changed = tuple((replace(binding, implementation_review_ref="SYNTH-OTHER-REF"), root) for binding, root in resolved)
    assert overlap_message(changed)[0] == overlap_message(resolved)[0]


def test_only_node_structure_binding_identity_and_root_link_are_read(monkeypatch):
    current = tree()
    resolved = entries(current, (("COND_A", "G_A"), ("COND_B", "G_B")))
    def guard(allowed):
        def access(value, name):
            if name not in allowed:
                pytest.fail("소유 helper 책임 밖 필드를 읽었습니다: " + name)
            return object.__getattribute__(value, name)
        return access
    monkeypatch.setattr(ConditionBinding, "__getattribute__", guard({"condition_id", "rule_root_id"}))
    monkeypatch.setattr(RuleGroup, "__getattribute__", guard({"rule_id", "children"}))
    for model in (PolicyRule, ResidentRegistrationRule, BirthDateRule):
        monkeypatch.setattr(model, "__getattribute__", guard({"rule_id"}))
    assert domain._validate_binding_ownership_no_overlap(resolved) is None


def test_no_lookup_review_fingerprint_revalidation_or_external_io(monkeypatch):
    current = tree()
    disjoint = entries(current, (("COND_A", "G_A"), ("COND_B", "G_B")))
    collision = entries(current, (("COND_A", "G_A"), ("COND_B", "G_A")))
    from backend.policy_engine.policy_data import coverage_fingerprint, coverage_review_matching, coverage_review_resolution, rule_root_resolution
    def forbidden(*args, **kwargs):
        pytest.fail("소유 helper가 lookup·검토·지문·재검증·외부 상태를 사용했습니다")
    for model in (Policy, RuleGroup, PolicyRule, ResidentRegistrationRule, BirthDateRule, ConditionBinding):
        monkeypatch.setattr(model, "__post_init__", forbidden)
    for module, names in (
        (rule_root_resolution, ("_resolve_rule_root",)),
        (coverage_fingerprint, ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree")),
        (coverage_review_matching, ("_match_inventory_review", "_match_implementation_review")),
        (coverage_review_resolution, ("_resolve_inventory_review", "_resolve_implementation_review")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    for name in ("builtins.open", "hashlib.sha256", "socket.socket", "subprocess.run", "pathlib.Path.exists",
                 "pathlib.Path.read_text", "os.getenv", "time.time"):
        monkeypatch.setattr(name, forbidden)
    assert domain._validate_binding_ownership_no_overlap(disjoint) is None
    assert overlap_message(collision)[1]["overlap_count"] == 6


def test_duplicate_and_unsupported_trees_are_blocked_without_mutating_frozen_objects():
    node = atomic()
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        group("GROUP", (node, node))
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        group("GROUP", (atomic("SAME"), atomic("SAME")))
    with pytest.raises(PolicyDataError):
        group("GROUP", (object(),))


def test_private_signatures_and_function_dependencies_keep_narrow_scope():
    from backend.policy_engine import policy_data
    for function, parameter in ((domain._collect_owned_rule_ids, "root"),
                                 (domain._validate_binding_ownership_no_overlap, "resolved_bindings")):
        signature = inspect.signature(function)
        assert list(signature.parameters) == [parameter]
        assert signature.parameters[parameter].default is inspect.Parameter.empty
        assert function.__name__ not in policy_data.__all__ and not hasattr(policy_data, function.__name__)
        names = {node.id for node in ast.walk(ast.parse(inspect.getsource(function))) if isinstance(node, ast.Name)}
        assert not names & {"Policy", "EligibilityCoverage", "ConditionInventory", "CoverageReviewContext", "CoverageResult",
                            "RuleTreeIndex", "ResolvedConditionBinding", "_resolve_rule_root", "fingerprint_rule_subtree"}
