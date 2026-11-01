"""합성 subtree 지문. GV12/GV13 기대 JSON·길이·digest는 문서의 고정 literal이다."""

import ast
from dataclasses import fields, replace
from datetime import date
import inspect
import json
import re
import unicodedata

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import FactBasis, Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule
from backend.policy_engine.policy_data import fingerprint_policy_tree, fingerprint_rule_subtree
from backend.policy_engine.policy_data import coverage_fingerprint as domain


GOLDEN = (
    ("GV12", '{"fingerprint_schema":"coverage-subtree-1.0","root":{"children":[{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19},{"evidence_refs":["SYNTH-SRC#b"],"fact_basis":null,"field":"student_status","node_type":"atomic","operator":"eq","rule_id":"RULE_B","value":false}],"node_type":"group","operator":"ALL","rule_id":"GROUP_AB"}}', 406, "6f7467494db11ce6391444c0e54127706a8ee62eb13e2937726638d92351da17"),
    ("GV13", '{"fingerprint_schema":"coverage-subtree-1.0","root":{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19}}', 186, "7c4088644283ad50806d182d288587bdfad0aa9e08192ad2755594f46f8add69"),
)


def atomic(**changes):
    values = dict(rule_id="RULE_A", field=Field.AGE, operator=Operator.GTE, value=19,
                  evidence_refs=("SYNTH-SRC#a",))
    values.update(changes)
    return PolicyRule(**values)


def student():
    return atomic(rule_id="RULE_B", field=Field.STUDENT_STATUS, operator=Operator.EQ, value=False,
                  evidence_refs=("SYNTH-SRC#b",))


def group(operator=GroupOperator.ALL, children=None, rule_id="GROUP_AB"):
    return RuleGroup(rule_id, operator, (atomic(), student()) if children is None else children)


def resident():
    return ResidentRegistrationRule("RESIDENT_A", RegionRef("SEOUL", "JONGNO"),
                                    ReferenceDateSource.APPLICATION_DATE, ("SYNTH-SRC#a",))


def birth():
    return BirthDateRule("BIRTH_A", date(2000, 1, 1), date(2001, 1, 1), ("SYNTH-SRC#a",))


def policy(root, **changes):
    values = dict(policy_id="SYNTH-POLICY", policy_name="SYNTHETIC", rule_version="r0001", root=root)
    values.update(changes)
    return Policy(**values)


@pytest.mark.parametrize("vector_id,expected_json,expected_length,expected_digest", GOLDEN, ids=[r[0] for r in GOLDEN])
def test_subtree_golden_wrapper_json_bytes_and_literal_digest(
    vector_id, expected_json, expected_length, expected_digest, monkeypatch,
):
    root = group() if vector_id == "GV12" else atomic()
    payloads, encoded = [], []
    real_digest, real_sha = domain._digest_payload, domain.hashlib.sha256
    def spy_digest(payload, label):
        payloads.append(payload)
        return real_digest(payload, label)
    def spy_sha(data):
        encoded.append(data)
        return real_sha(data)
    monkeypatch.setattr(domain, "_digest_payload", spy_digest)
    monkeypatch.setattr(domain.hashlib, "sha256", spy_sha)
    assert fingerprint_rule_subtree(root) == expected_digest
    assert payloads == [json.loads(expected_json)]
    assert json.dumps(payloads[0], sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False) == expected_json
    assert encoded == [expected_json.encode("utf-8")]
    assert len(encoded[0]) == expected_length
    assert not encoded[0].startswith(b"\xef\xbb\xbf") and not encoded[0].endswith(b"\n")


@pytest.mark.parametrize("factory", [atomic, resident, birth, group])
def test_each_node_kind_is_deterministic_and_uses_same_payload_as_tree(factory, monkeypatch):
    root = factory()
    tree_node = domain._build_policy_tree_payload(policy(root))["root"]
    calls = []
    real_digest = domain._digest_payload
    def spy(payload, label):
        calls.append(payload)
        return real_digest(payload, label)
    monkeypatch.setattr(domain, "_digest_payload", spy)
    first = fingerprint_rule_subtree(root)
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    for _ in range(3):
        assert fingerprint_rule_subtree(root) == first
    assert all(payload == {"fingerprint_schema": "coverage-subtree-1.0", "root": tree_node} for payload in calls)


def test_same_subtree_under_different_parents_keeps_subtree_digest_only():
    original = group()
    independent = group()
    assert original == independent and original is not independent
    other = birth()
    first = policy(group(children=(original, other), rule_id="PARENT_A"))
    second = policy(group(GroupOperator.ANY, (other, independent), "PARENT_B"))
    assert fingerprint_rule_subtree(first.root.children[0]) == fingerprint_rule_subtree(second.root.children[1])
    assert fingerprint_rule_subtree(original) == GOLDEN[0][3]
    assert fingerprint_policy_tree(first) != fingerprint_policy_tree(second)


@pytest.mark.parametrize("changes", [{"rule_version": "r0002"}, {"policy_id": "SYNTH-OTHER-POLICY"}])
def test_policy_identity_and_version_are_outside_subtree(changes):
    root = group()
    first = policy(root)
    second = policy(group(), **changes)
    assert fingerprint_rule_subtree(first.root) == fingerprint_rule_subtree(second.root) == GOLDEN[0][3]
    assert fingerprint_policy_tree(first) != fingerprint_policy_tree(second)


@pytest.mark.parametrize("factory", [atomic, resident, birth, group])
def test_root_id_is_included(factory):
    root = factory()
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(replace(root, rule_id="OTHER_ROOT"))


@pytest.mark.parametrize("operator", [GroupOperator.ANY, GroupOperator.NOT])
def test_group_operator_is_included(operator):
    root = group(children=(atomic(),))
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(replace(root, operator=operator))


def test_child_order_and_root_group_are_included():
    root = group()
    reversed_root = replace(root, children=tuple(reversed(root.children)))
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(reversed_root)
    assert fingerprint_rule_subtree(group(children=(atomic(),))) != fingerprint_rule_subtree(atomic())


@pytest.mark.parametrize("changes", [
    {"value": 20}, {"operator": Operator.LTE},
    {"field": Field.HOUSEHOLD_INCOME, "fact_basis": FactBasis("SYNTH", "household", "month", 2026, "KRW")},
])
def test_atomic_meaning_is_included(changes):
    root = atomic()
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(replace(root, **changes))


@pytest.mark.parametrize("field,value", [
    ("basis", "SYNTH-OTHER"), ("subject", "individual"), ("period", "year"),
    ("reference_year", 2027), ("unit", "SYNTH-UNIT"),
])
def test_all_fact_basis_fields_remain_part_of_subtree(field, value):
    root = atomic(field=Field.HOUSEHOLD_INCOME, fact_basis=FactBasis("SYNTH", "household", "month", 2026, "KRW"))
    other = replace(root, fact_basis=replace(root.fact_basis, **{field: value}))
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(other)


def test_resident_region_is_included():
    root = resident()
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(
        replace(root, required_region=RegionRef("GYEONGGI", "SUWON"))
    )


@pytest.mark.parametrize("changes", [
    {"min_birth_date": date(2000, 1, 2)}, {"max_birth_date": date(2001, 1, 2)},
])
def test_birth_boundaries_are_included(changes):
    root = birth()
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(replace(root, **changes))


@pytest.mark.parametrize("factory", [atomic, resident, birth])
@pytest.mark.parametrize("refs", [
    ("SYNTH-SRC#a", "SYNTH-SRC#b"),
    ("SYNTH-SRC#b", "SYNTH-SRC#a"),
    ("SYNTH-SRC#a", "SYNTH-SRC#a"),
])
def test_evidence_addition_order_and_duplicates_change_digest(factory, refs):
    root = factory()
    changed = replace(root, evidence_refs=refs)
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(changed)
    if len(set(refs)) == 2:
        assert fingerprint_rule_subtree(changed) != fingerprint_rule_subtree(
            replace(changed, evidence_refs=tuple(reversed(refs)))
        )


def test_100_nested_group_runs_preserve_input_hierarchy_and_objects():
    inner = group(GroupOperator.ANY, (resident(), birth()), "INNER_ANY")
    negation = group(GroupOperator.NOT, (student(),), "INNER_NOT")
    children = (atomic(), inner, negation)
    root = group(children=children)
    before = domain._build_rule_node_payload(root)
    first = fingerprint_rule_subtree(root)
    for _ in range(100):
        assert fingerprint_rule_subtree(root) == first
        assert domain._build_rule_node_payload(root) == before
    assert root.children is children and root.children[1] is inner and root.children[2] is negation
    assert before["children"][1]["operator"] == "ANY"
    assert before["children"][2]["children"][0]["rule_id"] == "RULE_B"


class FakeNode:
    def to_dict(self):
        pytest.fail("미지원 객체의 generic serializer를 호출했습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "RULE_A", 1, True, object(), FakeNode(), policy(atomic())])
def test_unsupported_roots_fail_closed(bad):
    with pytest.raises(PolicyDataError, match="RuleNode"):
        fingerprint_rule_subtree(bad)


@pytest.mark.parametrize("factory", [atomic, resident, birth, group])
def test_node_subclasses_are_rejected_as_in_tree_function(factory):
    original = factory()
    subtype = type("SyntheticNodeSubclass", (type(original),), {})
    value = subtype(**{field.name: getattr(original, field.name) for field in fields(original)})
    with pytest.raises(PolicyDataError):
        fingerprint_rule_subtree(value)


def test_api_has_one_root_argument_and_no_policy_context_options():
    signature = inspect.signature(fingerprint_rule_subtree)
    assert list(signature.parameters) == ["root"]
    assert signature.parameters["root"].default is inspect.Parameter.empty
    for extra in ("policy", "rule_version", "parent", "sort_children", "rule_root_id"):
        with pytest.raises(TypeError):
            fingerprint_rule_subtree(atomic(), **{extra: None})


def test_public_function_reuses_only_existing_node_payload_and_encoder():
    tree = ast.parse(inspect.getsource(fingerprint_rule_subtree))
    assert {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)} == {"_build_rule_node_payload", "_digest_payload"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"Policy", "walk_nodes", "ConditionBinding", "ImplementationBindingReview", "UserProfile",
                        "EvaluationFacts", "EvaluationContext", "PolicyEvaluation", "CoverageResult"}


def test_node_payload_is_not_duplicated_or_reinterpreted(monkeypatch):
    original = atomic()
    expected_node = domain._build_rule_node_payload(original)
    calls, payloads = [], []
    real_digest = domain._digest_payload
    def node_spy(root):
        calls.append(root)
        return expected_node
    def digest_spy(payload, label):
        payloads.append(payload)
        return real_digest(payload, label)
    monkeypatch.setattr(domain, "_build_rule_node_payload", node_spy)
    monkeypatch.setattr(domain, "_digest_payload", digest_spy)
    assert fingerprint_rule_subtree(original) == GOLDEN[1][3]
    assert calls == [original] and calls[0] is original
    assert payloads[0]["root"] is expected_node
    assert set(payloads[0]) == {"fingerprint_schema", "root"}


def test_same_encoder_recipe_and_strict_unicode_behavior(monkeypatch):
    nfc = "서울 조건"
    root = atomic(field=Field.REGION, operator=Operator.EQ, value=nfc)
    calls = []
    real_dumps = domain.json.dumps
    def spy(payload, **kwargs):
        calls.append(kwargs)
        return real_dumps(payload, **kwargs)
    monkeypatch.setattr(domain.json, "dumps", spy)
    assert fingerprint_rule_subtree(root) != fingerprint_rule_subtree(
        replace(root, value=unicodedata.normalize("NFD", nfc))
    )
    assert all(kwargs == dict(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) for kwargs in calls)
    with pytest.raises(PolicyDataError):
        fingerprint_rule_subtree(replace(root, value="SYNTH-private-" + chr(0xD800)))


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_encoder_failure_never_returns_placeholder_or_leaks_input(error_type, monkeypatch):
    root = atomic()
    def fail(*args, **kwargs):
        raise error_type("SYNTH-private-input")
    monkeypatch.setattr(domain.json, "dumps", fail)
    with pytest.raises(PolicyDataError) as caught:
        fingerprint_rule_subtree(root)
    assert "SYNTH-private" not in str(caught.value)


def test_no_lookup_revalidation_generic_serializer_or_external_io(monkeypatch):
    root = group(children=(atomic(), resident(), birth()))
    expected = fingerprint_rule_subtree(root)
    def forbidden(*args, **kwargs):
        pytest.fail("subtree 지문 계산에서 lookup·재검증·외부 상태에 접근했습니다")
    monkeypatch.setattr("backend.policy_engine.models.walk_nodes", forbidden)
    monkeypatch.setattr("backend.policy_engine.models._jsonable", forbidden)
    for node_type in (Policy, PolicyRule, RuleGroup, ResidentRegistrationRule, BirthDateRule, RegionRef):
        monkeypatch.setattr(node_type, "__post_init__", forbidden)
    for node_type in (ResidentRegistrationRule, BirthDateRule, RegionRef):
        monkeypatch.setattr(node_type, "to_dict", forbidden)
    monkeypatch.setattr(domain, "fingerprint_policy_tree", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("os.getenv", forbidden)
    assert fingerprint_rule_subtree(root) == expected
