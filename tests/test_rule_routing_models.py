"""M1.6G: 합성 규칙/입력과 트리 구조만 검증한다. 평가/로딩 연결 없음."""

from dataclasses import fields, FrozenInstanceError, replace
from datetime import date, datetime
import json
from typing import get_args, get_type_hints

import pytest

from backend.policy_engine import (
    ContextValidationError, EvaluationContext, EvaluationFacts, Field, GroupOperator,
    Operator, Policy, PolicyDataError, PolicyReferenceContext, PolicyRule, PolicySet,
    ProfileValidationError, ReferenceDateSource, ResidentRegistrationRule, RuleGroup, UserProfile,
)
from backend.policy_engine.facts import (
    RegionRef, RegistrationSource, ResidentRegistrationFact, ResidentRegistrationValidationError,
)
from backend.policy_engine.models import RuleNode, walk_nodes


DAY = date(2026, 11, 10)
ANSAN = RegionRef("GYEONGGI", "ANSAN")
SUWON = RegionRef("GYEONGGI", "SUWON")


def resident(rule_id="SYN_R"):
    return ResidentRegistrationRule(rule_id, ANSAN, ReferenceDateSource.APPLICATION_DATE, ("synthetic:resident",))


def atomic(rule_id="SYN_A"):
    return PolicyRule(rule_id, Field.AGE, Operator.GTE, 19, evidence_refs=("synthetic:age",))


def policy(root, policy_id="SYN_P"):
    return Policy(policy_id, "합성 구조 테스트", "synthetic-1", root)


def fact(region=ANSAN, source=RegistrationSource.SELF_REPORTED):
    return ResidentRegistrationFact(region, DAY, source)


def dataset(policies, version="m1.0"):
    return PolicySet(version, "synthetic-model-test", policies)


def test_resident_rule_exact_fields_and_stable_representation():
    value = resident()
    assert {f.name for f in fields(value)} == {"rule_id", "required_region", "reference_date_source", "evidence_refs"}
    assert value.required_region is ANSAN
    assert value.reference_date_source is ReferenceDateSource.APPLICATION_DATE
    assert value == resident()
    assert value.to_dict() == {
        "rule_id": "SYN_R", "required_region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "reference_date_source": "APPLICATION_DATE", "evidence_refs": ["synthetic:resident"],
    }
    assert json.loads(json.dumps(value.to_dict())) == value.to_dict()
    assert repr(value) == repr(resident())


@pytest.mark.parametrize("bad", [None, "", "   ", 1, True, ()])
def test_invalid_resident_rule_id(bad):
    with pytest.raises(PolicyDataError, match="rule_id"):
        replace(resident(), rule_id=bad)


@pytest.mark.parametrize("bad", [None, "ANSAN", {"sido": "GYEONGGI", "sigungu": "ANSAN"}, 1, fact()])
def test_invalid_required_region_is_policy_error(bad):
    with pytest.raises(PolicyDataError, match="required_region"):
        replace(resident(), required_region=bad)


def test_partial_region_cannot_be_created_before_rule():
    with pytest.raises(ResidentRegistrationValidationError, match="INVALID_REGION"):
        ResidentRegistrationRule("SYN_BAD", RegionRef("GYEONGGI", None),
                                 ReferenceDateSource.APPLICATION_DATE, ("synthetic:bad",))


@pytest.mark.parametrize("bad", [None, "APPLICATION_DATE", "APPLICATION_REFERENCE_DATE", "EVALUATION_DATE", "FIXED_DATE", "SYSTEM_TODAY", 1])
def test_reference_source_does_not_parse_or_fallback(bad):
    with pytest.raises(PolicyDataError, match="reference_date_source"):
        replace(resident(), reference_date_source=bad)


def test_reference_date_enum_reused_without_new_members():
    assert list(ReferenceDateSource) == [ReferenceDateSource.APPLICATION_DATE]
    assert ReferenceDateSource.APPLICATION_DATE.value == "APPLICATION_DATE"


@pytest.mark.parametrize("bad", [None, (), [], ["synthetic:ref"], "synthetic:ref", ("",), (" ",), (None,), (1,)])
def test_invalid_evidence_refs(bad):
    with pytest.raises(PolicyDataError, match="evidence_refs"):
        replace(resident(), evidence_refs=bad)


def test_default_empty_evidence_is_not_valid_policy_data():
    with pytest.raises(PolicyDataError, match="evidence_refs"):
        ResidentRegistrationRule("SYN_NO_REF", ANSAN, ReferenceDateSource.APPLICATION_DATE)


def test_rule_has_no_user_fact_or_result_storage():
    with pytest.raises(TypeError):
        ResidentRegistrationRule("SYN_R", ANSAN, ReferenceDateSource.APPLICATION_DATE,
                                 ("synthetic:resident",), facts=(fact(),))
    assert not hasattr(resident(), "__dict__")


def test_reference_context_date_missing_equality_and_serialization():
    value = PolicyReferenceContext("SYN_P", DAY)
    assert value == PolicyReferenceContext("SYN_P", DAY)
    assert value.to_dict() == {"policy_id": "SYN_P", "application_date": "2026-11-10"}
    missing = PolicyReferenceContext("SYN_P")
    assert missing == PolicyReferenceContext("SYN_P", None)
    assert missing.to_dict() == {"policy_id": "SYN_P", "application_date": None}
    assert {f.name for f in fields(value)} == {"policy_id", "application_date"}


@pytest.mark.parametrize("bad", ["2026-11-10", datetime(2026, 11, 10), 0, False, [], {}])
def test_invalid_application_date_type(bad):
    with pytest.raises(ContextValidationError, match="application_date"):
        PolicyReferenceContext("SYN_P", bad)


@pytest.mark.parametrize("bad", [None, "", "   ", 1, True, ()])
def test_invalid_reference_policy_id(bad):
    with pytest.raises(ContextValidationError, match="policy_id"):
        PolicyReferenceContext(bad, DAY)


def test_reference_context_does_not_overwrite_evaluation_date_or_check_eligibility():
    context = EvaluationContext(date(2026, 10, 20), "synthetic-1")
    reference = PolicyReferenceContext("SYN_P", DAY)
    assert context.as_of == date(2026, 10, 20)
    assert reference.application_date == DAY
    assert reference.application_date > context.as_of
    assert not hasattr(reference, "status")


def test_empty_evaluation_facts_has_no_region_fallback():
    user = UserProfile(region="안산시")
    value = EvaluationFacts()
    assert value.resident_registrations == ()
    assert value.to_dict() == {"resident_registrations": []}
    assert user.region == "안산시"
    assert {f.name for f in fields(value)} == {"resident_registrations", "birth"}
    assert value.birth is None


def test_one_fact_preserved_without_copying_profile():
    selected = fact()
    value = EvaluationFacts((selected,))
    assert value.resident_registrations == (selected,)
    assert value.resident_registrations[0] is selected
    assert value == EvaluationFacts((selected,))
    assert value.to_dict() == {"resident_registrations": [{
        "region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "as_of_date": "2026-11-10", "source": "SELF_REPORTED",
    }]}
    assert json.loads(json.dumps(value.to_dict())) == value.to_dict()


def test_facts_keep_order_duplicates_sources_and_conflicting_claims():
    first, second = fact(SUWON), fact(ANSAN, RegistrationSource.OFFICIAL_DATA)
    given = (first, second, first)
    value = EvaluationFacts(given)
    assert value.resident_registrations is given
    assert len(value.resident_registrations) == 3
    assert [f.region for f in value.resident_registrations] == [SUWON, ANSAN, SUWON]
    assert value.resident_registrations[1].source is RegistrationSource.OFFICIAL_DATA
    # 같은 날짜의 충돌을 여기서 판정·해결하지 않는다. 기존 Resolver의 책임이다.


@pytest.mark.parametrize("bad", [None, [], [fact()], {"resident": fact()}, "facts", (None,), (UserProfile(),), (object(),)])
def test_facts_require_exact_typed_tuple(bad):
    with pytest.raises(ProfileValidationError, match="resident_registrations"):
        EvaluationFacts(bad)


def test_fact_generator_rejected_without_consuming_it():
    iterator = iter((fact(),))
    with pytest.raises(ProfileValidationError):
        EvaluationFacts(iterator)
    assert next(iterator) == fact()


def test_individual_fact_errors_keep_existing_error_type():
    with pytest.raises(ResidentRegistrationValidationError, match="INVALID_SOURCE"):
        EvaluationFacts((ResidentRegistrationFact(ANSAN, DAY, "SELF_REPORTED"),))


@pytest.mark.parametrize("operator", [GroupOperator.ALL, GroupOperator.ANY])
def test_mixed_children_allowed_and_order_preserved(operator):
    a, r = atomic(), resident()
    group = RuleGroup("SYN_ROOT", operator, (a, r))
    assert group.children == (a, r)
    assert list(walk_nodes(group)) == [group, a, r]
    assert policy(group).root is group


def test_resident_inside_not_and_as_policy_root():
    r = resident()
    group = RuleGroup("SYN_NOT", GroupOperator.NOT, (r,))
    assert group.children == (r,)
    assert policy(r).root is r
    assert list(walk_nodes(r)) == [r]


def test_nested_mixed_tree_structure_only():
    a, r = atomic(), resident()
    student = PolicyRule("SYN_STUDENT", Field.STUDENT_STATUS, Operator.EQ, True, evidence_refs=("synthetic:student",))
    employment = PolicyRule("SYN_EMP", Field.EMPLOYMENT_STATUS, Operator.EQ, "employed", evidence_refs=("synthetic:emp",))
    inner = RuleGroup("SYN_ANY", GroupOperator.ANY, (student, employment))
    root = RuleGroup("SYN_ALL", GroupOperator.ALL, (a, r, inner))
    value = policy(root)
    assert [node.rule_id for node in walk_nodes(value.root)] == [
        "SYN_ALL", "SYN_A", "SYN_R", "SYN_ANY", "SYN_STUDENT", "SYN_EMP",
    ]
    assert value.synthetic is True and value.test_only is True


def test_union_and_recursive_annotations_match_runtime_types():
    from backend.policy_engine.specialized_rules import BirthDateRule

    assert set(get_args(RuleNode)) == {PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup}
    assert get_type_hints(RuleGroup)["children"] == tuple[RuleNode, ...]
    assert get_type_hints(Policy)["root"] == RuleNode


@pytest.mark.parametrize("operator", list(GroupOperator))
def test_empty_group_still_rejected(operator):
    with pytest.raises(PolicyDataError):
        RuleGroup("SYN_EMPTY", operator, ())


@pytest.mark.parametrize("children", [(atomic(), resident()), (resident(), atomic())])
def test_not_requires_exactly_one_child(children):
    with pytest.raises(PolicyDataError, match="NOT"):
        RuleGroup("SYN_NOT", GroupOperator.NOT, children)


@pytest.mark.parametrize("bad", [None, object(), {"rule_id": "SYN_FAKE"}, "SYN_R", fact(), PolicyReferenceContext("SYN_P")])
def test_invalid_child_and_policy_root_rejected(bad):
    with pytest.raises(PolicyDataError):
        RuleGroup("SYN_ROOT", GroupOperator.ALL, (atomic(), bad))
    with pytest.raises(PolicyDataError):
        policy(bad)


def test_mutable_children_rejected():
    with pytest.raises(PolicyDataError):
        RuleGroup("SYN_ROOT", GroupOperator.ALL, [atomic(), resident()])


@pytest.mark.parametrize("pair", [
    (atomic("SYN_DUP"), atomic("SYN_DUP")),
    (atomic("SYN_DUP"), resident("SYN_DUP")),
    (resident("SYN_DUP"), resident("SYN_DUP")),
])
def test_duplicate_leaf_ids_across_types_rejected(pair):
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        RuleGroup("SYN_ROOT", GroupOperator.ALL, pair)


def test_nested_duplicate_id_is_global_to_tree():
    inner = RuleGroup("SYN_INNER", GroupOperator.NOT, (resident("SYN_DUP"),))
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        RuleGroup("SYN_ROOT", GroupOperator.ALL, (atomic("SYN_DUP"), inner))


def test_group_and_resident_id_collision_rejected():
    with pytest.raises(PolicyDataError, match="중복 rule_id"):
        RuleGroup("SYN_DUP", GroupOperator.NOT, (resident("SYN_DUP"),))


@pytest.mark.parametrize("root", [resident(), RuleGroup("SYN_ROOT", GroupOperator.ALL, (atomic(), resident()))])
def test_m10_policy_set_cannot_bypass_loader_schema_boundary(root):
    with pytest.raises(PolicyDataError, match="m1.0"):
        dataset((policy(root),))


def test_global_dataset_rule_id_check_still_includes_specialized_nodes():
    with pytest.raises(PolicyDataError, match="데이터셋의 rule_id는 모두 유일"):
        dataset((policy(atomic("SYN_DUP"), "SYN_P1"), policy(resident("SYN_DUP"), "SYN_P2")))


def test_m11_enabled_with_versioned_loader_contract():
    # M1.7 사용자 승인: 임시 버전 차단만 새 지원 계약으로 갱신한다.
    value = dataset((policy(resident()),), version="m1.1")
    assert value.schema_version == "m1.1"
    assert type(value.policies[0].root) is ResidentRegistrationRule


def test_existing_atomic_models_nested_tree_and_three_samples(policy_set):
    a = atomic()
    inner = RuleGroup("SYN_INNER", GroupOperator.NOT, (a,))
    outer = RuleGroup("SYN_OUTER", GroupOperator.ALL, (inner,))
    assert dataset((policy(outer),)).policies[0].root == outer
    assert len(policy_set.policies) == 3
    assert all(type(n) in (PolicyRule, RuleGroup) for p in policy_set.policies for n in walk_nodes(p.root))


@pytest.mark.parametrize("value", [resident(), ANSAN, PolicyReferenceContext("SYN_P", DAY), EvaluationFacts((fact(),)), fact()])
def test_all_new_input_and_rule_layers_are_frozen(value):
    with pytest.raises(FrozenInstanceError):
        setattr(value, fields(value)[0].name, None)


def test_serialized_copies_cannot_mutate_inputs():
    r, f, c = resident(), EvaluationFacts((fact(),)), PolicyReferenceContext("SYN_P", DAY)
    rd, fd, cd = r.to_dict(), f.to_dict(), c.to_dict()
    rd["required_region"]["sigungu"] = "SUWON"
    rd["evidence_refs"].clear()
    fd["resident_registrations"][0]["region"]["sigungu"] = "SUWON"
    cd["application_date"] = None
    assert r == resident() and f == EvaluationFacts((fact(),)) and c.application_date == DAY


def test_validation_errors_do_not_echo_supplied_values():
    with pytest.raises(PolicyDataError) as err:
        replace(resident(), required_region="private-region-value")
    assert "private-region-value" not in str(err.value)
