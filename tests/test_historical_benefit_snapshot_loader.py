"""M2.60 합성 bytes 검증. 실제 정책·발급·공식 의미·현재 usability 검증은 아니다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from enum import Enum
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
from typing import get_type_hints
import unicodedata

import pytest

from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, ApplicabilityScope, ArtifactReference, BenefitAcceptanceStatus,
    BenefitAmountType, BenefitMedium, BenefitPaymentCadence, BenefitRestriction, BenefitSnapshot,
    PolicyBenefitAcceptance, SourceBinding, fingerprint_benefit_snapshot,
    load_acceptance_review_artifact_bytes, load_historical_benefit_snapshot_bytes,
)
from backend.policy_engine.policy_data import historical_benefit_snapshot_loader as domain
from backend.policy_engine.sources import SourceRegistry


KEYS = (
    "policy_id", "scope", "benefit_id", "benefit_version", "amount_type", "amount_krw",
    "amount_description", "payment_cadence", "benefit_medium", "restriction", "restriction_details",
    "applicable_months", "benefit_evidence_refs", "source_bindings", "dataset_version",
    "source_registry_fingerprint",
)
REFERENCES = (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref",
)
FIXED_DEFINITION = "46c9a388b359c3e782e0a1d0d484ce8d19afe92e37080b20adda7000bcd45cd3"  # 기존 BV01
FIXED_RAW_SHA256 = "14af199097a6b4e9e20e9c7b1e805604dbbc0001a676d370ee497525dfc58e46"


def payload(**changes):
    return {"schema_version": "historical-benefit-snapshot-1.0", "snapshot": {
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "benefit_id": "SYNTH-BENEFIT", "benefit_version": "b0001", "amount_type": "FIXED",
        "amount_krw": 100000, "amount_description": None, "payment_cadence": "MONTHLY",
        "benefit_medium": "UNRESTRICTED_CASH", "restriction": "UNRESTRICTED", "restriction_details": None,
        "applicable_months": ["2026-09"], "benefit_evidence_refs": ["SYNTH-SOURCE#benefit-definition"],
        "source_bindings": [{"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"}],
        "dataset_version": "SYNTH-D1", "source_registry_fingerprint": "3" * 64, **changes,
    }}


def encode(body):
    # fixture 저작용 독립 encoder. production loader/canonical helper를 사용하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def definition_for_fixture(snapshot):
    # 소비 중 기대값 대체가 아닌 합성 fixture 저작. 정상 기본 정의는 BV01 literal로 별도 고정한다.
    projection = {key: snapshot[key] for key in KEYS
                  if key not in ("dataset_version", "source_registry_fingerprint")}
    projection["fingerprint_schema"] = "benefit-snapshot-1.0"
    return hashlib.sha256(encode(projection)).hexdigest()


def record_values(**changes):
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": FIXED_DEFINITION, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64,
        "reviewed_at": date(2026, 1, 1), "valid_until": date(2026, 12, 31),
        "review_artifact_ref": "acceptance-review:sha256:" + "f" * 64,
        "revokes_acceptance_ref": None, **changes,
    }


def raw_record(values):
    # 외부 원본 metadata로 raw20을 저작하며 loader의 projection/serializer는 호출하지 않는다.
    result = {}
    for key, value in values.items():
        if key == "review_artifact_ref":
            continue
        if type(value) is ApplicabilityScope:
            value = {"edition_id": value.edition_id, "quarter": value.quarter}
        elif type(value) is date:
            value = value.isoformat()
        elif isinstance(value, Enum):
            value = value.value
        result[key] = value
    return result


def raw_entry(values, terms_hash):
    revoked = values["status"] is BenefitAcceptanceStatus.REVOKED
    reference = {"path": "synthetic/missing-benefit.json", "sha256": terms_hash}
    binding = {"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"}
    return {
        "acceptance": raw_record(values),
        **{key: None if revoked else dict(reference) for key in REFERENCES},
        "claim_evidence": [] if revoked else [
            {"claim": claim, "evidence_refs": ["SYNTH-SOURCE#benefit-definition"]}
            for claim in ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding), "artifact": {
            "path": "synthetic/missing-source.pdf", "sha256": "b" * 64}}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
        "review_note": "합성 검토 기록", "manual_scenario_ids": ["HB01"],
    }


def bundle(raw, *, changes=None, terms_hash=None, extras=(), target_first=False):
    # 모든 정상 API fixture는 실제 M2.57로 복원한다. hash 계산은 호출 전에 끝나는 fixture 저작이다.
    target = record_values(**(changes or {}))
    specs = [(target, terms_hash if terms_hash is not None else hashlib.sha256(raw).hexdigest())]
    specs = specs + list(extras) if target_first else list(extras) + specs
    review_raw = encode({"schema_version": "benefit-acceptance-review-1.0",
                         "entries": [raw_entry(values, digest) for values, digest in specs]})
    root_ref = "acceptance-review:sha256:" + hashlib.sha256(review_raw).hexdigest()
    originals = tuple(PolicyBenefitAcceptance(**{**values, "review_artifact_ref": root_ref}) for values, _ in specs)
    root = load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=originals)
    original = originals[0 if target_first else len(originals) - 1]
    assert next(e for e in root.entries if e.acceptance.acceptance_ref == original.acceptance_ref).acceptance is original
    return root, original


def run(raw, *, prepared=None, **fixture_options):
    root, original = prepared if prepared is not None else bundle(raw, **fixture_options)
    return load_historical_benefit_snapshot_bytes(raw_bytes=raw, artifact=root, expected_acceptance=original)


def error(prefix, raw, *, prepared=None, field=None, **fixture_options):
    with pytest.raises(PolicyDataError) as caught:
        run(raw, prepared=prepared, **fixture_options)
    assert type(caught.value) is PolicyDataError
    message = str(caught.value)
    assert message.startswith(prefix + ": "), message
    if field is not None:
        assert message.startswith(prefix + ": " + field + ": "), message
    return message


def at(body, path):
    for key in path:
        body = body[key]
    return body


def path_name(path):
    result = ""
    for part in path:
        result += f"[{part}]" if type(part) is int else ("." if result else "") + part
    return result or "root"


def changed_raw(path, value):
    body = payload()
    at(body, path[:-1])[path[-1]] = value
    return encode(body)


OBJECTS = (
    ((), ("schema_version", "snapshot")), (("snapshot",), KEYS),
    (("snapshot", "scope"), ("edition_id", "quarter")),
    (("snapshot", "source_bindings", 0), ("source_document_id", "document_version")),
)


def test_exact_public_api_and_approved_raw_field_order():
    fn = load_historical_benefit_snapshot_bytes
    assert fn is domain.load_historical_benefit_snapshot_bytes
    assert policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "artifact", "expected_acceptance")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "artifact": AcceptanceReviewArtifact,
                                  "expected_acceptance": PolicyBenefitAcceptance, "return": BenefitSnapshot}
    assert KEYS == tuple(f.name for f in fields(BenefitSnapshot)) == domain._SNAPSHOT_KEYS
    for kwargs in ({}, {"raw_bytes": b""}, {"raw_bytes": b"", "artifact": None}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", None, None)
    for option in ("skip_hash", "ignore_version", "allow_stale", "fallback_snapshot", "current_benefit",
                   "auto_select_entry", "expected_artifact_ref"):
        with pytest.raises(TypeError):
            fn(raw_bytes=b"", artifact=None, expected_acceptance=None, **{option: True})


def test_fixed_fixture_restores_all_sixteen_fields_and_uses_independent_bv01():
    raw = encode(payload())
    assert len(raw) == 681
    assert hashlib.sha256(raw).hexdigest() == FIXED_RAW_SHA256
    root, original = bundle(raw, terms_hash=FIXED_RAW_SHA256)
    result = run(raw, prepared=(root, original))
    assert type(result) is BenefitSnapshot
    assert result.to_dict() == payload()["snapshot"]
    assert type(result.scope) is ApplicabilityScope
    assert type(result.amount_krw) is int
    assert result.amount_type is BenefitAmountType.FIXED
    assert result.payment_cadence is BenefitPaymentCadence.MONTHLY
    assert result.benefit_medium is BenefitMedium.UNRESTRICTED_CASH
    assert result.restriction is BenefitRestriction.UNRESTRICTED
    assert result.applicable_months == ("2026-09",)
    assert type(result.source_bindings[0]) is SourceBinding
    assert fingerprint_benefit_snapshot(result) == original.benefit_fingerprint == FIXED_DEFINITION
    assert definition_for_fixture(payload()["snapshot"]) == FIXED_DEFINITION
    assert root.entries[0].acceptance is original
    assert root.entries[0].accepted_terms_ref.path == "synthetic/missing-benefit.json"
    assert root.entries[0].accepted_terms_ref.sha256 == FIXED_RAW_SHA256 != FIXED_DEFINITION


@pytest.mark.parametrize("changes", [
    {"amount_krw": 0}, {"applicable_months": None},
    {"applicable_months": ["2026-08", "2026-09"]},
    {"amount_type": "VARIABLE", "amount_krw": None, "amount_description": "가구 조건에 따라 달라짐"},
    {"amount_type": "UNKNOWN", "amount_krw": None, "amount_description": None,
     "payment_cadence": "UNKNOWN", "benefit_medium": "UNKNOWN", "restriction": "UNKNOWN",
     "applicable_months": None},
    {"payment_cadence": "QUARTERLY", "benefit_medium": "LOCAL_CURRENCY", "restriction": "RESTRICTED",
     "restriction_details": "지역 내 사용"},
    {"benefit_evidence_refs": ["SYNTH-SOURCE#payment-months", "SYNTH-SOURCE#benefit-definition"]},
    {"benefit_evidence_refs": ["SYNTH-SOURCE#benefit-definition"] * 2},
    {"benefit_evidence_refs": ["SYNTH-A#amount", "SYNTH-SOURCE#benefit-definition"], "source_bindings": [
        {"source_document_id": "SYNTH-A", "document_version": "d0002"},
        {"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"}]},
    {"payment_cadence": "ONE_TIME"}, {"benefit_version": "b10000"},
    {"scope": {"edition_id": "0000", "quarter": None}},
])
def test_structurally_valid_partial_and_nonbridge_snapshots_are_not_approval(changes):
    body = payload(**changes)
    snapshot = body["snapshot"]
    record_changes = {"benefit_fingerprint": definition_for_fixture(snapshot),
                      "scope": ApplicabilityScope(**snapshot["scope"]),
                      "benefit_version": snapshot["benefit_version"]}
    result = run(encode(body), changes=record_changes)
    assert result.to_dict() == snapshot
    assert not any(hasattr(result, key) for key in (
        "accepted", "reviewed", "artifact_verified", "is_complete", "current_usable", "bridge_supported",
        "raw_file_path", "loaded_from_hash"))


def test_unicode_preserves_nfc_nfd_and_existing_untrimmed_string_contract():
    outputs = []
    for description in ("가구별 지급", unicodedata.normalize("NFD", "가구별 지급"), "  가구별 지급  "):
        body = payload(amount_type="VARIABLE", amount_krw=None, amount_description=description)
        result = run(encode(body), changes={"benefit_fingerprint": definition_for_fixture(body["snapshot"])})
        assert result.amount_description == description
        outputs.append(fingerprint_benefit_snapshot(result))
    assert len(set(outputs)) == 3


@pytest.mark.parametrize("target_first", [True, False])
def test_exact_entry_selection_across_multiple_targets_versions_and_shared_terms(target_first):
    raw = encode(payload())
    other_raw = encode(payload(amount_krw=125000))
    extras = (
        (record_values(acceptance_ref="SYNTH-OTHER", policy_id="SYNTH-OTHER-POLICY",
                       benefit_id="SYNTH-OTHER-BENEFIT"), hashlib.sha256(other_raw).hexdigest()),
        (record_values(acceptance_ref="SYNTH-ACCEPT-C", acceptance_version="a0003"),
         hashlib.sha256(raw).hexdigest()),
    )
    root, original = bundle(raw, extras=extras, target_first=target_first)
    assert run(raw, prepared=(root, original)).amount_krw == 100000
    shared = next(e.acceptance for e in root.entries if e.acceptance.acceptance_ref == "SYNTH-ACCEPT-C")
    assert run(raw, prepared=(root, shared)).benefit_version == "b0001"
    error("HISTORICAL_BENEFIT_BYTES_MISMATCH", other_raw, prepared=(root, original))


@pytest.mark.parametrize("field,bad", [
    ("raw_bytes", None), ("raw_bytes", "{}"), ("raw_bytes", bytearray(b"{}")),
    ("raw_bytes", memoryview(b"{}")), ("raw_bytes", type("BytesSubclass", (bytes,), {})(b"{}")),
    ("artifact", None), ("artifact", {}), ("artifact", ArtifactReference("synthetic/a.json", "a" * 64)),
    ("expected_acceptance", None), ("expected_acceptance", {}),
])
def test_exact_input_types(field, bad):
    raw = encode(payload())
    root, original = bundle(raw)
    kwargs = {"raw_bytes": raw, "artifact": root, "expected_acceptance": original, field: bad}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_BENEFIT_LOADER_INPUT: " + field + ": "):
        load_historical_benefit_snapshot_bytes(**kwargs)


@pytest.mark.parametrize("field", ["artifact", "expected_acceptance"])
def test_exact_model_subclasses_are_rejected_without_mutation(field):
    raw = encode(payload())
    root, original = bundle(raw)
    obj = root if field == "artifact" else original
    derived = type("Derived", (type(obj),), {})(**{f.name: getattr(obj, f.name) for f in fields(obj)})
    kwargs = {"raw_bytes": raw, "artifact": root, "expected_acceptance": original, field: derived}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_BENEFIT_LOADER_INPUT: " + field):
        load_historical_benefit_snapshot_bytes(**kwargs)


@pytest.mark.parametrize("changes,field", [
    ({}, "entry.acceptance"),
    ({"acceptance_version": "a0002"}, "entry.acceptance"),
    ({"policy_id": "SYNTH-OTHER"}, "entry.acceptance"),
    ({"benefit_id": "SYNTH-OTHER"}, "entry.acceptance"),
    ({"scope": ApplicabilityScope("2026", None)}, "entry.acceptance"),
    ({"acceptance_ref": "SYNTH-ABSENT"}, "artifact.entries"),
    ({"review_artifact_ref": "acceptance-review:sha256:" + "e" * 64}, "artifact.review_artifact_ref"),
])
def test_same_values_copy_wrong_revision_target_absent_entry_and_root_are_rejected(changes, field):
    raw = encode(payload())
    root, original = bundle(raw)
    error("HISTORICAL_BENEFIT_REVIEW_BINDING_MISMATCH", raw,
          prepared=(root, replace(original, **changes)), field=field)


def test_revoked_direct_input_is_rejected_before_hash_or_target_lookup():
    raw = b"not-json"
    root, original = bundle(raw, changes={"status": BenefitAcceptanceStatus.REVOKED,
                                         "revokes_acceptance_ref": "SYNTH-OLDER"})
    assert root.entries[0].accepted_terms_ref is None
    error("HISTORICAL_BENEFIT_REVIEW_BINDING_MISMATCH", raw, prepared=(root, original),
          field="expected_acceptance.status")


def test_duplicate_entry_and_missing_expected_ref_are_rejected_by_existing_models():
    raw = encode(payload())
    root, original = bundle(raw)
    entry = root.entries[0]
    # 일반 불변 객체만 사용한다. 중복 Entry/ACCEPTED의 None ref는 loader 진입 전에 차단된다.
    for second in (entry, replace(entry), replace(entry, acceptance=replace(original, acceptance_version="a0002"))):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: entries:"):
            AcceptanceReviewArtifact(review_artifact_ref=root.review_artifact_ref, entries=(entry, second))
    for bad in (None, "not-a-ref"):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: accepted_terms_ref:"):
            replace(entry, accepted_terms_ref=bad)


def test_mutated_bytes_same_filename_and_changed_expected_digest_fail_before_parse(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    changed = raw.replace(b"100000", b"100001")
    wrong_hash_prepared = bundle(raw, terms_hash="a" * 64)

    def forbidden(*args, **kwargs):
        pytest.fail("P2 실패 후 JSON parsing을 실행했습니다")

    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", forbidden)
        for bad in (changed, b"broken", b"\xff", raw + b"\n"):
            error("HISTORICAL_BENEFIT_BYTES_MISMATCH", bad, prepared=prepared)
        error("HISTORICAL_BENEFIT_BYTES_MISMATCH", raw, prepared=wrong_hash_prepared)
    assert prepared[0].entries[0].accepted_terms_ref.path == wrong_hash_prepared[0].entries[0].accepted_terms_ref.path


@pytest.mark.parametrize("raw", [b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xef\xbb\xbf{}"])
def test_invalid_utf8_and_bom(raw):
    error("INVALID_HISTORICAL_BENEFIT_ENCODING", raw)


@pytest.mark.parametrize("raw", [b"", b"{", b"[] garbage", b"{}{}", b'{"a":}', b"+Infinity"])
def test_malformed_json(raw):
    error("INVALID_HISTORICAL_BENEFIT_JSON", raw)


@pytest.mark.parametrize("raw", [
    b'{"a":1,"a":2}', b'{"a":1,"\\u0061":2}', b'{"a":{"b":1,"b":2}}',
    b'{"a":[{"b":1,"b":2}]}',
])
def test_duplicate_keys_at_every_depth_including_equivalent_escaped_keys(raw):
    error("DUPLICATE_HISTORICAL_BENEFIT_JSON_KEY", raw)


@pytest.mark.parametrize("token", [b"1.0", b"1e3", b"-1.5", b"NaN", b"Infinity", b"-Infinity"])
def test_noninteger_and_nonfinite_tokens(token):
    raw = encode(payload()).replace(b'"amount_krw":100000', b'"amount_krw":' + token)
    error("INVALID_HISTORICAL_BENEFIT_NUMBER", raw)


@pytest.mark.parametrize("raw", [b'{"\\ud800":0}', b'{"x":"\\udfff"}', b'["\\ud800"]'])
def test_unpaired_unicode_in_keys_and_values(raw):
    error("INVALID_HISTORICAL_BENEFIT_UNICODE", raw)


def test_runtime_parser_failures_are_mapped_without_global_limit_changes(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    limit, recursion = sys.get_int_max_str_digits(), sys.getrecursionlimit()

    def recursion_failure(*args, **kwargs):
        raise RecursionError("synthetic parser failure")

    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", recursion_failure)
        error("INVALID_HISTORICAL_BENEFIT_JSON", raw, prepared=prepared)
    if limit:
        giant = b'{"amount":' + b"9" * (limit + 1) + b"}"
        error("INVALID_HISTORICAL_BENEFIT_NUMBER", giant)
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_BENEFIT_NUMBER:"):
        domain._integer("invalid-token")
    assert (sys.get_int_max_str_digits(), sys.getrecursionlimit()) == (limit, recursion)


@pytest.mark.parametrize("path,key", [(path, key) for path, keys in OBJECTS for key in keys])
def test_each_required_key_is_distinct_from_null_and_cannot_be_missing(path, key):
    body = payload()
    del at(body, path)[key]
    error("INVALID_HISTORICAL_BENEFIT_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,keys", OBJECTS)
def test_extra_fields_at_all_object_depths(path, keys):
    body = payload()
    at(body, path)["unapproved-secret-key"] = 1
    message = error("INVALID_HISTORICAL_BENEFIT_FIELDS", encode(body), field=path_name(path))
    assert "unapproved-secret-key" not in message


@pytest.mark.parametrize("schema", ["historical-benefit-snapshot-2.0", "benefit-snapshot-1.0", "", "1.0"])
def test_wrong_schema_literal(schema):
    body = payload()
    body["schema_version"] = schema
    error("INVALID_HISTORICAL_BENEFIT_SCHEMA", encode(body), field="schema_version")


TYPE_CASES = (
    *((path, value) for path in ((), ("snapshot",), ("snapshot", "scope"), ("snapshot", "source_bindings", 0))
      for value in (None, [], "object", 1, True)),
    *((path, value) for path in (("schema_version",), ("snapshot", "policy_id"),
      ("snapshot", "benefit_id"), ("snapshot", "benefit_version"), ("snapshot", "amount_type"),
      ("snapshot", "payment_cadence"), ("snapshot", "benefit_medium"), ("snapshot", "restriction"),
      ("snapshot", "dataset_version"), ("snapshot", "source_registry_fingerprint"),
      ("snapshot", "scope", "edition_id"), ("snapshot", "source_bindings", 0, "source_document_id"),
      ("snapshot", "source_bindings", 0, "document_version")) for value in (None, 1, True, [], {})),
    *((('snapshot', key), value) for key in ("amount_description", "restriction_details")
      for value in (1, True, [], {})),
    *((('snapshot', 'amount_krw'), value) for value in (True, False, "100000", [], {})),
    *((('snapshot', 'scope', 'quarter'), value) for value in (True, "3", [], {})),
    *((('snapshot', key), value) for key in ("applicable_months", "benefit_evidence_refs", "source_bindings")
      for value in (True, "array", 1, {})),
    (("snapshot", "benefit_evidence_refs"), None), (("snapshot", "source_bindings"), None),
    *((path, value) for path in (("snapshot", "applicable_months", 0),
      ("snapshot", "benefit_evidence_refs", 0)) for value in (None, 1, True, [], {})),
)


@pytest.mark.parametrize("path,value", TYPE_CASES)
def test_strict_raw_types_and_nullable_boundaries(path, value):
    body = payload()
    if not path:
        body = value
    else:
        at(body, path[:-1])[path[-1]] = value
    error("INVALID_HISTORICAL_BENEFIT_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("kind", ["whitespace", "key_order", "newline", "escape", "negative_zero", "surrogate_pair"])
def test_noncanonical_representations_with_matching_expected_hash(kind):
    body = payload()
    if kind in ("escape", "surrogate_pair"):
        body["snapshot"].update(amount_type="VARIABLE", amount_krw=None,
                                amount_description="한국어" if kind == "escape" else "💡")
    raw = encode(body)
    if kind == "whitespace": raw = raw.replace(b":", b": ", 1)
    elif kind == "key_order": raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    elif kind == "newline": raw += b"\n"
    elif kind == "escape": raw = raw.replace("한국어".encode("utf-8"), b"\\ud55c\\uad6d\\uc5b4")
    elif kind == "negative_zero": raw = raw.replace(b'"amount_krw":100000', b'"amount_krw":-0')
    else: raw = raw.replace("💡".encode("utf-8"), b"\\ud83d\\udca1")
    error("NONCANONICAL_HISTORICAL_BENEFIT_BYTES", raw)


@pytest.mark.parametrize("key", ["amount_type", "payment_cadence", "benefit_medium", "restriction"])
@pytest.mark.parametrize("bad", ["wrong", "", "FIXED "])
def test_malformed_enums_use_existing_enum_conversion(key, bad):
    error("INVALID_HISTORICAL_BENEFIT_VALUE", changed_raw(("snapshot", key), bad), field="snapshot." + key)


MODEL_CASES = (
    (("policy_id",), "bad-id"), (("benefit_id",), "bad_id"),
    *((('benefit_version',), value) for value in ("b0000", "b1", "b00001", "a0001")),
    (("scope", "edition_id"), "２０２６"), (("scope", "edition_id"), "202"),
    *((('scope', 'quarter'), value) for value in (0, 5, -1)),
    (("amount_krw",), -1), (("amount_krw",), None), (("amount_description",), "unexpected"),
    (("restriction_details",), "unexpected"), (("applicable_months",), []),
    *((('applicable_months',), value) for value in (["2026-13"], ["0000-01"], ["2026-9"],
      ["2026-09", "2026-08"], ["2026-09", "2026-09"])),
    (("benefit_evidence_refs",), []),
    *((('benefit_evidence_refs',), value) for value in (["missing-locator"], ["bad#ref"],
      ["SYNTH-SOURCE#Upper"], ["SYNTH-SOURCE#two#parts"])),
    (("source_bindings",), []),
    (("source_bindings", 0, "document_version"), "d0000"),
    (("source_bindings", 0, "source_document_id"), "bad-id"),
    (("source_bindings", 0, "source_document_id"), "SYNTH-OTHER"),
    (("source_bindings",), [{"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"}] * 2),
    (("dataset_version",), "  "), (("source_registry_fingerprint",), "A" * 64),
)


@pytest.mark.parametrize("path,value", MODEL_CASES)
def test_existing_model_structure_invariants_are_reused(path, value):
    error("INVALID_HISTORICAL_BENEFIT_MODEL", changed_raw(("snapshot", *path), value))


@pytest.mark.parametrize("changes", [
    {"amount_type": "VARIABLE"}, {"amount_type": "VARIABLE", "amount_krw": None},
    {"amount_type": "UNKNOWN"}, {"amount_type": "UNKNOWN", "amount_krw": None, "amount_description": "설명"},
    {"restriction": "RESTRICTED"}, {"benefit_medium": "RESTRICTED_CASH_EQUIVALENT"},
    {"payment_cadence": "ONE_TIME", "applicable_months": ["2026-08", "2026-09"]},
    {"benefit_evidence_refs": ["SYNTH-A#amount", "SYNTH-SOURCE#benefit-definition"], "source_bindings": [
        {"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"},
        {"source_document_id": "SYNTH-A", "document_version": "d0001"}]},
])
def test_model_cross_field_contradictions_are_not_unknown_or_partial_results(changes):
    error("INVALID_HISTORICAL_BENEFIT_MODEL", encode(payload(**changes)))


@pytest.mark.parametrize("key,value", [
    ("policy_id", "SYNTH-OTHER"), ("benefit_id", "SYNTH-OTHER"),
    ("scope", {"edition_id": "2026", "quarter": None}), ("benefit_version", "b0002"),
])
def test_historical_identity_and_version_mismatch_precedes_fingerprint(key, value):
    error("HISTORICAL_BENEFIT_IDENTITY_MISMATCH", encode(payload(**{key: value})), field="snapshot." + key)


def test_same_version_content_mismatch_is_not_normal_staleness():
    error("HISTORICAL_BENEFIT_FINGERPRINT_MISMATCH", encode(payload(amount_krw=125000)))


@pytest.mark.parametrize("key,value,prefix", [
    ("dataset_version", "SYNTH-D2", "HISTORICAL_BENEFIT_DATASET_MISMATCH"),
    ("source_registry_fingerprint", "a" * 64, "HISTORICAL_BENEFIT_REGISTRY_MISMATCH"),
])
def test_provenance_changes_preserve_definition_but_fail_historical_binding(key, value, prefix):
    body = payload(**{key: value})
    assert definition_for_fixture(body["snapshot"]) == FIXED_DEFINITION
    error(prefix, encode(body), field="snapshot." + key)


def test_other_acceptance_with_exact_bytes_still_fails_its_own_binding():
    raw = encode(payload())
    root, original = bundle(raw, changes={"benefit_id": "SYNTH-OTHER"})
    error("HISTORICAL_BENEFIT_IDENTITY_MISMATCH", raw, prepared=(root, original), field="snapshot.benefit_id")


def test_compound_error_precedence_across_phases_and_identity_axes():
    raw = encode(payload())
    root, original = bundle(raw)
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_BENEFIT_LOADER_INPUT: raw_bytes:"):
        load_historical_benefit_snapshot_bytes(raw_bytes=None, artifact=None, expected_acceptance=None)
    error("HISTORICAL_BENEFIT_REVIEW_BINDING_MISMATCH", b"\xff", prepared=(root, replace(original)))
    error("HISTORICAL_BENEFIT_BYTES_MISMATCH", b"\xff", prepared=(root, original))
    body = payload()
    del body["snapshot"]["policy_id"]
    body["snapshot"]["extra"] = True
    error("INVALID_HISTORICAL_BENEFIT_FIELDS", encode(body), field="snapshot")
    bad_enum = encode(payload(amount_type="bad"))
    error("NONCANONICAL_HISTORICAL_BENEFIT_BYTES", bad_enum + b"\n")
    error("INVALID_HISTORICAL_BENEFIT_VALUE", encode(payload(amount_type="bad", source_bindings=[])))
    error("INVALID_HISTORICAL_BENEFIT_MODEL", encode(payload(scope={"edition_id": "bad", "quarter": 3},
                                                           amount_type="bad")), field="snapshot.scope")
    changed = {"policy_id": "SYNTH-OTHER", "scope": {"edition_id": "2026", "quarter": None},
               "benefit_id": "SYNTH-OTHER", "benefit_version": "b0002", "amount_krw": 125000,
               "dataset_version": "SYNTH-D2", "source_registry_fingerprint": "a" * 64}
    for key in ("policy_id", "scope", "benefit_id", "benefit_version"):
        error("HISTORICAL_BENEFIT_IDENTITY_MISMATCH", encode(payload(**changed)), field="snapshot." + key)
        del changed[key]
    error("HISTORICAL_BENEFIT_FINGERPRINT_MISMATCH", encode(payload(**changed)))
    del changed["amount_krw"]
    error("HISTORICAL_BENEFIT_DATASET_MISMATCH", encode(payload(**changed)))
    del changed["dataset_version"]
    error("HISTORICAL_BENEFIT_REGISTRY_MISMATCH", encode(payload(**changed)))


def test_real_existing_fingerprint_is_called_once_on_the_returned_snapshot(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    seen = []
    original = domain.fingerprint_benefit_snapshot

    def spy(snapshot):
        seen.append(snapshot)
        return original(snapshot)

    monkeypatch.setattr(domain, "fingerprint_benefit_snapshot", spy)
    result = run(raw, prepared=prepared)
    assert len(seen) == 1 and seen[0] is result


def test_existing_fingerprint_data_error_mapping_and_no_blanket_exception_catch(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)

    def data_failure(snapshot):
        raise PolicyDataError("synthetic-private-detail")

    with monkeypatch.context() as patch:
        patch.setattr(domain, "fingerprint_benefit_snapshot", data_failure)
        message = error("INVALID_HISTORICAL_BENEFIT_FINGERPRINT", raw, prepared=prepared)
        assert "synthetic-private-detail" not in message

    def runtime_failure(snapshot):
        raise RuntimeError("unexpected programming error")

    monkeypatch.setattr(domain, "fingerprint_benefit_snapshot", runtime_failure)
    with pytest.raises(RuntimeError):
        run(raw, prepared=prepared)


def test_one_hundred_runs_preserve_bytes_artifact_acceptance_and_isolate_snapshots():
    raw = encode(payload())
    root, original = bundle(raw)
    before_raw, before_root, before_record = raw, root.to_dict(), original.to_dict()
    entry, ref = root.entries[0], root.entries[0].accepted_terms_ref
    first = run(raw, prepared=(root, original))
    for _ in range(100):
        result = run(raw, prepared=(root, original))
        assert result == first and result is not first
        output = result.to_dict()
        output["scope"].clear()
        output["applicable_months"].clear()
        output["source_bindings"][0].clear()
        assert result.to_dict() == payload()["snapshot"]
        assert raw is before_raw and root.entries[0] is entry and entry.acceptance is original
        assert entry.accepted_terms_ref is ref and root.to_dict() == before_root
        assert original.to_dict() == before_record
    with pytest.raises(FrozenInstanceError):
        first.amount_krw = 0
    assert not hasattr(first, "__dict__")


def test_errors_do_not_echo_untrusted_values_or_payload():
    secret = "SYNTH-PRIVATE-SECRET"
    message = error("HISTORICAL_BENEFIT_IDENTITY_MISMATCH", encode(payload(benefit_id=secret)))
    assert secret not in message
    message = error("INVALID_HISTORICAL_BENEFIT_MODEL", encode(payload(benefit_version=secret)))
    assert secret not in message


def test_current_snapshot_is_not_substituted_and_loader_success_is_not_review_or_payment():
    raw = encode(payload())
    historical = run(raw)
    current = replace(historical, benefit_version="b0002")
    assert historical.benefit_version == "b0001" and current.benefit_version == "b0002"
    assert type(historical) is BenefitSnapshot and tuple(historical.to_dict()) == KEYS
    assert not hasattr(historical, "status")


def test_no_external_io_registry_review_revalidation_or_mutable_cache(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    tree = ast.parse(inspect.getsource(domain))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names)
    assert imports <= {"hashlib", "json", "errors", "benefit_acceptance", "benefit_acceptance_review_artifact",
                       "benefit_fingerprint", "benefit_snapshot", "eligibility_coverage", "envelope", "manifest"}
    own = [value for value in vars(domain).values()
           if inspect.isfunction(value) and value.__module__ == domain.__name__]
    assert [fn.__name__ for fn in own if not fn.__name__.startswith("_")] == [
        "load_historical_benefit_snapshot_bytes"]
    assert all(not isinstance(v, (dict, list, set)) for k, v in vars(domain).items() if not k.startswith("__"))

    def forbidden(*args, **kwargs):
        pytest.fail("순수 loader가 외부 준비/Registry/다른 평가를 실행했습니다")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(SourceRegistry, "resolve", forbidden)
        patch.setattr(SourceRegistry, "get_source", forbidden)
        patch.setattr(BenefitSnapshot, "to_dict", forbidden)
        patch.setattr(policy_data, "load_acceptance_review_artifact_bytes", forbidden)
        patch.setattr(policy_data, "evaluate_eligibility_coverage", forbidden)
        result = run(raw, prepared=prepared)
    assert result.amount_krw == 100000


def test_all_twenty_error_prefixes_are_declared_without_claiming_unreachable_model_states():
    spec = (Path(__file__).resolve().parents[1] /
            "docs/HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md").read_text(encoding="utf-8")
    prefixes = re.findall(r"^\| P\d[a-d]? \| ([A-Z_]+) \|", spec, re.M)
    assert len(prefixes) == len(set(prefixes)) == 20
    code = inspect.getsource(domain)
    assert all('"' + prefix + '"' in code for prefix in prefixes)
    # INVALID_EXPECTED_REF/duplicate-entry 분기는 정상 모델로 도달할 수 없다. 강제 변조하지 않는다.
