"""m1.1 합성 생년월일 JSON 경계와 기존 판정 경로의 통합 계약."""

from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path

import pytest

from backend.policy_engine import (
    BirthDateRule, BirthDateReasonCode as BR, EvaluationContext, EvaluationFacts,
    Field, GroupOperator, Operator, Policy, PolicyDataError, PolicyRule, PolicySet,
    PolicyReferenceContext, ReferenceDateSource, ResidentRegistrationRule,
    RuleGroup, Status, UserProfile, evaluate_birth_date_rule, evaluate_policy_tree,
    load_policy_set, parse_policy_set,
)
from backend.policy_engine.facts import (
    BirthFact, BirthSource, RegionRef, RegistrationSource, ResidentRegistrationFact,
)
from backend.policy_engine.policy_data import parse_policy_envelope


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/synthetic/policies_m11_birth.json"
LOW, HIGH = date(1998, 1, 10), date(1999, 1, 9)
REFS = ("SYNTH-BIRTH-SOURCE-001#birth-date-range",)


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def leaf():
    return payload()["policies"][0]["root"]["children"][2]


def single(node=None):
    result = payload()
    result["policies"][0]["root"] = leaf() if node is None else node
    return result


def group(operator, children, rule_id="SYNTH-GROUP"):
    return {"kind": "group", "rule_id": rule_id, "operator": operator, "children": children}


def handmade():
    return PolicySet("m1.1", "synthetic-birth-loader-001", (
        Policy("SYNTH-BIRTH-POLICY-001", "합성 test_only 생년월일 혼합 정책", "r0001",
            RuleGroup("SYNTH-BIRTH-ROOT", GroupOperator.ALL, (
                PolicyRule("SYNTH-BIRTH-AGE", Field.AGE, Operator.GTE, 19,
                           evidence_refs=("SYNTH-SOURCE-001#application-period",)),
                ResidentRegistrationRule("SYNTH-BIRTH-RESIDENT", RegionRef("SEOUL", "JONGNO"),
                    ReferenceDateSource.APPLICATION_DATE, ("SYNTH-SOURCE-001#eligibility-residence",)),
                BirthDateRule("SYNTH-BIRTH-RANGE", LOW, HIGH, REFS),
            ))),
    ), True, True)


def test_fixture_matches_independently_constructed_complete_tree():
    loaded = load_policy_set(FIXTURE)
    assert loaded == handmade()
    assert type(loaded.policies[0].root.children[2].min_birth_date) is date


@pytest.mark.parametrize("field", ["min_birth_date", "max_birth_date"])
@pytest.mark.parametrize("bad", [
    None, True, False, 19980110, 1.5, [], {}, date(1998, 1, 10), datetime(1998, 1, 10),
    "1998-1-10", "1998/01/10", "10-01-1998", "19980110", "1998-W02-6",
    " 1998-01-10", "1998-01-10 ", "1998-01-10\n", "1998-01-10T00:00:00",
    "1998-01-10Z", "１９９８-０１-１０", "١٩٩٨-٠١-١٠", "0000-01-01",
    "1999-02-29", "1900-02-29", "1998-13-01", "1998-04-31", "1998-00-10", "1998-01-00",
    "10000-01-01", "private-birth-payload",
])
def test_dates_reject_wrong_shape_types_and_invalid_calendar(field, bad):
    node = leaf()
    node[field] = bad
    with pytest.raises(PolicyDataError) as error:
        parse_policy_set(single(node))
    assert "private-birth-payload" not in str(error.value)


@pytest.mark.parametrize("value", ["0001-01-01", "2000-02-29", "2400-02-29", "9999-12-31"])
def test_single_day_and_valid_leap_dates(value):
    node = leaf()
    node.update(min_birth_date=value, max_birth_date=value)
    rule = parse_policy_set(single(node)).policies[0].root
    assert rule.min_birth_date == rule.max_birth_date == date.fromisoformat(value)


def test_reversed_range_is_rejected_by_constructor_invariant():
    node = leaf()
    node.update(min_birth_date="1999-01-10", max_birth_date="1999-01-09")
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


@pytest.mark.parametrize("key", list(leaf()))
def test_every_birth_key_is_required(key):
    node = leaf()
    del node[key]
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


@pytest.mark.parametrize("key", ["age", "quarter", "birth_source", "inclusive_min", "inclusive_max",
    "reference_date_source", "min_birthdate", "metadata", "fact_basis"])
def test_no_extra_birth_fields(key):
    node = leaf()
    node[key] = None
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


@pytest.mark.parametrize("kind", [None, True, "Rule", "group", "birth_date", "unknown"])
def test_rule_type_does_not_override_invalid_kind(kind):
    node = leaf()
    node["kind"] = kind
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


@pytest.mark.parametrize("rule_type", [None, True, 1, "BirthDate", "BIRTH_DATE", "birth-date",
    "birthdate", "unknown", "atomic", "resident_registration"])
def test_explicit_dispatch_does_not_infer_birth_shape(rule_type):
    node = leaf()
    node["rule_type"] = rule_type
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


@pytest.mark.parametrize("refs", [None, "source", {}, (), 1, True, [], [1], [True], [None], [""], ["  "]])
def test_evidence_requires_nonempty_array_of_nonblank_strings(refs):
    node = leaf()
    node["evidence_refs"] = refs
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


def test_standalone_evidence_preserves_noncanonical_order_and_duplicates():
    node = leaf()
    node["evidence_refs"] = ["synthetic:second", "synthetic:first", "synthetic:second"]
    rule = parse_policy_set(single(node)).policies[0].root
    assert rule.evidence_refs == tuple(node["evidence_refs"])


@pytest.mark.parametrize("operator", ["ALL", "ANY", "NOT"])
@pytest.mark.parametrize("nested", [False, True])
def test_birth_at_every_group_position(operator, nested):
    node = group(operator, [leaf()])
    if nested:
        node = group("ALL", [node], "SYNTH-OUTER")
    root = parse_policy_set(single(node)).policies[0].root
    if nested:
        root = root.children[0]
    assert root.operator.value == operator
    assert root.children == (BirthDateRule("SYNTH-BIRTH-RANGE", LOW, HIGH, REFS),)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("remove_discriminator", [False, True])
def test_m10_rejects_birth_even_without_discriminator(nested, remove_discriminator):
    node = leaf()
    if remove_discriminator:
        del node["rule_type"]
    data = single(group("ALL", [node]) if nested else node)
    data["schema_version"] = "m1.0"
    with pytest.raises(PolicyDataError):
        parse_policy_set(data)


def test_memory_policyset_keeps_m10_guard_and_accepts_m11():
    selected = handmade()
    with pytest.raises(PolicyDataError):
        PolicySet("m1.0", selected.dataset_version, selected.policies, True, True)
    assert PolicySet("m1.1", selected.dataset_version, selected.policies, True, True) == selected


@pytest.mark.parametrize("version", [None, True, "m1.2", "m1.01", "M1.1", "unknown"])
def test_unsupported_schema_remains_error(version):
    data = single()
    data["schema_version"] = version
    with pytest.raises(PolicyDataError):
        parse_policy_set(data)


@pytest.mark.parametrize("other_index", [0, 1, 2])
@pytest.mark.parametrize("nested", [False, True])
def test_duplicate_ids_across_leaf_types_and_nested_groups(other_index, nested):
    other = payload()["policies"][0]["root"]["children"][other_index]
    other["rule_id"] = leaf()["rule_id"]
    node = group("ANY", [other], "SYNTH-INNER") if nested else other
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(group("ALL", [leaf(), node])))


def test_group_id_cannot_collide_with_birth_id():
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(group("ALL", [leaf()], leaf()["rule_id"])))


def test_birth_rule_id_collision_across_policies_is_rejected():
    data = single()
    other = deepcopy(data["policies"][0])
    other["policy_id"] = "SYNTH-OTHER-POLICY"
    data["policies"].append(other)
    with pytest.raises(PolicyDataError):
        parse_policy_set(data)


def test_group_disallows_birth_discriminator():
    node = group("ALL", [leaf()])
    node["rule_type"] = "birth_date"
    with pytest.raises(PolicyDataError):
        parse_policy_set(single(node))


def test_combined_nested_mixed_groups_preserve_child_order():
    children = payload()["policies"][0]["root"]["children"]
    node = group("ALL", [children[0], group("ANY", [children[1],
        group("NOT", [children[2]], "SYNTH-NOT")], "SYNTH-ANY")])
    root = parse_policy_set(single(node)).policies[0].root
    assert type(root.children[0]) is PolicyRule
    assert type(root.children[1].children[0]) is ResidentRegistrationRule
    assert type(root.children[1].children[1].children[0]) is BirthDateRule


@pytest.mark.parametrize("duplicate_key", list(leaf()))
def test_file_reader_rejects_duplicate_json_keys(tmp_path, duplicate_key):
    data = single()
    encoded = json.dumps(data)
    marker = json.dumps(duplicate_key) + ": " + json.dumps(leaf()[duplicate_key])
    encoded = encoded.replace(marker, marker + ", " + marker, 1)
    path = tmp_path / "duplicate.json"
    path.write_text(encoded, encoding="utf-8")
    with pytest.raises(PolicyDataError):
        load_policy_set(path)


@pytest.mark.parametrize("position", ["child", "policy"])
def test_invalid_later_item_fails_entire_load(position):
    data = payload()
    bad = leaf()
    bad["min_birth_date"] = "invalid"
    bad["rule_id"] = "SYNTH-BAD"
    if position == "child":
        data["policies"][0]["root"]["children"].append(bad)
    else:
        extra = deepcopy(data["policies"][0])
        extra.update(policy_id="SYNTH-BAD-POLICY", root=bad)
        data["policies"].append(extra)
    with pytest.raises(PolicyDataError):
        parse_policy_set(data)


@pytest.mark.parametrize(("birthday", "status", "reason"), [
    (LOW, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (HIGH, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (date(1998, 1, 9), Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
    (date(1999, 1, 10), Status.FAIL, BR.BIRTH_DATE_AFTER_RANGE),
    (None, Status.UNKNOWN, BR.BIRTH_DATE_MISSING),
])
def test_loaded_mixed_tree_matches_handbuilt_evaluation_and_serialization(birthday, status, reason):
    loaded, direct = load_policy_set(FIXTURE), handmade()
    fact = BirthFact(birthday, BirthSource.SELF_REPORTED)
    day = date(2026, 1, 10)
    facts = EvaluationFacts((ResidentRegistrationFact(RegionRef("SEOUL", "JONGNO"), day,
                            RegistrationSource.SELF_REPORTED),), birth=fact)
    context = EvaluationContext(day, loaded.dataset_version)
    reference = PolicyReferenceContext(loaded.policies[0].policy_id, day)
    def run(selected):
        return evaluate_policy_tree(UserProfile(age=24), selected.policies[0], context,
                                    facts=facts, reference_context=reference)
    result = run(loaded)
    assert result == run(direct)
    assert result.to_dict() == run(direct).to_dict() == run(loaded).to_dict()
    assert result.overall_status is status
    birth_result = result.rule_results[-1]
    assert birth_result == evaluate_birth_date_rule(direct.policies[0].root.children[2], fact)
    assert birth_result.reason_code is reason
    assert birth_result.evidence_refs == REFS


def envelope_payload():
    # 합성 구조 전파만 검증한다. 새 birth source의 Registry 실재 검증은 수행하지 않는다.
    data = json.loads((ROOT / "data/synthetic/policy_envelope_m11.json").read_text(encoding="utf-8"))
    data["policy"]["root"] = leaf()
    data["coverage"]["included_rule_ids"] = [leaf()["rule_id"]]
    data["source_bindings"] = [{"source_document_id": "SYNTH-BIRTH-SOURCE-001", "document_version": "d0001"}]
    return data


def test_synthetic_envelope_propagates_birth_without_loader_changes():
    data = envelope_payload()
    snapshot = deepcopy(data)
    envelope = parse_policy_envelope(data)
    assert data == snapshot
    assert envelope.policy.root == parse_policy_set(single()).policies[0].root
    result = evaluate_policy_tree(UserProfile(), envelope.policy,
        EvaluationContext(date(2026, 1, 10), envelope.dataset_version),
        facts=EvaluationFacts(birth=BirthFact(LOW, BirthSource.SELF_REPORTED)))
    assert result.overall_status is Status.PASS


@pytest.mark.parametrize("bad_refs", [["noncanonical"], [REFS[0], REFS[0]]])
def test_envelope_keeps_stricter_reference_contract(bad_refs):
    data = envelope_payload()
    data["policy"]["root"]["evidence_refs"] = bad_refs
    with pytest.raises(ValueError):
        parse_policy_envelope(data)


def test_envelope_requires_birth_coverage():
    data = envelope_payload()
    data["coverage"]["included_rule_ids"] = ["SYNTH-WRONG"]
    with pytest.raises(ValueError):
        parse_policy_envelope(data)


def test_absent_birth_fact_remains_unknown_after_loading():
    selected = parse_policy_set(single())
    result = evaluate_policy_tree(UserProfile(age=24), selected.policies[0],
                                 EvaluationContext(date(2026, 1, 10), selected.dataset_version))
    assert result.overall_status is Status.UNKNOWN
    assert result.missing_fields == ("birth.birth_date",)


def test_parser_does_not_mutate_input_or_require_source_registry():
    data = payload()
    snapshot = deepcopy(data)
    assert parse_policy_set(data) == handmade()
    assert data == snapshot
