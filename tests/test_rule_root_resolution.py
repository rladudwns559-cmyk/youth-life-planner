"""합성 Policy의 exact root 조회. 생성자를 우회하거나 불변 tree를 훼손하지 않는다."""

import ast
from dataclasses import replace
from datetime import date
import inspect
import unicodedata

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import (
    Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, _jsonable, walk_nodes,
)
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule
from backend.policy_engine.policy_data import rule_root_resolution as domain


def atomic(rule_id="SYNTH-ATOMIC"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))


def resident(rule_id="SYNTH-RESIDENT"):
    return ResidentRegistrationRule(rule_id, RegionRef("SEOUL", "JONGNO"), ReferenceDateSource.APPLICATION_DATE,
                                    ("SYNTH-SRC#resident",))


def birth(rule_id="SYNTH-BIRTH"):
    return BirthDateRule(rule_id, date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#birth",))


def group(rule_id="SYNTH-GROUP", operator=GroupOperator.ALL, children=None):
    return RuleGroup(rule_id, operator, (atomic(),) if children is None else children)


def policy(root=None, **changes):
    values = dict(policy_id="SYNTH-POLICY", policy_name="합성 정책", rule_version="r0001", root=group() if root is None else root)
    values.update(changes)
    return Policy(**values)


def nested_policy():
    a, r, b = atomic(), resident(), birth()
    negation = group("SYNTH-NOT", GroupOperator.NOT, (b,))
    any_group = group("SYNTH-ANY", GroupOperator.ANY, (a, negation))
    root = group("SYNTH-ALL", GroupOperator.ALL, (r, any_group))
    nodes = (root, r, any_group, a, negation, b)
    return policy(root), nodes


@pytest.mark.parametrize("factory", [atomic, resident, birth, group])
def test_top_level_leaf_or_group_returns_original_root(factory):
    root = factory()
    assert domain._resolve_rule_root(policy(root), root.rule_id) is root


@pytest.mark.parametrize("index", range(6))
def test_all_nested_leaf_and_group_types_return_original_object(index):
    current, nodes = nested_policy()
    assert domain._resolve_rule_root(current, nodes[index].rule_id) is nodes[index]


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_all_group_operators_are_lookup_roots(operator):
    root = group(operator=operator)
    current = policy(group("SYNTH-OUTER", children=(root,)))
    assert domain._resolve_rule_root(current, root.rule_id) is root


@pytest.mark.parametrize("depth", [5, 12])
def test_deep_valid_tree_preserves_leaf_and_inner_group_identity(depth):
    leaf = birth()
    root = leaf
    groups = []
    for index in range(depth):
        root = group(f"SYNTH-NEST-{index}", GroupOperator.NOT, (root,))
        groups.append(root)
    current = policy(root)
    assert domain._resolve_rule_root(current, leaf.rule_id) is leaf
    assert domain._resolve_rule_root(current, groups[2].rule_id) is groups[2]


@pytest.mark.parametrize("requested", ["rule_a", "RULE_A ", " RULE_A", "RULE_A_", "RULE", "A", "SYNTH-ABSENT"])
def test_exact_string_mismatch_is_not_found_without_fallback(requested):
    current = policy(atomic("RULE_A"))
    with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
        domain._resolve_rule_root(current, requested)


@pytest.mark.parametrize("rule_id", ["RULE_A", " RULE_A ", "rule_a", "조건 A", "123", "내부 공백 ID"])
def test_valid_nonblank_ids_have_no_extra_grammar_or_normalization(rule_id):
    node = atomic(rule_id)
    assert domain._resolve_rule_root(policy(node), rule_id) is node


def test_distinct_padding_case_and_unicode_forms_can_coexist():
    ids = ("RULE_A", " RULE_A ", "rule_a", "조건", unicodedata.normalize("NFD", "조건"))
    nodes = tuple(atomic(rule_id) for rule_id in ids)
    current = policy(group(children=nodes))
    for node in nodes:
        assert domain._resolve_rule_root(current, node.rule_id) is node


@pytest.mark.parametrize("has_other_leaf", [False, True])
def test_renamed_or_removed_old_id_is_not_remapped(has_other_leaf):
    renamed = atomic("RULE_B")
    root = group(children=(renamed, resident())) if has_other_leaf else renamed
    with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
        domain._resolve_rule_root(policy(root), "RULE_A")


@pytest.mark.parametrize("requested", ["SYNTH-ALL", "SYNTH-RESIDENT", "SYNTH-BIRTH", "SYNTH-ABSENT"])
def test_existing_walk_is_reused_once_and_exhausted_even_after_early_match(requested, monkeypatch):
    current, nodes = nested_policy()
    visited, completed, roots = [], [], []
    def observe(root):
        roots.append(root)
        for node in walk_nodes(root):
            visited.append(node)
            yield node
        completed.append(True)
    monkeypatch.setattr(domain, "walk_nodes", observe)
    if requested == "SYNTH-ABSENT":
        with pytest.raises(PolicyDataError, match="^RULE_ROOT_NOT_FOUND:"):
            domain._resolve_rule_root(current, requested)
    else:
        expected = next(node for node in nodes if node.rule_id == requested)
        assert domain._resolve_rule_root(current, requested) is expected
    assert len(roots) == 1 and roots[0] is current.root
    assert len(visited) == len(nodes) and all(a is b for a, b in zip(visited, nodes))
    assert completed == [True]


class TextSubclass(str):
    pass


class PolicySubclass(Policy):
    pass


class FakePolicy:
    @property
    def root(self):
        pytest.fail("잘못된 Policy의 root를 읽었습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "SYNTH", 1, True, FakePolicy(), atomic(), resident(), birth(), group()])
def test_wrong_policy_type_is_rejected_before_root_access(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: policy:"):
        domain._resolve_rule_root(bad, "SYNTH-ATOMIC")


def test_policy_subclass_is_not_automatically_supported():
    current = PolicySubclass("SYNTH-POLICY", "합성 정책", "r0001", atomic())
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: policy:"):
        domain._resolve_rule_root(current, "SYNTH-ATOMIC")


@pytest.mark.parametrize("bad", [None, "", " \t\n", 1, True, b"SYNTH", [], {}, (), TextSubclass("SYNTH-ATOMIC")])
def test_invalid_id_is_rejected_before_traversal(bad, monkeypatch):
    current = policy()
    def forbidden(*args):
        pytest.fail("ID 입력 오류보다 먼저 순회했습니다")
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: rule_root_id:"):
        domain._resolve_rule_root(current, bad)


def test_invalid_policy_precedes_invalid_id_without_traversal(monkeypatch):
    def forbidden(*args):
        pytest.fail("잘못된 입력으로 순회했습니다")
    monkeypatch.setattr(domain, "walk_nodes", forbidden)
    with pytest.raises(PolicyDataError, match="^INVALID_STRUCTURE_INPUT: policy:"):
        domain._resolve_rule_root(FakePolicy(), None)


@pytest.mark.parametrize("reverse", [False, True])
def test_child_order_changes_do_not_change_exact_target_or_mutate_tuple(reverse):
    nodes = (atomic(), resident(), birth())
    children = tuple(reversed(nodes)) if reverse else nodes
    current = policy(group(children=children))
    for node in nodes:
        assert domain._resolve_rule_root(current, node.rule_id) is node
    assert current.root.children is children


@pytest.mark.parametrize("target_index", [0, 3, 5])
def test_100_calls_keep_original_identity_and_all_observable_structure(target_index):
    current, nodes = nested_policy()
    original_root = current.root
    child_tuples = tuple((node, node.children) for node in nodes if type(node) is RuleGroup)
    evidence_tuples = tuple((node, node.evidence_refs) for node in nodes if type(node) is not RuleGroup)
    before = _jsonable(current)
    target = nodes[target_index]
    for _ in range(100):
        assert domain._resolve_rule_root(current, target.rule_id) is target
    assert _jsonable(current) == before and current.root is original_root
    assert all(node.children is children for node, children in child_tuples)
    assert all(node.evidence_refs is refs for node, refs in evidence_tuples)
    assert all(a is b for a, b in zip(walk_nodes(current.root), nodes))


def test_parent_child_sibling_and_repeated_targets_have_no_ownership_state():
    current, nodes = nested_policy()
    for target in (nodes[2], nodes[3], nodes[5], nodes[2], nodes[1], nodes[0]):
        assert domain._resolve_rule_root(current, target.rule_id) is target


def test_same_id_in_two_policies_returns_each_policies_own_object():
    first_node, second_node = atomic(), atomic()
    assert first_node is not second_node
    first = policy(first_node)
    second = policy(second_node, policy_id="SYNTH-OTHER", rule_version="r9999")
    assert domain._resolve_rule_root(first, first_node.rule_id) is first_node
    assert domain._resolve_rule_root(second, first_node.rule_id) is second_node


@pytest.mark.parametrize("changes", [{"policy_id": "SYNTH-OTHER"}, {"rule_version": "r9999"}, {"rule_version": " 규칙 2판 "}])
def test_policy_metadata_does_not_gate_lookup(changes):
    original = policy()
    current = replace(original, **changes)
    assert domain._resolve_rule_root(current, current.root.rule_id) is original.root


@pytest.mark.parametrize("same_object", [False, True])
def test_duplicate_nodes_are_already_blocked_by_public_group_constructor(same_object):
    first = atomic("SYNTH-DUPLICATE")
    second = first if same_object else atomic("SYNTH-DUPLICATE")
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        group(children=(first, second))


def test_root_and_descendant_id_collision_is_blocked_by_public_constructor():
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        group("SYNTH-SAME", children=(atomic("SYNTH-SAME"),))


class AtomicSubclass(PolicyRule):
    pass


@pytest.mark.parametrize("unsupported", [object(), {}, "SYNTH-FUTURE", AtomicSubclass(
    "SYNTH-SUBCLASS", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))])
def test_unsupported_nodes_are_blocked_by_normal_public_constructors(unsupported):
    with pytest.raises(PolicyDataError):
        group(children=(unsupported,))
    with pytest.raises(PolicyDataError):
        policy(unsupported)


def test_missing_error_class_prefix_message_are_deterministic_without_ref_echo():
    current, _ = nested_policy()
    results = []
    for ref in ("SYNTH-PRIVATE-ABSENT-A", "SYNTH-PRIVATE-ABSENT-B"):
        for _ in range(100):
            with pytest.raises(PolicyDataError) as caught:
                domain._resolve_rule_root(current, ref)
            results.append((type(caught.value), str(caught.value)))
            assert ref not in str(caught.value)
    assert len(set(results)) == 1 and results[0][1].startswith("RULE_ROOT_NOT_FOUND:")


def test_only_tree_structure_and_ids_are_read(monkeypatch):
    current, nodes = nested_policy()
    def guard(allowed):
        def access(value, name):
            if name not in allowed:
                pytest.fail("root lookup 책임 밖 필드를 읽었습니다: " + name)
            return object.__getattribute__(value, name)
        return access
    monkeypatch.setattr(Policy, "__getattribute__", guard({"root"}))
    monkeypatch.setattr(RuleGroup, "__getattribute__", guard({"rule_id", "children"}))
    for model in (PolicyRule, ResidentRegistrationRule, BirthDateRule):
        monkeypatch.setattr(model, "__getattribute__", guard({"rule_id"}))
    assert domain._resolve_rule_root(current, "SYNTH-BIRTH") is nodes[5]


def test_lookup_has_no_calculation_revalidation_or_external_io(monkeypatch):
    current, nodes = nested_policy()
    from backend.policy_engine.policy_data import coverage_fingerprint, coverage_review_matching, coverage_review_resolution
    def forbidden(*args, **kwargs):
        pytest.fail("lookup이 계산·검토·재검증·외부 상태에 접근했습니다")
    for model in (Policy, RuleGroup, PolicyRule, ResidentRegistrationRule, BirthDateRule):
        monkeypatch.setattr(model, "__post_init__", forbidden)
    for module, names in (
        (coverage_fingerprint, ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree")),
        (coverage_review_matching, ("_match_inventory_review", "_match_implementation_review")),
        (coverage_review_resolution, ("_resolve_inventory_review", "_resolve_implementation_review")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    for name in ("builtins.open", "hashlib.sha256", "socket.socket", "subprocess.run", "pathlib.Path.exists",
                 "pathlib.Path.read_text", "os.getenv", "time.time", "json.dumps"):
        monkeypatch.setattr(name, forbidden)
    assert domain._resolve_rule_root(current, "SYNTH-BIRTH") is nodes[5]


def test_private_api_has_exact_two_required_parameters_and_no_semantic_dependencies():
    from backend.policy_engine import policy_data
    signature = inspect.signature(domain._resolve_rule_root)
    assert list(signature.parameters) == ["policy", "rule_root_id"]
    assert all(value.default is inspect.Parameter.empty for value in signature.parameters.values())
    assert "_resolve_rule_root" not in policy_data.__all__ and not hasattr(policy_data, "_resolve_rule_root")
    tree = ast.parse(inspect.getsource(domain._resolve_rule_root))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"ConditionBinding", "EligibilityCoverage", "CoverageReviewContext", "CoverageResult",
                        "RuleTreeIndex", "ResolvedConditionBinding", "fingerprint_rule_subtree", "ReviewMatchStatus"}
    current = policy()
    with pytest.raises(TypeError):
        domain._resolve_rule_root(current)
    with pytest.raises(TypeError):
        domain._resolve_rule_root(current, current.root.rule_id, include_root=False)
