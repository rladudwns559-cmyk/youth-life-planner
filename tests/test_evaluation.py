from dataclasses import FrozenInstanceError, asdict, replace
from datetime import date, datetime

import pytest

from backend.policy_engine import ContextValidationError, EvaluationContext, Field, GroupOperator, Operator, Policy, PolicyFact, PolicyRule, ReasonCode, RuleGroup, Status, UserProfile, evaluate_policies, evaluate_policy, parse_profile


@pytest.mark.parametrize(("age", "expected"), [
    (18, Status.FAIL), (19, Status.PASS), (34, Status.PASS), (35, Status.FAIL), (None, Status.UNKNOWN),
])
def test_age_boundaries(age, expected, policy_set, profile, context):
    assert evaluate_policy(replace(profile, age=age), policy_set.policies[0], context).overall_status is expected


@pytest.mark.parametrize(("region", "expected", "missing"), [
    ("안산시", Status.PASS, ()), ("수원시", Status.FAIL, ()), (None, Status.UNKNOWN, ("region",)),
])
def test_region(region, expected, missing, policy_set, profile, context):
    result = evaluate_policy(replace(profile, region=region), policy_set.policies[0], context)
    assert result.overall_status is expected
    assert result.missing_fields == missing


@pytest.mark.parametrize(("employment", "expected"), [
    ("unemployed", Status.PASS), ("employed", Status.FAIL), (None, Status.UNKNOWN),
])
def test_employment(employment, expected, policy_set, profile, context):
    result = evaluate_policy(replace(profile, employment_status=employment), policy_set.policies[1], context)
    assert result.overall_status is expected
    assert result.missing_fields == (("employment_status",) if employment is None else ())


@pytest.mark.parametrize(("income", "expected"), [
    (2999999, Status.PASS), (3000000, Status.PASS), (3000001, Status.FAIL),
    (0, Status.PASS), (None, Status.UNKNOWN),
])
def test_income_boundaries(income, expected, policy_set, profile, income_basis, context):
    user = replace(profile, policy_facts=(PolicyFact(Field.HOUSEHOLD_INCOME, income, income_basis),))
    result = evaluate_policy(user, policy_set.policies[2], context)
    assert result.overall_status is expected
    assert result.rule_results[-1].evaluated_value == income


@pytest.mark.parametrize("monthly_income", [0, 1500000, 99999999])
def test_living_income_never_substitutes_policy_income(monthly_income, policy_set, profile, context):
    user = replace(profile, monthly_income=monthly_income)
    result = evaluate_policy(user, policy_set.policies[2], context)
    assert result.overall_status is Status.UNKNOWN
    assert result.missing_fields == ("household_income",)


@pytest.mark.parametrize(("field", "changed"), [
    ("basis", "different_basis"), ("subject", "personal"), ("period", "yearly"),
    ("reference_year", 2025), ("unit", "different_unit"),
])
def test_each_income_basis_dimension_must_match(field, changed, policy_set, profile, income_basis, context):
    different = replace(income_basis, **{field: changed})
    user = replace(profile, policy_facts=(PolicyFact(Field.HOUSEHOLD_INCOME, 0, different),))
    result = evaluate_policy(user, policy_set.policies[2], context)
    assert result.overall_status is Status.UNKNOWN
    assert result.rule_results[-1].reason_code is ReasonCode.FACT_BASIS_MISMATCH
    assert result.missing_fields == ("household_income",)


def test_income_without_basis_is_unknown(policy_set, profile, context):
    user = replace(profile, policy_facts=(PolicyFact(Field.HOUSEHOLD_INCOME, 0),))
    result = evaluate_policy(user, policy_set.policies[2], context)
    assert result.overall_status is Status.UNKNOWN
    assert result.rule_results[-1].reason_code is ReasonCode.FACT_BASIS_MISSING


def test_missing_and_explicit_null_are_unknown(policy_set, context):
    missing = parse_profile({"age": 24})
    explicit_null = parse_profile({"age": 24, "region": None})
    for user in (missing, explicit_null):
        result = evaluate_policy(user, policy_set.policies[0], context)
        assert result.overall_status is Status.UNKNOWN
        assert result.missing_fields == ("region",)


@pytest.mark.parametrize(("student", "expected"), [(False, Status.PASS), (True, Status.FAIL), (None, Status.UNKNOWN)])
def test_false_is_a_real_value(student, expected, context):
    rule = PolicyRule("BOOL", Field.STUDENT_STATUS, Operator.EQ, False, evidence_refs=("synthetic:boolean",))
    result = evaluate_policy(UserProfile(student_status=student), Policy("BOOL", "합성", "1", rule), context)
    assert result.overall_status is expected
    assert result.rule_results[0].evaluated_value is student


@pytest.mark.parametrize("student", [True, False, None])
def test_student_and_employment_are_independent(student, policy_set, profile, context):
    user = replace(profile, student_status=student, employment_status="employed")
    assert evaluate_policy(user, policy_set.policies[1], context).overall_status is Status.FAIL


@pytest.mark.parametrize(("field", "candidates", "user", "expected"), [
    (Field.REGION, ("안산시", "수원시"), UserProfile(region="안산시"), Status.PASS),
    (Field.REGION, ("안산시", "수원시"), UserProfile(region="서울시"), Status.FAIL),
    (Field.REGION, ("안산시",), UserProfile(), Status.UNKNOWN),
    (Field.AGE, (0, 19), UserProfile(age=0), Status.PASS),
    (Field.STUDENT_STATUS, (False,), UserProfile(student_status=False), Status.PASS),
])
def test_in_operator(field, candidates, user, expected, context):
    rule = PolicyRule("IN", field, Operator.IN, candidates, evidence_refs=("synthetic:in",))
    assert evaluate_policy(user, Policy("IN", "합성", "1", rule), context).overall_status is expected


# 기대 진리표는 엔진 계산을 재사용하지 않고 명시한다.
TRUTH_TABLE = [
    (Status.PASS, Status.PASS, Status.PASS, Status.PASS),
    (Status.PASS, Status.FAIL, Status.FAIL, Status.PASS),
    (Status.PASS, Status.UNKNOWN, Status.UNKNOWN, Status.PASS),
    (Status.FAIL, Status.PASS, Status.FAIL, Status.PASS),
    (Status.FAIL, Status.FAIL, Status.FAIL, Status.FAIL),
    (Status.FAIL, Status.UNKNOWN, Status.FAIL, Status.UNKNOWN),
    (Status.UNKNOWN, Status.PASS, Status.UNKNOWN, Status.PASS),
    (Status.UNKNOWN, Status.FAIL, Status.FAIL, Status.UNKNOWN),
    (Status.UNKNOWN, Status.UNKNOWN, Status.UNKNOWN, Status.UNKNOWN),
]


def leaf(status, rule_id):
    if status is Status.UNKNOWN:
        return PolicyRule(rule_id, Field.STUDENT_STATUS, Operator.EQ, True, evidence_refs=("synthetic:truth",))
    return PolicyRule(rule_id, Field.AGE, Operator.EQ, 24 if status is Status.PASS else 25, evidence_refs=("synthetic:truth",))


@pytest.mark.parametrize(("left", "right", "expected_all", "expected_any"), TRUTH_TABLE)
def test_all_and_any_truth_table(left, right, expected_all, expected_any, context):
    for operator, expected in ((GroupOperator.ALL, expected_all), (GroupOperator.ANY, expected_any)):
        group = RuleGroup("ROOT", operator, (leaf(left, "LEFT"), leaf(right, "RIGHT")))
        result = evaluate_policy(UserProfile(age=24), Policy("TABLE", "합성", "1", group), context)
        assert result.overall_status is expected
        assert result.rule_results[0].reason_code.value == f"{operator.value}_{expected.value}"
        assert [r.rule_id for r in result.rule_results] == ["ROOT", "LEFT", "RIGHT"]
        assert [r.status for r in result.rule_results[1:]] == [left, right]


@pytest.mark.parametrize(("child", "expected"), [
    (Status.PASS, Status.FAIL), (Status.FAIL, Status.PASS), (Status.UNKNOWN, Status.UNKNOWN),
])
def test_not_truth_table(child, expected, context):
    group = RuleGroup("NOT", GroupOperator.NOT, (leaf(child, "CHILD"),))
    result = evaluate_policy(UserProfile(age=24), Policy("NOT", "합성", "1", group), context)
    assert result.overall_status is expected
    assert result.rule_results[0].reason_code.value == f"NOT_{expected.value}"


def test_nested_rules_preserve_missing_fields_even_when_overall_pass(context):
    inner = RuleGroup("INNER", GroupOperator.ALL, (leaf(Status.PASS, "P"), leaf(Status.UNKNOWN, "U")))
    root = RuleGroup("ROOT", GroupOperator.ANY, (inner, leaf(Status.PASS, "P2")))
    result = evaluate_policy(UserProfile(age=24), Policy("NESTED", "합성", "1", root), context)
    assert result.overall_status is Status.PASS
    assert result.missing_fields == ("student_status",)
    assert [r.rule_id for r in result.rule_results] == ["ROOT", "INNER", "P", "U", "P2"]
    assert result.rule_results[0].evidence_refs == ("synthetic:truth",)


def test_fail_does_not_hide_later_unknown_or_other_missing_fields(policy_set, context):
    user = UserProfile(age=18)
    result = evaluate_policy(user, policy_set.policies[0], context)
    assert result.overall_status is Status.FAIL
    assert result.missing_fields == ("region",)
    income = evaluate_policy(user, policy_set.policies[2], context)
    assert income.missing_fields == ("household_income", "region")


def test_repeatability_and_input_immutability(policy_set, profile, context):
    before = (asdict(profile), asdict(policy_set), asdict(context))
    first = evaluate_policies(profile, policy_set, context)
    second = evaluate_policies(profile, policy_set, context)
    assert first == second
    assert [r.to_dict() for r in first] == [r.to_dict() for r in second]
    assert before == (asdict(profile), asdict(policy_set), asdict(context))
    with pytest.raises(FrozenInstanceError):
        profile.age = 35
    with pytest.raises(FrozenInstanceError):
        policy_set.policies[0].root.children[0].value = 100


def test_nested_fact_is_immutable(income_basis):
    fact = PolicyFact(Field.HOUSEHOLD_INCOME, 0, income_basis)
    user = UserProfile(policy_facts=(fact,))
    with pytest.raises(FrozenInstanceError):
        user.policy_facts[0].value = 100
    with pytest.raises(FrozenInstanceError):
        user.policy_facts[0].fact_basis.unit = "different"


def test_dataset_version_mismatch_rejected(policy_set, profile):
    context = EvaluationContext(date(2026, 10, 20), "different-version")
    with pytest.raises(ContextValidationError):
        evaluate_policies(profile, policy_set, context)


@pytest.mark.parametrize("bad_date", [None, "2026-10-20", datetime(2026, 10, 20)])
def test_explicit_date_is_required(bad_date):
    with pytest.raises(ContextValidationError):
        EvaluationContext(bad_date, "synthetic-v1")
