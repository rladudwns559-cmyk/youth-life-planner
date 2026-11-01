"""합성 Policy tree만 검증한다. 고정 digest는 M2.16 문서의 literal이다."""

import ast
from dataclasses import replace
from datetime import date
import inspect
import json
import re
import unicodedata

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegionRef
from backend.policy_engine.models import (
    FactBasis, Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup,
)
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule
from backend.policy_engine.policy_data import fingerprint_policy_tree
from backend.policy_engine.policy_data import coverage_fingerprint as domain


TREE_GOLDEN = (
    ("GV07", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"fact_basis\":null,\"field\":\"age\",\"node_type\":\"atomic\",\"operator\":\"gte\",\"rule_id\":\"RULE_A\",\"value\":19},\"rule_version\":\"r0001\"}", 240, "e887c0978fdc6e5d652e6982c23913d7d1a2b5570f4d983edd77c953240a63c0"),
    ("GV08", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"children\":[{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"fact_basis\":null,\"field\":\"age\",\"node_type\":\"atomic\",\"operator\":\"gte\",\"rule_id\":\"RULE_A\",\"value\":19},{\"evidence_refs\":[\"SYNTH-SRC#b\"],\"fact_basis\":null,\"field\":\"student_status\",\"node_type\":\"atomic\",\"operator\":\"eq\",\"rule_id\":\"RULE_B\",\"value\":false}],\"node_type\":\"group\",\"operator\":\"ALL\",\"rule_id\":\"GROUP_AB\"},\"rule_version\":\"r0001\"}", 460, "d95f5a2328666f69f7eb72a3e270b6f3ea39c2303197e522123ffdfe81a23a37"),
    ("GV09", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"children\":[{\"evidence_refs\":[\"SYNTH-SRC#b\"],\"fact_basis\":null,\"field\":\"student_status\",\"node_type\":\"atomic\",\"operator\":\"eq\",\"rule_id\":\"RULE_B\",\"value\":false},{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"fact_basis\":null,\"field\":\"age\",\"node_type\":\"atomic\",\"operator\":\"gte\",\"rule_id\":\"RULE_A\",\"value\":19}],\"node_type\":\"group\",\"operator\":\"ALL\",\"rule_id\":\"GROUP_AB\"},\"rule_version\":\"r0001\"}", 460, "56dc91d1f5ee476f2b7068194dc4dbeb33f1faf77c75ecedaa464f2b63193161"),
    ("GV10", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"node_type\":\"resident_registration\",\"reference_date_source\":\"APPLICATION_DATE\",\"required_region\":{\"sido\":\"SEOUL\",\"sigungu\":\"JONGNO\"},\"rule_id\":\"RESIDENT_A\"},\"rule_version\":\"r0001\"}", 296, "cac2f242577922304c63f28bdac4c5c9712d54b2e6948d2cb74206aa5528658d"),
    ("GV11", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"max_birth_date\":\"2001-01-01\",\"min_birth_date\":\"2000-01-01\",\"node_type\":\"birth_date\",\"rule_id\":\"BIRTH_A\"},\"rule_version\":\"r0001\"}", 245, "3a08146cbe12770cd371868c11d2d6c1e0b8622f48ff044e2826116833bfdf04"),
    ("GV14", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"fact_basis\":{\"basis\":\"SYNTH-BASIS\",\"period\":\"month\",\"reference_year\":2026,\"subject\":\"household\",\"unit\":\"KRW\"},\"field\":\"household_income\",\"node_type\":\"atomic\",\"operator\":\"lte\",\"rule_id\":\"INCOME_A\",\"value\":2000000},\"rule_version\":\"r0001\"}", 353, "63221aca921c1e31080e1845e4c40c2c4a09671df3bc2276a357aada739ecdbe"),
    ("GV15", "{\"fingerprint_schema\":\"coverage-policy-tree-1.0\",\"policy_id\":\"SYNTH-POLICY\",\"root\":{\"evidence_refs\":[\"SYNTH-SRC#a\"],\"fact_basis\":null,\"field\":\"region\",\"node_type\":\"atomic\",\"operator\":\"in\",\"rule_id\":\"REGION_A\",\"value\":[\"SEOUL\",\"GYEONGGI\"]},\"rule_version\":\"r0001\"}", 262, "4c971d7417a4b86448c979b54ae8116645a126061d9c3695d69ad567cf9feea4"),
)


def atomic(**changes):
    values = dict(rule_id="RULE_A", field=Field.AGE, operator=Operator.GTE, value=19,
                  evidence_refs=("SYNTH-SRC#a",))
    values.update(changes)
    return PolicyRule(**values)


def student():
    return atomic(rule_id="RULE_B", field=Field.STUDENT_STATUS, operator=Operator.EQ,
                  value=False, evidence_refs=("SYNTH-SRC#b",))


def group(operator=GroupOperator.ALL, children=None, rule_id="GROUP_AB"):
    return RuleGroup(rule_id, operator, (atomic(), student()) if children is None else children)


def resident(**changes):
    values = dict(rule_id="RESIDENT_A", required_region=RegionRef("SEOUL", "JONGNO"),
                  reference_date_source=ReferenceDateSource.APPLICATION_DATE, evidence_refs=("SYNTH-SRC#a",))
    values.update(changes)
    return ResidentRegistrationRule(**values)


def birth(**changes):
    values = dict(rule_id="BIRTH_A", min_birth_date=date(2000, 1, 1), max_birth_date=date(2001, 1, 1),
                  evidence_refs=("SYNTH-SRC#a",))
    values.update(changes)
    return BirthDateRule(**values)


def income():
    return atomic(rule_id="INCOME_A", field=Field.HOUSEHOLD_INCOME, operator=Operator.LTE, value=2000000,
                  fact_basis=FactBasis("SYNTH-BASIS", "household", "month", 2026, "KRW"))


def policy(root=None, **changes):
    values = dict(policy_id="SYNTH-POLICY", policy_name="SYNTHETIC", rule_version="r0001",
                  root=atomic() if root is None else root)
    values.update(changes)
    return Policy(**values)


def vector_policy(vector_id):
    if vector_id == "GV07":
        return policy()
    if vector_id == "GV08":
        return policy(group())
    if vector_id == "GV09":
        return policy(group(children=(student(), atomic())))
    if vector_id == "GV10":
        return policy(resident())
    if vector_id == "GV11":
        return policy(birth())
    if vector_id == "GV14":
        return policy(income())
    assert vector_id == "GV15"
    return policy(atomic(rule_id="REGION_A", field=Field.REGION, operator=Operator.IN, value=("SEOUL", "GYEONGGI")))


@pytest.mark.parametrize("vector_id,expected_json,expected_length,expected_digest", TREE_GOLDEN,
                         ids=[row[0] for row in TREE_GOLDEN])
def test_all_document_policy_tree_golden_vectors(vector_id, expected_json, expected_length, expected_digest, monkeypatch):
    value = vector_policy(vector_id)
    payload = domain._build_policy_tree_payload(value)
    assert payload == json.loads(expected_json)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert canonical == expected_json
    seen = []
    real_sha256 = domain.hashlib.sha256
    def spy_sha256(data):
        seen.append(data)
        return real_sha256(data)
    monkeypatch.setattr(domain.hashlib, "sha256", spy_sha256)
    assert fingerprint_policy_tree(value) == expected_digest
    assert seen == [expected_json.encode("utf-8")]
    assert len(seen[0]) == expected_length
    assert not seen[0].startswith(b"\xef\xbb\xbf") and not seen[0].endswith(b"\n")


def test_tree_order_is_preserved_and_not_normalized_as_inventory():
    children = (atomic(), student())
    first, reverse = policy(group(children=children)), policy(group(children=tuple(reversed(children))))
    assert fingerprint_policy_tree(first) == TREE_GOLDEN[1][3]
    assert fingerprint_policy_tree(reverse) == TREE_GOLDEN[2][3]
    assert fingerprint_policy_tree(first) != fingerprint_policy_tree(reverse)
    assert first.root.children is children


@pytest.mark.parametrize("operator", [GroupOperator.ANY, GroupOperator.NOT])
def test_valid_group_operator_change_changes_digest(operator):
    child = atomic()
    first = policy(group(children=(child,)))
    changed = policy(group(operator=operator, children=(child,)))
    assert fingerprint_policy_tree(first) != fingerprint_policy_tree(changed)


def test_nested_all_any_not_preserves_hierarchy_instead_of_flat_walk():
    inner = group(GroupOperator.ANY, (
        birth(), group(GroupOperator.NOT, (student(),), "NOT_STUDENT"),
    ), "INNER_ANY")
    value = policy(group(children=(atomic(), inner)))
    root = domain._build_policy_tree_payload(value)["root"]
    assert root["operator"] == "ALL"
    assert root["children"][1]["operator"] == "ANY"
    assert root["children"][1]["children"][1]["operator"] == "NOT"
    assert root["children"][1]["children"][1]["children"][0]["rule_id"] == "RULE_B"
    other_inner = replace(inner, operator=GroupOperator.ALL)
    assert fingerprint_policy_tree(value) != fingerprint_policy_tree(policy(group(children=(atomic(), other_inner))))


@pytest.mark.parametrize("factory", [atomic, resident, birth, group])
def test_rule_or_group_id_is_part_of_snapshot(factory):
    root = factory()
    assert fingerprint_policy_tree(policy(root)) != fingerprint_policy_tree(policy(replace(root, rule_id="OTHER_ID")))


@pytest.mark.parametrize("changes", [
    {"value": 20}, {"operator": Operator.LTE},
    {"field": Field.HOUSEHOLD_INCOME, "fact_basis": FactBasis("SYNTH", "household", "month", 2026, "KRW")},
])
def test_atomic_semantic_fields_change_digest(changes):
    root = atomic()
    assert fingerprint_policy_tree(policy(root)) != fingerprint_policy_tree(policy(replace(root, **changes)))


@pytest.mark.parametrize("name,new_value", [
    ("basis", "SYNTH-OTHER"), ("subject", "individual"), ("period", "year"),
    ("reference_year", 2027), ("unit", "SYNTH-UNIT"),
])
def test_all_five_fact_basis_fields_are_included(name, new_value):
    root = income()
    changed = replace(root, fact_basis=replace(root.fact_basis, **{name: new_value}))
    assert fingerprint_policy_tree(policy(root)) != fingerprint_policy_tree(policy(changed))


def test_atomic_scalar_types_and_in_tuple_order_remain_distinct():
    rules = (
        atomic(value=1),
        atomic(field=Field.REGION, operator=Operator.EQ, value="1"),
        atomic(field=Field.STUDENT_STATUS, operator=Operator.EQ, value=True),
    )
    assert [type(domain._build_rule_node_payload(rule)["value"]) for rule in rules] == [int, str, bool]
    assert len({fingerprint_policy_tree(policy(rule)) for rule in rules}) == 3
    root = atomic(field=Field.REGION, operator=Operator.IN, value=("SEOUL", "GYEONGGI", "SEOUL"))
    assert domain._build_rule_node_payload(root)["value"] == ["SEOUL", "GYEONGGI", "SEOUL"]
    assert fingerprint_policy_tree(policy(root)) != fingerprint_policy_tree(
        policy(replace(root, value=("GYEONGGI", "SEOUL", "SEOUL")))
    )


def test_resident_region_changes_and_current_reference_source_is_explicit():
    first = resident()
    other = resident(required_region=RegionRef("GYEONGGI", "SUWON"))
    assert fingerprint_policy_tree(policy(first)) != fingerprint_policy_tree(policy(other))
    assert domain._build_rule_node_payload(first)["reference_date_source"] == "APPLICATION_DATE"
    assert domain._build_rule_node_payload(first)["required_region"] == {"sido": "SEOUL", "sigungu": "JONGNO"}


@pytest.mark.parametrize("changes", [
    {"min_birth_date": date(2000, 1, 2)}, {"max_birth_date": date(2001, 1, 2)},
])
def test_birth_boundaries_change_digest(changes):
    first = birth()
    assert fingerprint_policy_tree(policy(first)) != fingerprint_policy_tree(policy(replace(first, **changes)))


@pytest.mark.parametrize("factory", [atomic, resident, birth])
@pytest.mark.parametrize("refs", [
    ("SYNTH-SRC#a", "SYNTH-SRC#b"),
    ("SYNTH-SRC#b", "SYNTH-SRC#a"),
    ("SYNTH-SRC#a", "SYNTH-SRC#a"),
])
def test_evidence_addition_order_and_duplicates_are_preserved(factory, refs):
    root = factory()
    changed = replace(root, evidence_refs=refs)
    assert domain._build_rule_node_payload(changed)["evidence_refs"] == list(refs)
    assert fingerprint_policy_tree(policy(root)) != fingerprint_policy_tree(policy(changed))
    if len(set(refs)) == 2:
        assert fingerprint_policy_tree(policy(changed)) != fingerprint_policy_tree(
            policy(replace(changed, evidence_refs=tuple(reversed(refs))))
        )


@pytest.mark.parametrize("field,value", [("rule_version", "r0002"), ("policy_id", "SYNTH-OTHER-POLICY")])
def test_policy_identity_and_rule_version_are_included(field, value):
    original = policy()
    assert fingerprint_policy_tree(original) != fingerprint_policy_tree(replace(original, **{field: value}))


def test_policy_text_is_preserved_without_imposing_envelope_version_syntax():
    value = policy(rule_version=" custom version ", policy_id=" SYNTH-POLICY ")
    payload = domain._build_policy_tree_payload(value)
    assert payload["rule_version"] == " custom version " and payload["policy_id"] == " SYNTH-POLICY "


def test_excluded_display_name_and_valid_flags_do_not_change_digest():
    original = policy()
    changed_name = replace(original, policy_name="다른 표시명")
    # 실제 정책 자료가 아닌 메모리상 합성 metadata 비교이며 운영 승인과 무관하다.
    changed_flags = policy(synthetic=False, test_only=False, allow_real_data=True)
    assert fingerprint_policy_tree(original) == fingerprint_policy_tree(changed_name) == fingerprint_policy_tree(changed_flags)
    assert set(domain._build_policy_tree_payload(original)) == {"fingerprint_schema", "policy_id", "rule_version", "root"}


def test_korean_string_is_utf8_without_normalization(monkeypatch):
    nfc = "서울 조건"
    nfd = unicodedata.normalize("NFD", nfc)
    value = policy(atomic(field=Field.REGION, operator=Operator.EQ, value=nfc))
    seen = []
    real_sha256 = domain.hashlib.sha256
    def spy_sha256(data):
        seen.append(data)
        return real_sha256(data)
    monkeypatch.setattr(domain.hashlib, "sha256", spy_sha256)
    digest = fingerprint_policy_tree(value)
    assert nfc.encode("utf-8") in seen[0] and b"\\u" not in seen[0]
    assert digest != fingerprint_policy_tree(policy(atomic(field=Field.REGION, operator=Operator.EQ, value=nfd)))


class PolicySubclass(Policy):
    pass


class FakeNode:
    def to_dict(self):
        pytest.fail("미지원 객체의 generic serializer를 호출했습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "SYNTH", 1, True, FakeNode(), atomic(), group()])
def test_wrong_policy_input_is_rejected_without_conversion(bad):
    with pytest.raises(PolicyDataError, match="policy"):
        fingerprint_policy_tree(bad)


def test_policy_subclass_is_rejected():
    value = PolicySubclass("SYNTH-POLICY", "SYNTHETIC", "r0001", atomic())
    with pytest.raises(PolicyDataError):
        fingerprint_policy_tree(value)


@pytest.mark.parametrize("bad", [None, {}, [], (), "SYNTH", 1, True, FakeNode()])
def test_private_node_helper_fails_closed_on_unsupported_type(bad):
    with pytest.raises(PolicyDataError, match="RuleNode"):
        domain._build_rule_node_payload(bad)


@pytest.mark.parametrize("factory", [atomic, resident, birth, group])
def test_node_subclasses_do_not_gain_automatic_support(factory):
    original = factory()
    subtype = type("SyntheticNodeSubclass", (type(original),), {})
    from dataclasses import fields
    value = subtype(**{field.name: getattr(original, field.name) for field in fields(original)})
    with pytest.raises(PolicyDataError):
        domain._build_rule_node_payload(value)


def test_api_has_one_required_parameter_and_no_semantic_options():
    signature = inspect.signature(fingerprint_policy_tree)
    assert list(signature.parameters) == ["policy"]
    assert signature.parameters["policy"].default is inspect.Parameter.empty
    for extra in ("include_evidence", "sort_children", "ignore_rule_version"):
        with pytest.raises(TypeError):
            fingerprint_policy_tree(policy(), **{extra: True})


def test_canonical_json_recipe_is_shared_with_inventory(monkeypatch):
    calls = []
    real_dumps = domain.json.dumps
    def spy_dumps(payload, **kwargs):
        calls.append(kwargs)
        return real_dumps(payload, **kwargs)
    monkeypatch.setattr(domain.json, "dumps", spy_dumps)
    assert fingerprint_policy_tree(policy()) == TREE_GOLDEN[0][3]
    assert calls == [dict(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)]
    # 두 public 함수가 같은 private encoder를 호출하는지 AST로 확인한다.
    for function in (domain.fingerprint_policy_tree, domain.fingerprint_condition_inventory):
        tree = ast.parse(inspect.getsource(function))
        assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == "_digest_payload" for node in ast.walk(tree))


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_canonical_json_failure_is_data_error_without_payload_leak(error_type, monkeypatch):
    value = policy()
    def fail(*args, **kwargs):
        raise error_type("SYNTH-private-payload")
    monkeypatch.setattr(domain.json, "dumps", fail)
    with pytest.raises(PolicyDataError) as caught:
        fingerprint_policy_tree(value)
    assert "SYNTH-private" not in str(caught.value)


def test_strict_utf8_failure_is_data_error_without_replacement():
    value = policy(atomic(field=Field.REGION, operator=Operator.EQ, value="SYNTH-private-" + chr(0xD800)))
    with pytest.raises(PolicyDataError) as caught:
        fingerprint_policy_tree(value)
    assert "SYNTH-private" not in str(caught.value)


def test_100_repeats_preserve_policy_tree_and_all_input_objects():
    children = (atomic(), resident(), birth(), group(GroupOperator.NOT, (student(),), "NOT_B"))
    original = policy(group(children=children))
    before = domain._build_policy_tree_payload(original)
    digest = fingerprint_policy_tree(original)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    for _ in range(100):
        assert fingerprint_policy_tree(original) == digest
        assert domain._build_policy_tree_payload(original) == before
    assert original.root.children is children
    assert all(left is right for left, right in zip(original.root.children, children))
    copy = domain._build_policy_tree_payload(original)
    copy["root"]["children"][1]["required_region"]["sido"] = "CHANGED"
    copy["root"]["children"][0]["evidence_refs"].clear()
    assert domain._build_policy_tree_payload(original) == before


def test_no_generic_serialization_revalidation_or_external_state(monkeypatch):
    original = policy(group(children=(atomic(), resident(), birth())))
    def forbidden(*args, **kwargs):
        pytest.fail("지문 계산에서 generic serializer·재검증·외부 조회를 호출했습니다")
    monkeypatch.setattr("backend.policy_engine.models._jsonable", forbidden)
    monkeypatch.setattr("backend.policy_engine.models.walk_nodes", forbidden)
    for node_type in (Policy, PolicyRule, RuleGroup, ResidentRegistrationRule, BirthDateRule, RegionRef):
        monkeypatch.setattr(node_type, "__post_init__", forbidden)
    for node_type in (ResidentRegistrationRule, BirthDateRule, RegionRef):
        monkeypatch.setattr(node_type, "to_dict", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("os.getenv", forbidden)
    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint_policy_tree(original))


def test_no_user_review_subtree_api_or_time_dependencies():
    tree = ast.parse(inspect.getsource(domain))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"UserProfile", "BirthFact", "ResidentRegistrationFact", "EvaluationFacts",
                        "EvaluationContext", "PolicyEvaluation", "CashflowInput", "InventoryCompletenessReview",
                        "ImplementationBindingReview", "CoverageReviewContext", "CoverageResult"}
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"today", "now", "getenv", "exists"} for node in ast.walk(tree))
    assert callable(domain.fingerprint_rule_subtree)

