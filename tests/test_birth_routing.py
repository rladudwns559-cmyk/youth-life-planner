"""합성 메모리 mixed tree의 birth 연결만 검증한다. JSON/실제 정책 자료는 추가하지 않는다."""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from itertools import product
import json

import pytest

from backend.policy_engine import (
    BirthDateRule, ContextValidationError, EvaluationContext, EvaluationFacts,
    Field, GroupOperator, Operator, Policy, PolicyDataError, PolicyReferenceContext,
    PolicyRule, PolicySet, ProfileValidationError, ReferenceDateSource,
    ResidentRegistrationRule, RuleGroup, Status, UserProfile,
    evaluate_birth_date_rule, evaluate_policy, evaluate_policy_tree,
)
from backend.policy_engine.facts import BirthFact, BirthSource, RegionRef, RegistrationSource, ResidentRegistrationFact
from backend.policy_engine.loader import parse_policy_set
from backend.policy_engine.models import walk_nodes
from backend.policy_engine.result_types import BirthDateReasonCode as BR, ResultValidationError


DAY = date(2026, 9, 15)
CTX = EvaluationContext(date(2026, 10, 20), "synthetic-birth-routing")
REF = PolicyReferenceContext("SYNTH-POLICY", DAY)
ANSAN, SUWON = RegionRef("GYEONGGI", "ANSAN"), RegionRef("GYEONGGI", "SUWON")
LOWER, UPPER = date(1998, 1, 10), date(1999, 1, 9)
EVIDENCE = ("synthetic:birth:second", "synthetic:birth:first", "synthetic:birth:second")


def birth(rule_id="B"):
    return BirthDateRule(rule_id, LOWER, UPPER, EVIDENCE)


def atom(rule_id="A"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 18, evidence_refs=("synthetic:age",))


def resident(rule_id="R"):
    return ResidentRegistrationRule(rule_id, ANSAN, ReferenceDateSource.APPLICATION_DATE, ("synthetic:resident",))


def bfact(status=Status.PASS):
    return {Status.PASS: BirthFact(LOWER, BirthSource.SELF_REPORTED),
            Status.FAIL: BirthFact(date(1990, 1, 1), BirthSource.SELF_REPORTED), Status.UNKNOWN: None}[status]


def rfacts(status=Status.PASS):
    if status is Status.UNKNOWN:
        return ()
    return (ResidentRegistrationFact(ANSAN if status is Status.PASS else SUWON, DAY, RegistrationSource.SELF_REPORTED),)


def policy(root):
    return Policy("SYNTH-POLICY", "합성 birth routing", "synthetic-1", root)


def run(root, *, facts=None, profile=None, reference=None, context=CTX):
    return evaluate_policy_tree(profile or UserProfile(age=24), policy(root), context,
                                facts=facts, reference_context=reference)


@pytest.mark.parametrize(("fact", "status", "reason"), [
    (BirthFact(LOWER, BirthSource.SELF_REPORTED), Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (BirthFact(date(1990, 1, 1), BirthSource.SELF_REPORTED), Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
    (BirthFact(date(2010, 1, 1), BirthSource.SELF_REPORTED), Status.FAIL, BR.BIRTH_DATE_AFTER_RANGE),
    (None, Status.UNKNOWN, BR.BIRTH_DATE_MISSING),
    (BirthFact(None, BirthSource.OFFICIAL_DATA), Status.UNKNOWN, BR.BIRTH_DATE_MISSING),
])
def test_birth_root_returns_the_existing_evaluators_complete_result(fact, status, reason):
    root = birth()
    output = run(root, facts=EvaluationFacts(birth=fact))
    assert output.overall_status is status
    assert output.rule_results == (evaluate_birth_date_rule(root, fact),)
    assert output.rule_results[0].reason_code is reason
    assert output.to_dict()["rule_results"] == [evaluate_birth_date_rule(root, fact).to_dict()]


@pytest.mark.parametrize("facts", [None, EvaluationFacts(), EvaluationFacts(birth=None)])
def test_missing_birth_and_age_24_have_no_fallback(facts):
    output = run(birth(), facts=facts, profile=UserProfile(age=24))
    assert output.overall_status is Status.UNKNOWN
    assert output.missing_fields == ("birth.birth_date",)


@pytest.mark.parametrize("age", [None, 23, 25])
def test_birth_in_range_ignores_profile_age(age):
    assert run(birth(), facts=EvaluationFacts(birth=bfact()), profile=UserProfile(age=age)).overall_status is Status.PASS


@pytest.mark.parametrize("bad", ["birth", {}, [], (), 0, True, UserProfile(age=24)])
def test_evaluation_facts_reject_invalid_birth_at_construction(bad):
    with pytest.raises(ProfileValidationError, match="birth"):
        EvaluationFacts(birth=bad)


def test_facts_constructor_snapshot_and_immutability_preserve_existing_compatibility():
    residents = rfacts()
    assert EvaluationFacts(residents).resident_registrations is residents
    assert EvaluationFacts().to_dict() == {"resident_registrations": []}
    assert EvaluationFacts(residents).to_dict() == {"resident_registrations": [residents[0].to_dict()]}
    selected = bfact()
    facts = EvaluationFacts(residents, birth=selected)
    assert facts.birth is selected
    assert facts.to_dict()["birth"] == selected.to_dict()
    assert EvaluationFacts(birth=BirthFact(None, BirthSource.SELF_REPORTED)).to_dict()["birth"]["birth_date"] is None
    with pytest.raises(TypeError):
        EvaluationFacts(residents, selected)
    with pytest.raises(FrozenInstanceError):
        facts.birth = None
    snapshot = facts.to_dict()
    snapshot["birth"]["birth_date"] = "changed"
    assert facts.birth is selected and facts.to_dict()["birth"] == selected.to_dict()


@pytest.mark.parametrize("reference", [None, PolicyReferenceContext("SYNTH-POLICY"), REF,
    PolicyReferenceContext("SYNTH-POLICY", date(2027, 1, 1))])
def test_birth_only_does_not_depend_on_application_date(reference):
    root, fact = birth(), bfact()
    assert run(root, facts=EvaluationFacts(birth=fact), reference=reference).rule_results[0] == evaluate_birth_date_rule(root, fact)


def test_birth_leaf_is_invariant_to_evaluation_date_but_policy_context_is_preserved():
    facts = EvaluationFacts(birth=bfact())
    first = run(birth(), facts=facts)
    second = run(birth(), facts=facts, context=replace(CTX, as_of=date(2027, 2, 1)))
    assert first.rule_results == second.rule_results
    assert first.to_dict()["context"] != second.to_dict()["context"]


@pytest.mark.parametrize("bad", [PolicyReferenceContext("OTHER", DAY), "reference"])
def test_explicit_invalid_reference_context_still_errors_for_birth_only(bad):
    with pytest.raises(ContextValidationError):
        run(birth(), reference=bad)


def test_resident_context_preflight_is_not_bypassed_by_birth_pass():
    root = RuleGroup("ROOT", GroupOperator.ANY, (birth(), resident()))
    with pytest.raises(ContextValidationError):
        run(root, facts=EvaluationFacts(birth=bfact()))
    output = run(root, facts=EvaluationFacts(birth=bfact()), reference=PolicyReferenceContext("SYNTH-POLICY"))
    assert output.overall_status is Status.PASS
    assert output.rule_results[2].status is Status.UNKNOWN


@pytest.mark.parametrize(("rstatus", "bstatus", "expected"), [
    (Status.PASS, Status.PASS, Status.PASS), (Status.PASS, Status.FAIL, Status.FAIL),
    (Status.PASS, Status.UNKNOWN, Status.UNKNOWN), (Status.FAIL, Status.PASS, Status.FAIL),
    (Status.UNKNOWN, Status.PASS, Status.UNKNOWN),
])
def test_required_resident_birth_all_cases(rstatus, bstatus, expected):
    root = RuleGroup("ROOT", GroupOperator.ALL, (resident(), birth()))
    output = run(root, facts=EvaluationFacts(rfacts(rstatus), birth=bfact(bstatus)), reference=REF)
    assert output.overall_status is expected
    assert [leaf.rule_id for leaf in output.rule_results] == ["ROOT", "R", "B"]
    assert [leaf.status for leaf in output.rule_results[1:]] == [rstatus, bstatus]


@pytest.mark.parametrize(("operator", "astatus", "bstatus"), list(product(
    [GroupOperator.ALL, GroupOperator.ANY], list(Status), list(Status))))
def test_atomic_birth_all_any_truth_tables(operator, astatus, bstatus):
    age = {Status.PASS: 24, Status.FAIL: 17, Status.UNKNOWN: None}[astatus]
    root = RuleGroup("ROOT", operator, (atom(), birth()))
    output = run(root, profile=UserProfile(age=age), facts=EvaluationFacts(birth=bfact(bstatus)))
    if operator is GroupOperator.ALL:
        expected = Status.FAIL if Status.FAIL in (astatus, bstatus) else Status.PASS if astatus is bstatus is Status.PASS else Status.UNKNOWN
    else:
        expected = Status.PASS if Status.PASS in (astatus, bstatus) else Status.FAIL if astatus is bstatus is Status.FAIL else Status.UNKNOWN
    assert output.overall_status is expected
    assert output.rule_results[1].status is astatus and output.rule_results[2].status is bstatus


@pytest.mark.parametrize(("bstatus", "expected"), [(Status.PASS, Status.FAIL), (Status.FAIL, Status.PASS), (Status.UNKNOWN, Status.UNKNOWN)])
def test_not_uses_existing_status_inversion(bstatus, expected):
    output = run(RuleGroup("NOT", GroupOperator.NOT, (birth(),)), facts=EvaluationFacts(birth=bfact(bstatus)))
    assert output.overall_status is expected and output.rule_results[1].status is bstatus


def test_nested_mixed_result_order_missing_union_evidence_and_serialization():
    root = RuleGroup("ROOT", GroupOperator.ALL, (
        atom(), birth(), RuleGroup("CHOICE", GroupOperator.ANY, (resident(), atom("OTHER"))),
    ))
    facts = EvaluationFacts(rfacts(), birth=None)
    before = facts.to_dict()
    output = run(root, facts=facts, reference=REF)
    assert output.overall_status is Status.UNKNOWN
    assert [node.rule_id for node in walk_nodes(root)] == ["ROOT", "A", "B", "CHOICE", "R", "OTHER"]
    assert [item.rule_id for item in output.rule_results] == ["ROOT", "A", "B", "CHOICE", "R", "OTHER"]
    assert output.missing_fields == ("birth.birth_date",)
    leaf = output.rule_results[2]
    assert leaf.evidence_refs is EVIDENCE
    assert output.rule_results[0].evidence_refs == tuple(sorted(set(EVIDENCE + ("synthetic:age", "synthetic:resident"))))
    value = output.to_dict()
    assert value["rule_results"][2]["reason_code"] == "BIRTH_DATE_MISSING"
    assert value["rule_results"][4]["details"]["reference_date"] == DAY.isoformat()
    assert json.loads(json.dumps(value)) == value
    assert output == run(root, facts=facts, reference=REF) and facts.to_dict() == before
    passed = run(root, facts=replace(facts, birth=bfact()), reference=REF).to_dict()
    assert passed["rule_results"][2]["evaluated_value"] == LOWER.isoformat()
    assert passed["rule_results"][2]["details"] == {"birth_source": "SELF_REPORTED"}


@pytest.mark.parametrize("other", [atom("B"), resident("B"), birth(), RuleGroup("B", GroupOperator.ALL, (atom(),))])
def test_duplicate_ids_across_all_node_types_are_rejected(other):
    with pytest.raises(PolicyDataError, match="중복"):
        RuleGroup("ROOT", GroupOperator.ALL, (other, birth()))


def test_nested_birth_id_collision_is_rejected():
    inner = RuleGroup("INNER", GroupOperator.NOT, (birth(),))
    with pytest.raises(PolicyDataError, match="중복"):
        RuleGroup("ROOT", GroupOperator.ALL, (inner, atom("B")))


def test_dispatch_preserves_node_fact_and_returned_result_identity(monkeypatch):
    from backend.policy_engine import routing
    node, fact = birth(), bfact()
    expected = evaluate_birth_date_rule(node, fact)
    calls = []

    def track(given_rule, given_fact):
        assert given_rule is node and given_fact is fact
        calls.append(True)
        return expected

    monkeypatch.setattr(routing, "evaluate_birth_date_rule", track)
    assert run(node, facts=EvaluationFacts(birth=fact)).rule_results[0] is expected
    assert calls == [True]


@pytest.mark.parametrize("error", [PolicyDataError("synthetic"), ProfileValidationError("synthetic"), ResultValidationError("SYNTHETIC", "birth")])
def test_birth_evaluator_error_propagates_without_partial_results(monkeypatch, error):
    from backend.policy_engine import routing

    def fail(*args):
        raise error

    monkeypatch.setattr(routing, "evaluate_birth_date_rule", fail)
    with pytest.raises(type(error)) as caught:
        run(RuleGroup("ROOT", GroupOperator.ANY, (atom(), birth())))
    assert caught.value is error


def test_unsupported_nodes_and_legacy_evaluation_remain_rejected():
    with pytest.raises(PolicyDataError):
        policy(object())
    with pytest.raises(PolicyDataError):
        RuleGroup("ROOT", GroupOperator.ALL, (object(),))
    with pytest.raises(PolicyDataError):
        evaluate_policy(UserProfile(), policy(birth()), CTX)


@pytest.mark.parametrize("version", ["m1.0", "m1.1"])
def test_policy_set_birth_is_blocked_until_loader_schema_support(version):
    if version == "m1.0":
        with pytest.raises(PolicyDataError, match="BirthDateRule"):
            PolicySet(version, CTX.dataset_version, (policy(birth()),))
    else:
        selected = policy(birth())
        assert PolicySet(version, CTX.dataset_version, (selected,)).policies == (selected,)


def test_m11_birth_json_still_fails_without_loader_changes():
    data = dict(schema_version="m1.1", dataset_version="synthetic-birth-routing", synthetic=True, test_only=True,
                policies=[dict(policy_id="SYNTH-POLICY", policy_name="합성", rule_version="synthetic-1", synthetic=True, test_only=True,
                               root=dict(kind="rule", rule_type="birth_date", **birth().to_dict()))])
    loaded = parse_policy_set(data).policies[0]
    output = evaluate_policy_tree(UserProfile(age=24), loaded, CTX, facts=EvaluationFacts(birth=bfact()))
    assert output == run(birth(), facts=EvaluationFacts(birth=bfact()))
