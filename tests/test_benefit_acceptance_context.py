"""합성 이력의 구조/명시 조회만 검증한다. 현재 사용·철회 효과·실제 발급을 평가하지 않는다."""

from dataclasses import FrozenInstanceError, MISSING, fields, replace
from datetime import date
from enum import Enum
import inspect
from itertools import permutations
import json
from pathlib import Path
import re
from typing import get_type_hints

import pytest

from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    ApplicabilityScope, BenefitAcceptanceContext, BenefitAcceptanceStatus, PolicyBenefitAcceptance,
)
from backend.policy_engine.policy_data import benefit_acceptance_context as domain
from backend.policy_engine.policy_data.benefit_acceptance_resolution import _resolve_benefit_acceptance


FIELD_NAMES = ("policy_id", "scope", "benefit_id", "records")
BINDING_FIELDS = (
    "coverage_inventory_version", "coverage_inventory_fingerprint", "coverage_rule_version",
    "coverage_policy_tree_fingerprint", "coverage_dataset_version",
    "coverage_source_registry_fingerprint", "coverage_implementation_fingerprint",
    "benefit_version", "benefit_fingerprint", "benefit_dataset_version",
    "benefit_source_registry_fingerprint",
)


def accepted(ref="SYNTH-A", version="a0001", **changes):
    return PolicyBenefitAcceptance(**{
        "acceptance_ref": ref, "acceptance_version": version, "status": BenefitAcceptanceStatus.ACCEPTED,
        "policy_id": "SYNTH-POLICY", "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": date(2026, 1, 1),
        "valid_until": date(2026, 12, 31), "review_artifact_ref": "SYNTH-ARTIFACT-A",
        "revokes_acceptance_ref": None, **changes,
    })


def revoked(target, ref="SYNTH-B", version="a0002", **changes):
    # 정상 constructor/replace만 사용해 각 record의 local invariants를 유지한다.
    return replace(target, **{
        "acceptance_ref": ref, "acceptance_version": version, "status": BenefitAcceptanceStatus.REVOKED,
        "revokes_acceptance_ref": target.acceptance_ref, "reviewed_at": date(2026, 10, 22),
        "valid_until": date(2026, 12, 31), "review_artifact_ref": "SYNTH-ARTIFACT-B", **changes,
    })


def context_values(records=(), **changes):
    return {"policy_id": "SYNTH-POLICY", "scope": ApplicabilityScope("2026", 3),
            "benefit_id": "SYNTH-BENEFIT", "records": records, **changes}


def context(records=(), **changes):
    return BenefitAcceptanceContext(**context_values(records, **changes))


def assert_error(code, field, records=(), **changes):
    with pytest.raises(PolicyDataError) as error:
        context(records, **changes)
    assert type(error.value) is PolicyDataError
    assert str(error.value).startswith(code + ": " + field + ": ")
    return str(error.value)


def binding_change(field):
    # provenance는 record 내부 equality를 지키면서 A/B 사이의 차이를 만든다.
    if "dataset_version" in field:
        return {"coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2"}
    if "source_registry_fingerprint" in field:
        return {"coverage_source_registry_fingerprint": "6" * 64,
                "benefit_source_registry_fingerprint": "6" * 64}
    if field == "coverage_inventory_version":
        return {field: "i0002"}
    if field == "coverage_rule_version":
        return {field: "release-two"}
    if field == "benefit_version":
        return {field: "b0002"}
    return {field: "6" * 64}


class StringSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class RecordSubclass(PolicyBenefitAcceptance):
    pass


class ContextSubclass(BenefitAcceptanceContext):
    pass


class OtherStringEnum(str, Enum):
    ID = "SYNTH-POLICY"


def test_exact_four_fields_types_order_slots_and_required_keyword_only_constructor():
    actual = fields(BenefitAcceptanceContext)
    assert tuple(field.name for field in actual) == FIELD_NAMES == BenefitAcceptanceContext.__slots__
    assert all(field.default is MISSING and field.default_factory is MISSING and field.kw_only and field.compare
               for field in actual)
    assert get_type_hints(BenefitAcceptanceContext) == {
        "policy_id": str, "scope": ApplicabilityScope, "benefit_id": str,
        "records": tuple[PolicyBenefitAcceptance, ...],
    }
    signature = inspect.signature(BenefitAcceptanceContext)
    assert tuple(signature.parameters) == FIELD_NAMES
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in signature.parameters.values())
    assert BenefitAcceptanceContext.__dataclass_params__.frozen
    assert not hasattr(context(), "__dict__")


def test_four_fields_and_eleven_bindings_match_approved_spec():
    text = (Path(__file__).resolve().parents[1] / "docs/BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md").read_text(encoding="utf-8")
    section = text.split("## 4. ", 1)[1].split("## 5. ", 1)[0]
    assert re.findall(r"^\| ([1-4]) \| ([a-z_]+) \|", section, re.M) == [
        (str(index), name) for index, name in enumerate(FIELD_NAMES, 1)]
    section = text.split("## 15. ", 1)[1].split("## 16. ", 1)[0]
    binding = section.split("```text\n", 1)[1].split("```", 1)[0].strip().splitlines()
    assert tuple(binding) == BINDING_FIELDS == domain._SNAPSHOT_BINDING_FIELDS


@pytest.mark.parametrize("field", FIELD_NAMES)
def test_every_field_is_required(field):
    inputs = context_values()
    del inputs[field]
    with pytest.raises(TypeError):
        BenefitAcceptanceContext(**inputs)


def test_positional_and_extra_arguments_are_type_errors():
    with pytest.raises(TypeError):
        BenefitAcceptanceContext(*context_values().values())
    with pytest.raises(TypeError):
        BenefitAcceptanceContext(**context_values(), selected_acceptance_ref=None)


@pytest.mark.parametrize("field", ["policy_id", "benefit_id"])
@pytest.mark.parametrize("bad", [None, True, 1, {}, b"A", "", " ", "lowercase", "SYNTH_ID", "A--B", "A-",
                                      "-A", " A", "A\n", "Ａ", StringSubclass("SYNTH-ID"), OtherStringEnum.ID])
def test_target_ids_use_exact_existing_grammar(field, bad):
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", field, **{field: bad})


@pytest.mark.parametrize("bad", [None, {}, {"edition_id": "2026", "quarter": 3}, "2026-Q3", ("2026", 3),
                                      ScopeSubclass("2026", 3)])
def test_scope_requires_exact_domain_type(bad):
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "scope", scope=bad)


@pytest.mark.parametrize("bad", [None, [], {}, "", 1, TupleSubclass(()), iter(()), (x for x in ())])
def test_records_requires_exact_tuple_without_conversion(bad):
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "records", records=bad)


@pytest.mark.parametrize("bad", [None, {}, [], "SYNTH-A", True, accepted().to_dict(),
                                      RecordSubclass(**{f.name: getattr(accepted(), f.name) for f in fields(PolicyBenefitAcceptance)})])
def test_each_element_requires_exact_record(bad):
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "records", records=(accepted(), bad))


@pytest.mark.parametrize("quarter", [1, 2, 3, 4, None])
def test_empty_context_and_value_equal_distinct_scope_objects_preserve_originals(quarter):
    scope = ApplicabilityScope("2026", quarter)
    record_scope = ApplicabilityScope("2026", quarter)
    record = accepted(scope=record_scope)
    records = (record,)
    empty = context(scope=scope)
    result = context(records, scope=scope)
    assert empty.records == ()
    assert empty.scope is scope and result.scope is scope
    assert result.records is records and result.records[0] is record
    assert result.records[0].scope is record_scope and result.scope is not record_scope


@pytest.mark.parametrize("field,value", [
    ("policy_id", "SYNTH-OTHER-POLICY"), ("benefit_id", "SYNTH-OTHER-BENEFIT"),
    ("scope", ApplicabilityScope("2027", 3)), ("scope", ApplicabilityScope("2026", 4)),
    ("scope", ApplicabilityScope("2026", None)),
])
def test_wrong_target_is_never_filtered_or_reused(field, value):
    wrong = accepted("SYNTH-WRONG", "a0002", **{field: value})
    assert_error("ACCEPTANCE_CONTEXT_TARGET_MISMATCH", "records." + field, (accepted(), wrong))


@pytest.mark.parametrize("field", BINDING_FIELDS)
def test_independent_accepted_history_may_have_different_binding_values(field):
    a = accepted()
    c = accepted("SYNTH-C", "a0003", **binding_change(field))
    result = context((a, c))
    assert _resolve_benefit_acceptance(result, a.acceptance_ref) is a
    assert _resolve_benefit_acceptance(result, c.acceptance_ref) is c


def test_same_snapshot_re_review_can_share_artifact_and_need_not_have_global_date_order():
    a = accepted(reviewed_at=date(2026, 6, 1))
    c = replace(a, acceptance_ref="SYNTH-C", acceptance_version="a0003", reviewed_at=date(2025, 1, 1))
    result = context((c, a))
    assert result.records == (c, a)
    assert _resolve_benefit_acceptance(result, "SYNTH-A") is a
    assert c.review_artifact_ref == a.review_artifact_ref


@pytest.mark.parametrize("duplicate_kind", ["same-object", "equal-copy", "other-content"])
def test_duplicate_ref_is_error_even_for_equal_records(duplicate_kind):
    a = accepted()
    other = a if duplicate_kind == "same-object" else replace(a)
    if duplicate_kind == "other-content":
        other = replace(a, acceptance_version="a0002", benefit_version="b0002")
    assert_error("DUPLICATE_ACCEPTANCE_REF", "records.acceptance_ref", (a, other))


@pytest.mark.parametrize("different_content", [False, True])
def test_duplicate_version_with_distinct_ref_is_error(different_content):
    a = accepted()
    other = replace(a, acceptance_ref="SYNTH-OTHER", **({"benefit_version": "b0002"} if different_content else {}))
    assert_error("DUPLICATE_ACCEPTANCE_VERSION", "records.acceptance_version", (a, other))


def test_exact_ref_identity_does_not_normalize_whitespace_or_case():
    a = accepted("SYNTH-A")
    spaced = accepted(" SYNTH-A ", "a0002")
    lower = accepted("synth-a", "a0003")
    result = context((a, spaced, lower))
    for record in result.records:
        assert _resolve_benefit_acceptance(result, record.acceptance_ref) is record


def test_accept_revoke_reaccept_permutations_and_one_hundred_repeats_preserve_history():
    a = accepted()
    b = revoked(a)
    c = accepted("SYNTH-C", "a0003", reviewed_at=date(2026, 10, 22), valid_until=date(2027, 1, 31))
    originals = (a.to_dict(), b.to_dict(), c.to_dict())
    base = context((a, b, c))
    for order in permutations((a, b, c)):
        for _ in range(100):
            current = context(order)
            assert current.records is order
            assert current == context(order) and hash(current) == hash(context(order))
            assert current.to_dict() == context(order).to_dict()
            for record in (a, b, c):
                assert _resolve_benefit_acceptance(current, record.acceptance_ref) is record
        if order != base.records:
            assert current != base
    assert (a.to_dict(), b.to_dict(), c.to_dict()) == originals
    assert a.status is BenefitAcceptanceStatus.ACCEPTED


@pytest.mark.parametrize("records_kind", ["accepted-only", "pair", "reacceptance", "different-release"])
def test_normal_collection_shapes(records_kind):
    a = accepted()
    b = revoked(a)
    c = accepted("SYNTH-C", "a0003", **(binding_change("benefit_dataset_version") if records_kind == "different-release" else {}))
    records = {"accepted-only": (a,), "pair": (b, a), "reacceptance": (a, b, c),
               "different-release": (a, b, c)}[records_kind]
    assert context(records).records is records


def test_dangling_revocation_is_context_error_not_absence():
    a = accepted()
    b = revoked(a)
    assert_error("REVOCATION_TARGET_NOT_FOUND", "records.revokes_acceptance_ref", (b,))


def test_revoking_revoked_is_error_without_generic_graph_processing():
    a = accepted()
    b = revoked(a)
    c = revoked(b, "SYNTH-C", "a0003")
    assert_error("INVALID_REVOCATION_TARGET_STATUS", "records.revokes_acceptance_ref", (a, b, c))


@pytest.mark.parametrize("field", BINDING_FIELDS)
def test_each_revocation_binding_mismatch_uses_valid_records(field):
    a = accepted()
    b = revoked(a, **binding_change(field))
    expected_field = field
    if field == "benefit_dataset_version":
        expected_field = "coverage_dataset_version"
    if field == "benefit_source_registry_fingerprint":
        expected_field = "coverage_source_registry_fingerprint"
    assert_error("REVOCATION_SNAPSHOT_MISMATCH", "records." + expected_field, (a, b))


def test_duplicate_direct_revocation_target_is_error():
    a = accepted()
    b = revoked(a)
    c = revoked(a, "SYNTH-C", "a0003", reviewed_at=date(2026, 11, 1))
    assert_error("DUPLICATE_REVOCATION_TARGET", "records.revokes_acceptance_ref", (b, c, a))


@pytest.mark.parametrize("target_version,revoke_version", [
    ("a0001", "a0002"), ("a0009", "a0010"), ("a9999", "a10000"), ("a10000", "a10001"),
    ("a" + "9" * 5000, "a1" + "0" * 5000),
])
def test_revision_numeric_boundaries_without_integer_conversion(target_version, revoke_version):
    a = accepted(version=target_version)
    b = revoked(a, version=revoke_version)
    assert context((b, a)).records == (b, a)


@pytest.mark.parametrize("target_version,revoke_version,code", [
    ("a0002", "a0001", "INVALID_REVOCATION_ORDER"),
    ("a10000", "a9999", "INVALID_REVOCATION_ORDER"),
    ("a0001", "a0001", "DUPLICATE_ACCEPTANCE_VERSION"),
])
def test_previous_or_equal_revision_is_error(target_version, revoke_version, code):
    a = accepted(version=target_version)
    b = revoked(a, version=revoke_version)
    assert_error(code, "records.acceptance_version", (a, b))


@pytest.mark.parametrize("reviewed", [date(2026, 1, 1), date(2026, 10, 22)])
def test_same_or_later_revocation_review_date(reviewed):
    a = accepted()
    b = revoked(a, reviewed_at=reviewed)
    assert context((a, b)).records == (a, b)


def test_earlier_revocation_review_date_is_error():
    a = accepted()
    b = revoked(a, reviewed_at=date(2025, 12, 31))
    assert_error("INVALID_REVOCATION_ORDER", "records.reviewed_at", (a, b))


@pytest.mark.parametrize("target_until,revoke_date,revoke_until", [
    (date(2026, 1, 1), date(2026, 2, 1), date(2026, 2, 1)),
    (date(2026, 12, 31), date(2026, 1, 1), date(2026, 1, 1)),
    (date(2000, 1, 2), date(2000, 1, 3), date(2000, 1, 4)),
])
def test_no_cross_record_valid_until_constraint_or_current_expiry(target_until, revoke_date, revoke_until):
    a = accepted(reviewed_at=date(2000, 1, 1), valid_until=target_until)
    b = revoked(a, reviewed_at=revoke_date, valid_until=revoke_until)
    result = context((a, b))
    assert _resolve_benefit_acceptance(result, a.acceptance_ref) is a
    assert _resolve_benefit_acceptance(result, b.acceptance_ref) is b


@pytest.mark.parametrize("field", FIELD_NAMES)
@pytest.mark.parametrize("operation", ["assign", "delete"])
def test_all_context_fields_are_frozen(field, operation):
    result = context((accepted(),))
    with pytest.raises(FrozenInstanceError):
        if operation == "assign":
            setattr(result, field, getattr(result, field))
        else:
            delattr(result, field)


def test_scope_and_record_remain_immutable_and_addition_uses_new_context():
    a = accepted()
    original = context((a,))
    new = context((a, revoked(a)))
    assert original.records == (a,) and len(new.records) == 2
    with pytest.raises(FrozenInstanceError):
        original.scope.quarter = 4
    with pytest.raises(FrozenInstanceError):
        original.records[0].status = BenefitAcceptanceStatus.REVOKED
    assert not hasattr(original.records, "append")


@pytest.mark.parametrize("field,value", [("policy_id", "SYNTH-OTHER"), ("scope", ApplicabilityScope("2026", None)),
                                      ("benefit_id", "SYNTH-OTHER"), ("records", (accepted(),))])
def test_all_four_fields_participate_in_equality(field, value):
    assert context() != context(**{field: value})
    assert context() == context()
    assert hash(context()) == hash(context())


def test_empty_serialization_is_literal_four_key_snapshot():
    result = context().to_dict()
    assert tuple(result) == FIELD_NAMES
    assert result == {"policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
                      "benefit_id": "SYNTH-BENEFIT", "records": []}


def test_serializer_delegates_to_existing_record_serializer_in_original_order(monkeypatch):
    a = accepted()
    b = revoked(a)
    supplied = context((b, a))
    calls = []

    def serialize(record):
        calls.append(record)
        return {"synthetic-marker": record.acceptance_ref}

    monkeypatch.setattr(PolicyBenefitAcceptance, "to_dict", serialize)
    result = supplied.to_dict()
    assert tuple(result) == FIELD_NAMES
    assert calls[0] is b and calls[1] is a and len(calls) == 2
    assert result["records"] == [{"synthetic-marker": "SYNTH-B"}, {"synthetic-marker": "SYNTH-A"}]


def test_serialization_is_json_friendly_and_nested_mutation_isolated_one_hundred_times():
    a = accepted()
    b = revoked(a)
    supplied = context((b, a))
    original = supplied.to_dict()
    assert original["records"][0]["status"] == "REVOKED"
    assert original["records"][1]["revokes_acceptance_ref"] is None
    assert original["records"][0]["reviewed_at"] == "2026-10-22"
    assert json.loads(json.dumps(original)) == original
    for _ in range(100):
        result = supplied.to_dict()
        assert result == original
        result["scope"]["quarter"] = None
        result["records"][0]["scope"]["quarter"] = None
        result["records"][0]["status"] = "ACCEPTED"
        result["records"][1].pop("revokes_acceptance_ref")
        result["records"].append({})
        assert supplied.to_dict() == original
    assert supplied.records == (b, a)


@pytest.mark.parametrize("field", [
    "current_acceptance", "selected_acceptance_ref", "current_acceptance_ref", "latest_acceptance", "latest_ref",
    "current_version", "usable", "expired", "stale", "is_stale", "data_use_date", "lookup_cache", "by_ref",
    "status", "verification_status", "monthly_amount", "profile", "dataset_version",
])
def test_context_has_no_selection_current_state_or_stored_index(field):
    supplied = context((accepted(),))
    assert not hasattr(supplied, field)
    assert field not in supplied.to_dict()


@pytest.mark.parametrize("bad", [None, {}, [], "SYNTH-CONTEXT", ContextSubclass(**context_values())])
def test_resolver_context_requires_exact_type(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_RESOLUTION_INPUT: context:"):
        _resolve_benefit_acceptance(bad, "SYNTH-A")


@pytest.mark.parametrize("bad", [None, "", " ", "\t\n", "\u3000", True, 1, {}, b"SYNTH-A",
                                      StringSubclass("SYNTH-A"), OtherStringEnum.ID])
def test_resolver_ref_requires_exact_nonblank_string_without_no_selection_semantics(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_RESOLUTION_INPUT: acceptance_ref:"):
        _resolve_benefit_acceptance(context((accepted(),)), bad)


@pytest.mark.parametrize("ref", ["SYNTH-MISSING", "synth-a", " SYNTH-A", "SYNTH-A ", "SYNTH", "a0001"])
@pytest.mark.parametrize("empty", [False, True])
def test_resolver_missing_ref_is_error_without_normalization_or_fallback(ref, empty):
    supplied = context(() if empty else (accepted(),))
    with pytest.raises(PolicyDataError, match="^ACCEPTANCE_REF_NOT_FOUND: acceptance_ref:"):
        _resolve_benefit_acceptance(supplied, ref)


def test_resolver_accepts_opaque_original_refs_and_preserves_exact_identity():
    a = accepted("  가상 ref\t")
    b = revoked(a, ref="https://invalid.example/synthetic")
    supplied = context((b, a))
    assert _resolve_benefit_acceptance(supplied, "  가상 ref\t") is a
    assert _resolve_benefit_acceptance(context=supplied, acceptance_ref=b.acceptance_ref) is b


def test_resolver_signature_is_two_required_inputs_with_exact_return_annotation():
    signature = inspect.signature(_resolve_benefit_acceptance)
    assert tuple(signature.parameters) == ("context", "acceptance_ref")
    assert all(p.default is inspect.Parameter.empty and p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
               for p in signature.parameters.values())
    assert get_type_hints(_resolve_benefit_acceptance) == {
        "context": BenefitAcceptanceContext, "acceptance_ref": str, "return": PolicyBenefitAcceptance}


def test_constructor_does_not_revalidate_records_and_resolver_does_not_revalidate_context(monkeypatch):
    a = accepted()
    b = revoked(a)
    inputs = context_values((b, a))

    def fail(*args, **kwargs):
        pytest.fail("불변 입력을 재생성/재검증했습니다")

    monkeypatch.setattr(PolicyBenefitAcceptance, "__post_init__", fail)
    monkeypatch.setattr(ApplicabilityScope, "__post_init__", fail)
    supplied = BenefitAcceptanceContext(**inputs)
    monkeypatch.setattr(BenefitAcceptanceContext, "__post_init__", fail)
    for _ in range(100):
        assert _resolve_benefit_acceptance(supplied, a.acceptance_ref) is a
        assert _resolve_benefit_acceptance(supplied, b.acceptance_ref) is b
        assert supplied.to_dict()["records"][1]["status"] == "ACCEPTED"


def test_context_input_phases_one_through_five_precede_later_errors():
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "policy_id", policy_id=None, scope=None, benefit_id=None, records=[])
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "scope", scope=None, benefit_id=None, records=[])
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "benefit_id", benefit_id=None, records=[])
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "records", records=[None])
    wrong_target = accepted(policy_id="SYNTH-OTHER")
    assert_error("INVALID_ACCEPTANCE_CONTEXT_INPUT", "records", (wrong_target, None))


def test_global_target_phase_precedes_any_duplicate_phase_and_has_defined_field_order():
    wrong = accepted(policy_id="SYNTH-OTHER", scope=ApplicabilityScope("2027", 1), benefit_id="SYNTH-OTHER")
    assert_error("ACCEPTANCE_CONTEXT_TARGET_MISMATCH", "records.policy_id", (wrong, wrong))
    first = accepted(scope=ApplicabilityScope("2027", 1), benefit_id="SYNTH-OTHER")
    second = accepted("SYNTH-SECOND", "a0002", policy_id="SYNTH-OTHER")
    assert_error("ACCEPTANCE_CONTEXT_TARGET_MISMATCH", "records.scope", (first, second))


def test_ref_duplicates_anywhere_precede_earlier_version_duplicates():
    a = accepted()
    same_version = accepted("SYNTH-C", "a0001")
    assert_error("DUPLICATE_ACCEPTANCE_REF", "records.acceptance_ref", (a, same_version, a))


def test_version_duplicate_precedes_revocation_existence():
    a = accepted()
    same_version = accepted("SYNTH-C", "a0001")
    dangling = revoked(accepted("SYNTH-MISSING"), version="a0003")
    assert_error("DUPLICATE_ACCEPTANCE_VERSION", "records.acceptance_version", (dangling, a, same_version))


def test_all_revocation_existence_precedes_target_status():
    a = accepted()
    b = revoked(a)
    c = revoked(b, "SYNTH-C", "a0003")
    dangling = revoked(accepted("SYNTH-MISSING"), "SYNTH-D", "a0004")
    assert_error("REVOCATION_TARGET_NOT_FOUND", "records.revokes_acceptance_ref", (a, b, c, dangling))


def test_all_revocation_status_precedes_snapshot_binding():
    a = accepted()
    b = revoked(a, benefit_version="b0002")
    c = revoked(b, "SYNTH-C", "a0003")
    assert_error("INVALID_REVOCATION_TARGET_STATUS", "records.revokes_acceptance_ref", (a, b, c))


def test_all_snapshot_bindings_precede_duplicate_revocations_and_keep_record_then_field_order():
    a = accepted()
    b = revoked(a)
    c = revoked(a, "SYNTH-C", "a0003", benefit_version="b0002")
    assert_error("REVOCATION_SNAPSHOT_MISMATCH", "records.benefit_version", (a, b, c))
    d = revoked(a, "SYNTH-D", "a0004", coverage_inventory_version="i0002", benefit_version="b0002")
    assert_error("REVOCATION_SNAPSHOT_MISMATCH", "records.benefit_version", (a, c, d))
    assert_error("REVOCATION_SNAPSHOT_MISMATCH", "records.coverage_inventory_version", (a, d))


def test_duplicate_revocation_precedes_revision_order():
    a = accepted(version="a0003")
    b = revoked(a, version="a0001")
    c = revoked(a, "SYNTH-C", "a0002")
    assert_error("DUPLICATE_REVOCATION_TARGET", "records.revokes_acceptance_ref", (a, b, c))


def test_all_revision_checks_precede_dates_on_any_edge():
    a = accepted()
    b = revoked(a, reviewed_at=date(2025, 1, 1))
    c = accepted("SYNTH-C", "a0004")
    d = revoked(c, "SYNTH-D", "a0003")
    assert_error("INVALID_REVOCATION_ORDER", "records.acceptance_version", (a, b, c, d))


def test_error_messages_are_deterministic_and_never_echo_ref_payloads():
    a = accepted("SYNTH-private-ref-that-must-not-appear")
    b = revoked(a, ref="SYNTH-private-revoker", revokes_acceptance_ref="SYNTH-private-missing-target")
    messages = {assert_error("REVOCATION_TARGET_NOT_FOUND", "records.revokes_acceptance_ref", (a, b))
                for _ in range(100)}
    assert len(messages) == 1
    assert not any(ref in next(iter(messages)) for ref in (a.acceptance_ref, b.acceptance_ref, b.revokes_acceptance_ref))
    with pytest.raises(PolicyDataError) as error:
        _resolve_benefit_acceptance(context((a,)), "SYNTH-private-query")
    assert "SYNTH-private-query" not in str(error.value)


def test_public_export_adds_context_only_and_keeps_resolver_private():
    assert policy_data.BenefitAcceptanceContext is BenefitAcceptanceContext
    assert policy_data.__all__.count("BenefitAcceptanceContext") == 1
    assert "_resolve_benefit_acceptance" not in policy_data.__all__
    assert not hasattr(policy_data, "_resolve_benefit_acceptance")


def test_current_operations_do_not_depend_on_external_evaluation_hashing_io_or_latest_selection(monkeypatch):
    # 해당 함수들의 실행 의존만 확인해 다른 미래 모듈/함수 추가를 금지하지 않는다.
    functions = [BenefitAcceptanceContext.__post_init__, BenefitAcceptanceContext.to_dict,
                 domain._identifier, domain._invalid, domain._revision_key, _resolve_benefit_acceptance]
    forbidden = {"evaluate_eligibility_coverage", "fingerprint_benefit_snapshot", "fingerprint_condition_inventory",
                 "fingerprint_policy_tree", "fingerprint_rule_subtree", "calculate_cashflow", "today", "now",
                 "open", "read_text", "read_bytes", "environ", "requests", "max", "sorted", "sort", "int"}
    for function in functions:
        assert forbidden.isdisjoint(function.__code__.co_names)
    a = accepted()
    b = revoked(a)

    def fail(*args, **kwargs):
        pytest.fail("Context/조회가 외부 계산을 호출했습니다")

    for name in ("evaluate_eligibility_coverage", "fingerprint_benefit_snapshot", "fingerprint_condition_inventory",
                 "fingerprint_policy_tree", "fingerprint_rule_subtree"):
        monkeypatch.setattr(policy_data, name, fail)
    supplied = context((b, a))
    assert _resolve_benefit_acceptance(supplied, a.acceptance_ref) is a
    assert supplied.to_dict()["records"][0]["status"] == "REVOKED"
