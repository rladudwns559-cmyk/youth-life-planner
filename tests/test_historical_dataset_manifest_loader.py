"""HM1의 독립 bytes/원본 Entry/직접 선언 대응을 검증한다. 전체 release 검증은 아니다."""

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import hashlib
import inspect
import json
from pathlib import Path
import re
from typing import get_type_hints
import unicodedata

import pytest

from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, ApplicabilityScope, ArtifactReference, BenefitAcceptanceStatus,
    DatasetManifest, PolicyBenefitAcceptance, PolicyEditionReference, SourceBinding, SourceRegistryReference,
    load_acceptance_review_artifact_bytes, load_historical_dataset_manifest_bytes,
)
from backend.policy_engine.policy_data import historical_dataset_manifest_loader as domain


FIXED_RAW_SHA256 = "814826438ac659b85f2eee106a6905e07051156cfc75822c6909020a0be39a33"
MANIFEST_KEYS = ("schema_version", "dataset_id", "dataset_version", "created_at", "freshness_max_age_days",
    "engine_version", "engine_artifact_sha256", "policy_versions", "source_registry", "source_versions", "review_manifest")
POLICY_KEYS = ("policy_id", "edition_id", "rule_version", "artifact", "fingerprint", "schema_version", "rule_schema_version")
REFERENCES = ("accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
              "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref")
M = ("manifest",)
P = M + ("policy_versions", 1)
S = M + ("source_versions", 0)
G = M + ("source_registry",)


def reference(path, digit):
    return {"path": path, "sha256": digit * 64}


def payload(*, review=False):
    return {"schema_version": "historical-dataset-manifest-1.0", "manifest": {
        "schema_version": "dataset-manifest-1.0", "dataset_id": "합성 데이터 묶음", "dataset_version": "SYNTH-D1",
        "created_at": "2026-01-02T03:04:05+00:00", "freshness_max_age_days": 7,
        "engine_version": "historical-engine", "engine_artifact_sha256": "7" * 64,
        "policy_versions": [
            {"policy_id": "SYNTH-OTHER", "edition_id": "2025", "rule_version": "r0002",
             "artifact": reference("synthetic/missing-other-policy.json", "8"), "fingerprint": "8" * 64,
             "schema_version": "policy-data-1.0", "rule_schema_version": "m1.1"},
            {"policy_id": "SYNTH-POLICY", "edition_id": "2026", "rule_version": "r0001",
             "artifact": reference("synthetic/missing-policy.json", "b"), "fingerprint": "a" * 64,
             "schema_version": "policy-data-1.0", "rule_schema_version": "m1.1"}],
        "source_registry": {"artifact": reference("synthetic/missing-registry.json", "9"),
                            "fingerprint": "3" * 64, "schema_version": "source-registry-1.0"},
        "source_versions": [{"source_document_id": "SYNTH-Z", "document_version": "d0002"},
                            {"source_document_id": "SYNTH-SRC", "document_version": "d0001"}],
        "review_manifest": reference("synthetic/other-policy-reviews.json", "6") if review else None,
    }}


def encode(body):
    # 합성 fixture 저작 전용. 소비 loader의 helper/to_dict를 이용하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def record_values(**changes):
    return {"acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": date(2026, 1, 3),
        "valid_until": date(2026, 12, 31), "review_artifact_ref": "acceptance-review:sha256:" + "f" * 64,
        "revokes_acceptance_ref": None, **changes}


def raw_record(values):
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


def raw_entry(values, manifest_hash, reference_changes=None):
    revoked = values["status"] is BenefitAcceptanceStatus.REVOKED
    refs = {key: None if revoked else reference(f"synthetic/{key}.json", "b") for key in REFERENCES}
    if not revoked:
        refs.update(dataset_manifest_ref={"path": "synthetic/missing-manifest.json", "sha256": manifest_hash},
                    policy_envelope_ref=reference("synthetic/missing-policy.json", "b"),
                    source_registry_ref=reference("synthetic/missing-registry.json", "9"))
    refs.update(reference_changes or {})
    binding = {"source_document_id": "SYNTH-SRC", "document_version": "d0001"}
    return {"acceptance": raw_record(values), **refs,
        "claim_evidence": [] if revoked else [{"claim": claim, "evidence_refs": ["SYNTH-SRC#a"]}
            for claim in ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding),
            "artifact": reference("synthetic/missing-source.pdf", "a")}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER", "review_note": "합성 Manifest 원본 대응",
        "manual_scenario_ids": ["HM01"]}


def bundle(raw, *, changes=None, expected_hash=None, extras=(), target_first=False, reference_changes=None):
    # 독립 fixture 저작 시 H를 고정한다. 실제 M2.57 반환 A와 원본 R을 소비 API에 전달한다.
    target = record_values(**(changes or {}))
    specs = [(target, expected_hash if expected_hash is not None else hashlib.sha256(raw).hexdigest())]
    specs = specs + list(extras) if target_first else list(extras) + specs
    rows = [raw_entry(values, digest, reference_changes if values is target else None) for values, digest in specs]
    review_raw = encode({"schema_version": "benefit-acceptance-review-1.0", "entries": rows})
    ref = "acceptance-review:sha256:" + hashlib.sha256(review_raw).hexdigest()
    records = tuple(PolicyBenefitAcceptance(**{**values, "review_artifact_ref": ref}) for values, _ in specs)
    artifact = load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=records)
    original = records[0 if target_first else -1]
    assert next(e for e in artifact.entries if e.acceptance.acceptance_ref == original.acceptance_ref).acceptance is original
    return artifact, original


def run(raw, *, prepared=None, **options):
    artifact, record = prepared if prepared is not None else bundle(raw, **options)
    return load_historical_dataset_manifest_bytes(raw_bytes=raw, artifact=artifact, expected_acceptance=record)


def error(prefix, raw, *, field=None, prepared=None, **options):
    with pytest.raises(PolicyDataError) as caught:
        run(raw, prepared=prepared, **options)
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


def change(body, path, value):
    at(body, path[:-1])[path[-1]] = value
    return body


def path_name(path):
    result = ""
    for key in path:
        result += f"[{key}]" if type(key) is int else ("." if result else "") + key
    return result or "root"


OBJECT_PATHS = ((), M, M + ("policy_versions", 0), M + ("policy_versions", 0, "artifact"), P,
    P + ("artifact",), G, G + ("artifact",), S, M + ("source_versions", 1), M + ("review_manifest",))
OBJECT_KEYS = tuple((path, tuple(at(payload(review=True), path))) for path in OBJECT_PATHS)
STRING_PATHS = tuple(path + (key,) for path, keys in OBJECT_KEYS for key in keys
                     if type(at(payload(review=True), path)[key]) is str)


def test_public_api_exact_types_and_stored_fields():
    fn = load_historical_dataset_manifest_bytes
    assert fn is domain.load_historical_dataset_manifest_bytes
    assert policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "artifact", "expected_acceptance")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "artifact": AcceptanceReviewArtifact,
        "expected_acceptance": PolicyBenefitAcceptance, "return": DatasetManifest}
    assert tuple(f.name for f in fields(DatasetManifest)) == MANIFEST_KEYS
    assert tuple(f.name for f in fields(PolicyEditionReference)) == POLICY_KEYS
    assert tuple(f.name for f in fields(SourceRegistryReference)) == ("artifact", "fingerprint", "schema_version")
    assert tuple(f.name for f in fields(ArtifactReference)) == ("path", "sha256")
    assert tuple(f.name for f in fields(SourceBinding)) == ("source_document_id", "document_version")
    for kwargs in ({}, {"raw_bytes": b""}, {"raw_bytes": b"", "artifact": None}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", None, None)
    for option in ("skip_hash", "force_verified", "allow_stale", "ignore_registry", "skip_membership",
                   "use_current_manifest", "auto_select_entry"):
        with pytest.raises(TypeError):
            fn(raw_bytes=b"", artifact=None, expected_acceptance=None, **{option: True})


@pytest.mark.parametrize("review", (False, True))
def test_hm01_11_field_restoration_and_nullable_review(review):
    body = payload(review=review)
    raw = encode(body)
    if not review:
        assert hashlib.sha256(raw).hexdigest() == FIXED_RAW_SHA256
    artifact, record = bundle(raw)
    result = run(raw, prepared=(artifact, record))
    assert type(result) is DatasetManifest and result.to_dict() == body["manifest"]
    assert result.created_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert result.created_at.tzinfo is timezone.utc
    assert type(result.policy_versions) is tuple and type(result.source_versions) is tuple
    assert [p.policy_id for p in result.policy_versions] == ["SYNTH-OTHER", "SYNTH-POLICY"]
    assert [s.source_document_id for s in result.source_versions] == ["SYNTH-Z", "SYNTH-SRC"]
    assert all(type(p) is PolicyEditionReference and type(p.artifact) is ArtifactReference for p in result.policy_versions)
    assert type(result.source_registry) is SourceRegistryReference
    assert type(result.source_registry.artifact) is ArtifactReference
    assert all(type(s) is SourceBinding for s in result.source_versions)
    assert (result.review_manifest is None) is (not review)
    assert result.engine_artifact_sha256 != record.coverage_implementation_fingerprint
    assert result.policy_versions[1].fingerprint != record.coverage_policy_tree_fingerprint
    assert result.fingerprint() != artifact.entries[-1].dataset_manifest_ref.sha256


@pytest.mark.parametrize("target_first", (False, True))
def test_explicit_entry_revision_not_position_or_other_digest(target_first):
    raw = encode(payload())
    other = record_values(acceptance_ref="SYNTH-ACCEPT-OTHER", acceptance_version="a0002")
    prepared = bundle(raw, extras=((other, "0" * 64),), target_first=target_first)
    assert run(raw, prepared=prepared).dataset_version == "SYNTH-D1"


@pytest.mark.parametrize("target_first", (False, True))
def test_other_entry_matching_digest_never_falls_back(target_first):
    raw = encode(payload())
    other = record_values(acceptance_ref="SYNTH-ACCEPT-OTHER", acceptance_version="a0002")
    prepared = bundle(raw, expected_hash="0" * 64, extras=((other, hashlib.sha256(raw).hexdigest()),),
                      target_first=target_first)
    error("HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH", raw, prepared=prepared)


@pytest.mark.parametrize("digest", ("4" * 64, "7" * 64))
def test_engine_hash_equality_or_difference_does_not_prove_zip_execution(digest):
    raw = encode(change(payload(), M + ("engine_artifact_sha256",), digest))
    result = run(raw)
    assert result.engine_artifact_sha256 == digest and result.engine_version == "historical-engine"
    assert not hasattr(result, "zip_verified")


@pytest.mark.parametrize("field", ("dataset_id", "dataset_version", "engine_version"))
@pytest.mark.parametrize("value", ("한국어 release 이름", " non-semver value ", "i", "2025 이전 묶음"))
def test_nonblank_metadata_is_not_normalized_or_assigned_new_grammar(field, value):
    body = change(payload(), M + (field,), value)
    opts = {"coverage_dataset_version": value, "benefit_dataset_version": value} if field == "dataset_version" else {}
    result = run(encode(body), changes=opts)
    assert getattr(result, field) == value


@pytest.mark.parametrize("quarter", (None, 1, 2, 3, 4))
def test_manifest_does_not_prove_or_overwrite_quarter(quarter):
    result = run(encode(payload()), changes={"scope": ApplicabilityScope("2026", quarter)})
    assert result.policy_versions[1].edition_id == "2026"
    assert not hasattr(result.policy_versions[1], "quarter")


def test_order_unicode_and_utc_snapshot_domain_boundaries():
    body = payload()
    first = run(encode(body))
    body["manifest"]["policy_versions"].reverse()
    body["manifest"]["source_versions"].reverse()
    second = run(encode(body))
    assert first.policy_versions == tuple(reversed(second.policy_versions))
    assert first.source_versions == tuple(reversed(second.source_versions))
    assert first.fingerprint() == second.fingerprint()
    assert encode(payload()) != encode(body)
    nfc = change(payload(), M + ("dataset_id",), "가é")
    nfd = deepcopy(nfc)
    nfd["manifest"]["dataset_id"] = unicodedata.normalize("NFD", nfc["manifest"]["dataset_id"])
    assert run(encode(nfc)).dataset_id != run(encode(nfd)).dataset_id
    original = replace(first, created_at=datetime(2026, 1, 2, 12, 4, 5, tzinfo=timezone(timedelta(hours=9)), fold=1))
    assert original.to_dict() == first.to_dict()
    assert first.created_at.fold == 0 and first.created_at.tzinfo is timezone.utc


def test_100_repetitions_determinism_immutability_and_no_input_mutation():
    raw = encode(payload(review=True))
    artifact, record = bundle(raw)
    before = (raw, artifact.to_dict(), record.to_dict())
    results = [run(raw, prepared=(artifact, record)) for _ in range(100)]
    assert all(x == results[0] and x.to_dict() == results[0].to_dict() for x in results)
    assert (raw, artifact.to_dict(), record.to_dict()) == before
    result = results[0]
    for obj in (result, *result.policy_versions, result.source_registry, *result.source_versions,
                result.review_manifest, result.source_registry.artifact):
        assert not hasattr(obj, "__dict__")
        for f in fields(obj):
            with pytest.raises(FrozenInstanceError):
                setattr(obj, f.name, getattr(obj, f.name))
    snapshot = result.to_dict()
    snapshot["policy_versions"].clear()
    assert len(result.policy_versions) == 2


@pytest.mark.parametrize("field", ("raw_bytes", "artifact", "expected_acceptance"))
@pytest.mark.parametrize("bad", (None, True, 0, "x", [], {}, bytearray(b"x")))
def test_exact_input_types(field, bad):
    raw = encode(payload()); artifact, record = bundle(raw)
    kwargs = {"raw_bytes": raw, "artifact": artifact, "expected_acceptance": record, field: bad}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_DATASET_MANIFEST_LOADER_INPUT: " + field + ":"):
        load_historical_dataset_manifest_bytes(**kwargs)


@pytest.mark.parametrize("field", ("raw_bytes", "artifact", "expected_acceptance"))
def test_subclass_input_is_rejected(field):
    raw = encode(payload()); artifact, record = bundle(raw)
    kwargs = {"raw_bytes": raw, "artifact": artifact, "expected_acceptance": record}
    original = kwargs[field]
    sub = type("SyntheticSubclass", (type(original),), {})
    kwargs[field] = sub(raw) if field == "raw_bytes" else sub(**{f.name: getattr(original, f.name) for f in fields(original)})
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_DATASET_MANIFEST_LOADER_INPUT:"):
        load_historical_dataset_manifest_bytes(**kwargs)


@pytest.mark.parametrize("kind", ("copy", "root", "missing", "revision", "revoked"))
def test_entry_identity_and_status_fail_before_bytes(kind):
    raw = encode(payload()); artifact, record = bundle(raw)
    if kind == "copy":
        record = replace(record)
    elif kind == "root":
        record = replace(record, review_artifact_ref="acceptance-review:sha256:" + "0" * 64)
    elif kind == "missing":
        record = replace(record, acceptance_ref="SYNTH-MISSING")
    elif kind == "revision":
        record = replace(record, acceptance_ref="SYNTH-ACCEPT-B", acceptance_version="a0002")
    else:
        artifact, record = bundle(raw, changes={"status": BenefitAcceptanceStatus.REVOKED,
            "revokes_acceptance_ref": "SYNTH-PREVIOUS"})
    error("HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH", b"not json", prepared=(artifact, record))


@pytest.mark.parametrize("bad", (None, "path", {"path": "x", "sha256": "0" * 64}))
def test_invalid_manifest_ref_is_rejected_by_existing_entry_constructor_without_frozen_damage(bad):
    artifact, _ = bundle(encode(payload()))
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT:"):
        replace(artifact.entries[0], dataset_manifest_ref=bad)


def test_duplicate_entry_and_cross_leg_contradictions_fail_at_existing_model_boundary():
    artifact, record = bundle(encode(payload()))
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT:"):
        replace(artifact, entries=artifact.entries * 2)
    for values in ({"benefit_dataset_version": "different"}, {"benefit_source_registry_fingerprint": "f" * 64}):
        with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE:"):
            replace(record, **values)


@pytest.mark.parametrize("raw", (b"{", b"\xef\xbb\xbf{}", b"\xff", b"", b"{not json}"))
def test_sha_mismatch_blocks_decode_parse_and_construction(raw, monkeypatch):
    prepared = bundle(raw, expected_hash="0" * 64)
    def forbidden(*args, **kwargs):
        pytest.fail("SHA mismatch 이후 parsing/복원을 실행했습니다")
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", forbidden)
        patch.setattr(domain, "_load_manifest", forbidden)
        error("HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH", raw, prepared=prepared)


def test_raw_byte_change_and_wrong_hash_domain_are_not_adopted():
    raw = encode(payload()); prepared = bundle(raw)
    error("HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH", raw + b"\n", prepared=prepared)
    for digest in ("3" * 64, "7" * 64, run(raw).fingerprint()):
        error("HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH", raw, expected_hash=digest)


@pytest.mark.parametrize("raw", (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xef\xbb\xbf{}"))
def test_encoding_failures_use_independently_authored_h(raw):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_ENCODING", raw)


@pytest.mark.parametrize("raw", (b"", b"{", b"{bad}", b"{}{}", b'{"a":01}', b'{"a":+1}', b'[1,]', b'{"a":}'))
def test_malformed_json(raw):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_JSON", raw)


@pytest.mark.parametrize("token", ("NaN", "Infinity", "-Infinity", "1.0", "1e0", "1E+1", "0.1", "9" * 5000))
def test_noninteger_or_unconvertible_number_tokens(token):
    raw = encode(payload()).replace(b'"freshness_max_age_days":7', ('"freshness_max_age_days":' + token).encode())
    error("INVALID_HISTORICAL_DATASET_MANIFEST_NUMBER", raw)


def test_json_decoder_recursion_is_explicit_json_error():
    # 이 CPython JSON decoder의 C 재귀 한도는 Python 함수 재귀 한도와 다르다.
    depth = 20000
    error("INVALID_HISTORICAL_DATASET_MANIFEST_JSON", ("[" * depth + "0" + "]" * depth).encode())


@pytest.mark.parametrize("path,keys", OBJECT_KEYS)
def test_duplicate_keys_at_every_object_depth(path, keys):
    body = payload(review=True)
    row = at(body, path)
    encoded = encode(row)
    key = keys[0]
    duplicate = encoded[:-1] + b"," + encode(key) + b":" + encode(row[key]) + b"}"
    raw = encode(body).replace(encoded, duplicate, 1)
    error("DUPLICATE_HISTORICAL_DATASET_MANIFEST_JSON_KEY", raw)


@pytest.mark.parametrize("raw", (b'{"a":"\\ud800"}', b'{"\\udfff":0}', b'["\\ud800"]'))
def test_unicode_surrogates_in_values_or_keys(raw):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_UNICODE", raw)


@pytest.mark.parametrize("kind", ("pretty", "newline", "space", "ordering", "ascii", "negative_zero", "escaped_slash"))
def test_noncanonical_representations_are_not_rewritten(kind):
    body = payload(); raw = encode(body)
    if kind == "pretty":
        raw = json.dumps(body, ensure_ascii=False, indent=2).encode()
    elif kind == "newline":
        raw += b"\n"
    elif kind == "space":
        raw = b" " + raw
    elif kind == "ordering":
        raw = json.dumps(body, sort_keys=False, separators=(",", ":"), ensure_ascii=False).encode()
    elif kind == "ascii":
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    elif kind == "negative_zero":
        raw = raw.replace(b'"freshness_max_age_days":7', b'"freshness_max_age_days":-0')
    else:
        raw = raw.replace(b"synthetic/", b"synthetic\\/")
    error("NONCANONICAL_HISTORICAL_DATASET_MANIFEST_BYTES", raw)


@pytest.mark.parametrize("path,key", tuple((p, k) for p, keys in OBJECT_KEYS for k in keys))
def test_missing_fields_including_defaults_are_not_filled(path, key):
    body = payload(review=True); del at(body, path)[key]
    error("INVALID_HISTORICAL_DATASET_MANIFEST_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,keys", OBJECT_KEYS)
def test_extra_fields_at_all_depths(path, keys):
    body = payload(review=True); at(body, path)["unexpected"] = "x"
    error("INVALID_HISTORICAL_DATASET_MANIFEST_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,keys", OBJECT_KEYS)
@pytest.mark.parametrize("bad", (None, [], "x", 1, True))
def test_object_types_at_every_depth(path, keys, bad):
    body = change(payload(review=True), path, bad) if path else bad
    if path == M + ("review_manifest",) and bad is None:
        assert run(encode(body)).review_manifest is None
    else:
        error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("path", STRING_PATHS)
@pytest.mark.parametrize("bad", (None, 0, True, [], {}))
def test_string_primitives_at_every_field(path, bad):
    body = change(payload(review=True), path, bad)
    error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("field", ("policy_versions", "source_versions"))
@pytest.mark.parametrize("bad", (None, {}, "x", 1, True))
def test_collection_types(field, bad):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", encode(change(payload(), M + (field,), bad)))


@pytest.mark.parametrize("field", ("policy_versions", "source_versions"))
@pytest.mark.parametrize("bad", (None, [], "x", 1, True))
def test_collection_item_types(field, bad):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", encode(change(payload(), M + (field, 0), bad)))


@pytest.mark.parametrize("bad", (None, True, False, "7", [], {}))
def test_freshness_exact_integer_type(bad):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", encode(change(payload(), M + ("freshness_max_age_days",), bad)))


@pytest.mark.parametrize("path", (("schema_version",), M + ("schema_version",)))
@pytest.mark.parametrize("value", ("", "wrong", "historical-dataset-manifest-2.0", "dataset-manifest-2.0"))
def test_outer_and_domain_schema_literals(path, value):
    error("UNSUPPORTED_HISTORICAL_DATASET_MANIFEST_SCHEMA", encode(change(payload(), path, value)), field=path_name(path))


@pytest.mark.parametrize("value", ("2026-01-02T03:04:05+00:00", "2026-01-02T03:04:05.000001+00:00",
    "2026-01-02T03:04:05.123000+00:00", "0001-01-01T00:00:00+00:00", "9999-12-31T23:59:59.999999+00:00",
    "2024-02-29T00:00:00+00:00"))
def test_utc_timestamp_valid_boundaries(value):
    result = run(encode(change(payload(), M + ("created_at",), value)))
    assert type(result.created_at) is datetime and result.created_at.isoformat() == value
    assert result.to_dict()["created_at"] == value


@pytest.mark.parametrize("value", ("", "2026-01-02", "2026-01-02T03:04:05", "2026-01-02T03:04:05Z",
    "2026-01-02 03:04:05+00:00", "2026-01-02t03:04:05+00:00", "2026-01-02T03:04:05+09:00",
    "2026-01-02T03:04:05-00:00", "2026-01-02T03:04:05.000000+00:00", "2026-01-02T03:04:05.123+00:00",
    "2026-01-02T03:04:05.1234567+00:00", "2026-01-02T03:04+00:00", "2026-02-29T00:00:00+00:00",
    "0000-01-01T00:00:00+00:00", "10000-01-01T00:00:00+00:00", "2026-01-02T24:00:00+00:00",
    "2026-01-02T03:04:60+00:00", "２０２６-01-02T03:04:05+00:00", " 2026-01-02T03:04:05+00:00",
    "2026-01-02T03:04:05+00:00:00"))
def test_utc_timestamp_rejects_non_hm1_without_correction(value):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_TIMESTAMP", encode(change(payload(), M + ("created_at",), value)),
          field="manifest.created_at")


MODEL_BAD_VALUES = (
    *((M + (field,), value) for field in ("dataset_id", "dataset_version", "engine_version") for value in ("", " \t")),
    (M + ("freshness_max_age_days",), 0), (M + ("freshness_max_age_days",), -1),
    (M + ("policy_versions",), []), (M + ("source_versions",), []),
    *((P + ("policy_id",), value) for value in ("bad", "A_B", "", "-A")),
    *((P + ("edition_id",), value) for value in ("26", "２０２６", "20260", "")),
    *((P + ("rule_version",), value) for value in ("r0000", "r1", "r00001", "R0001", "")),
    *((S + ("document_version",), value) for value in ("d0000", "d1", "d00001", "")),
    (S + ("source_document_id",), "bad_source"),
    (P + ("schema_version",), "policy-data-2.0"), (P + ("rule_schema_version",), "m1.0"),
    (G + ("schema_version",), "source-registry-2.0"),
    *((path, value) for path in (M + ("engine_artifact_sha256",), P + ("fingerprint",), G + ("fingerprint",),
        P + ("artifact", "sha256"), G + ("artifact", "sha256"), M + ("review_manifest", "sha256"))
      for value in ("", "f" * 63, "F" * 64, "g" * 64)),
    *((P + ("artifact", "path"), value) for value in ("", " ../x", "../x", "/x", "x/", "x//y",
        "x/./y", "C:/x", "x\\y", "x\x00y", "x\x7fy")),
)


@pytest.mark.parametrize("path,value", MODEL_BAD_VALUES)
def test_existing_constructor_invariants_are_not_weakened(path, value):
    error("INVALID_HISTORICAL_DATASET_MANIFEST_MODEL", encode(change(payload(review=True), path, value)))


@pytest.mark.parametrize("kind", ("policy_same", "policy_other_edition", "source_same", "source_other_version",
                                 "policy_registry_path", "policy_review_path", "registry_review_path"))
def test_duplicate_ids_and_artifact_paths_are_not_deduplicated(kind):
    body = payload(review=True); m = body["manifest"]
    if kind.startswith("policy_same") or kind == "policy_other_edition":
        duplicate = deepcopy(m["policy_versions"][1])
        if kind == "policy_other_edition":
            duplicate["edition_id"] = "2025"
            duplicate["artifact"]["path"] = "synthetic/another.json"
        m["policy_versions"].append(duplicate)
    elif kind.startswith("source"):
        duplicate = deepcopy(m["source_versions"][0])
        if kind == "source_other_version":
            duplicate["document_version"] = "d0003"
        m["source_versions"].append(duplicate)
    elif kind == "policy_registry_path":
        m["source_registry"]["artifact"]["path"] = m["policy_versions"][1]["artifact"]["path"]
    elif kind == "policy_review_path":
        m["review_manifest"]["path"] = m["policy_versions"][1]["artifact"]["path"]
    else:
        m["review_manifest"]["path"] = m["source_registry"]["artifact"]["path"]
    error("INVALID_HISTORICAL_DATASET_MANIFEST_MODEL", encode(body))


@pytest.mark.parametrize("path,value,prefix", (
    (M + ("dataset_version",), "SYNTH-D2", "DATASET_MISMATCH"),
    (P + ("policy_id",), "SYNTH-ABSENT", "POLICY_MEMBERSHIP_MISMATCH"),
    (P + ("edition_id",), "2025", "EDITION_MISMATCH"),
    (P + ("rule_version",), "r0002", "RULE_VERSION_MISMATCH"),
    (G + ("fingerprint",), "c" * 64, "REGISTRY_FINGERPRINT_MISMATCH"),
    (P + ("artifact", "path"), "synthetic/different-policy.json", "POLICY_REFERENCE_MISMATCH"),
    (P + ("artifact", "sha256"), "c" * 64, "POLICY_REFERENCE_MISMATCH"),
    (G + ("artifact", "path"), "synthetic/different-registry.json", "REGISTRY_REFERENCE_MISMATCH"),
    (G + ("artifact", "sha256"), "c" * 64, "REGISTRY_REFERENCE_MISMATCH"),
))
def test_direct_bindings_and_exact_artifact_path_plus_sha(path, value, prefix):
    error("HISTORICAL_DATASET_MANIFEST_" + prefix, encode(change(payload(), path, value)))


@pytest.mark.parametrize("selected", ("policy_envelope_ref", "source_registry_ref"))
def test_binding_compares_same_entry_refs_instead_of_repairing_them(selected):
    raw = encode(payload())
    error("HISTORICAL_DATASET_MANIFEST_" + ("POLICY" if selected == "policy_envelope_ref" else "REGISTRY")
          + "_REFERENCE_MISMATCH", raw, reference_changes={selected: reference("synthetic/different.json", "c")})


@pytest.mark.parametrize("first,second,prefix", (
    ((M + ("created_at",), "bad"), (P + ("rule_version",), "bad"), "INVALID_HISTORICAL_DATASET_MANIFEST_TIMESTAMP"),
    ((M + ("schema_version",), "bad"), (P + ("rule_version",), "bad"), "UNSUPPORTED_HISTORICAL_DATASET_MANIFEST_SCHEMA"),
    ((M + ("policy_versions",), []), (M + ("dataset_version",), "other"), "INVALID_HISTORICAL_DATASET_MANIFEST_MODEL"),
    ((M + ("dataset_version",), "other"), (P + ("policy_id",), "ABSENT"), "HISTORICAL_DATASET_MANIFEST_DATASET_MISMATCH"),
    ((P + ("policy_id",), "ABSENT"), (G + ("fingerprint",), "c" * 64), "HISTORICAL_DATASET_MANIFEST_POLICY_MEMBERSHIP_MISMATCH"),
    ((P + ("edition_id",), "2025"), (P + ("rule_version",), "r0002"), "HISTORICAL_DATASET_MANIFEST_EDITION_MISMATCH"),
    ((P + ("rule_version",), "r0002"), (G + ("fingerprint",), "c" * 64), "HISTORICAL_DATASET_MANIFEST_RULE_VERSION_MISMATCH"),
    ((G + ("fingerprint",), "c" * 64), (P + ("artifact", "sha256"), "c" * 64), "HISTORICAL_DATASET_MANIFEST_REGISTRY_FINGERPRINT_MISMATCH"),
    ((P + ("artifact", "sha256"), "c" * 64), (G + ("artifact", "sha256"), "c" * 64), "HISTORICAL_DATASET_MANIFEST_POLICY_REFERENCE_MISMATCH"),
))
def test_cross_and_within_phase_precedence(first, second, prefix):
    body = payload()
    change(body, *first); change(body, *second)
    error(prefix, encode(body))


def test_p0_order_and_schema_before_canonical_before_timestamp():
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_DATASET_MANIFEST_LOADER_INPUT: raw_bytes:"):
        load_historical_dataset_manifest_bytes(raw_bytes=bytearray(), artifact=None, expected_acceptance=None)
    body = change(payload(), M + ("created_at",), "bad")
    error("NONCANONICAL_HISTORICAL_DATASET_MANIFEST_BYTES", encode(body) + b"\n")
    del body["manifest"]["review_manifest"]
    error("INVALID_HISTORICAL_DATASET_MANIFEST_FIELDS", encode(body) + b"\n")


def test_constructor_sequence_and_exact_same_bytes_used(monkeypatch):
    raw = encode(payload(review=True)); prepared = bundle(raw)
    real_sha, real_loads, real_construct = domain.hashlib.sha256, domain.json.loads, domain._construct
    observed, events = [], []
    def sha(value):
        observed.append(("hash", value))
        return real_sha(value)
    def loads(value, **kwargs):
        observed.append(("parse", value))
        return real_loads(value, **kwargs)
    def construct(constructor, field, **kwargs):
        result = real_construct(constructor, field, **kwargs)
        events.append((constructor.__name__, field, result))
        return result
    with monkeypatch.context() as patch:
        patch.setattr(domain.hashlib, "sha256", sha)
        patch.setattr(domain.json, "loads", loads)
        patch.setattr(domain, "_construct", construct)
        result = run(raw, prepared=prepared)
    assert observed == [("hash", raw), ("parse", raw.decode("utf-8"))]
    assert observed[0][1] is raw
    assert [e[0] for e in events] == ["ArtifactReference", "PolicyEditionReference", "ArtifactReference",
        "PolicyEditionReference", "ArtifactReference", "SourceRegistryReference", "SourceBinding", "SourceBinding",
        "ArtifactReference", "DatasetManifest"]
    assert result is events[-1][2]
    assert result.policy_versions[0] is events[1][2] and result.source_registry is events[5][2]


@pytest.mark.parametrize("constructor", ("PolicyEditionReference", "SourceRegistryReference", "SourceBinding", "DatasetManifest"))
def test_constructor_data_error_wrapping_and_programming_error_propagation(constructor, monkeypatch):
    raw = encode(payload()); prepared = bundle(raw)
    def data_error(**kwargs):
        raise PolicyDataError("secret original value")
    with monkeypatch.context() as patch:
        patch.setattr(domain, constructor, data_error)
        message = error("INVALID_HISTORICAL_DATASET_MANIFEST_MODEL", raw, prepared=prepared)
        assert "secret" not in message and "original value" not in message
    def programming_error(**kwargs):
        raise RuntimeError("programming error")
    monkeypatch.setattr(domain, constructor, programming_error)
    with pytest.raises(RuntimeError, match="programming error"):
        run(raw, prepared=prepared)


def test_exact_22_prefixes_match_spec_and_constructor_category_is_preserved():
    source = inspect.getsource(domain)
    prefixes = set(re.findall(r'"([A-Z][A-Z0-9_]+)"', source))
    spec = (Path(__file__).resolve().parents[1] / "docs/HISTORICAL_DATASET_MANIFEST_ARTIFACT_PREPARATION_SPEC.md").read_text(encoding="utf-8")
    declared = set(re.findall(r'^\| \d+ \| P\d \| ([A-Z_]+) \|', spec, re.M))
    assert prefixes == declared and len(prefixes) == 22
    msg = error("INVALID_HISTORICAL_DATASET_MANIFEST_MODEL",
        encode(change(payload(), P + ("rule_version",), "r0000")), field="manifest.policy_versions[1].rule_version")
    assert "INVALID_ENVELOPE_VERSION" in msg


def test_pure_loader_never_reads_registry_zip_other_artifacts_or_evaluates_full(monkeypatch):
    import builtins
    import os
    import socket
    import subprocess
    from backend.policy_engine.sources import SourceRegistry
    from backend.policy_engine.policy_data import manifest, validation
    raw = encode(payload()); prepared = bundle(raw)
    tree = ast.parse(inspect.getsource(domain))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names)
    assert imports <= {"datetime", "hashlib", "json", "re", "errors", "benefit_acceptance",
        "benefit_acceptance_review_artifact", "envelope", "manifest"}
    own = [v for v in vars(domain).values() if inspect.isfunction(v) and v.__module__ == domain.__name__]
    assert [fn.__name__ for fn in own if not fn.__name__.startswith("_")] == ["load_historical_dataset_manifest_bytes"]
    assert not any(isinstance(v, (dict, list, set)) for k, v in vars(domain).items() if not k.startswith("__"))
    assert not any(isinstance(n, ast.Attribute) and n.attr in ("now", "today", "utcnow") for n in ast.walk(tree))
    def forbidden(*args, **kwargs):
        pytest.fail("Manifest 원본 복원 범위 밖의 호출을 실행했습니다")
    with monkeypatch.context() as patch:
        for obj, name in ((builtins, "open"), (Path, "open"), (Path, "read_bytes"), (os, "getenv"),
            (socket, "create_connection"), (subprocess, "run"), (SourceRegistry, "get_source"), (SourceRegistry, "resolve"),
            (DatasetManifest, "fingerprint")):
            patch.setattr(obj, name, forbidden)
        for module, names in (
            (policy_data, ("load_acceptance_review_artifact_bytes", "load_historical_benefit_snapshot_bytes",
                "load_historical_eligibility_coverage_bytes", "load_historical_policy_envelope_bytes",
                "load_historical_coverage_review_context_bytes", "evaluate_eligibility_coverage")),
            (manifest, ("fingerprint_source_registry", "fingerprint_policy_envelope")),
            (validation, ("validate_dataset_manifest", "validate_envelope_sources")),
        ):
            for name in names:
                patch.setattr(module, name, forbidden)
        result = run(raw, prepared=prepared)
    assert result.to_dict() == payload()["manifest"]
    assert not any(hasattr(result, name) for name in ("status", "matched", "is_full", "usable", "amount"))

