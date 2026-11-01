"""m1.1 합성 JSON의 엄격한 로딩과 기존 단일 Policy routing 통합."""

from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from backend.policy_engine import (
    EvaluationContext, EvaluationFacts, Field, GroupOperator, Operator, Policy,
    PolicyDataError, PolicyReferenceContext, PolicyRule, PolicySet, ReferenceDateSource,
    ResidentRegistrationRule, RuleGroup, Status, UserProfile, evaluate_policy_tree,
    load_policy_set, parse_policy_set,
)
from backend.policy_engine.facts import RegionRef, RegistrationSource, ResidentRegistrationFact
from backend.policy_engine.models import walk_nodes


ROOT = Path(__file__).resolve().parents[1]
M11_PATH = ROOT / "data/synthetic/policies_m11.json"
DAY = date(2026, 11, 10)
ANSAN = RegionRef("GYEONGGI", "ANSAN")
SUWON = RegionRef("GYEONGGI", "SUWON")


@pytest.fixture
def raw():
    return json.loads(M11_PATH.read_text(encoding="utf-8"))


def root(raw):
    return raw["policies"][0]["root"]


def resident_node(raw):
    return root(raw)["children"][1]


def hand_built_policy():
    # M1.6H와 같은 독립 Python 구성. 로더나 JSON에서 기대 트리를 생성하지 않는다.
    age = PolicyRule("AGE", Field.AGE, Operator.GTE, 19, evidence_refs=("synthetic:AGE",))
    resident = ResidentRegistrationRule("RESIDENT", ANSAN, ReferenceDateSource.APPLICATION_DATE, ("synthetic:resident",))
    student = PolicyRule("STUDENT", Field.STUDENT_STATUS, Operator.EQ, True, evidence_refs=("synthetic:STUDENT",))
    employment = PolicyRule("UNEMPLOYED", Field.EMPLOYMENT_STATUS, Operator.EQ, "unemployed", evidence_refs=("synthetic:UNEMPLOYED",))
    choices = RuleGroup("LIFE", GroupOperator.ANY, (student, employment))
    return Policy("SYN_MIX", "합성 혼합 트리", "synthetic-1", RuleGroup("ROOT", GroupOperator.ALL, (age, resident, choices)))


def test_loaded_tree_matches_hand_built_tree_and_order():
    value = load_policy_set(M11_PATH)
    assert value.schema_version == "m1.1" and value.synthetic is True and value.test_only is True
    assert value.policies == (hand_built_policy(),)
    assert [n.rule_id for n in walk_nodes(value.policies[0].root)] == ["ROOT", "AGE", "RESIDENT", "LIFE", "STUDENT", "UNEMPLOYED"]
    resident = value.policies[0].root.children[1]
    assert type(resident.required_region) is RegionRef
    assert resident.reference_date_source is ReferenceDateSource.APPLICATION_DATE
    assert resident.evidence_refs == ("synthetic:resident",)


@pytest.mark.parametrize(("region", "application_date", "expected", "missing"), [
    (ANSAN, DAY, Status.PASS, ()),
    (SUWON, DAY, Status.FAIL, ()),
    (None, DAY, Status.UNKNOWN, ("resident_registration",)),
    (ANSAN, None, Status.UNKNOWN, ("reference_date",)),
])
def test_loader_routing_scenarios_equal_hand_built(region, application_date, expected, missing):
    loaded = load_policy_set(M11_PATH)
    facts = EvaluationFacts(() if region is None else (ResidentRegistrationFact(region, DAY, RegistrationSource.SELF_REPORTED),))
    profile = UserProfile(age=24, student_status=True, employment_status="employed")
    context = EvaluationContext(DAY, loaded.dataset_version)
    reference = PolicyReferenceContext("SYN_MIX", application_date)
    actual = evaluate_policy_tree(profile, loaded.policies[0], context, facts=facts, reference_context=reference)
    expected_tree_result = evaluate_policy_tree(profile, hand_built_policy(), context, facts=facts, reference_context=reference)
    assert actual.overall_status is expected and actual.missing_fields == missing
    assert actual == expected_tree_result
    assert actual.to_dict() == expected_tree_result.to_dict()


@pytest.mark.parametrize("operator,value", [("eq",19), ("in",[19,24]), ("gte",19), ("lte",34)])
def test_m11_atomic_parser_reuses_legacy_semantics(raw, operator, value):
    atom = root(raw)["children"][0]
    atom["operator"], atom["value"] = operator, value
    raw["policies"][0]["root"] = atom
    loaded = parse_policy_set(raw).policies[0].root
    assert loaded == PolicyRule("AGE", Field.AGE, Operator(operator), tuple(value) if operator=="in" else value,
                                evidence_refs=("synthetic:AGE",))


def test_atomic_only_m11_and_m10_share_fact_basis_parser(raw):
    old = json.loads((ROOT / "data/synthetic/policies.json").read_text(encoding="utf-8"))
    legacy = old["policies"][2]["root"]["children"][1]
    raw["policies"][0]["root"] = {**deepcopy(legacy), "rule_type": "atomic"}
    assert parse_policy_set(raw).policies[0].root == load_policy_set(ROOT / "data/synthetic/policies.json").policies[2].root.children[1]


@pytest.mark.parametrize("bad", [None, "unknown", "group", "", 1, [], {}])
def test_invalid_or_missing_leaf_rule_type(raw, bad):
    resident_node(raw)["rule_type"] = bad
    with pytest.raises(PolicyDataError, match="rule_type"):
        parse_policy_set(raw)


def test_missing_leaf_rule_type_does_not_infer_from_region(raw):
    del resident_node(raw)["rule_type"]
    with pytest.raises(PolicyDataError, match="rule_type"):
        parse_policy_set(raw)


def test_required_region_missing(raw):
    del resident_node(raw)["required_region"]
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("region", [
    None, "안산", "안산시", "경기도 안산시", ["ANSAN"],
    {"sido":"UNKNOWN", "sigungu":"ANSAN"}, {"sido":"GYEONGGI", "sigungu":"UNKNOWN"},
    {"sido":"SEOUL", "sigungu":"ANSAN"}, {"sido":"GYEONGGI", "sigungu":None},
    {"sido":123, "sigungu":"ANSAN"}, {"sido":"GYEONGGI"},
    {"sido":"GYEONGGI", "sigungu":"ANSAN", "name":"alias"},
])
def test_invalid_region_or_alias_rejected(raw, region):
    resident_node(raw)["required_region"] = region
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("source", [None, "application_date", "APPLICATION_REFERENCE_DATE", "EVALUATION_DATE", "FIXED_DATE", "SYSTEM_TODAY", 1, []])
def test_unsupported_reference_source_no_fallback(raw, source):
    resident_node(raw)["reference_date_source"] = source
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("refs", [None, "synthetic:resident", 1, [], [None], [True], [123], [""], ["synthetic:ref", 1]])
def test_invalid_evidence_refs(raw, refs):
    resident_node(raw)["evidence_refs"] = refs
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("operator,children", [("ALL",[]), ("ANY",[]), ("NOT",[]), ("NOT",[0,1]), ("X",[0]), (None,[0])])
def test_group_operator_and_child_count(raw, operator, children):
    original = root(raw)["children"]
    root(raw)["operator"] = operator
    root(raw)["children"] = [original[i] for i in children]
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


def test_not_specialized_and_nested_mixed_group_supported(raw):
    selected = deepcopy(resident_node(raw))
    raw["policies"][0]["root"] = {"kind":"group", "rule_id":"NOT", "operator":"NOT", "children":[selected]}
    value = parse_policy_set(raw).policies[0].root
    assert value.operator is GroupOperator.NOT
    assert type(value.children[0]) is ResidentRegistrationRule


@pytest.mark.parametrize("location", ["atomic_resident", "nested", "parent", "other_policy"])
def test_duplicate_ids_across_all_node_types_and_policies(raw, location):
    if location == "atomic_resident":
        resident_node(raw)["rule_id"] = root(raw)["children"][0]["rule_id"]
    elif location == "nested":
        root(raw)["children"][2]["children"][0]["rule_id"] = resident_node(raw)["rule_id"]
    elif location == "parent":
        resident_node(raw)["rule_id"] = root(raw)["rule_id"]
    else:
        other = deepcopy(raw["policies"][0])
        other["policy_id"] = "SYN_OTHER"
        raw["policies"].append(other)
    with pytest.raises(PolicyDataError, match="rule_id"):
        parse_policy_set(raw)


@pytest.mark.parametrize("level", ["envelope", "policy", "group", "atomic", "resident", "region"])
def test_unknown_extra_fields_rejected_at_every_level(raw, level):
    targets = {"envelope":raw, "policy":raw["policies"][0], "group":root(raw),
               "atomic":root(raw)["children"][0], "resident":resident_node(raw),
               "region":resident_node(raw)["required_region"]}
    targets[level]["unexpected"] = "not-ignored"
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("value", ["19", True, 19.0, None, [19]])
def test_no_numeric_coercion(raw, value):
    root(raw)["children"][0]["value"] = value
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("child", [None, 1, "resident", [], {"rule_type":"resident_registration"}])
def test_malformed_nested_child(raw, child):
    root(raw)["children"][2]["children"][0] = child
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("version", ["m1.2", "", "M1.1", None, 1, True, [], {}])
def test_invalid_version_checked_before_rule_parsing(raw, version):
    raw["schema_version"] = version
    raw["policies"][0]["root"] = None
    with pytest.raises(PolicyDataError, match="schema_version"):
        parse_policy_set(raw)


def test_missing_version_is_explicit_error(raw):
    del raw["schema_version"]
    with pytest.raises(PolicyDataError, match="schema_version"):
        parse_policy_set(raw)


@pytest.mark.parametrize("version", ["m1.0", "m1.1"])
def test_domain_policy_set_supports_exact_versions(raw, version):
    r = hand_built_policy() if version == "m1.1" else Policy("SYN_A","합성","1",PolicyRule("A",Field.AGE,Operator.EQ,24,evidence_refs=("synthetic:A",)))
    assert PolicySet(version, "synthetic-domain", (r,)).schema_version == version


def test_m10_rejects_specialized_without_schema_upgrade(raw):
    selected = deepcopy(resident_node(raw))
    raw["schema_version"] = "m1.0"
    raw["policies"][0]["root"] = selected
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


def test_m11_does_not_fallback_to_legacy_atomic_shape(raw):
    del root(raw)["children"][0]["rule_type"]
    with pytest.raises(PolicyDataError, match="rule_type"):
        parse_policy_set(raw)


def test_m10_still_rejects_rule_type_extra_key():
    raw = json.loads((ROOT / "data/synthetic/policies.json").read_text(encoding="utf-8"))
    raw["policies"][0]["root"]["children"][0]["rule_type"] = "atomic"
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


def test_group_uses_explicit_kind_and_rejects_rule_type_extra(raw):
    root(raw)["rule_type"] = "group"
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


@pytest.mark.parametrize("key", ["synthetic", "test_only"])
def test_real_data_flags_not_enabled(raw, key):
    raw[key] = False
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)
    raw[key] = True
    raw["policies"][0][key] = False
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)


def test_no_partial_load_or_input_mutation(raw):
    invalid = deepcopy(raw["policies"][0])
    invalid["policy_id"] = "SYN_INVALID"
    invalid["root"] = {"kind":"rule", "rule_type":"unknown"}
    raw["policies"].append(invalid)
    before = deepcopy(raw)
    with pytest.raises(PolicyDataError):
        parse_policy_set(raw)
    assert raw == before


def test_file_duplicate_keys_and_invalid_json_are_errors(tmp_path):
    path = tmp_path / "synthetic-invalid.json"
    for content in ['{"schema_version":"m1.1","schema_version":"m1.0"}', '{', 'null']:
        path.write_text(content,encoding="utf-8")
        with pytest.raises(PolicyDataError):
            load_policy_set(path)


def test_same_json_produces_equal_domain_and_keeps_child_order(raw):
    before = deepcopy(raw)
    first, second = parse_policy_set(raw), load_policy_set(M11_PATH)
    assert first == second
    assert raw == before
    assert first.policies[0].root.children[0].rule_id == "AGE"
    assert isinstance(first.policies[0].root.children, tuple)
