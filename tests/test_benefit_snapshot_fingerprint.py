"""혜택 정의 지문. BV01~BV16의 JSON/길이/digest 기대값은 승인된 문서의 literal이다."""

import ast
from dataclasses import fields, replace
import inspect
import json
import re
import unicodedata

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine import policy_data
from backend.policy_engine.policy_data import (
    ApplicabilityScope, BenefitAmountType, BenefitMedium, BenefitPaymentCadence,
    BenefitRestriction, BenefitSnapshot, SourceBinding, fingerprint_benefit_snapshot,
)
from backend.policy_engine.policy_data import benefit_fingerprint as domain
from backend.policy_engine.sources import SourceRegistry


GOLDEN = (
    pytest.param("BV01", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 535, "46c9a388b359c3e782e0a1d0d484ce8d19afe92e37080b20adda7000bcd45cd3", id="BV01-fixed_monthly_cash"),
    pytest.param("BV02", '{"amount_description":null,"amount_krw":125000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 535, "0da2a6ef35da21eb9b296f708154773a5e5cc6422e9a06694076d00af0e2b2c0", id="BV02-fixed_amount_changed"),
    pytest.param("BV03", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"QUARTERLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 537, "59456a9b057751bdebc3a7c3521175abd7dc4c8ac75b26075c379e9e3d448043", id="BV03-quarterly_cash"),
    pytest.param("BV04", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"IN_KIND","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 525, "bb6f1e779880fb25c98d03a3acabbde6e9a294849a5081bd98ccfebe30d88ac5", id="BV04-in_kind_unrestricted"),
    pytest.param("BV05", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"IN_KIND","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"RESTRICTED","restriction_details":"Education only","scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 535, "cb5fd08dbb8ce3c2ba3e0e7dc42b3ee64dc28350746569e0b89f37ecf3ac9151", id="BV05-in_kind_restricted_english"),
    pytest.param("BV06", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-08","2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 545, "6ba5de9d61b2ed68b04ceac98eedc4149703aaa6ed7132e0783c376e1ff431b4", id="BV06-months_added"),
    pytest.param("BV07", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition","SYNTH-SOURCE#payment-months"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 565, "d9d2bb4963dbce79f54a81007dd04d13c5453ca96fbb685110626bb4102dda50", id="BV07-evidence_added"),
    pytest.param("BV08", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":null},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 538, "48f2a5b47e9d545c01584548e4303df1a94746ff5835709e43ddbff0c38faa20", id="BV08-annual_scope"),
    pytest.param("BV09", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0002","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 535, "89c309d32965d335b39f009a7422530e4447e803c257fa4d2786248acc30e95d", id="BV09-version_label_changed"),
    pytest.param("BV10", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"IN_KIND","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"RESTRICTED","restriction_details":"교육 목적 사용","scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 541, "88ec6da60cae53840b3ad3dab072f795e29b9698587c388cfae8f74f0d58f51f", id="BV10-korean_restriction_details"),
    pytest.param("BV11", '{"amount_description":"가구 조건에 따라 금액이 달라짐","amount_krw":null,"amount_type":"VARIABLE","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 577, "13d1fd894a2a49e90c1b3b17d8a2d9dc9a89fe5e2788ac443634974613b132ee", id="BV11-variable_korean_amount"),
    pytest.param("BV12", '{"amount_description":null,"amount_krw":null,"amount_type":"UNKNOWN","applicable_months":null,"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNKNOWN","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"UNKNOWN","policy_id":"SYNTH-POLICY","restriction":"UNKNOWN","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 513, "fd04ca7d068e1377d9c18f51a19f8c2e5669049191ade3734277b20bea5a4bc2", id="BV12-unknown_metadata_and_null_months"),
    pytest.param("BV13", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#payment-months","SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 565, "a4c583320d2ecc98d5da11512b055ad34c974879d70363798df35b896eb16408", id="BV13-evidence_reordered"),
    pytest.param("BV14", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition","SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 569, "d23e9c96c5ce11e52cf613d0cfac2336c357c60aa9460c00cbfbfd5db440a3a9", id="BV14-evidence_duplicated"),
    pytest.param("BV15", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0002","source_document_id":"SYNTH-SOURCE"}]}', 535, "8194798e866570af26d32216f77da3cc3fda07387043fccd0ebfd8bd35df9902", id="BV15-related_source_version_changed"),
    pytest.param("BV16", '{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":null,"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}', 528, "8cf044c857382b867507cb3954d5e6dc73232c9f8cae55fab47c587a66552255", id="BV16-null_months_only"),
)


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


def snapshot(**changes):
    return BenefitSnapshot(**values(**changes))


def vector_snapshot(vector_id):
    """기대 JSON을 역변환하지 않고 문서상 각 사례를 실제 값 모델로 구성한다."""
    changes = {}
    if vector_id == "BV02":
        changes["amount_krw"] = 125000
    elif vector_id == "BV03":
        changes["payment_cadence"] = BenefitPaymentCadence.QUARTERLY
    elif vector_id == "BV04":
        changes["benefit_medium"] = BenefitMedium.IN_KIND
    elif vector_id in ("BV05", "BV10"):
        changes.update(
            benefit_medium=BenefitMedium.IN_KIND, restriction=BenefitRestriction.RESTRICTED,
            restriction_details="Education only" if vector_id == "BV05" else "교육 목적 사용",
        )
    elif vector_id == "BV06":
        changes["applicable_months"] = ("2026-08", "2026-09")
    elif vector_id in ("BV07", "BV13"):
        refs = ("SYNTH-SOURCE#benefit-definition", "SYNTH-SOURCE#payment-months")
        changes["benefit_evidence_refs"] = refs if vector_id == "BV07" else tuple(reversed(refs))
    elif vector_id == "BV08":
        changes["scope"] = ApplicabilityScope("2026", None)
    elif vector_id == "BV09":
        changes["benefit_version"] = "b0002"
    elif vector_id == "BV11":
        changes.update(
            amount_type=BenefitAmountType.VARIABLE, amount_krw=None,
            amount_description="가구 조건에 따라 금액이 달라짐",
        )
    elif vector_id == "BV12":
        changes.update(
            amount_type=BenefitAmountType.UNKNOWN, amount_krw=None,
            payment_cadence=BenefitPaymentCadence.UNKNOWN, benefit_medium=BenefitMedium.UNKNOWN,
            restriction=BenefitRestriction.UNKNOWN, applicable_months=None,
        )
    elif vector_id == "BV14":
        changes["benefit_evidence_refs"] = ("SYNTH-SOURCE#benefit-definition",) * 2
    elif vector_id == "BV15":
        changes["source_bindings"] = (SourceBinding("SYNTH-SOURCE", "d0002"),)
    elif vector_id == "BV16":
        changes["applicable_months"] = None
    return snapshot(**changes)


@pytest.mark.parametrize("vector_id,expected_json,expected_length,expected_digest", GOLDEN)
def test_document_golden_payload_canonical_bytes_and_literal_digest(
    vector_id, expected_json, expected_length, expected_digest, monkeypatch,
):
    value = vector_snapshot(vector_id)
    payloads, strings, encoding_options, hashed_bytes = [], [], [], []
    real_dumps, real_sha256 = domain.json.dumps, domain.hashlib.sha256

    def capture_json(payload, **options):
        payloads.append(payload)
        encoding_options.append(options)
        result = real_dumps(payload, **options)
        strings.append(result)
        return result

    def capture_sha256(raw):
        hashed_bytes.append(raw)
        return real_sha256(raw)

    monkeypatch.setattr(domain.json, "dumps", capture_json)
    monkeypatch.setattr(domain.hashlib, "sha256", capture_sha256)
    actual = fingerprint_benefit_snapshot(value)
    assert payloads == [json.loads(expected_json)]
    assert len(payloads[0]) == 15
    assert strings == [expected_json]
    assert encoding_options == [{
        "sort_keys": True, "separators": (",", ":"), "ensure_ascii": False, "allow_nan": False,
    }]
    assert hashed_bytes == [expected_json.encode("utf-8", errors="strict")]
    assert len(hashed_bytes[0]) == expected_length
    assert not hashed_bytes[0].startswith(b"\xef\xbb\xbf")
    assert not hashed_bytes[0].endswith(b"\n")
    assert actual == expected_digest
    assert re.fullmatch(r"[0-9a-f]{64}", actual)


def test_public_signature_and_export_have_one_required_domain_input_and_no_options():
    signature = inspect.signature(fingerprint_benefit_snapshot)
    assert tuple(signature.parameters) == ("snapshot",)
    assert signature.parameters["snapshot"].annotation is BenefitSnapshot
    assert signature.parameters["snapshot"].default is inspect.Parameter.empty
    assert signature.return_annotation is str
    assert policy_data.fingerprint_benefit_snapshot is fingerprint_benefit_snapshot
    assert policy_data.__all__.count("fingerprint_benefit_snapshot") == 1
    assert "_build_benefit_snapshot_fingerprint_payload" not in policy_data.__all__
    assert not hasattr(policy_data, "_build_benefit_snapshot_fingerprint_payload")
    with pytest.raises(TypeError):
        fingerprint_benefit_snapshot()
    with pytest.raises(TypeError):
        fingerprint_benefit_snapshot(snapshot(), include_dataset=True)


class SnapshotSubclass(BenefitSnapshot):
    pass


class FakeSnapshot:
    def __getattribute__(self, name):
        raise AssertionError("잘못된 타입의 속성에 접근하면 안 됩니다")


@pytest.mark.parametrize("bad", [
    None, {}, [], (), "SYNTH", 1, True, object(), SnapshotSubclass(**values()),
])
def test_only_exact_snapshot_is_accepted_before_any_attribute_or_encoding_access(bad, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("잘못된 타입은 payload/encoding 전에 거부해야 합니다")

    monkeypatch.setattr(domain, "_build_benefit_snapshot_fingerprint_payload", forbidden)
    monkeypatch.setattr(domain.json, "dumps", forbidden)
    with pytest.raises(PolicyDataError, match="benefit snapshot fingerprint: 정확한 BenefitSnapshot"):
        fingerprint_benefit_snapshot(bad)


def test_fake_snapshot_is_rejected_without_accessing_its_attributes():
    with pytest.raises(PolicyDataError, match="정확한 BenefitSnapshot"):
        fingerprint_benefit_snapshot(FakeSnapshot())


def test_explicit_fifteen_keys_and_nested_representations_have_no_provenance_or_metadata():
    payload = domain._build_benefit_snapshot_fingerprint_payload(snapshot())
    assert set(payload) == {
        "fingerprint_schema", "policy_id", "scope", "benefit_id", "benefit_version",
        "amount_type", "amount_krw", "amount_description", "payment_cadence", "benefit_medium",
        "restriction", "restriction_details", "applicable_months", "benefit_evidence_refs", "source_bindings",
    }
    assert payload["fingerprint_schema"] == "benefit-snapshot-1.0"
    assert payload["scope"] == {"edition_id": "2026", "quarter": 3}
    assert payload["source_bindings"] == [{
        "source_document_id": "SYNTH-SOURCE", "document_version": "d0001",
    }]
    assert payload["applicable_months"] == ["2026-09"]
    assert payload["amount_description"] is None
    assert payload["restriction_details"] is None


@pytest.mark.parametrize("changes", [
    {"dataset_version": "SYNTH-DATASET-2"},
    {"source_registry_fingerprint": "b" * 64},
    {"dataset_version": "SYNTH-DATASET-2", "source_registry_fingerprint": "b" * 64},
])
def test_provenance_changes_value_equality_and_serializer_but_not_definition_fingerprint(changes):
    first = snapshot()
    second = replace(first, **changes)
    assert first != second
    assert first.to_dict() != second.to_dict()
    assert len(first.to_dict()) == len(second.to_dict()) == 16
    assert fingerprint_benefit_snapshot(first) == fingerprint_benefit_snapshot(second)


@pytest.mark.parametrize("base,changes", [
    ({}, {"policy_id": "SYNTH-POLICY-OTHER"}),
    ({}, {"benefit_id": "SYNTH-BENEFIT-OTHER"}),
    ({}, {"scope": ApplicabilityScope("2026", 4)}),
    ({}, {"scope": ApplicabilityScope("2026", None)}),
    ({}, {"scope": ApplicabilityScope("2027", 3)}),
    ({}, {"benefit_version": "b0002"}),
    ({}, {"amount_krw": 125000}),
    ({}, {"amount_krw": 0}),
    ({}, {"amount_type": BenefitAmountType.VARIABLE, "amount_krw": None, "amount_description": "가변 금액"}),
    ({}, {"amount_type": BenefitAmountType.UNKNOWN, "amount_krw": None}),
    ({"amount_type": BenefitAmountType.VARIABLE, "amount_krw": None, "amount_description": "가구별 산정"},
     {"amount_description": "다른 산정 정의"}),
    ({}, {"payment_cadence": BenefitPaymentCadence.QUARTERLY}),
    ({}, {"benefit_medium": BenefitMedium.IN_KIND}),
    ({}, {"benefit_medium": BenefitMedium.LOCAL_CURRENCY,
          "restriction": BenefitRestriction.RESTRICTED, "restriction_details": "지역 내 사용"}),
    ({"benefit_medium": BenefitMedium.IN_KIND}, {"restriction": BenefitRestriction.UNKNOWN}),
    ({"benefit_medium": BenefitMedium.IN_KIND},
     {"restriction": BenefitRestriction.RESTRICTED, "restriction_details": "교육 목적"}),
    ({"benefit_medium": BenefitMedium.IN_KIND, "restriction": BenefitRestriction.RESTRICTED,
      "restriction_details": "교육 목적"}, {"restriction_details": "주거 목적"}),
    ({}, {"applicable_months": ("2026-08", "2026-09")}),
    ({}, {"applicable_months": None}),
    ({}, {"benefit_evidence_refs": ("SYNTH-SOURCE#benefit-definition", "SYNTH-SOURCE#payment-months")}),
    ({}, {"benefit_evidence_refs": ("SYNTH-SOURCE#benefit-definition",) * 2}),
    ({}, {"source_bindings": (SourceBinding("SYNTH-SOURCE", "d0002"),)}),
])
def test_definition_changes_are_detected_for_structurally_valid_snapshots(base, changes):
    first = snapshot(**base)
    second = replace(first, **changes)
    assert first != second
    assert fingerprint_benefit_snapshot(first) != fingerprint_benefit_snapshot(second)


def test_evidence_order_duplicates_and_canonical_multiple_source_bindings_are_preserved():
    first = snapshot(
        benefit_evidence_refs=("SYNTH-B#second", "SYNTH-A#first", "SYNTH-B#second"),
        source_bindings=(SourceBinding("SYNTH-A", "d0001"), SourceBinding("SYNTH-B", "d0002")),
    )
    reversed_refs = replace(first, benefit_evidence_refs=tuple(reversed(first.benefit_evidence_refs[:2])))
    payload = domain._build_benefit_snapshot_fingerprint_payload(first)
    assert payload["benefit_evidence_refs"] == ["SYNTH-B#second", "SYNTH-A#first", "SYNTH-B#second"]
    assert [binding["source_document_id"] for binding in payload["source_bindings"]] == ["SYNTH-A", "SYNTH-B"]
    assert fingerprint_benefit_snapshot(first) != fingerprint_benefit_snapshot(reversed_refs)


@pytest.mark.parametrize("vector_id", ["BV07", "BV13", "BV14"])
def test_added_reordered_and_duplicate_evidence_each_have_distinct_definition_fingerprint(vector_id):
    first = vector_snapshot(vector_id)
    other_ids = {"BV01", "BV07", "BV13", "BV14"} - {vector_id}
    assert all(fingerprint_benefit_snapshot(first) != fingerprint_benefit_snapshot(vector_snapshot(other))
               for other in other_ids)


def test_nulls_are_not_omitted_or_replaced_by_empty_collections():
    payload = domain._build_benefit_snapshot_fingerprint_payload(vector_snapshot("BV12"))
    assert payload["amount_krw"] is None
    assert payload["amount_description"] is None
    assert payload["restriction_details"] is None
    assert payload["applicable_months"] is None
    assert payload["amount_type"] == payload["payment_cadence"] == payload["benefit_medium"] == payload["restriction"] == "UNKNOWN"
    assert set(payload) == set(domain._build_benefit_snapshot_fingerprint_payload(snapshot()))


def test_fingerprint_uses_explicit_fields_not_snapshot_or_scope_serializers(monkeypatch):
    value = snapshot()

    def forbidden(*args, **kwargs):
        pytest.fail("일반 serializer 전체를 지문 payload로 사용하면 안 됩니다")

    monkeypatch.setattr(BenefitSnapshot, "to_dict", forbidden)
    monkeypatch.setattr(ApplicabilityScope, "to_dict", forbidden)
    assert fingerprint_benefit_snapshot(value) == "46c9a388b359c3e782e0a1d0d484ce8d19afe92e37080b20adda7000bcd45cd3"


def test_fingerprint_does_not_reconstruct_validate_or_resolve_input_values(monkeypatch):
    value = snapshot()

    def forbidden(*args, **kwargs):
        pytest.fail("검증된 입력을 재생성하거나 Registry를 조회하면 안 됩니다")

    monkeypatch.setattr(BenefitSnapshot, "__post_init__", forbidden)
    monkeypatch.setattr(ApplicabilityScope, "__post_init__", forbidden)
    monkeypatch.setattr(SourceBinding, "__post_init__", forbidden)
    monkeypatch.setattr(SourceRegistry, "resolve", forbidden)
    monkeypatch.setattr(SourceRegistry, "get_source", forbidden)
    assert fingerprint_benefit_snapshot(value) == "46c9a388b359c3e782e0a1d0d484ce8d19afe92e37080b20adda7000bcd45cd3"


def test_payload_is_a_fresh_mutation_isolated_projection():
    value = snapshot()
    before = value.to_dict()
    first = domain._build_benefit_snapshot_fingerprint_payload(value)
    second = domain._build_benefit_snapshot_fingerprint_payload(value)
    first["scope"]["quarter"] = 4
    first["applicable_months"].clear()
    first["benefit_evidence_refs"].append("SYNTH-SOURCE#extra")
    first["source_bindings"][0]["document_version"] = "d0002"
    assert value.to_dict() == before
    assert second == domain._build_benefit_snapshot_fingerprint_payload(value)


def test_one_hundred_repeats_are_deterministic_and_keep_all_original_nested_values():
    value = vector_snapshot("BV14")
    original = (value.scope, value.applicable_months, value.benefit_evidence_refs, value.source_bindings)
    before = value.to_dict()
    expected = "d23e9c96c5ce11e52cf613d0cfac2336c357c60aa9460c00cbfbfd5db440a3a9"
    for _ in range(100):
        assert fingerprint_benefit_snapshot(value) == expected
    assert value.to_dict() == before
    assert all(current is prior for current, prior in zip(
        (value.scope, value.applicable_months, value.benefit_evidence_refs, value.source_bindings), original,
    ))


@pytest.mark.parametrize("text", ['한글 "인용" \\ 경로\n다음줄', " 앞뒤 공백 ", "가구별 산정", "e\u0301"])
def test_original_unicode_whitespace_and_json_escaping_are_preserved(text, monkeypatch):
    value = snapshot(amount_type=BenefitAmountType.VARIABLE, amount_krw=None, amount_description=text)
    encoded = []
    real_sha256 = domain.hashlib.sha256

    def capture(raw):
        encoded.append(raw)
        return real_sha256(raw)

    monkeypatch.setattr(domain.hashlib, "sha256", capture)
    fingerprint_benefit_snapshot(value)
    raw = encoded[0]
    assert json.loads(raw.decode("utf-8"))["amount_description"] == text
    assert not raw.startswith(b"\xef\xbb\xbf") and not raw.endswith(b"\n")
    if "한글" in text:
        assert "한글".encode("utf-8") in raw
        assert b"\\u" not in raw
        assert b"\\n" in raw and b"\\\"" in raw


def test_nfc_and_nfd_text_are_not_automatically_normalized():
    composed = "é"
    decomposed = unicodedata.normalize("NFD", composed)
    first = snapshot(amount_type=BenefitAmountType.VARIABLE, amount_krw=None, amount_description=composed)
    second = replace(first, amount_description=decomposed)
    assert first.amount_description != second.amount_description
    assert fingerprint_benefit_snapshot(first) != fingerprint_benefit_snapshot(second)


@pytest.mark.parametrize("text", ["\ud800", "가구\udfff"])
def test_strict_utf8_failure_is_policy_data_error_without_hash_or_fallback(text, monkeypatch):
    value = snapshot(amount_type=BenefitAmountType.VARIABLE, amount_krw=None, amount_description=text)

    def forbidden(raw):
        pytest.fail("잘못된 UTF-8 문자열은 hash 전에 실패해야 합니다")

    monkeypatch.setattr(domain.hashlib, "sha256", forbidden)
    with pytest.raises(PolicyDataError, match="canonical JSON/UTF-8") as caught:
        fingerprint_benefit_snapshot(value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert text not in str(caught.value)


@pytest.mark.parametrize("error_type", [TypeError, ValueError, UnicodeError])
def test_canonical_json_failures_are_wrapped_without_payload_or_empty_result(error_type, monkeypatch):
    value = snapshot()

    def fail(*args, **kwargs):
        raise error_type("PRIVATE-SYNTHETIC-PAYLOAD")

    def forbidden(raw):
        pytest.fail("encoding 실패 후 hash를 호출하면 안 됩니다")

    monkeypatch.setattr(domain.json, "dumps", fail)
    monkeypatch.setattr(domain.hashlib, "sha256", forbidden)
    with pytest.raises(PolicyDataError, match="benefit snapshot fingerprint: canonical JSON/UTF-8") as caught:
        fingerprint_benefit_snapshot(value)
    assert "PRIVATE-SYNTHETIC-PAYLOAD" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_large_exact_integer_is_not_cast_rounded_or_capped():
    value = snapshot(amount_krw=10**100)
    payload = domain._build_benefit_snapshot_fingerprint_payload(value)
    assert type(payload["amount_krw"]) is int and payload["amount_krw"] == 10**100
    assert fingerprint_benefit_snapshot(value) != fingerprint_benefit_snapshot(snapshot())


def test_snapshot_stored_contract_and_definition_only_dependency_direction_remain_unchanged():
    names = tuple(field.name for field in fields(BenefitSnapshot))
    assert len(names) == 16
    assert "dataset_version" in names and "source_registry_fingerprint" in names
    assert not hasattr(snapshot(), "benefit_fingerprint")
    tree = ast.parse(inspect.getsource(domain))
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert not any(token in (getattr(node, "module", None) or "")
                   for node in imports for token in ("coverage_fingerprint", "cashflow", "bridge", "acceptance"))
    behavior = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in ("fingerprint_benefit_snapshot", "_build_benefit_snapshot_fingerprint_payload")]
    calls = {node.func.id if isinstance(node.func, ast.Name) else node.func.attr
             for root in behavior for node in ast.walk(root) if isinstance(node, ast.Call)
             and isinstance(node.func, (ast.Name, ast.Attribute))}
    assert not calls & {"open", "today", "now", "getenv", "resolve", "sorted", "to_dict", "asdict", "eval", "exec", "round"}
    assert not any(isinstance(node, (ast.Div, ast.FloorDiv)) for root in behavior for node in ast.walk(root))

