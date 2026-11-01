import json
from copy import deepcopy
from dataclasses import replace

import pytest

from backend.policy_engine import Field, GroupOperator, Operator, PolicyDataError, PolicyFact, PolicyRule, ProfileValidationError, RuleGroup, UserProfile, load_policy_set, load_profile, parse_policy_set, parse_profile


@pytest.fixture
def raw_data(policy_data_path):
    return json.loads(policy_data_path.read_text(encoding="utf-8"))


def load_bad_json(tmp_path, data):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return load_policy_set(path)


@pytest.mark.parametrize("operator", ["ALL", "ANY", "NOT"])
def test_empty_group_rejected_at_load(operator, raw_data, tmp_path):
    root = raw_data["policies"][0]["root"]
    root["operator"] = operator
    root["children"] = []
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


def test_not_with_multiple_children_rejected(raw_data, tmp_path):
    raw_data["policies"][0]["root"]["operator"] = "NOT"
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("operator", ["gt", "contains", "__import__('os')", None, 0, ["eq"]])
def test_unknown_operator_rejected(operator, raw_data, tmp_path):
    raw_data["policies"][1]["root"]["operator"] = operator
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("operator", ["AND", "", None, False])
def test_unknown_group_operator_rejected(operator, raw_data, tmp_path):
    raw_data["policies"][0]["root"]["operator"] = operator
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("duplicate_location", ["sibling", "parent", "other_policy"])
def test_duplicate_rule_ids_rejected(duplicate_location, raw_data, tmp_path):
    root = raw_data["policies"][0]["root"]
    duplicate = root["children"][0]["rule_id"]
    if duplicate_location == "sibling":
        root["children"][1]["rule_id"] = duplicate
    elif duplicate_location == "parent":
        root["rule_id"] = duplicate
    else:
        raw_data["policies"][1]["root"]["rule_id"] = duplicate
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("value", ["19", True, False, 19.0, None, [], {}, -1])
def test_wrong_numeric_rule_value_rejected(value, raw_data, tmp_path):
    raw_data["policies"][0]["root"]["children"][0]["value"] = value
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("value", [[], ["안산시", False], [None], "안산시", {"a": 1}])
def test_invalid_in_candidates_rejected(value, raw_data, tmp_path):
    rule = raw_data["policies"][0]["root"]["children"][2]
    rule.update(operator="in", value=value)
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


def test_in_loads_as_immutable_tuple(raw_data):
    rule = raw_data["policies"][0]["root"]["children"][2]
    rule.update(operator="in", value=["안산시", "수원시"])
    loaded = parse_policy_set(raw_data)
    assert loaded.policies[0].root.children[2].value == ("안산시", "수원시")


@pytest.mark.parametrize("field", ["monthly_income", "arbitrary", None, 123])
def test_unregistered_field_rejected(field, raw_data, tmp_path):
    raw_data["policies"][1]["root"]["field"] = field
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("field", ["region", "student_status"])
def test_order_comparison_for_non_numeric_field_rejected(field, raw_data, tmp_path):
    rule = raw_data["policies"][1]["root"]
    rule.update(field=field, operator="gte", value="안산시" if field == "region" else False)
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("basis", [None, {}, {"basis": "only_one_key"}])
def test_income_rule_requires_complete_basis(basis, raw_data, tmp_path):
    raw_data["policies"][2]["root"]["children"][1]["fact_basis"] = basis
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("flag", [False, 1, "true", None])
def test_synthetic_flags_are_explicit_booleans(flag, raw_data, tmp_path):
    raw_data["policies"][0]["test_only"] = flag
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("location", ["dataset", "policy", "rule"])
def test_unknown_keys_rejected(location, raw_data, tmp_path):
    target = {"dataset": raw_data, "policy": raw_data["policies"][0], "rule": raw_data["policies"][1]["root"]}[location]
    target["typo"] = "ignored?"
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


def test_duplicate_policy_id_rejected(raw_data, tmp_path):
    raw_data["policies"][1]["policy_id"] = "SAMPLE-001"
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)


@pytest.mark.parametrize("content", ["", "{", "[]", "null", '{"schema_version":"m1.0","schema_version":"m1.0"}'])
def test_bad_json_rejected(content, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(PolicyDataError):
        load_policy_set(path)


@pytest.mark.parametrize("data", [
    {"age": True}, {"age": 24.0}, {"age": "24"}, {"age": -1},
    {"region": 0}, {"region": False}, {"region": " "},
    {"student_status": 0}, {"student_status": 1}, {"student_status": "false"},
    {"employment_status": "student"}, {"employment_status": False},
    {"monthly_income": False}, {"monthly_income": "100"}, {"monthly_income": -1},
    {"household_income": 100}, {"policy_facts": None},
    {"policy_facts": [{"field": "household_income", "value": False}]},
    {"policy_facts": [{"field": "household_income", "value": "0"}]},
])
def test_invalid_profile_never_becomes_unknown(data):
    with pytest.raises(ProfileValidationError):
        parse_profile(data)


def test_profile_file_validation(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text('{"age": false}', encoding="utf-8")
    with pytest.raises(ProfileValidationError):
        load_profile(path)


def test_duplicate_profile_fact_rejected():
    with pytest.raises(ProfileValidationError):
        parse_profile({"policy_facts": [
            {"field": "household_income", "value": 0},
            {"field": "household_income", "value": None},
        ]})


def test_direct_construction_also_validates(profile, policy_set):
    with pytest.raises(ProfileValidationError):
        UserProfile(age=False)
    with pytest.raises(ProfileValidationError):
        UserProfile(policy_facts=[])
    with pytest.raises(ProfileValidationError):
        PolicyFact(Field.HOUSEHOLD_INCOME, False)
    with pytest.raises(PolicyDataError):
        PolicyRule("BAD", Field.AGE, Operator.GTE, True, evidence_refs=("synthetic:test",))
    with pytest.raises(PolicyDataError):
        RuleGroup("BAD", GroupOperator.ALL, ())
    with pytest.raises(PolicyDataError):
        replace(policy_set.policies[0], synthetic=False)


def test_parsing_does_not_mutate_raw_data(raw_data):
    before = deepcopy(raw_data)
    parse_policy_set(raw_data)
    assert raw_data == before


def test_bad_rule_late_in_dataset_rejects_entire_load(raw_data, tmp_path):
    raw_data["policies"][2]["root"]["children"][1]["value"] = False
    with pytest.raises(PolicyDataError):
        load_bad_json(tmp_path, raw_data)
