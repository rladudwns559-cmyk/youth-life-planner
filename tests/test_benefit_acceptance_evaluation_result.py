"""합성 결과 값의 표현·로컬 조합만 검증한다. 실제 current 평가/gate 성공을 검증하지 않는다."""

from dataclasses import InitVar, FrozenInstanceError, MISSING, fields, replace
from datetime import date, datetime
from enum import Enum
import inspect
from itertools import combinations
import json
from pathlib import Path
import re
from typing import get_type_hints

import pytest

from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import ApplicabilityScope, BenefitAcceptanceStatus
from backend.policy_engine.policy_data import benefit_acceptance_evaluation_result as domain
from backend.policy_engine.policy_data.benefit_acceptance_evaluation_result import (
    BenefitAcceptanceEvaluation as Evaluation, BenefitAcceptanceEvaluationStatus as Status,
    BenefitAcceptanceReason as Reason, _create_benefit_acceptance_evaluation as create,
)


FIELD_NAMES = (
    "policy_id", "scope", "benefit_id", "data_use_date", "selected_acceptance_ref",
    "selected_acceptance_version", "selected_acceptance_status", "revocation_acceptance_ref", "reasons",
)
REASON_NAMES = (
    "NO_ACCEPTANCE_CONTEXT", "NO_ACCEPTANCE_RECORDS", "ACCEPTANCE_NOT_SELECTED", "ACCEPTANCE_REVOKED",
    "ACCEPTANCE_NOT_YET_VALID", "ACCEPTANCE_EXPIRED", "COVERAGE_NOT_FULL", "POLICY_NOT_VERIFIED",
    "BENEFIT_METADATA_NOT_REVIEWED", "COVERAGE_SNAPSHOT_CHANGED", "BENEFIT_SNAPSHOT_CHANGED",
    "BENEFIT_PROVENANCE_CHANGED",
)
NO_SELECTION = (Reason.NO_ACCEPTANCE_CONTEXT, Reason.NO_ACCEPTANCE_RECORDS, Reason.ACCEPTANCE_NOT_SELECTED)
INDEPENDENT = (Reason.COVERAGE_NOT_FULL, Reason.POLICY_NOT_VERIFIED, Reason.BENEFIT_METADATA_NOT_REVIEWED)
SELECTED_ONLY = (Reason.ACCEPTANCE_REVOKED, Reason.ACCEPTANCE_NOT_YET_VALID, Reason.ACCEPTANCE_EXPIRED,
                 Reason.COVERAGE_SNAPSHOT_CHANGED, Reason.BENEFIT_SNAPSHOT_CHANGED, Reason.BENEFIT_PROVENANCE_CHANGED)


def values(**changes):
    return {
        "policy_id": "SYNTH-POLICY", "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "data_use_date": date(2026, 10, 22), "selected_acceptance_ref": "SYNTH-A",
        "selected_acceptance_version": "a0001", "selected_acceptance_status": BenefitAcceptanceStatus.ACCEPTED,
        "revocation_acceptance_ref": None, "reasons": (), **changes,
    }


def unselected_values(reason=Reason.NO_ACCEPTANCE_CONTEXT, **changes):
    return values(**{"selected_acceptance_ref": None, "selected_acceptance_version": None,
                     "selected_acceptance_status": None, "reasons": (reason,), **changes})


def revoked_values(**changes):
    return values(**{"selected_acceptance_ref": "SYNTH-B", "selected_acceptance_version": "a0002",
                     "selected_acceptance_status": BenefitAcceptanceStatus.REVOKED,
                     "revocation_acceptance_ref": "SYNTH-B", "reasons": (Reason.ACCEPTANCE_REVOKED,), **changes})


def expected(**changes):
    return {
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "benefit_id": "SYNTH-BENEFIT", "data_use_date": "2026-10-22",
        "selected_acceptance_ref": "SYNTH-A", "selected_acceptance_version": "a0001",
        "selected_acceptance_status": "ACCEPTED", "revocation_acceptance_ref": None,
        "reasons": [], "status": "USABLE", **changes,
    }


def assert_invalid(field, **changes):
    with pytest.raises(PolicyDataError) as error:
        create(**values(**changes))
    assert type(error.value) is PolicyDataError
    assert str(error.value).startswith("INVALID_ACCEPTANCE_EVALUATION_RESULT: " + field + ": ")
    return str(error.value)


class StringSubclass(str):
    pass


class DateSubclass(date):
    pass


class TupleSubclass(tuple):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class OtherEnum(str, Enum):
    ACCEPTED = "ACCEPTED"
    COVERAGE_NOT_FULL = "COVERAGE_NOT_FULL"


def test_exact_nine_stored_fields_types_slots_required_keyword_only_and_nonstored_token():
    actual = fields(Evaluation)
    assert tuple(f.name for f in actual) == FIELD_NAMES == Evaluation.__slots__
    assert all(f.default is MISSING and f.default_factory is MISSING and f.kw_only and f.compare for f in actual)
    hints = get_type_hints(Evaluation)
    token_hint = hints.pop("_creation_token")
    assert isinstance(token_hint, InitVar) and token_hint.type is object
    assert hints == {
        "policy_id": str, "scope": ApplicabilityScope, "benefit_id": str, "data_use_date": date,
        "selected_acceptance_ref": str | None, "selected_acceptance_version": str | None,
        "selected_acceptance_status": BenefitAcceptanceStatus | None, "revocation_acceptance_ref": str | None,
        "reasons": tuple[Reason, ...],
    }
    parameters = inspect.signature(Evaluation).parameters
    assert tuple(parameters) == FIELD_NAMES + ("_creation_token",)
    assert all(parameters[name].default is inspect.Parameter.empty for name in FIELD_NAMES)
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters.values())
    assert parameters["_creation_token"].default is None
    assert Evaluation.__dataclass_params__.frozen
    assert not hasattr(create(**values()), "__dict__")


def test_field_and_enum_names_match_approved_spec():
    text = (Path(__file__).resolve().parents[1] / "docs/BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md").read_text(encoding="utf-8")
    section = text.split("## 5. ", 1)[1].split("## 6. ", 1)[0]
    assert re.findall(r"^\| ([0-9]+) \| ([a-z_]+) \|", section, re.M) == [
        (str(i), name) for i, name in enumerate(FIELD_NAMES, 1)]
    section = text.split("## 13. ", 1)[1].split("## 14. ", 1)[0]
    assert re.findall(r"^\| ([0-9]+) \| ([A-Z_]+) \|", section, re.M) == [
        (str(i), name) for i, name in enumerate(REASON_NAMES, 1)]


def test_status_and_reason_enums_have_exact_members_values_order_and_no_aliases():
    assert tuple(Status.__members__) == ("USABLE", "UNUSABLE")
    assert tuple(s.value for s in Status) == ("USABLE", "UNUSABLE")
    assert tuple(Reason.__members__) == REASON_NAMES == tuple(r.value for r in Reason)
    for cls in (Status, Reason):
        assert issubclass(cls, str) and issubclass(cls, Enum)
        assert len(cls.__members__) == len(tuple(cls))


@pytest.mark.parametrize("field", FIELD_NAMES)
def test_every_field_is_required_even_optional_values(field):
    inputs = values()
    del inputs[field]
    with pytest.raises(TypeError):
        create(**inputs)


@pytest.mark.parametrize("token", [None, False, True, object(), "SYNTH-TOKEN"])
def test_direct_constructor_without_private_token_is_rejected_before_field_checks(token):
    with pytest.raises(TypeError, match="내부 factory"):
        Evaluation(**values(policy_id=None), _creation_token=token)


def test_direct_construction_replace_status_and_factory_extra_args_are_rejected():
    with pytest.raises(TypeError):
        Evaluation(**values())
    with pytest.raises(TypeError):
        Evaluation(*values().values())
    with pytest.raises(TypeError):
        create(*values().values())
    for change in ({}, {"reasons": (Reason.POLICY_NOT_VERIFIED,)}):
        with pytest.raises(TypeError, match="내부 factory"):
            replace(create(**values()), **change)
    for change in ({"status": Status.UNUSABLE}, {"usable": True}, {"_creation_token": object()}):
        with pytest.raises(TypeError):
            create(**values(), **change)


def test_factory_forwards_nine_original_values_and_private_token_once(monkeypatch):
    inputs = values()
    captured = []
    result_marker = object()

    def build(**kwargs):
        captured.append(kwargs)
        return result_marker

    monkeypatch.setattr(domain, "BenefitAcceptanceEvaluation", build)
    assert create(**inputs) is result_marker
    assert len(captured) == 1
    assert tuple(captured[0]) == FIELD_NAMES + ("_creation_token",)
    assert captured[0]["_creation_token"] is domain._RESULT_CREATION_TOKEN
    for name in FIELD_NAMES:
        assert captured[0][name] is inputs[name]


def test_factory_propagates_original_model_error_without_fallback(monkeypatch):
    failure = PolicyDataError("SYNTH-MODEL-ERROR")

    def build(**kwargs):
        raise failure

    monkeypatch.setattr(domain, "BenefitAcceptanceEvaluation", build)
    with pytest.raises(PolicyDataError) as error:
        create(**values())
    assert error.value is failure


@pytest.mark.parametrize("field", ["policy_id", "benefit_id"])
@pytest.mark.parametrize("bad", [None, True, 1, b"A", "", " ", "lower", "SYNTH_ID", "A--B", "A-", "-A",
                                      " A", "A\n", "Ａ", StringSubclass("SYNTH-A"), OtherEnum.ACCEPTED])
def test_ids_keep_existing_exact_canonical_grammar(field, bad):
    assert_invalid(field, **{field: bad})


@pytest.mark.parametrize("bad", [None, {}, {"edition_id": "2026", "quarter": 3}, "2026-Q3", True,
                                      ScopeSubclass("2026", 3)])
def test_scope_requires_exact_existing_value(bad):
    assert_invalid("scope", scope=bad)


@pytest.mark.parametrize("quarter", [1, 2, 3, 4, None])
def test_scope_original_is_preserved_and_not_inferred_from_date(quarter):
    scope = ApplicabilityScope("2026", quarter)
    inputs = values(scope=scope, data_use_date=date(1999, 1, 1))
    result = create(**inputs)
    assert result.scope is scope
    assert result.data_use_date is inputs["data_use_date"]
    assert result.to_dict()["scope"] == {"edition_id": "2026", "quarter": quarter}


@pytest.mark.parametrize("bad", [None, True, 1, "2026-10-22", datetime(2026, 10, 22),
                                      DateSubclass(2026, 10, 22)])
def test_data_use_date_is_exact_date_without_parsing_or_current_default(bad):
    assert_invalid("data_use_date", data_use_date=bad)


@pytest.mark.parametrize("day", [date(1, 1, 1), date(2024, 2, 29), date(9999, 12, 31)])
def test_valid_calendar_values_do_not_recalculate_claimed_expiry(day):
    result = create(**values(data_use_date=day, reasons=(Reason.ACCEPTANCE_EXPIRED,)))
    assert result.data_use_date is day
    assert result.reasons == (Reason.ACCEPTANCE_EXPIRED,)
    assert result.to_dict()["data_use_date"] == day.isoformat()


@pytest.mark.parametrize("field", ["selected_acceptance_ref", "revocation_acceptance_ref"])
@pytest.mark.parametrize("bad", ["", " ", "\t\n", "\u3000", True, 1, b"SYNTH-A", {},
                                      StringSubclass("SYNTH-A"), OtherEnum.ACCEPTED])
def test_optional_refs_require_exact_nonblank_strings(field, bad):
    assert_invalid(field, **{field: bad})


def test_opaque_selection_and_revocation_refs_preserve_whitespace_and_unicode():
    a = "  가상 A\t"
    b = "  가상 B\n"
    result = create(**values(selected_acceptance_ref=a, revocation_acceptance_ref=b,
                             reasons=(Reason.ACCEPTANCE_REVOKED,)))
    assert result.selected_acceptance_ref is a and result.revocation_acceptance_ref is b
    assert result.to_dict()["selected_acceptance_ref"] == a
    direct = create(**revoked_values(selected_acceptance_ref=b, revocation_acceptance_ref=b))
    assert direct.selected_acceptance_ref is b and direct.revocation_acceptance_ref is b


@pytest.mark.parametrize("bad", ["a0000", "a1", "a001", "a00001", "a01000", "A0001", "b0001", " a0001",
                                      "a0001\n", "a０００１", True, 1, b"a0001", StringSubclass("a0001")])
def test_optional_selected_version_uses_existing_a_grammar(bad):
    assert_invalid("selected_acceptance_version", selected_acceptance_version=bad)


@pytest.mark.parametrize("version", ["a0001", "a9999", "a10000", "a" + "1" * 5000])
def test_selected_version_boundaries_are_explicit_and_preserved(version):
    assert create(**values(selected_acceptance_version=version)).selected_acceptance_version is version


@pytest.mark.parametrize("bad", ["ACCEPTED", "REVOKED", True, 1, OtherEnum.ACCEPTED, Status.USABLE, Reason.ACCEPTANCE_REVOKED])
def test_selected_status_requires_original_record_enum_without_conversion(bad):
    assert_invalid("selected_acceptance_status", selected_acceptance_status=bad)


@pytest.mark.parametrize("bad", [None, [], [Reason.COVERAGE_NOT_FULL], "COVERAGE_NOT_FULL", TupleSubclass(()),
                                      ("COVERAGE_NOT_FULL",), (OtherEnum.COVERAGE_NOT_FULL,), (Status.UNUSABLE,),
                                      (Reason.COVERAGE_NOT_FULL, None)])
def test_reasons_requires_exact_tuple_and_exact_reason_members(bad):
    assert_invalid("reasons", reasons=bad)


@pytest.mark.parametrize("reason", tuple(Reason))
def test_duplicate_reason_rejected_before_semantic_combinations(reason):
    message = assert_invalid("reasons", reasons=(reason, reason))
    assert "canonical" in message


def test_reversed_canonical_order_is_rejected_without_sorting():
    reasons = (Reason.POLICY_NOT_VERIFIED, Reason.COVERAGE_NOT_FULL)
    message = assert_invalid("reasons", reasons=reasons)
    assert "canonical" in message
    assert reasons == (Reason.POLICY_NOT_VERIFIED, Reason.COVERAGE_NOT_FULL)


@pytest.mark.parametrize("reason", NO_SELECTION)
def test_each_no_selection_branch_with_independent_gate_reasons_is_valid(reason):
    reasons = (reason,) + INDEPENDENT
    result = create(**unselected_values(reason, reasons=reasons))
    assert result.status is Status.UNUSABLE and result.reasons is reasons
    assert result.selected_acceptance_ref is None
    assert result.selected_acceptance_version is None
    assert result.selected_acceptance_status is None
    assert result.revocation_acceptance_ref is None


@pytest.mark.parametrize("reason", NO_SELECTION)
def test_each_no_selection_branch_serializes_all_null_metadata(reason):
    result = create(**unselected_values(reason))
    assert result.to_dict() == expected(
        selected_acceptance_ref=None, selected_acceptance_version=None, selected_acceptance_status=None,
        reasons=[reason.value], status="UNUSABLE")


@pytest.mark.parametrize("missing_fields", [
    ("selected_acceptance_ref",), ("selected_acceptance_version",), ("selected_acceptance_status",),
    ("selected_acceptance_ref", "selected_acceptance_version"),
    ("selected_acceptance_ref", "selected_acceptance_status"),
    ("selected_acceptance_version", "selected_acceptance_status"),
])
def test_all_six_partial_selection_metadata_patterns_are_rejected(missing_fields):
    assert_invalid("selected_acceptance_ref", **{name: None for name in missing_fields})


@pytest.mark.parametrize("reasons", [(), INDEPENDENT])
def test_no_selection_requires_one_of_three_selection_reasons(reasons):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: reasons:"):
        create(**unselected_values(reasons=reasons))


@pytest.mark.parametrize("reasons", tuple(combinations(NO_SELECTION, 2)) + (NO_SELECTION,))
def test_no_selection_reasons_are_mutually_exclusive(reasons):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: reasons:"):
        create(**unselected_values(reasons=reasons))


@pytest.mark.parametrize("reason", NO_SELECTION)
def test_selected_metadata_cannot_claim_no_selection(reason):
    assert_invalid("reasons", reasons=(reason,))


@pytest.mark.parametrize("reason", SELECTED_ONLY)
def test_unselected_cannot_claim_selected_only_date_revocation_or_snapshot_comparisons(reason):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: reasons:"):
        create(**unselected_values(reasons=(Reason.NO_ACCEPTANCE_CONTEXT, reason)))


def test_unselected_cannot_have_revocation_evidence():
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: revocation_acceptance_ref:"):
        create(**unselected_values(revocation_acceptance_ref="SYNTH-B"))


def test_accepted_with_no_reasons_is_structural_usable_not_a_gate_execution():
    result = create(**values())
    assert result.status is Status.USABLE
    assert result.selected_acceptance_status is BenefitAcceptanceStatus.ACCEPTED
    assert result.reasons == () and result.revocation_acceptance_ref is None
    assert result.to_dict() == expected()


@pytest.mark.parametrize("reason", (Reason.ACCEPTANCE_NOT_YET_VALID, Reason.ACCEPTANCE_EXPIRED) + INDEPENDENT + (
    Reason.COVERAGE_SNAPSHOT_CHANGED, Reason.BENEFIT_SNAPSHOT_CHANGED, Reason.BENEFIT_PROVENANCE_CHANGED,
))
def test_each_selected_normal_reason_can_be_represented_without_running_its_gate(reason):
    result = create(**values(reasons=(reason,)))
    assert result.status is Status.UNUSABLE and result.reasons == (reason,)


def test_accepted_a_with_revocation_evidence_b_preserves_both_refs():
    result = create(**values(revocation_acceptance_ref="SYNTH-B", reasons=(Reason.ACCEPTANCE_REVOKED,)))
    assert result.selected_acceptance_ref == "SYNTH-A"
    assert result.revocation_acceptance_ref == "SYNTH-B"
    assert result.selected_acceptance_status is BenefitAcceptanceStatus.ACCEPTED
    assert result.to_dict() == expected(revocation_acceptance_ref="SYNTH-B",
                                        reasons=["ACCEPTANCE_REVOKED"], status="UNUSABLE")


def test_direct_revoked_b_uses_b_itself_as_evidence_not_record_self_revocation():
    result = create(**revoked_values())
    assert result.status is Status.UNUSABLE
    assert result.selected_acceptance_ref == result.revocation_acceptance_ref == "SYNTH-B"
    assert result.selected_acceptance_status is BenefitAcceptanceStatus.REVOKED
    assert result.to_dict() == expected(selected_acceptance_ref="SYNTH-B", selected_acceptance_version="a0002",
        selected_acceptance_status="REVOKED", revocation_acceptance_ref="SYNTH-B",
        reasons=["ACCEPTANCE_REVOKED"], status="UNUSABLE")


@pytest.mark.parametrize("metadata", [
    {"revocation_acceptance_ref": "SYNTH-B", "reasons": ()},
    {"revocation_acceptance_ref": None, "reasons": (Reason.ACCEPTANCE_REVOKED,)},
    {"revocation_acceptance_ref": "SYNTH-A", "reasons": (Reason.ACCEPTANCE_REVOKED,)},
])
def test_accepted_revocation_evidence_and_reason_must_agree(metadata):
    assert_invalid("revocation_acceptance_ref", **metadata)


@pytest.mark.parametrize("changes", [
    {"revocation_acceptance_ref": None}, {"revocation_acceptance_ref": "SYNTH-OTHER"},
    {"reasons": ()}, {"revocation_acceptance_ref": None, "reasons": ()},
])
def test_direct_revoked_selection_requires_self_evidence_and_revoked_reason(changes):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: revocation_acceptance_ref:"):
        create(**revoked_values(**changes))


@pytest.mark.parametrize("direct_revoked", [False, True])
def test_before_and_after_date_reasons_are_mutually_exclusive(direct_revoked):
    reasons = (Reason.ACCEPTANCE_NOT_YET_VALID, Reason.ACCEPTANCE_EXPIRED)
    inputs = values(reasons=reasons)
    if direct_revoked:
        inputs = revoked_values(reasons=(Reason.ACCEPTANCE_REVOKED,) + reasons)
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: reasons:"):
        create(**inputs)


@pytest.mark.parametrize("reason", [Reason.ACCEPTANCE_NOT_YET_VALID, Reason.ACCEPTANCE_EXPIRED])
def test_direct_revoked_cannot_claim_accepted_date_gate_reasons(reason):
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_EVALUATION_RESULT: reasons:"):
        create(**revoked_values(reasons=(Reason.ACCEPTANCE_REVOKED, reason)))


def test_multiple_independent_and_snapshot_reasons_keep_canonical_subset_without_recalculation():
    reasons = (Reason.ACCEPTANCE_REVOKED, Reason.ACCEPTANCE_EXPIRED, Reason.COVERAGE_NOT_FULL,
               Reason.POLICY_NOT_VERIFIED, Reason.BENEFIT_METADATA_NOT_REVIEWED,
               Reason.COVERAGE_SNAPSHOT_CHANGED, Reason.BENEFIT_SNAPSHOT_CHANGED, Reason.BENEFIT_PROVENANCE_CHANGED)
    inputs = values(revocation_acceptance_ref="SYNTH-B", reasons=reasons)
    result = create(**inputs)
    assert result.reasons is reasons and result.status is Status.UNUSABLE
    assert result.to_dict()["reasons"] == [
        "ACCEPTANCE_REVOKED", "ACCEPTANCE_EXPIRED", "COVERAGE_NOT_FULL", "POLICY_NOT_VERIFIED",
        "BENEFIT_METADATA_NOT_REVIEWED", "COVERAGE_SNAPSHOT_CHANGED", "BENEFIT_SNAPSHOT_CHANGED", "BENEFIT_PROVENANCE_CHANGED",
    ]
    direct = create(**revoked_values(reasons=(Reason.ACCEPTANCE_REVOKED, Reason.COVERAGE_SNAPSHOT_CHANGED,
                                            Reason.BENEFIT_SNAPSHOT_CHANGED, Reason.BENEFIT_PROVENANCE_CHANGED)))
    assert direct.status is Status.UNUSABLE


@pytest.mark.parametrize("field", FIELD_NAMES)
@pytest.mark.parametrize("operation", ["assign", "delete"])
def test_nine_fields_are_frozen(field, operation):
    result = create(**values())
    with pytest.raises(FrozenInstanceError):
        if operation == "assign":
            setattr(result, field, getattr(result, field))
        else:
            delattr(result, field)


def test_status_is_read_only_property_and_not_constructor_or_serialized_input_state():
    result = create(**values())
    assert isinstance(Evaluation.status, property) and Evaluation.status.fset is None
    assert "status" not in {field.name for field in fields(Evaluation)}
    for operation in (lambda: setattr(result, "status", Status.UNUSABLE), lambda: delattr(result, "status")):
        with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
            operation()
    assert result.status is Status.USABLE


@pytest.mark.parametrize("field", FIELD_NAMES)
def test_equality_includes_every_stored_field(field):
    base = values()
    changes = {
        "policy_id": "SYNTH-OTHER", "scope": ApplicabilityScope("2026", None), "benefit_id": "SYNTH-OTHER",
        "data_use_date": date(2026, 10, 23), "selected_acceptance_ref": "SYNTH-OTHER",
        "selected_acceptance_version": "a0002", "selected_acceptance_status": BenefitAcceptanceStatus.REVOKED,
        "revocation_acceptance_ref": "SYNTH-OTHER-EVIDENCE", "reasons": (Reason.POLICY_NOT_VERIFIED,),
    }
    altered = {field: changes[field]}
    if field in ("selected_acceptance_status", "revocation_acceptance_ref"):
        base = values(revocation_acceptance_ref="SYNTH-A", selected_acceptance_status=BenefitAcceptanceStatus.REVOKED,
                      reasons=(Reason.ACCEPTANCE_REVOKED,)) if field == "selected_acceptance_status" else values(
            revocation_acceptance_ref="SYNTH-B", reasons=(Reason.ACCEPTANCE_REVOKED,))
        if field == "selected_acceptance_status":
            altered = {"selected_acceptance_status": BenefitAcceptanceStatus.ACCEPTED,
                       "revocation_acceptance_ref": "SYNTH-B"}
    original = create(**base)
    assert original == create(**base) and hash(original) == hash(create(**base))
    assert original != create(**{**base, **altered})


def test_ten_ordered_serialization_keys_original_inputs_and_nested_mutation_isolation_one_hundred_times():
    reasons = (Reason.ACCEPTANCE_REVOKED, Reason.ACCEPTANCE_EXPIRED, Reason.POLICY_NOT_VERIFIED)
    inputs = values(revocation_acceptance_ref="SYNTH-B", reasons=reasons)
    before = inputs.copy()
    wanted = expected(revocation_acceptance_ref="SYNTH-B", status="UNUSABLE",
                      reasons=["ACCEPTANCE_REVOKED", "ACCEPTANCE_EXPIRED", "POLICY_NOT_VERIFIED"])
    result = create(**inputs)
    for _ in range(100):
        current = create(**inputs)
        assert current == result and current.scope is inputs["scope"] and current.reasons is reasons
        serialized = current.to_dict()
        assert tuple(serialized) == FIELD_NAMES + ("status",) and len(serialized) == 10
        assert serialized == wanted == json.loads(json.dumps(serialized))
        serialized["scope"]["quarter"] = None
        serialized["reasons"].clear()
        serialized["selected_acceptance_status"] = "REVOKED"
        serialized.pop("revocation_acceptance_ref")
        assert result.to_dict() == wanted
    assert inputs == before and result.reasons is reasons
    with pytest.raises(FrozenInstanceError):
        result.scope.quarter = None


def test_validation_order_token_fields_reason_order_selection_revocation_and_date_combinations():
    with pytest.raises(TypeError, match="내부 factory"):
        Evaluation(**values(policy_id=None, reasons=[]))
    for index, field in enumerate(FIELD_NAMES):
        assert_invalid(field, **{name: [] for name in FIELD_NAMES[index:]})
    message = assert_invalid("reasons", selected_acceptance_version=None,
                             reasons=(Reason.POLICY_NOT_VERIFIED, Reason.COVERAGE_NOT_FULL))
    assert "canonical" in message
    assert_invalid("selected_acceptance_ref", selected_acceptance_version=None, reasons=NO_SELECTION)
    message = assert_invalid("reasons", **unselected_values(reasons=(), revocation_acceptance_ref="SYNTH-B"))
    assert "정확히 하나" in message
    assert_invalid("revocation_acceptance_ref", **unselected_values(
        reasons=(Reason.NO_ACCEPTANCE_CONTEXT, Reason.ACCEPTANCE_REVOKED), revocation_acceptance_ref="SYNTH-B"))
    message = assert_invalid("reasons", revocation_acceptance_ref="SYNTH-B", reasons=(Reason.NO_ACCEPTANCE_CONTEXT,))
    assert "미선택 사유" in message
    assert_invalid("revocation_acceptance_ref", revocation_acceptance_ref="SYNTH-B",
                   reasons=(Reason.ACCEPTANCE_NOT_YET_VALID, Reason.ACCEPTANCE_EXPIRED))


def test_errors_are_deterministic_and_do_not_echo_input_payload():
    secret = "SYNTH-private-invalid-input"
    messages = {assert_invalid("selected_acceptance_version", selected_acceptance_version=secret) for _ in range(100)}
    assert len(messages) == 1 and secret not in next(iter(messages))


@pytest.mark.parametrize("field", [
    "usable", "accepted", "expired", "stale", "current_context", "selected_record", "coverage_result",
    "benefit_snapshot", "fingerprint", "current_date", "bridge_amount", "from_dict", "deserialize",
])
def test_result_has_no_extra_state_loaders_or_convenience_properties(field):
    result = create(**values())
    assert not hasattr(result, field)
    assert field not in result.to_dict()


def test_internal_types_and_factory_are_not_added_to_package_public_exports():
    for name in ("BenefitAcceptanceEvaluation", "BenefitAcceptanceEvaluationStatus", "BenefitAcceptanceReason",
                 "_create_benefit_acceptance_evaluation"):
        assert name not in policy_data.__all__
        assert not hasattr(policy_data, name)


def test_model_current_function_dependencies_exclude_actual_evaluation_and_io(monkeypatch):
    # 현재 함수의 실행 의존만 검사하며 다른 미래 모듈/함수를 일괄 금지하지 않는다.
    functions = [Evaluation.__post_init__, Evaluation.status.fget, Evaluation.to_dict, create,
                 domain._identifier, domain._optional_ref, domain._invalid]
    forbidden = {"_resolve_benefit_acceptance", "evaluate_benefit_acceptance", "evaluate_eligibility_coverage",
                 "fingerprint_benefit_snapshot", "fingerprint_condition_inventory", "fingerprint_policy_tree",
                 "fingerprint_rule_subtree", "validate_dataset_manifest", "validate_envelope_sources",
                 "calculate_cashflow", "today", "now", "open", "read_text", "read_bytes", "environ",
                 "requests", "sorted", "sort"}
    for function in functions:
        assert forbidden.isdisjoint(function.__code__.co_names)

    def fail(*args, **kwargs):
        pytest.fail("결과 모델이 실제 평가/gate를 실행했습니다")

    for name in ("evaluate_eligibility_coverage", "fingerprint_benefit_snapshot", "validate_dataset_manifest",
                 "validate_envelope_sources"):
        monkeypatch.setattr(policy_data, name, fail)
    assert create(**values()).status is Status.USABLE
    assert create(**revoked_values()).status is Status.UNUSABLE
