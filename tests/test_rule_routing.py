"""단일 합성 mixed tree routing. 실제 정책/새 JSON 형식은 사용하지 않는다."""

from dataclasses import asdict, replace
from datetime import date
from itertools import permutations
import json

import pytest

from backend.policy_engine import (
    ContextValidationError, EvaluationContext, EvaluationFacts, Field, GroupOperator,
    Operator, Policy, PolicyDataError, PolicyReferenceContext, PolicyRule, ProfileValidationError,
    ReasonCode, ReferenceDateSource, ResidentRegistrationRule, RuleGroup, Status, UserProfile,
    evaluate_policy, evaluate_policy_tree,
)
from backend.policy_engine import routing
from backend.policy_engine.facts import RegionRef, RegistrationSource, ResidentRegistrationFact, ResidentRegistrationValidationError
from backend.policy_engine.resolvers.resident_registration import ResidentRegistrationReasonCode as RR
from backend.policy_engine.result_types import RegionSnapshot, ResultValidationError


DAY = date(2026, 11, 10)
ANSAN = RegionRef("GYEONGGI", "ANSAN")
SUWON = RegionRef("GYEONGGI", "SUWON")
CTX = EvaluationContext(DAY, "synthetic-routing-1")
REF = PolicyReferenceContext("SYN_MIX", DAY)
USER = UserProfile(age=24, region="안산시", student_status=True, employment_status="employed")


def fact(region=ANSAN, day=DAY, source=RegistrationSource.SELF_REPORTED):
    return ResidentRegistrationFact(region, day, source)


def resident():
    return ResidentRegistrationRule("RESIDENT", ANSAN, ReferenceDateSource.APPLICATION_DATE, ("synthetic:resident",))


def atom(rule_id="AGE", operator=Operator.GTE, value=19, field=Field.AGE):
    return PolicyRule(rule_id, field, operator, value, evidence_refs=(f"synthetic:{rule_id}",))


def policy(root):
    return Policy("SYN_MIX", "합성 혼합 트리", "synthetic-1", root)


def mixed_policy():
    choices = RuleGroup("LIFE", GroupOperator.ANY, (
        atom("STUDENT", Operator.EQ, True, Field.STUDENT_STATUS),
        atom("UNEMPLOYED", Operator.EQ, "unemployed", Field.EMPLOYMENT_STATUS),
    ))
    return policy(RuleGroup("ROOT", GroupOperator.ALL, (atom(), resident(), choices)))


def run(root, *, profile=USER, facts=(fact(),), reference=REF, context=CTX):
    return evaluate_policy_tree(profile, policy(root), context,
                                facts=EvaluationFacts(facts), reference_context=reference)


@pytest.mark.parametrize(("age", "facts", "expected", "resident_status"), [
    (24, (fact(),), Status.PASS, Status.PASS),
    (24, (fact(SUWON),), Status.FAIL, Status.FAIL),
    (24, (), Status.UNKNOWN, Status.UNKNOWN),
    (18, (), Status.FAIL, Status.UNKNOWN),
])
def test_four_required_mixed_scenarios(age, facts, expected, resident_status):
    p = mixed_policy()
    output = evaluate_policy_tree(replace(USER, age=age), p, CTX,
                                  facts=EvaluationFacts(facts), reference_context=REF)
    assert output.overall_status is expected
    assert [r.rule_id for r in output.rule_results] == ["ROOT", "AGE", "RESIDENT", "LIFE", "STUDENT", "UNEMPLOYED"]
    assert output.rule_results[2].status is resident_status
    assert output.rule_results[3].status is Status.PASS
    assert output.context is CTX and output.rule_version == p.rule_version
    assert output.reason_codes == tuple(sorted(set(output.reason_codes), key=lambda code: code.value))


@pytest.mark.parametrize(("facts", "reference", "status", "reason", "missing"), [
    ((fact(),), REF, Status.PASS, RR.RESIDENT_REGION_MATCH, ()),
    ((fact(SUWON),), REF, Status.FAIL, RR.RESIDENT_REGION_MISMATCH, ()),
    ((), REF, Status.UNKNOWN, RR.RESIDENT_REGISTRATION_MISSING, ("resident_registration",)),
    ((fact(),), PolicyReferenceContext("SYN_MIX"), Status.UNKNOWN, RR.RESIDENT_REFERENCE_DATE_MISSING, ("reference_date",)),
    ((fact(day=date(2026, 11, 11)),), PolicyReferenceContext("SYN_MIX", date(2026, 11, 11)), Status.UNKNOWN, RR.RESIDENT_REFERENCE_DATE_IN_FUTURE, ()),
    ((fact(region=None),), REF, Status.UNKNOWN, RR.RESIDENT_REGION_MISSING, ("resident_registration.region",)),
    ((fact(day=None),), REF, Status.UNKNOWN, RR.RESIDENT_REGISTRATION_DATE_MISSING, ("resident_registration.as_of_date",)),
    ((fact(day=date(2026, 10, 1)),), REF, Status.UNKNOWN, RR.RESIDENT_REGISTRATION_DATE_UNPROVEN, ()),
])
def test_all_resident_reasons_flow_through_router(facts, reference, status, reason, missing):
    output = run(resident(), facts=facts, reference=reference)
    leaf = output.rule_results[0]
    assert leaf.status is status and leaf.reason_code is reason
    assert leaf.missing_fields == missing
    assert leaf.evidence_refs == ("synthetic:resident",)
    assert leaf.details.reference_date == reference.application_date


@pytest.mark.parametrize("source", list(RegistrationSource))
def test_policy_and_user_evidence_preserved_separately(source):
    leaf = run(resident(), facts=(fact(source=source),)).rule_results[0]
    assert leaf.status is Status.PASS
    assert leaf.evidence_refs == ("synthetic:resident",)
    assert leaf.evaluated_value == RegionSnapshot("GYEONGGI", "ANSAN")
    assert leaf.expected_condition.required_region == RegionSnapshot("GYEONGGI", "ANSAN")
    evidence = leaf.details.evidence[0]
    assert evidence.source is source and evidence.fact_as_of_date == DAY
    assert evidence.region == leaf.evaluated_value
    assert evidence.field_path == "resident_registration.region"


# 기대값은 구현의 집계기에서 생성하지 않는다.
TRUTH = [
    (24, (fact(),), Status.PASS, Status.PASS),
    (24, (fact(SUWON),), Status.FAIL, Status.PASS),
    (24, (), Status.UNKNOWN, Status.PASS),
    (25, (fact(),), Status.FAIL, Status.PASS),
    (25, (fact(SUWON),), Status.FAIL, Status.FAIL),
    (25, (), Status.FAIL, Status.UNKNOWN),
    (None, (fact(),), Status.UNKNOWN, Status.PASS),
    (None, (fact(SUWON),), Status.FAIL, Status.UNKNOWN),
    (None, (), Status.UNKNOWN, Status.UNKNOWN),
]


@pytest.mark.parametrize(("age", "facts", "all_status", "any_status"), TRUTH)
def test_mixed_all_any_truth_tables(age, facts, all_status, any_status):
    for op, expected in ((GroupOperator.ALL, all_status), (GroupOperator.ANY, any_status)):
        output = run(RuleGroup("ROOT", op, (atom(operator=Operator.EQ, value=24), resident())),
                     profile=replace(USER, age=age), facts=facts)
        assert output.overall_status is expected
        assert output.rule_results[0].reason_code.value == f"{op.value}_{expected.value}"
        if not facts:
            assert "resident_registration" in output.missing_fields


@pytest.mark.parametrize(("facts", "leaf_status", "parent_status"), [
    ((fact(),), Status.PASS, Status.FAIL),
    ((fact(SUWON),), Status.FAIL, Status.PASS),
    ((), Status.UNKNOWN, Status.UNKNOWN),
])
def test_not_resident_preserves_original_leaf(facts, leaf_status, parent_status):
    leaf = run(resident(), facts=facts).rule_results[0]
    output = run(RuleGroup("ROOT", GroupOperator.NOT, (resident(),)), facts=facts)
    assert output.overall_status is parent_status
    assert output.rule_results[0].reason_code.value == f"NOT_{parent_status.value}"
    assert output.rule_results[0].details is None
    assert output.rule_results[1] == leaf
    assert leaf.status is leaf_status


@pytest.mark.parametrize("operator", [Operator.EQ, Operator.IN, Operator.GTE, Operator.LTE])
@pytest.mark.parametrize("age", [18, 24, None])
def test_atomic_operators_equal_legacy(operator, age):
    value = (19, 24) if operator is Operator.IN else 24
    p = policy(atom(operator=operator, value=value))
    user = replace(USER, age=age)
    expected = evaluate_policy(user, p, CTX)
    actual = evaluate_policy_tree(user, p, CTX)
    assert actual == expected
    assert actual.to_dict() == expected.to_dict()


@pytest.mark.parametrize("age", [18, 24, None])
def test_atomic_nested_all_any_not_equal_legacy(age):
    inner = RuleGroup("ANY", GroupOperator.ANY, (atom("A", Operator.EQ, 24), atom("B", Operator.EQ, True, Field.STUDENT_STATUS)))
    root = RuleGroup("ROOT", GroupOperator.ALL, (inner, RuleGroup("NOT", GroupOperator.NOT, (atom("C", Operator.LTE, 30),))))
    p, user = policy(root), replace(USER, age=age)
    assert evaluate_policy_tree(user, p, CTX) == evaluate_policy(user, p, CTX)


def test_existing_three_policies_equal_legacy(policy_set, profile, context):
    for p in policy_set.policies:
        expected = evaluate_policy(profile, p, context)
        actual = evaluate_policy_tree(profile, p, context)
        assert actual == expected and actual.to_dict() == expected.to_dict()


@pytest.mark.parametrize("reference", [None, PolicyReferenceContext("SYN_OTHER", DAY), {}, DAY])
def test_missing_or_mismatched_reference_context_is_error(reference):
    with pytest.raises(ContextValidationError):
        run(resident(), reference=reference)


def test_mismatched_provided_context_also_rejected_for_atomic_tree():
    with pytest.raises(ContextValidationError):
        run(atom(), reference=PolicyReferenceContext("SYN_OTHER", DAY))


def test_omitted_facts_become_unknown_without_profile_region_fallback():
    output = evaluate_policy_tree(USER, policy(resident()), CTX, reference_context=REF)
    assert output.overall_status is Status.UNKNOWN
    assert output.rule_results[0].reason_code is RR.RESIDENT_REGISTRATION_MISSING
    assert output.rule_results[0].details.evidence == ()


def test_distinct_dates_and_resolver_adapter_call_order(monkeypatch):
    calls = []
    real_resolve, real_adapt = routing.resolve_resident_registration, routing.adapt_resident_registration_resolution
    reference = PolicyReferenceContext("SYN_MIX", date(2026, 10, 1))
    given = EvaluationFacts((fact(day=date(2026, 10, 1)),))

    def resolve(facts, **kwargs):
        calls.append(("resolver", facts, kwargs))
        result = real_resolve(facts, **kwargs)
        calls.append(("resolution", result))
        return result

    def adapt(**kwargs):
        calls.append(("adapter", kwargs))
        return real_adapt(**kwargs)

    monkeypatch.setattr(routing, "resolve_resident_registration", resolve)
    monkeypatch.setattr(routing, "adapt_resident_registration_resolution", adapt)
    output = evaluate_policy_tree(USER, policy(resident()), CTX, facts=given, reference_context=reference)
    assert [call[0] for call in calls] == ["resolver", "resolution", "adapter"]
    assert calls[0][1] is given.resident_registrations
    assert calls[0][2] == {"required_region": ANSAN, "reference_date": reference.application_date, "evaluation_date": DAY}
    assert calls[2][1]["resolution"] is calls[1][1]
    assert calls[2][1]["rule_id"] == "RESIDENT"
    assert calls[2][1]["evidence_refs"] == resident().evidence_refs
    assert output.overall_status is Status.PASS
    assert output.context.as_of == DAY
    assert output.rule_results[0].details.reference_date == date(2026, 10, 1)


@pytest.mark.parametrize("operator", [GroupOperator.ALL, GroupOperator.ANY])
def test_group_does_not_short_circuit_conflicting_facts(operator):
    # ANY 앞 PASS, ALL 앞 FAIL 모두 뒤의 입력 오류를 숨기지 않는다.
    value = 24 if operator is GroupOperator.ANY else 25
    root = RuleGroup("ROOT", operator, (atom(operator=Operator.EQ, value=value), resident()))
    with pytest.raises(ResidentRegistrationValidationError, match="CONFLICTING_RESIDENT_REGISTRATION_FACTS"):
        run(root, facts=(fact(), fact(SUWON)))


def test_conflict_precedes_missing_application_date():
    with pytest.raises(ResidentRegistrationValidationError, match="CONFLICTING_RESIDENT_REGISTRATION_FACTS"):
        run(resident(), facts=(fact(), fact(SUWON)), reference=PolicyReferenceContext("SYN_MIX"))


def test_unrelated_historical_conflict_still_errors():
    old = date(2026, 1, 1)
    with pytest.raises(ResidentRegistrationValidationError, match="CONFLICTING_RESIDENT_REGISTRATION_FACTS"):
        run(resident(), facts=(fact(), fact(ANSAN, old), fact(SUWON, old)))


def test_adapter_error_propagates_same_exception(monkeypatch):
    expected = ResultValidationError("TEST_ADAPTER_CONTRACT", "test")

    def reject(**kwargs):
        raise expected

    monkeypatch.setattr(routing, "adapt_resident_registration_resolution", reject)
    with pytest.raises(ResultValidationError) as err:
        run(resident())
    assert err.value is expected


@pytest.mark.parametrize(("field", "changed", "code"), [
    ("evaluation_date", date(2026, 11, 9), "RESOLUTION_EVALUATION_DATE_MISMATCH"),
    ("reference_date", None, "RESOLUTION_REFERENCE_DATE_MISMATCH"),
])
def test_returned_date_contract_mismatch_rejected_before_adapter(monkeypatch, field, changed, code):
    real = routing.resolve_resident_registration

    def wrong(*args, **kwargs):
        return replace(real(*args, **kwargs), **{field: changed})

    def should_not_adapt(**kwargs):
        pytest.fail("불일치 결과가 Adapter에 전달됨")

    monkeypatch.setattr(routing, "resolve_resident_registration", wrong)
    monkeypatch.setattr(routing, "adapt_resident_registration_resolution", should_not_adapt)
    with pytest.raises(ResultValidationError) as err:
        run(resident())
    assert (err.value.code, err.value.field) == (code, field)


@pytest.mark.parametrize(("field", "bad", "error"), [
    ("profile", {}, ProfileValidationError), ("policy", object(), PolicyDataError),
    ("context", DAY, ContextValidationError), ("facts", (), ProfileValidationError),
])
def test_invalid_public_input_types(field, bad, error):
    args = dict(profile=USER, policy=policy(resident()), context=CTX,
                facts=EvaluationFacts((fact(),)), reference_context=REF)
    args[field] = bad
    with pytest.raises(error):
        evaluate_policy_tree(**args)


def test_unsupported_node_type_and_binding_fail_without_fallback():
    with pytest.raises(PolicyDataError):
        routing._route_node(USER, object(), CTX, EvaluationFacts(), REF)
    with pytest.raises(PolicyDataError):
        replace(resident(), reference_date_source="EVALUATION_DATE")


def test_legacy_api_explicitly_rejects_specialized_tree():
    with pytest.raises(PolicyDataError):
        evaluate_policy(USER, policy(resident()), CTX)


def test_inputs_unchanged_repeated_result_and_serialization():
    p, given = mixed_policy(), EvaluationFacts((fact(),))
    before = tuple(asdict(item) for item in (USER, p, CTX, REF, given))
    first = evaluate_policy_tree(USER, p, CTX, facts=given, reference_context=REF)
    second = evaluate_policy_tree(USER, p, CTX, facts=given, reference_context=REF)
    assert first == second and repr(first) == repr(second)
    assert json.dumps(first.to_dict(), ensure_ascii=False) == json.dumps(second.to_dict(), ensure_ascii=False)
    assert before == tuple(asdict(item) for item in (USER, p, CTX, REF, given))


def test_meaning_equivalent_fact_order_and_duplicates_deterministic():
    facts = (fact(), fact(source=RegistrationSource.OFFICIAL_DATA), fact())
    results = [run(resident(), facts=order) for order in permutations(facts)]
    assert all(result == results[0] for result in results)
    assert len(results[0].rule_results[0].details.evidence) == 2
