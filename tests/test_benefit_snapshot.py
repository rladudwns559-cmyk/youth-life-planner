"""합성 정의로16필드의 구조·불변성·직렬화만 검증한다. 지문/승인은 계산하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, MISSING, fields, replace
from decimal import Decimal
from enum import Enum, IntEnum
import inspect
import json
from typing import get_type_hints

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine import policy_data
from backend.policy_engine.policy_data import (
    ApplicabilityScope, BenefitAmountType, BenefitMedium, BenefitPaymentCadence,
    BenefitRestriction, BenefitSnapshot, SourceBinding,
)
from backend.policy_engine.policy_data import benefit_snapshot as domain
from backend.policy_engine.sources import SourceRegistry, SourceValidationError


FIELD_NAMES = (
    "policy_id", "scope", "benefit_id", "benefit_version", "amount_type", "amount_krw",
    "amount_description", "payment_cadence", "benefit_medium", "restriction",
    "restriction_details", "applicable_months", "benefit_evidence_refs", "source_bindings",
    "dataset_version", "source_registry_fingerprint",
)
ENUM_MEMBERS = {
    "BenefitAmountType": ("FIXED", "VARIABLE", "UNKNOWN"),
    "BenefitPaymentCadence": (
        "MONTHLY", "QUARTERLY", "SEMIANNUAL", "ANNUAL", "ONE_TIME", "IRREGULAR", "UNKNOWN",
    ),
    "BenefitMedium": (
        "UNRESTRICTED_CASH", "RESTRICTED_CASH_EQUIVALENT", "LOCAL_CURRENCY", "POINTS",
        "VOUCHER", "IN_KIND", "SAVINGS_MATCH", "LOAN", "INTEREST_SUPPORT", "UNKNOWN",
    ),
    "BenefitRestriction": ("UNRESTRICTED", "RESTRICTED", "UNKNOWN"),
}


def values(**changes):
    return {
        "policy_id": "SYNTH-POLICY", "scope": ApplicabilityScope("2026", 3),
        "benefit_id": "SYNTH-BENEFIT", "benefit_version": "b0001",
        "amount_type": BenefitAmountType.FIXED, "amount_krw": 100000,
        "amount_description": None, "payment_cadence": BenefitPaymentCadence.MONTHLY,
        "benefit_medium": BenefitMedium.UNRESTRICTED_CASH,
        "restriction": BenefitRestriction.UNRESTRICTED, "restriction_details": None,
        "applicable_months": ("2026-09",),
        "benefit_evidence_refs": ("SYNTH-SOURCE#benefit-definition",),
        "source_bindings": (SourceBinding("SYNTH-SOURCE", "d0001"),),
        "dataset_version": "SYNTH-DATASET-1", "source_registry_fingerprint": "a" * 64,
        **changes,
    }


def expected(**changes):
    return {
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "benefit_id": "SYNTH-BENEFIT", "benefit_version": "b0001", "amount_type": "FIXED",
        "amount_krw": 100000, "amount_description": None, "payment_cadence": "MONTHLY",
        "benefit_medium": "UNRESTRICTED_CASH", "restriction": "UNRESTRICTED",
        "restriction_details": None, "applicable_months": ["2026-09"],
        "benefit_evidence_refs": ["SYNTH-SOURCE#benefit-definition"],
        "source_bindings": [{"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"}],
        "dataset_version": "SYNTH-DATASET-1", "source_registry_fingerprint": "a" * 64,
        **changes,
    }


class StringSubclass(str):
    pass


class IntSubclass(int):
    pass


class TupleSubclass(tuple):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class BindingSubclass(SourceBinding):
    pass


class OtherStringEnum(str, Enum):
    FIXED = "FIXED"
    MONTHLY = "MONTHLY"
    UNRESTRICTED_CASH = "UNRESTRICTED_CASH"
    UNRESTRICTED = "UNRESTRICTED"


class OtherIntEnum(IntEnum):
    ZERO = 0


def test_exact_sixteen_stored_fields_annotations_slots_and_required_keyword_only_signature():
    actual = fields(BenefitSnapshot)
    assert tuple(field.name for field in actual) == FIELD_NAMES
    assert BenefitSnapshot.__slots__ == FIELD_NAMES
    assert all(field.default is MISSING and field.default_factory is MISSING for field in actual)
    assert all(field.kw_only and field.compare for field in actual)
    assert get_type_hints(BenefitSnapshot) == {
        "policy_id": str, "scope": ApplicabilityScope, "benefit_id": str,
        "benefit_version": str, "amount_type": BenefitAmountType, "amount_krw": int | None,
        "amount_description": str | None, "payment_cadence": BenefitPaymentCadence,
        "benefit_medium": BenefitMedium, "restriction": BenefitRestriction,
        "restriction_details": str | None, "applicable_months": tuple[str, ...] | None,
        "benefit_evidence_refs": tuple[str, ...], "source_bindings": tuple[SourceBinding, ...],
        "dataset_version": str, "source_registry_fingerprint": str,
    }
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY
               for p in inspect.signature(BenefitSnapshot).parameters.values())
    assert BenefitSnapshot.__dataclass_params__.frozen


def test_exact_four_enum_types_members_values_and_public_exports():
    actual = {name: value for name, value in vars(domain).items()
              if inspect.isclass(value) and value.__module__ == domain.__name__ and issubclass(value, Enum)}
    assert set(actual) == set(ENUM_MEMBERS)
    for name, names in ENUM_MEMBERS.items():
        enum = actual[name]
        assert issubclass(enum, str)
        assert tuple(enum.__members__) == names
        assert tuple(member.value for member in enum) == names
        assert getattr(policy_data, name) is enum and name in policy_data.__all__
    assert policy_data.BenefitSnapshot is BenefitSnapshot
    assert "BenefitSnapshot" in policy_data.__all__


@pytest.mark.parametrize("name", FIELD_NAMES)
def test_every_field_including_nullable_fields_is_required(name):
    supplied = values()
    del supplied[name]
    with pytest.raises(TypeError, match=name):
        BenefitSnapshot(**supplied)


def test_constructor_does_not_accept_positional_or_unknown_fields():
    with pytest.raises(TypeError):
        BenefitSnapshot(*values().values())
    with pytest.raises(TypeError, match="benefit_fingerprint"):
        BenefitSnapshot(**values(), benefit_fingerprint="a" * 64)


def test_fixed_monthly_cash_preserves_exact_original_nested_values_and_expected_serializer():
    supplied = values()
    snapshot = BenefitSnapshot(**supplied)
    for name in ("scope", "source_bindings", "applicable_months", "benefit_evidence_refs"):
        assert getattr(snapshot, name) is supplied[name]
    assert snapshot.source_bindings[0] is supplied["source_bindings"][0]
    assert snapshot.to_dict() == expected()
    assert tuple(snapshot.to_dict()) == FIELD_NAMES
    assert len(snapshot.to_dict()) == 16
    assert json.loads(json.dumps(snapshot.to_dict())) == expected()
    assert not hasattr(snapshot, "__dict__")


def test_quarterly_local_currency_keeps_original_amount_cadence_and_restriction():
    snapshot = BenefitSnapshot(**values(
        payment_cadence=BenefitPaymentCadence.QUARTERLY, benefit_medium=BenefitMedium.LOCAL_CURRENCY,
        restriction=BenefitRestriction.RESTRICTED, restriction_details="지역 내 사용",
    ))
    assert snapshot.to_dict() == expected(
        payment_cadence="QUARTERLY", benefit_medium="LOCAL_CURRENCY",
        restriction="RESTRICTED", restriction_details="지역 내 사용",
    )
    assert snapshot.amount_krw == 100000


@pytest.mark.parametrize("amount", [0, 1, 100000, 10**100])
def test_fixed_exact_nonnegative_int_has_no_rounding_or_cap(amount):
    snapshot = BenefitSnapshot(**values(amount_krw=amount))
    assert snapshot.amount_krw is amount
    assert snapshot.to_dict()["amount_krw"] == amount


@pytest.mark.parametrize("amount", [-1, True, False, 1.0, "100000", Decimal("100000"), IntSubclass(1), OtherIntEnum.ZERO])
def test_amount_scalar_is_exact_int_or_none_without_conversion(amount):
    with pytest.raises(PolicyDataError, match="amount_krw"):
        BenefitSnapshot(**values(amount_krw=amount))


@pytest.mark.parametrize("amount_type,amount,description", [
    (BenefitAmountType.VARIABLE, None, "가구 조건에 따라 금액이 달라짐"),
    (BenefitAmountType.VARIABLE, None, "  합성 범위100~200원\n"),
    (BenefitAmountType.UNKNOWN, None, None),
])
def test_nonfixed_or_unknown_definition_is_valid_without_fabricated_zero(amount_type, amount, description):
    snapshot = BenefitSnapshot(**values(amount_type=amount_type, amount_krw=amount, amount_description=description))
    assert snapshot.to_dict() == expected(amount_type=amount_type.value, amount_krw=None, amount_description=description)
    assert snapshot.amount_krw is None and snapshot.amount_description is description


@pytest.mark.parametrize("amount_type,amount,description,error_field", [
    (BenefitAmountType.FIXED, None, None, "amount_krw"),
    (BenefitAmountType.FIXED, 100000, "설명", "amount_description"),
    (BenefitAmountType.VARIABLE, 0, "가변", "amount_krw"),
    (BenefitAmountType.VARIABLE, 100000, "가변", "amount_krw"),
    (BenefitAmountType.VARIABLE, None, None, "amount_description"),
    (BenefitAmountType.UNKNOWN, 0, None, "amount_krw"),
    (BenefitAmountType.UNKNOWN, None, "미정", "amount_description"),
])
def test_amount_cross_field_contract(amount_type, amount, description, error_field):
    with pytest.raises(PolicyDataError, match=error_field):
        BenefitSnapshot(**values(amount_type=amount_type, amount_krw=amount, amount_description=description))


def test_fully_unknown_metadata_is_a_structural_partial_definition():
    snapshot = BenefitSnapshot(**values(
        amount_type=BenefitAmountType.UNKNOWN, amount_krw=None,
        payment_cadence=BenefitPaymentCadence.UNKNOWN, benefit_medium=BenefitMedium.UNKNOWN,
        restriction=BenefitRestriction.UNKNOWN, applicable_months=None,
    ))
    assert snapshot.to_dict() == expected(
        amount_type="UNKNOWN", amount_krw=None, payment_cadence="UNKNOWN",
        benefit_medium="UNKNOWN", restriction="UNKNOWN", applicable_months=None,
    )


@pytest.mark.parametrize("cadence", list(BenefitPaymentCadence))
def test_all_seven_cadences_are_structurally_supported(cadence):
    snapshot = BenefitSnapshot(**values(payment_cadence=cadence))
    assert snapshot.payment_cadence is cadence
    assert snapshot.to_dict()["payment_cadence"] == cadence.value


@pytest.mark.parametrize("medium", list(BenefitMedium))
def test_all_ten_media_are_definitions_not_bridge_support_decisions(medium):
    restricted = medium is BenefitMedium.RESTRICTED_CASH_EQUIVALENT
    snapshot = BenefitSnapshot(**values(
        benefit_medium=medium,
        restriction=BenefitRestriction.RESTRICTED if restricted else BenefitRestriction.UNRESTRICTED,
        restriction_details="합성 목적 제한" if restricted else None,
    ))
    assert snapshot.benefit_medium is medium
    assert snapshot.to_dict()["benefit_medium"] == medium.value


@pytest.mark.parametrize("restriction,details", [
    (BenefitRestriction.UNRESTRICTED, None),
    (BenefitRestriction.RESTRICTED, " 교육 목적 사용\n"),
    (BenefitRestriction.UNKNOWN, None),
])
def test_restriction_is_not_inferred_for_other_media(restriction, details):
    snapshot = BenefitSnapshot(**values(
        benefit_medium=BenefitMedium.IN_KIND, restriction=restriction, restriction_details=details,
    ))
    assert snapshot.restriction is restriction and snapshot.restriction_details is details


@pytest.mark.parametrize("restriction,details", [
    (BenefitRestriction.RESTRICTED, None),
    (BenefitRestriction.UNRESTRICTED, "제한 설명"),
    (BenefitRestriction.UNKNOWN, "미정 설명"),
])
def test_restriction_detail_cross_field_contract(restriction, details):
    with pytest.raises(PolicyDataError, match="restriction_details"):
        BenefitSnapshot(**values(benefit_medium=BenefitMedium.IN_KIND, restriction=restriction, restriction_details=details))


@pytest.mark.parametrize("medium,restriction,details", [
    (BenefitMedium.UNRESTRICTED_CASH, BenefitRestriction.RESTRICTED, "제한"),
    (BenefitMedium.UNRESTRICTED_CASH, BenefitRestriction.UNKNOWN, None),
    (BenefitMedium.RESTRICTED_CASH_EQUIVALENT, BenefitRestriction.UNRESTRICTED, None),
    (BenefitMedium.RESTRICTED_CASH_EQUIVALENT, BenefitRestriction.UNKNOWN, None),
])
def test_two_explicit_cash_medium_contradictions_are_rejected(medium, restriction, details):
    with pytest.raises(PolicyDataError, match="restriction:"):
        BenefitSnapshot(**values(benefit_medium=medium, restriction=restriction, restriction_details=details))


@pytest.mark.parametrize("field", ["amount_description", "restriction_details"])
@pytest.mark.parametrize("bad", ["", " ", "\t\n", 1, True, [], StringSubclass("설명")])
def test_description_fields_require_exact_nonblank_string_if_present(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        BenefitSnapshot(**values(**{field: bad}))


@pytest.mark.parametrize("field,raw,foreign", [
    ("amount_type", "FIXED", OtherStringEnum.FIXED),
    ("payment_cadence", "MONTHLY", OtherStringEnum.MONTHLY),
    ("benefit_medium", "UNRESTRICTED_CASH", OtherStringEnum.UNRESTRICTED_CASH),
    ("restriction", "UNRESTRICTED", OtherStringEnum.UNRESTRICTED),
])
def test_enum_fields_reject_raw_strings_other_enums_and_wrong_types(field, raw, foreign):
    for bad in (raw, foreign, None, True, 1, object()):
        with pytest.raises(PolicyDataError, match=field):
            BenefitSnapshot(**values(**{field: bad}))


@pytest.mark.parametrize("field", ["policy_id", "benefit_id"])
@pytest.mark.parametrize("bad", [None, True, 1, {}, "", " ", "a-b", "A_B", "A--B", "-A", "A-", "한글", " A", "A\n", StringSubclass("A")])
def test_identifiers_are_canonical_exact_strings_without_normalization(field, bad):
    with pytest.raises(PolicyDataError, match=field):
        BenefitSnapshot(**values(**{field: bad}))


@pytest.mark.parametrize("identifier", ["A", "1", "A-1", "SYNTH-POLICY-A"])
def test_valid_id_grammar_is_shared_without_extra_policy_specific_restrictions(identifier):
    snapshot = BenefitSnapshot(**values(policy_id=identifier, benefit_id=identifier))
    assert snapshot.policy_id == snapshot.benefit_id == identifier


@pytest.mark.parametrize("scope", [None, {}, {"edition_id": "2026", "quarter": 3}, "2026-Q3", True, ScopeSubclass("2026", 3)])
def test_scope_requires_exact_existing_object(scope):
    with pytest.raises(PolicyDataError, match="scope"):
        BenefitSnapshot(**values(scope=scope))


@pytest.mark.parametrize("edition,quarter,months", [
    ("2026", 3, ("2026-01", "2026-12")),
    ("2026", None, tuple(f"2026-{month:02d}" for month in range(1, 13))),
    ("0000", 1, ("0001-01",)),
    ("2026", 4, ("2027-01",)),
])
def test_scope_and_payment_months_are_not_inferred_or_artificially_clipped(edition, quarter, months):
    scope = ApplicabilityScope(edition, quarter)
    snapshot = BenefitSnapshot(**values(scope=scope, applicable_months=months))
    assert snapshot.scope is scope and snapshot.applicable_months is months


@pytest.mark.parametrize("version", ["b0001", "b9999", "b10000", "b100000", "b999999999999"])
def test_valid_b_versions_preserved(version):
    assert BenefitSnapshot(**values(benefit_version=version)).benefit_version is version


@pytest.mark.parametrize("version", [None, 1, True, "", "b0000", "b1", "b001", "b00001", "B0001", "r0001", " b0001", "b0001\n", "b０００１", StringSubclass("b0001")])
def test_invalid_b_versions_are_not_guessed_or_generated(version):
    with pytest.raises(PolicyDataError, match="benefit_version"):
        BenefitSnapshot(**values(benefit_version=version))


@pytest.mark.parametrize("months", [None, ("2026-09",), ("0001-01", "9999-12"), ("2026-03", "2026-06", "2026-09", "2026-12")])
def test_valid_months_preserved_without_cadence_inference(months):
    snapshot = BenefitSnapshot(**values(applicable_months=months))
    assert snapshot.applicable_months is months
    assert snapshot.to_dict()["applicable_months"] == (None if months is None else list(months))


@pytest.mark.parametrize("months", [
    (), [], ["2026-09"], "2026-09", {}, True, TupleSubclass(("2026-09",)),
    ("2026-09", "2026-09"), ("2026-12", "2026-03"), ("2026-00",), ("2026-13",),
    ("0000-01",), ("10000-01",), ("26-01",), ("2026-1",), ("２０２６-01",),
    ("2026-01 ",), ("2026-01\n",), (1,), (True,), (None,), (StringSubclass("2026-01"),),
])
def test_bad_month_collections_or_elements_are_rejected_without_sorting_or_conversion(months):
    with pytest.raises(PolicyDataError, match="applicable_months"):
        BenefitSnapshot(**values(applicable_months=months))


@pytest.mark.parametrize("months", [None, ("2026-09",)])
def test_one_time_allows_one_known_month_or_unknown(months):
    snapshot = BenefitSnapshot(**values(payment_cadence=BenefitPaymentCadence.ONE_TIME, applicable_months=months))
    assert snapshot.applicable_months is months


def test_one_time_rejects_multiple_known_months():
    with pytest.raises(PolicyDataError, match="applicable_months"):
        BenefitSnapshot(**values(payment_cadence=BenefitPaymentCadence.ONE_TIME, applicable_months=("2026-08", "2026-09")))


def test_evidence_order_and_duplicates_are_preserved_with_original_bindings():
    refs = ("SYNTH-B#second", "SYNTH-A#first", "SYNTH-B#second")
    bindings = (SourceBinding("SYNTH-A", "d0001"), SourceBinding("SYNTH-B", "d0002"))
    snapshot = BenefitSnapshot(**values(benefit_evidence_refs=refs, source_bindings=bindings))
    assert snapshot.benefit_evidence_refs is refs and snapshot.source_bindings is bindings
    assert snapshot.to_dict()["benefit_evidence_refs"] == list(refs)
    assert snapshot.to_dict()["source_bindings"] == [
        {"source_document_id": "SYNTH-A", "document_version": "d0001"},
        {"source_document_id": "SYNTH-B", "document_version": "d0002"},
    ]


@pytest.mark.parametrize("refs", [None, (), [], ["SYNTH-SOURCE#benefit-definition"], "SYNTH-SOURCE#benefit-definition", TupleSubclass(("SYNTH-SOURCE#benefit-definition",))])
def test_evidence_collection_requires_nonempty_exact_tuple(refs):
    with pytest.raises(PolicyDataError, match="benefit_evidence_refs"):
        BenefitSnapshot(**values(benefit_evidence_refs=refs))


@pytest.mark.parametrize("ref", [None, True, 1, "", "SYNTH-SOURCE", "SYNTH-SOURCE#", "#x", "SYNTH-SOURCE#x#y", "SOURCE_ID#x", "SYNTH-SOURCE#UPPER", StringSubclass("SYNTH-SOURCE#x")])
def test_evidence_ref_parser_errors_are_propagated(ref):
    with pytest.raises(SourceValidationError):
        BenefitSnapshot(**values(benefit_evidence_refs=(ref,)))


def test_existing_ref_parser_is_reused_once_per_original_ref_without_resolving_registry(monkeypatch):
    original = domain.parse_evidence_ref
    calls = []

    def parse(ref):
        calls.append(ref)
        return original(ref)

    def forbidden(*args, **kwargs):
        pytest.fail("Snapshot은 Registry를 조회하지 않아야 합니다")

    monkeypatch.setattr(domain, "parse_evidence_ref", parse)
    monkeypatch.setattr(SourceRegistry, "resolve", forbidden)
    monkeypatch.setattr(SourceRegistry, "get_source", forbidden)
    refs = ("SYNTH-SOURCE#unregistered", "SYNTH-SOURCE#unregistered")
    snapshot = BenefitSnapshot(**values(benefit_evidence_refs=refs))
    assert calls == list(refs) and snapshot.benefit_evidence_refs is refs


def test_original_source_validation_error_object_is_not_wrapped(monkeypatch):
    error = SourceValidationError("SYNTH_ERROR", "evidence_ref")

    def fail(ref):
        raise error

    monkeypatch.setattr(domain, "parse_evidence_ref", fail)
    with pytest.raises(SourceValidationError) as caught:
        BenefitSnapshot(**values())
    assert caught.value is error


@pytest.mark.parametrize("bindings", [None, (), [], {}, "x", (None,), ({"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"},), (BindingSubclass("SYNTH-SOURCE", "d0001"),), TupleSubclass((SourceBinding("SYNTH-SOURCE", "d0001"),))])
def test_source_collection_contains_only_exact_existing_bindings(bindings):
    with pytest.raises(PolicyDataError, match="source_bindings"):
        BenefitSnapshot(**values(source_bindings=bindings))


@pytest.mark.parametrize("bindings,refs", [
    ((SourceBinding("SYNTH-A", "d0001"),), ("SYNTH-A#x", "SYNTH-B#y")),
    ((SourceBinding("SYNTH-A", "d0001"), SourceBinding("SYNTH-B", "d0001")), ("SYNTH-A#x",)),
    ((SourceBinding("SYNTH-A", "d0001"), SourceBinding("SYNTH-A", "d0001")), ("SYNTH-A#x",)),
    ((SourceBinding("SYNTH-A", "d0001"), SourceBinding("SYNTH-A", "d0002")), ("SYNTH-A#x",)),
    ((SourceBinding("SYNTH-B", "d0001"), SourceBinding("SYNTH-A", "d0001")), ("SYNTH-A#x", "SYNTH-B#y")),
])
def test_missing_extra_duplicate_conflicting_or_unordered_source_bindings_fail(bindings, refs):
    with pytest.raises(PolicyDataError, match="source_bindings"):
        BenefitSnapshot(**values(source_bindings=bindings, benefit_evidence_refs=refs))


@pytest.mark.parametrize("dataset", [None, True, 1, [], {}, "", " \n\t", StringSubclass("D1")])
def test_dataset_is_exact_nonblank_string(dataset):
    with pytest.raises(PolicyDataError, match="dataset_version"):
        BenefitSnapshot(**values(dataset_version=dataset))


@pytest.mark.parametrize("dataset", ["D1", "  합성 확인본\n", "자료-1"])
def test_nonblank_dataset_is_preserved_without_imposing_an_id_grammar(dataset):
    assert BenefitSnapshot(**values(dataset_version=dataset)).dataset_version is dataset


@pytest.mark.parametrize("fingerprint", ["0" * 64, "a" * 64, "0123456789abcdef" * 4])
def test_registry_fingerprint_is_format_only(fingerprint):
    assert BenefitSnapshot(**values(source_registry_fingerprint=fingerprint)).source_registry_fingerprint is fingerprint


@pytest.mark.parametrize("fingerprint", [None, True, 1, b"a" * 64, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "a" * 64 + "\n", " " + "a" * 64, StringSubclass("a" * 64)])
def test_registry_fingerprint_requires_exact_lowercase_hex64(fingerprint):
    with pytest.raises(PolicyDataError, match="source_registry_fingerprint"):
        BenefitSnapshot(**values(source_registry_fingerprint=fingerprint))


@pytest.mark.parametrize("name", FIELD_NAMES)
def test_all_sixteen_fields_reject_assignment_and_deletion(name):
    snapshot = BenefitSnapshot(**values())
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, name, getattr(snapshot, name))
    with pytest.raises(FrozenInstanceError):
        delattr(snapshot, name)


def test_nested_scope_and_source_binding_remain_existing_frozen_objects():
    snapshot = BenefitSnapshot(**values())
    with pytest.raises(FrozenInstanceError):
        snapshot.scope.quarter = 4
    with pytest.raises(FrozenInstanceError):
        snapshot.source_bindings[0].document_version = "d0002"


@pytest.mark.parametrize("base,change", [
    ({}, {"policy_id": "SYNTH-OTHER"}), ({}, {"scope": ApplicabilityScope("2026", None)}),
    ({}, {"benefit_id": "SYNTH-OTHER"}), ({}, {"benefit_version": "b0002"}),
    ({}, {"amount_type": BenefitAmountType.VARIABLE, "amount_krw": None, "amount_description": "가변"}),
    ({}, {"amount_krw": 100001}),
    ({"amount_type": BenefitAmountType.VARIABLE, "amount_krw": None, "amount_description": "가변"}, {"amount_description": "다른 정의"}),
    ({}, {"payment_cadence": BenefitPaymentCadence.QUARTERLY}),
    ({}, {"benefit_medium": BenefitMedium.IN_KIND}),
    ({"benefit_medium": BenefitMedium.IN_KIND}, {"restriction": BenefitRestriction.UNKNOWN}),
    ({"benefit_medium": BenefitMedium.IN_KIND, "restriction": BenefitRestriction.RESTRICTED, "restriction_details": "교육"}, {"restriction_details": "주거"}),
    ({}, {"applicable_months": ("2026-08", "2026-09")}),
    ({}, {"benefit_evidence_refs": ("SYNTH-SOURCE#another-claim",)}),
    ({}, {"source_bindings": (SourceBinding("SYNTH-SOURCE", "d0002"),)}),
    ({}, {"dataset_version": "SYNTH-DATASET-2"}),
    ({}, {"source_registry_fingerprint": "b" * 64}),
])
def test_value_equality_includes_every_stored_field_and_provenance(base, change):
    first = BenefitSnapshot(**values(**base))
    same = BenefitSnapshot(**values(**base))
    changed = replace(first, **change)
    assert first == same and hash(first) == hash(same)
    assert first != changed and first.to_dict() != changed.to_dict()


def test_serialization_returns_fresh_mutation_isolated_nested_values():
    snapshot = BenefitSnapshot(**values())
    first, second = snapshot.to_dict(), snapshot.to_dict()
    first["scope"]["quarter"] = 4
    first["applicable_months"].append("2026-10")
    first["benefit_evidence_refs"].clear()
    first["source_bindings"][0]["document_version"] = "d9999"
    first["source_bindings"].clear()
    assert second == snapshot.to_dict() == expected()
    assert snapshot.scope.quarter == 3
    assert snapshot.source_bindings[0].document_version == "d0001"


def test_repeated_construction_serialization_and_equality_are_deterministic():
    supplied = values()
    first = BenefitSnapshot(**supplied)
    for _ in range(100):
        other = BenefitSnapshot(**supplied)
        assert other == first and other.to_dict() == expected()
        assert other.source_bindings is supplied["source_bindings"]
    assert supplied["applicable_months"] == ("2026-09",)


def test_model_does_not_encode_descriptions_or_repair_unicode_before_future_fingerprint():
    text = "가변\ud800"
    snapshot = BenefitSnapshot(**values(amount_type=BenefitAmountType.VARIABLE, amount_krw=None, amount_description=text))
    assert snapshot.amount_description is text
    assert snapshot.to_dict()["amount_description"] == text


@pytest.mark.parametrize("name", [
    "benefit_fingerprint", "acceptance_status", "acceptance_ref", "acceptance_version",
    "reviewed_at", "reviewer", "review_artifact_ref", "bridge_supported", "cashflow_applicable",
    "monthly_equivalent", "is_complete", "is_acceptance_ready", "accepted",
])
def test_definition_model_has_no_derived_approval_calculation_or_fingerprint_attributes(name):
    assert not hasattr(BenefitSnapshot(**values()), name)


def test_current_model_behavior_has_no_io_time_amount_execution_or_future_service_dependencies():
    source = inspect.getsource(domain)
    tree = ast.parse(source)
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = [alias.name for node in imports for alias in node.names]
    assert not {"hashlib", "json", "datetime", "date", "time", "requests", "os", "pathlib"} & set(imported)
    assert not any(token in (getattr(node, "module", None) or "").lower()
                   for node in imports for token in ("fingerprint", "acceptance", "cashflow", "bridge"))
    # 함수별 검사로 미래의 별도 모듈/함수 추가까지 막지 않는다.
    behavior = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in ("_invalid", "_identifier")]
    behavior += [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BenefitSnapshot"]
    calls = {node.func.id if isinstance(node.func, ast.Name) else node.func.attr
             for root in behavior for node in ast.walk(root) if isinstance(node, ast.Call)
             and isinstance(node.func, (ast.Name, ast.Attribute))}
    assert not calls & {"open", "eval", "exec", "round", "today", "now", "resolve", "get_source", "sorted"}
    assert not any(isinstance(node, (ast.Div, ast.FloorDiv)) for root in behavior for node in ast.walk(root))


def test_local_field_errors_precede_cross_field_errors_and_do_not_echo_payload():
    with pytest.raises(PolicyDataError, match="source_registry_fingerprint"):
        BenefitSnapshot(**values(amount_krw=None, source_registry_fingerprint="bad"))
    with pytest.raises(PolicyDataError, match="amount_krw"):
        BenefitSnapshot(**values(amount_krw=None, restriction_details="모순"))
    private_payload = "private-payload-do-not-echo"
    with pytest.raises(PolicyDataError) as caught:
        BenefitSnapshot(**values(policy_id=private_payload))
    assert str(caught.value).startswith("INVALID_BENEFIT_SNAPSHOT: policy_id:")
    assert private_payload not in str(caught.value)
