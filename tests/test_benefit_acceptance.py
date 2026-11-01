"""합성 결정 기록의 구조만 검증한다. 실제 검토·발급·현재 사용을 인증하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, MISSING, fields, replace
from datetime import date, datetime
from enum import Enum
import inspect
import json
from pathlib import Path
import re
from typing import get_type_hints

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine import policy_data
from backend.policy_engine.policy_data import (
    ApplicabilityScope, BenefitAcceptanceStatus, PolicyBenefitAcceptance,
)
from backend.policy_engine.policy_data import benefit_acceptance as domain


FIELD_NAMES = (
    "acceptance_ref", "acceptance_version", "status", "policy_id", "scope", "benefit_id",
    "coverage_inventory_version", "coverage_inventory_fingerprint", "coverage_rule_version",
    "coverage_policy_tree_fingerprint", "coverage_dataset_version",
    "coverage_source_registry_fingerprint", "coverage_implementation_fingerprint",
    "benefit_version", "benefit_fingerprint", "benefit_dataset_version",
    "benefit_source_registry_fingerprint", "reviewed_at", "valid_until", "review_artifact_ref",
    "revokes_acceptance_ref",
)
FINGERPRINT_FIELDS = (
    "coverage_inventory_fingerprint", "coverage_policy_tree_fingerprint",
    "coverage_source_registry_fingerprint", "coverage_implementation_fingerprint",
    "benefit_fingerprint", "benefit_source_registry_fingerprint",
)
VERSION_FIELDS = (
    ("acceptance_version", "a"), ("coverage_inventory_version", "i"), ("benefit_version", "b"),
)
NONBLANK_FIELDS = (
    "acceptance_ref", "coverage_rule_version", "coverage_dataset_version",
    "benefit_dataset_version", "review_artifact_ref", "revokes_acceptance_ref",
)


def values(**changes):
    # 지문은 형식 검사용 자리값이다. 외부 정의/실제 원본에서 계산하지 않는다.
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A1", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": date(2026, 1, 1),
        "valid_until": date(2026, 12, 31), "review_artifact_ref": "SYNTH-REVIEW-A1",
        "revokes_acceptance_ref": None, **changes,
    }


def revoked_values(**changes):
    return values(**{
        "acceptance_ref": "SYNTH-ACCEPT-A2", "acceptance_version": "a0002",
        "status": BenefitAcceptanceStatus.REVOKED, "reviewed_at": date(2026, 10, 22),
        "review_artifact_ref": "SYNTH-REVIEW-A2", "revokes_acceptance_ref": "SYNTH-ACCEPT-A1",
        **changes,
    })


def expected(**changes):
    # 실제 serializer로 기대값을 계산하지 않는다.
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A1", "acceptance_version": "a0001", "status": "ACCEPTED",
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "benefit_id": "SYNTH-BENEFIT", "coverage_inventory_version": "i0001",
        "coverage_inventory_fingerprint": "1" * 64, "coverage_rule_version": "r0001",
        "coverage_policy_tree_fingerprint": "2" * 64, "coverage_dataset_version": "SYNTH-D1",
        "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": "2026-01-01",
        "valid_until": "2026-12-31", "review_artifact_ref": "SYNTH-REVIEW-A1",
        "revokes_acceptance_ref": None, **changes,
    }


class StringSubclass(str):
    pass


class DateSubclass(date):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class OtherStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"


def assert_invalid(field, **changes):
    with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE: " + field + ": "):
        PolicyBenefitAcceptance(**values(**changes))


def test_exact_twenty_one_fields_order_types_slots_and_required_keyword_only_signature():
    actual = fields(PolicyBenefitAcceptance)
    assert tuple(field.name for field in actual) == FIELD_NAMES
    assert PolicyBenefitAcceptance.__slots__ == FIELD_NAMES
    assert all(field.default is MISSING and field.default_factory is MISSING for field in actual)
    assert all(field.kw_only and field.compare for field in actual)
    expected_types = {name: str for name in FIELD_NAMES}
    expected_types.update(status=BenefitAcceptanceStatus, scope=ApplicabilityScope,
                          reviewed_at=date, valid_until=date, revokes_acceptance_ref=str | None)
    assert get_type_hints(PolicyBenefitAcceptance) == expected_types
    signature = inspect.signature(PolicyBenefitAcceptance)
    assert tuple(signature.parameters) == FIELD_NAMES
    assert all(param.kind is inspect.Parameter.KEYWORD_ONLY
               and param.default is inspect.Parameter.empty for param in signature.parameters.values())
    assert PolicyBenefitAcceptance.__dataclass_params__.frozen


def test_field_names_and_order_match_approved_spec_table():
    document = (Path(__file__).resolve().parents[1] / "docs/BENEFIT_ACCEPTANCE_RECORD_SPEC.md").read_text(
        encoding="utf-8")
    section = document.split("## 14. ", 1)[1].split("## 15. ", 1)[0]
    table = re.findall(r"^\| ([0-9]+) \| ([a-z_]+) \|", section, flags=re.MULTILINE)
    assert table == [(str(index), name) for index, name in enumerate(FIELD_NAMES, 1)]


def test_enum_has_exactly_two_canonical_string_members_without_aliases():
    assert BenefitAcceptanceStatus.__members__ == {
        "ACCEPTED": BenefitAcceptanceStatus.ACCEPTED, "REVOKED": BenefitAcceptanceStatus.REVOKED,
    }
    assert tuple(member.value for member in BenefitAcceptanceStatus) == ("ACCEPTED", "REVOKED")
    assert issubclass(BenefitAcceptanceStatus, str) and issubclass(BenefitAcceptanceStatus, Enum)
    assert isinstance(BenefitAcceptanceStatus.ACCEPTED, str)


@pytest.mark.parametrize("field", FIELD_NAMES)
def test_every_field_is_required_even_nullable_revocation(field):
    inputs = values()
    del inputs[field]
    with pytest.raises(TypeError):
        PolicyBenefitAcceptance(**inputs)


def test_positional_and_extra_fields_are_python_type_errors():
    with pytest.raises(TypeError):
        PolicyBenefitAcceptance(*values().values())
    with pytest.raises(TypeError):
        PolicyBenefitAcceptance(**values(), usable=True)


@pytest.mark.parametrize("field", FIELD_NAMES)
@pytest.mark.parametrize("operation", ["assign", "delete"])
def test_all_stored_fields_are_frozen(field, operation):
    record = PolicyBenefitAcceptance(**values())
    with pytest.raises(FrozenInstanceError):
        if operation == "assign":
            setattr(record, field, getattr(record, field))
        else:
            delattr(record, field)


@pytest.mark.parametrize("quarter", [1, 2, 3, 4, None])
def test_exact_nested_scope_is_preserved_and_immutable(quarter):
    scope = ApplicabilityScope("2026", quarter)
    record = PolicyBenefitAcceptance(**values(scope=scope))
    assert record.scope is scope
    assert record.to_dict()["scope"] == {"edition_id": "2026", "quarter": quarter}
    for field in ("edition_id", "quarter"):
        with pytest.raises(FrozenInstanceError):
            setattr(record.scope, field, None)
        with pytest.raises(FrozenInstanceError):
            delattr(record.scope, field)
    assert not hasattr(record, "__dict__")


@pytest.mark.parametrize("bad", [None, {}, {"edition_id": "2026", "quarter": 3}, "2026-Q3",
                                      ("2026", 3), True, ScopeSubclass("2026", 3)])
def test_scope_raw_values_and_subclass_are_rejected(bad):
    assert_invalid("scope", scope=bad)


@pytest.mark.parametrize("bad", ["ACCEPTED", "REVOKED", "STALE", "EXPIRED", "MISSING",
                                      None, True, 1, OtherStatus.ACCEPTED])
def test_status_does_not_convert_raw_strings_or_other_enums(bad):
    assert_invalid("status", status=bad)


@pytest.mark.parametrize("field", NONBLANK_FIELDS)
@pytest.mark.parametrize("bad", ["", " ", "\t\n", "\u3000", None, True, 1, 1.0, b"X", [], {},
                                      StringSubclass("SYNTH-X"), OtherStatus.ACCEPTED])
def test_opaque_refs_and_nonblank_rule_dataset_contract(field, bad):
    if field == "revokes_acceptance_ref" and bad is None:
        with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE: revokes_acceptance_ref:"):
            PolicyBenefitAcceptance(**revoked_values(revokes_acceptance_ref=None))
    else:
        assert_invalid(field, **{field: bad})


@pytest.mark.parametrize("field", ["acceptance_ref", "review_artifact_ref", "revokes_acceptance_ref"])
@pytest.mark.parametrize("value", ["  합성 참조\t", "https://invalid.example/synthetic", "C:/SYNTH/missing.txt"])
def test_opaque_refs_are_preserved_without_normalization_or_lookup(field, value):
    inputs = revoked_values(**{field: value}) if field == "revokes_acceptance_ref" else values(**{field: value})
    record = PolicyBenefitAcceptance(**inputs)
    assert getattr(record, field) is value
    assert record.to_dict()[field] == value


@pytest.mark.parametrize("value", ["release-x", "r1", "r0000", " 배포 규칙\t", "버전\n설명"])
def test_rule_version_stays_nonblank_not_new_r_version_grammar(value):
    record = PolicyBenefitAcceptance(**values(coverage_rule_version=value))
    assert record.coverage_rule_version is value


@pytest.mark.parametrize("value", ["D", "  합성 배포\t", "2026/임의-version"])
def test_dataset_version_preserves_existing_nonblank_contract(value):
    record = PolicyBenefitAcceptance(**values(coverage_dataset_version=value, benefit_dataset_version=value))
    assert record.coverage_dataset_version is value
    assert record.benefit_dataset_version is value


@pytest.mark.parametrize("field", ["policy_id", "benefit_id"])
@pytest.mark.parametrize("bad", ["", " ", "synth-policy", "SYNTH_POLICY", "-A", "A-", "A--B", "A B",
                                      " A", "A ", "A\n", "가상", "Ａ", None, True, 1, b"A",
                                      StringSubclass("SYNTH-ID"), OtherStatus.ACCEPTED])
def test_ids_use_existing_canonical_grammar_without_conversion(field, bad):
    assert_invalid(field, **{field: bad})


@pytest.mark.parametrize("value", ["A", "0", "SYNTH-2026-X"])
def test_canonical_id_boundaries_are_valid(value):
    record = PolicyBenefitAcceptance(**values(policy_id=value, benefit_id=value))
    assert record.policy_id is value and record.benefit_id is value


@pytest.mark.parametrize("field,prefix", VERSION_FIELDS)
@pytest.mark.parametrize("suffix", ["0001", "0010", "9999", "10000", "12345678901234567890"])
def test_versions_keep_positive_padded_grammar(field, prefix, suffix):
    value = prefix + suffix
    assert getattr(PolicyBenefitAcceptance(**values(**{field: value})), field) == value


@pytest.mark.parametrize("field,prefix", VERSION_FIELDS)
@pytest.mark.parametrize("suffix", ["0000", "0", "1", "001", "00001", "01000", "00000", "-001",
                                          "+001", "0001.0", "０００１", "٠٠٠١", "0001\n", "0001 "])
def test_invalid_version_suffixes_are_rejected(field, prefix, suffix):
    assert_invalid(field, **{field: prefix + suffix})


@pytest.mark.parametrize("field,prefix", VERSION_FIELDS)
@pytest.mark.parametrize("bad", [None, True, 1, b"a0001", "A0001", "x0001", " a0001",
                                      StringSubclass("a0001"), OtherStatus.ACCEPTED])
def test_version_exact_type_and_prefix(field, prefix, bad):
    if type(bad) is StringSubclass:
        bad = StringSubclass(prefix + "0001")
    assert_invalid(field, **{field: bad})
    assert_invalid(field, **{field: prefix.upper() + "0001"})


@pytest.mark.parametrize("field", FINGERPRINT_FIELDS)
@pytest.mark.parametrize("bad", [None, True, 1, b"a" * 64, "", "a" * 63, "a" * 65, "A" * 64,
                                      "g" * 64, "0x" + "a" * 64, "a" * 64 + "\n", " " + "a" * 64,
                                      StringSubclass("a" * 64)])
def test_all_six_fingerprints_require_exact_lowercase_hex64(field, bad):
    assert_invalid(field, **{field: bad})


@pytest.mark.parametrize("field", FINGERPRINT_FIELDS)
def test_each_fingerprint_accepts_mixed_lowercase_hex_without_recalculation(field):
    value = "0123456789abcdef" * 4
    changes = {field: value}
    if field in ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"):
        changes.update(coverage_source_registry_fingerprint=value, benefit_source_registry_fingerprint=value)
    record = PolicyBenefitAcceptance(**values(**changes))
    assert getattr(record, field) is value


@pytest.mark.parametrize("field", ["reviewed_at", "valid_until"])
@pytest.mark.parametrize("bad", [None, True, 1, "2026-01-01", datetime(2026, 1, 1),
                                      DateSubclass(2026, 1, 1)])
def test_dates_are_required_exact_date_without_parser_or_truncation(field, bad):
    assert_invalid(field, **{field: bad})


@pytest.mark.parametrize("status", list(BenefitAcceptanceStatus))
@pytest.mark.parametrize("day", [date(2024, 2, 29), date(2026, 1, 1), date(1, 1, 1), date(9999, 12, 31)])
def test_same_day_and_leap_day_are_valid_for_both_statuses(status, day):
    inputs = revoked_values() if status is BenefitAcceptanceStatus.REVOKED else values()
    inputs.update(reviewed_at=day, valid_until=day)
    record = PolicyBenefitAcceptance(**inputs)
    assert record.reviewed_at is day and record.valid_until is day
    assert record.to_dict()["reviewed_at"] == day.isoformat()


@pytest.mark.parametrize("status", list(BenefitAcceptanceStatus))
def test_date_order_is_enforced_for_both_statuses(status):
    inputs = revoked_values() if status is BenefitAcceptanceStatus.REVOKED else values()
    inputs.update(reviewed_at=date(2026, 12, 31), valid_until=date(2026, 12, 30))
    with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE: valid_until:"):
        PolicyBenefitAcceptance(**inputs)


@pytest.mark.parametrize("status", list(BenefitAcceptanceStatus))
@pytest.mark.parametrize("field,value", [
    ("coverage_dataset_version", "SYNTH-D2"), ("benefit_dataset_version", "SYNTH-D2"),
    ("coverage_source_registry_fingerprint", "6" * 64),
    ("benefit_source_registry_fingerprint", "6" * 64),
])
def test_mixed_release_is_local_data_error_even_when_definition_fingerprint_is_same(status, field, value):
    inputs = revoked_values() if status is BenefitAcceptanceStatus.REVOKED else values()
    inputs[field] = value
    error_field = "benefit_dataset_version" if "dataset" in field else "benefit_source_registry_fingerprint"
    with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE: " + error_field + ":"):
        PolicyBenefitAcceptance(**inputs)


def test_provenance_can_change_together_without_changing_definition_fingerprint():
    old = PolicyBenefitAcceptance(**values())
    new = replace(old, coverage_dataset_version="SYNTH-D2", benefit_dataset_version="SYNTH-D2",
                  coverage_source_registry_fingerprint="6" * 64,
                  benefit_source_registry_fingerprint="6" * 64)
    assert old.benefit_fingerprint == new.benefit_fingerprint
    assert old != new


def test_accepted_cannot_include_revocation_ref():
    assert_invalid("revokes_acceptance_ref", revokes_acceptance_ref="SYNTH-OLD")


def test_revoked_requires_ref_and_rejects_self_reference():
    for ref in (None, "", "  ", "SYNTH-ACCEPT-A2"):
        with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE: revokes_acceptance_ref:"):
            PolicyBenefitAcceptance(**revoked_values(revokes_acceptance_ref=ref))


def test_revocation_can_be_constructed_without_target_resolution_or_revision_comparison():
    record = PolicyBenefitAcceptance(**revoked_values(
        acceptance_version="a0001", revokes_acceptance_ref="SYNTH-MISSING-OR-LATER-RECORD",
        reviewed_at=date(2000, 1, 1), valid_until=date(2000, 1, 1)))
    assert record.status is BenefitAcceptanceStatus.REVOKED
    assert record.revokes_acceptance_ref == "SYNTH-MISSING-OR-LATER-RECORD"
    assert record.valid_until == date(2000, 1, 1)


def test_new_revocation_revision_does_not_mutate_original_accepted_record():
    original = PolicyBenefitAcceptance(**values())
    before = original.to_dict()
    revoked = PolicyBenefitAcceptance(**revoked_values())
    assert revoked.revokes_acceptance_ref == original.acceptance_ref
    assert revoked.acceptance_version == "a0002"
    assert original.to_dict() == before == expected()
    assert original.status is BenefitAcceptanceStatus.ACCEPTED


@pytest.mark.parametrize("field", ["coverage_inventory_fingerprint", "coverage_policy_tree_fingerprint",
                                   "benefit_fingerprint", "coverage_implementation_fingerprint"])
def test_separate_records_do_not_perform_same_version_conflict_checks(field):
    old = PolicyBenefitAcceptance(**values())
    different = PolicyBenefitAcceptance(**values(**{field: "6" * 64}))
    assert old != different
    assert old.acceptance_version == different.acceptance_version


def test_historical_bindings_are_valid_without_current_snapshot_or_clock():
    record = PolicyBenefitAcceptance(**values(reviewed_at=date(2000, 1, 1), valid_until=date(2000, 12, 31)))
    assert record.coverage_rule_version == "r0001"
    assert record.benefit_version == "b0001"
    assert record.status is BenefitAcceptanceStatus.ACCEPTED


@pytest.mark.parametrize("field", FIELD_NAMES)
def test_equality_includes_each_of_twenty_one_fields(field):
    record = PolicyBenefitAcceptance(**values())
    assert record == PolicyBenefitAcceptance(**values())
    assert hash(record) == hash(PolicyBenefitAcceptance(**values()))
    alternatives = {
        "acceptance_ref": "SYNTH-OTHER", "acceptance_version": "a0002",
        "status": BenefitAcceptanceStatus.REVOKED, "policy_id": "SYNTH-OTHER-POLICY",
        "scope": ApplicabilityScope("2026", 4), "benefit_id": "SYNTH-OTHER-BENEFIT",
        "coverage_inventory_version": "i0002", "coverage_inventory_fingerprint": "6" * 64,
        "coverage_rule_version": "release-x", "coverage_policy_tree_fingerprint": "6" * 64,
        "coverage_dataset_version": "SYNTH-D2", "coverage_source_registry_fingerprint": "6" * 64,
        "coverage_implementation_fingerprint": "6" * 64, "benefit_version": "b0002",
        "benefit_fingerprint": "6" * 64, "benefit_dataset_version": "SYNTH-D2",
        "benefit_source_registry_fingerprint": "6" * 64, "reviewed_at": date(2026, 1, 2),
        "valid_until": date(2027, 1, 1), "review_artifact_ref": "SYNTH-OTHER-REVIEW",
        "revokes_acceptance_ref": "SYNTH-OTHER-TARGET",
    }
    # 비교할 두 record 모두 유효해야 하므로 결합 필드에는 같은 보조값을 공급한다.
    changes = {field: alternatives[field]}
    baseline_changes = {}
    if field == "status":
        changes["revokes_acceptance_ref"] = "SYNTH-OLD"
    elif field == "revokes_acceptance_ref":
        baseline_changes = {"status": BenefitAcceptanceStatus.REVOKED, "revokes_acceptance_ref": "SYNTH-OLD"}
        changes["status"] = BenefitAcceptanceStatus.REVOKED
    elif "dataset_version" in field:
        changes.update(coverage_dataset_version="SYNTH-D2", benefit_dataset_version="SYNTH-D2")
    elif "source_registry_fingerprint" in field:
        changes.update(coverage_source_registry_fingerprint="6" * 64,
                       benefit_source_registry_fingerprint="6" * 64)
    assert PolicyBenefitAcceptance(**values(**baseline_changes)) != PolicyBenefitAcceptance(**values(**changes))


@pytest.mark.parametrize("status", list(BenefitAcceptanceStatus))
def test_serializer_has_exact_twenty_one_ordered_keys_and_literal_values(status):
    inputs = revoked_values() if status is BenefitAcceptanceStatus.REVOKED else values()
    wanted = expected() if status is BenefitAcceptanceStatus.ACCEPTED else expected(
        acceptance_ref="SYNTH-ACCEPT-A2", acceptance_version="a0002", status="REVOKED",
        reviewed_at="2026-10-22", review_artifact_ref="SYNTH-REVIEW-A2",
        revokes_acceptance_ref="SYNTH-ACCEPT-A1")
    result = PolicyBenefitAcceptance(**inputs).to_dict()
    assert tuple(result) == FIELD_NAMES and len(result) == 21
    assert result == wanted
    assert type(result["status"]) is str
    assert json.loads(json.dumps(result)) == wanted


def test_repeated_serialization_is_deterministic_isolated_and_does_not_mutate_inputs():
    inputs = values()
    before = inputs.copy()
    record = PolicyBenefitAcceptance(**inputs)
    for _ in range(100):
        result = record.to_dict()
        assert result == expected()
        result["scope"]["quarter"] = 4
        result["scope"]["extra"] = True
        result["status"] = "REVOKED"
        result.pop("revokes_acceptance_ref")
        assert record.to_dict() == expected()
    assert inputs == before
    assert record.scope is inputs["scope"]


@pytest.mark.parametrize("field", [
    "stale", "is_stale", "expired", "usable", "acceptance_reason", "coverage_result", "benefit_snapshot",
    "accepted_terms", "bridge_supported", "monthly_amount", "current_date", "verification_status",
])
def test_record_has_no_current_state_or_foreign_object_fields(field):
    record = PolicyBenefitAcceptance(**values())
    assert not hasattr(record, field)
    assert field not in record.to_dict()


def test_field_validation_follows_approved_order_before_cross_field_invariants():
    # 각 타입 오류를 동시에 주어21필드 순서가 첫 오류를 정하는지 확인한다.
    for index, field in enumerate(FIELD_NAMES):
        bad = {later: [] for later in FIELD_NAMES[index:]}
        assert_invalid(field, **bad)
    assert_invalid("review_artifact_ref", reviewed_at=date(2027, 1, 1), review_artifact_ref="")
    assert_invalid("valid_until", reviewed_at=date(2027, 1, 1), benefit_dataset_version="SYNTH-D2",
                   benefit_source_registry_fingerprint="6" * 64, revokes_acceptance_ref="SYNTH-OLD")
    assert_invalid("benefit_dataset_version", benefit_dataset_version="SYNTH-D2",
                   benefit_source_registry_fingerprint="6" * 64, revokes_acceptance_ref="SYNTH-OLD")
    assert_invalid("benefit_source_registry_fingerprint", benefit_source_registry_fingerprint="6" * 64,
                   revokes_acceptance_ref="SYNTH-OLD")


def test_validation_errors_do_not_echo_input_payload():
    secret = "SYNTH-private-payload-should-not-appear"
    for field, bad in [("policy_id", secret), ("benefit_fingerprint", secret),
                       ("acceptance_version", secret), ("reviewed_at", secret)]:
        with pytest.raises(PolicyDataError) as error:
            PolicyBenefitAcceptance(**values(**{field: bad}))
        assert str(error.value).startswith("INVALID_BENEFIT_ACCEPTANCE: " + field + ": ")
        assert secret not in str(error.value)


def test_public_exports_expose_exact_two_new_domain_types():
    for name, cls in (("BenefitAcceptanceStatus", BenefitAcceptanceStatus),
                      ("PolicyBenefitAcceptance", PolicyBenefitAcceptance)):
        assert getattr(policy_data, name) is cls
        assert policy_data.__all__.count(name) == 1
    assert "_invalid" not in policy_data.__all__
    assert "_version" not in policy_data.__all__


def test_model_dependencies_and_behavior_have_no_external_calculation_or_io(monkeypatch):
    tree = ast.parse(inspect.getsource(domain))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    assert imports == {"dataclasses", "datetime", "enum", "re", "errors", "eligibility_coverage"}
    functions = [PolicyBenefitAcceptance.__post_init__, PolicyBenefitAcceptance.to_dict,
                 domain._nonblank, domain._identifier, domain._version, domain._fingerprint, domain._invalid]
    forbidden = {
        "fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree",
        "fingerprint_benefit_snapshot", "evaluate_eligibility_coverage", "today", "now", "open",
        "resolve", "read_text", "read_bytes", "hashlib", "requests", "calculate_cashflow",
    }
    for function in functions:
        assert forbidden.isdisjoint(function.__code__.co_names)

    def fail(*args, **kwargs):
        pytest.fail("결정 기록 모델이 외부 계산을 호출했습니다")

    monkeypatch.setattr(policy_data, "evaluate_eligibility_coverage", fail)
    monkeypatch.setattr(policy_data, "fingerprint_benefit_snapshot", fail)
    for name in ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree"):
        monkeypatch.setattr(policy_data, name, fail)
    assert PolicyBenefitAcceptance(**values()).to_dict() == expected()
    assert PolicyBenefitAcceptance(**revoked_values()).status is BenefitAcceptanceStatus.REVOKED
