"""HSR1 bytes/실제 domain fp/원본 Entry를 검증한다. 원문·사용 승인은 검증하지 않는다."""

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
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
from backend.policy_engine.sources import (
    SourceDocument, SourceEvidence, SourceRegistry, SourceStatus, SourceType, SourceValidationError,
    VerificationStatus, parse_source_registry,
)
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, ApplicabilityScope, ArtifactReference, BenefitAcceptanceStatus,
    PolicyBenefitAcceptance, fingerprint_source_registry, load_acceptance_review_artifact_bytes,
    load_historical_source_registry_bytes,
)
from backend.policy_engine.policy_data import historical_source_registry_loader as domain


FIXED_RAW_LENGTH = 2509
FIXED_RAW_SHA256 = "97978d60ef2d3f48bf3e675f3f93eb3c58a5f4d2673fa2c0a102dfd28586b7d2"
FIXED_DOMAIN_FP = "005f78470af9289e31b0b6bd46bb2bcc34861944c0670e276e8d4c5ecb37fc35"
FIXED_MINIMAL_FP = "bf0143340dec9898a7c99a1baeadef5d21d01ac5fb3c8fb4cca729e8093f5f7d"
DOCUMENT_REQUIRED = ("source_document_id", "document_version", "source_type", "issuer", "title", "official_url",
    "publication_date", "verified_at", "verification_status", "status", "locators")
DOCUMENT_OPTIONAL = ("notice_number", "attachment_url", "previous_urls", "effective_from", "effective_to",
    "supersedes", "content_sha256")
EVIDENCE_REQUIRED = ("locator_id", "section", "meaning_summary", "applicable_policy_ids", "verified_at",
    "verification_status", "status")
EVIDENCE_OPTIONAL = ("page", "table_position")
REFERENCES = ("accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
              "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref")
D = ("sources", 0)
E = D + ("locators", 0)


def evidence(locator_id, **changes):
    return {"locator_id": locator_id, "section": "합성 조건 절", "meaning_summary": "원문 사용 승인이 아닌 합성 설명",
        "applicable_policy_ids": ["SYNTH-Z", "SYNTH-POLICY"], "verified_at": "2026-01-09",
        "verification_status": "VERIFIED", "status": "ACTIVE", "page": 2,
        "table_position": "합성 표 2행", **changes}


def document(source_id, version, locators):
    return {"source_document_id": source_id, "document_version": version, "source_type": "OFFICIAL_NOTICE",
        "issuer": "합성 기관 TEST_ONLY", "title": "합성 공고", "official_url": "https://policy.example.invalid/notice",
        "publication_date": "2024-02-29", "verified_at": "2026-01-10", "verification_status": "VERIFIED",
        "status": "ACTIVE", "locators": locators, "notice_number": "합성 공고 1호",
        "attachment_url": "https://files.example.invalid/original.pdf",
        "previous_urls": ["https://old.example.invalid/z", "https://old.example.invalid/a"],
        "effective_from": "2020-01-01", "effective_to": "2030-01-01",
        "supersedes": [{"source_document_id": "SYNTH-OLD-Z", "document_version": "d0002"},
                       {"source_document_id": "SYNTH-OLD-A", "document_version": "d0001"}],
        "content_sha256": "a" * 64}


def payload(*, minimal=False):
    body = {"schema_version": "source-registry-1.0", "sources": [
        document("SYNTH-Z", "d0002", [evidence("z"), evidence("alpha")]),
        document("SYNTH-SRC", "d0001", [evidence("a")]),
    ]}
    if minimal:
        for doc in body["sources"]:
            for key in DOCUMENT_OPTIONAL:
                del doc[key]
            for row in doc["locators"]:
                for key in EVIDENCE_OPTIONAL:
                    del row[key]
    return body


def encode(body):
    # 합성 원본 저작 전용. 소비 loader의 private helper를 사용하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def author_fingerprint(body):
    # 기존에 검증된 참조 parser/helper로 fixture 발급 시 F를 고정한다. 소비 호출/spies보다 앞이다.
    return fingerprint_source_registry(parse_source_registry(deepcopy(body)))


def record_values(**changes):
    return {"acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": FIXED_DOMAIN_FP,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": FIXED_DOMAIN_FP, "reviewed_at": date(2026, 1, 11),
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


def raw_entry(values, registry_hash):
    revoked = values["status"] is BenefitAcceptanceStatus.REVOKED
    refs = {key: None if revoked else {"path": f"synthetic/{key}.json", "sha256": "b" * 64} for key in REFERENCES}
    if not revoked:
        refs["source_registry_ref"] = {"path": "synthetic/missing-registry.json", "sha256": registry_hash}
    binding = {"source_document_id": "SYNTH-SRC", "document_version": "d0001"}
    return {"acceptance": raw_record(values), **refs,
        "claim_evidence": [] if revoked else [{"claim": claim, "evidence_refs": ["SYNTH-SRC#a"]}
            for claim in ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding), "artifact": {
            "path": "synthetic/missing-original.pdf", "sha256": "a" * 64}}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER", "review_note": "합성 Registry 원본 검토",
        "manual_scenario_ids": ["HS01"]}


def bundle(raw, *, expected_hash=None, fingerprint=None, changes=None, extras=(), target_first=False):
    fp = fingerprint if fingerprint is not None else FIXED_DOMAIN_FP
    target = record_values(**{"coverage_source_registry_fingerprint": fp,
                              "benefit_source_registry_fingerprint": fp, **(changes or {})})
    specs = [(target, expected_hash if expected_hash is not None else hashlib.sha256(raw).hexdigest())]
    specs = specs + list(extras) if target_first else list(extras) + specs
    review_raw = encode({"schema_version": "benefit-acceptance-review-1.0",
        "entries": [raw_entry(values, digest) for values, digest in specs]})
    ref = "acceptance-review:sha256:" + hashlib.sha256(review_raw).hexdigest()
    records = tuple(PolicyBenefitAcceptance(**{**values, "review_artifact_ref": ref}) for values, _ in specs)
    root = load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=records)
    original = records[0 if target_first else -1]
    assert next(e for e in root.entries if e.acceptance.acceptance_ref == original.acceptance_ref).acceptance is original
    return root, original


def run(raw, *, prepared=None, **options):
    artifact, record = prepared if prepared is not None else bundle(raw, **options)
    return load_historical_source_registry_bytes(raw_bytes=raw, artifact=artifact, expected_acceptance=record)


def error(prefix, raw, *, prepared=None, field=None, **options):
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


DOC_PATHS = tuple(("sources", i) for i in range(2))
EVIDENCE_PATHS = tuple(p + ("locators", i) for p in DOC_PATHS for i in range(len(at(payload(), p)["locators"])))
PAIR_PATHS = tuple(p + ("supersedes", i) for p in DOC_PATHS for i in range(2))
OBJECT_KEYS = (((), ("schema_version", "sources"), ()),) + tuple((p, DOCUMENT_REQUIRED, DOCUMENT_OPTIONAL) for p in DOC_PATHS) \
    + tuple((p, EVIDENCE_REQUIRED, EVIDENCE_OPTIONAL) for p in EVIDENCE_PATHS) \
    + tuple((p, ("source_document_id", "document_version"), ()) for p in PAIR_PATHS)
NULLABLE_STRINGS = tuple(p + (k,) for p in DOC_PATHS for k in ("publication_date", "verified_at", "notice_number",
    "attachment_url", "effective_from", "effective_to", "content_sha256")) \
    + tuple(p + (k,) for p in EVIDENCE_PATHS for k in ("verified_at", "table_position"))
STRING_PATHS = tuple(p + (k,) for p, req, opt in OBJECT_KEYS for k in req + opt if type(at(payload(), p)[k]) is str)
ARRAY_PATHS = (("sources",),) + tuple(p + (k,) for p in DOC_PATHS for k in ("locators", "previous_urls", "supersedes")) \
    + tuple(p + ("applicable_policy_ids",) for p in EVIDENCE_PATHS)


def test_exact_api_types_and_existing_stored_fields():
    fn = load_historical_source_registry_bytes
    assert fn is domain.load_historical_source_registry_bytes and policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "artifact", "expected_acceptance")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "artifact": AcceptanceReviewArtifact,
        "expected_acceptance": PolicyBenefitAcceptance, "return": SourceRegistry}
    assert tuple(f.name for f in fields(SourceRegistry)) == ("sources",)
    assert tuple(f.name for f in fields(SourceDocument)) == DOCUMENT_REQUIRED + DOCUMENT_OPTIONAL
    assert tuple(f.name for f in fields(SourceEvidence)) == EVIDENCE_REQUIRED + EVIDENCE_OPTIONAL
    for kwargs in ({}, {"raw_bytes": b""}, {"raw_bytes": b"", "artifact": None}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", None, None)
    for option in ("skip_hash", "skip_fingerprint", "force_verified", "allow_stale", "ignore_source_status",
                   "use_current_registry", "fallback_registry", "auto_select_entry", "registry", "manifest"):
        with pytest.raises(TypeError):
            fn(raw_bytes=b"", artifact=None, expected_acceptance=None, **{option: True})


def test_fixed_raw_and_domain_vectors_and_full_restoration():
    body = payload(); raw = encode(body)
    assert len(raw) == FIXED_RAW_LENGTH
    assert hashlib.sha256(raw).hexdigest() == FIXED_RAW_SHA256
    assert author_fingerprint(body) == FIXED_DOMAIN_FP and FIXED_DOMAIN_FP != FIXED_RAW_SHA256
    result = run(raw)
    assert type(result) is SourceRegistry and result.to_dict() == body
    assert [s.source_document_id for s in result.sources] == ["SYNTH-Z", "SYNTH-SRC"]
    assert [s.document_version for s in result.sources] == ["d0002", "d0001"]
    assert [e.locator_id for e in result.sources[0].locators] == ["z", "alpha"]
    assert result.sources[0].previous_urls == tuple(body["sources"][0]["previous_urls"])
    assert result.sources[0].supersedes == (("SYNTH-OLD-Z", "d0002"), ("SYNTH-OLD-A", "d0001"))
    assert all(type(s) is SourceDocument and type(s.locators) is tuple for s in result.sources)
    assert all(type(e) is SourceEvidence for s in result.sources for e in s.locators)
    assert result.sources[0].publication_date == date(2024, 2, 29)
    assert result.sources[0].source_type is SourceType.OFFICIAL_NOTICE
    assert type(result.sources) is tuple


def test_optional_omission_and_explicit_defaults_have_same_model_but_distinct_raw():
    minimal = payload(minimal=True); explicit = deepcopy(minimal)
    for doc in explicit["sources"]:
        doc.update(notice_number=None, attachment_url=None, previous_urls=[], effective_from=None,
                   effective_to=None, supersedes=[], content_sha256=None)
        for item in doc["locators"]:
            item.update(page=None, table_position=None)
    assert author_fingerprint(minimal) == author_fingerprint(explicit) == FIXED_MINIMAL_FP
    raw_a, raw_b = encode(minimal), encode(explicit)
    assert hashlib.sha256(raw_a).hexdigest() != hashlib.sha256(raw_b).hexdigest()
    a = run(raw_a, fingerprint=FIXED_MINIMAL_FP); b = run(raw_b, fingerprint=FIXED_MINIMAL_FP)
    assert a == b and a.to_dict() == explicit and a.to_dict() != minimal
    assert "page" not in minimal["sources"][0]["locators"][0]


@pytest.mark.parametrize("path,key", tuple((p, k) for p, req, opt in OBJECT_KEYS for k in opt))
def test_each_legal_optional_omission_is_preserved_in_raw(path, key):
    body = payload(); del at(body, path)[key]
    before = deepcopy(body); raw = encode(body)
    result = run(raw, fingerprint=author_fingerprint(body))
    assert body == before and type(result) is SourceRegistry and key not in at(body, path)


@pytest.mark.parametrize("path", tuple(p + (k,) for p in DOC_PATHS for k in (
    "notice_number", "attachment_url", "effective_from", "effective_to", "content_sha256"))
    + tuple(p + (k,) for p in EVIDENCE_PATHS for k in ("page", "table_position")))
def test_nullable_optional_values(path):
    body = change(payload(), path, None)
    result = run(encode(body), fingerprint=author_fingerprint(body))
    assert at(result.to_dict(), path) is None


def test_required_nullable_dates_are_preserved_without_inference():
    body = payload()
    for doc in body["sources"]:
        doc.update(publication_date=None, verified_at=None, verification_status="DRAFT")
        for item in doc["locators"]:
            item.update(verified_at=None, verification_status="DRAFT")
    assert run(encode(body), fingerprint=author_fingerprint(body)).to_dict() == body


@pytest.mark.parametrize("verified_at", ("2000-01-01", "2099-12-31"))
def test_hs90_old_and_future_verification_dates_do_not_trigger_usage_gate(verified_at):
    body = payload()
    for doc in body["sources"]:
        doc["verified_at"] = verified_at
        for item in doc["locators"]:
            item["verified_at"] = verified_at
    result = run(encode(body), fingerprint=author_fingerprint(body))
    assert result.to_dict() == body


@pytest.mark.parametrize("doc_status", tuple(s.value for s in SourceStatus))
@pytest.mark.parametrize("evidence_status", tuple(s.value for s in SourceStatus))
def test_historical_lifecycle_states_are_not_used_as_referenceability_gate(doc_status, evidence_status):
    body = payload(); body["sources"][0]["status"] = doc_status
    body["sources"][0]["locators"][0]["status"] = evidence_status
    result = run(encode(body), fingerprint=author_fingerprint(body))
    assert result.sources[0].status is SourceStatus(doc_status)
    assert result.sources[0].locators[0].status is SourceStatus(evidence_status)


@pytest.mark.parametrize("doc_status", tuple(s.value for s in VerificationStatus))
@pytest.mark.parametrize("evidence_status", tuple(s.value for s in VerificationStatus))
def test_verification_states_are_preserved_independently(doc_status, evidence_status):
    body = payload(); body["sources"][0]["verification_status"] = doc_status
    body["sources"][0]["locators"][0]["verification_status"] = evidence_status
    assert run(encode(body), fingerprint=author_fingerprint(body)).to_dict() == body


@pytest.mark.parametrize("value", tuple(s.value for s in SourceType))
def test_source_types_are_existing_enum_values(value):
    body = change(payload(), D + ("source_type",), value)
    assert run(encode(body), fingerprint=author_fingerprint(body)).sources[0].source_type is SourceType(value)


def test_array_order_is_preserved_while_existing_domain_order_rules_apply():
    body = payload(); before = run(encode(body))
    body["sources"].reverse()
    for doc in body["sources"]:
        doc["locators"].reverse(); doc["supersedes"].reverse()
        for row in doc["locators"]:
            row["applicable_policy_ids"].reverse()
    result = run(encode(body))
    assert result.to_dict() == body
    assert [s.source_document_id for s in result.sources] == [s.source_document_id for s in reversed(before.sources)]
    assert author_fingerprint(body) == FIXED_DOMAIN_FP
    assert encode(body) != encode(payload())


def test_previous_urls_order_changes_domain_fp_and_is_not_sorted_back():
    body = payload(); body["sources"][0]["previous_urls"].reverse()
    error("HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH", encode(body))
    new_fp = author_fingerprint(body)
    assert new_fp != FIXED_DOMAIN_FP
    assert run(encode(body), fingerprint=new_fp).sources[0].previous_urls == tuple(body["sources"][0]["previous_urls"])


def test_unicode_normalization_is_not_applied():
    nfc = change(payload(), D + ("title",), "가é")
    nfd = deepcopy(nfc); nfd["sources"][0]["title"] = unicodedata.normalize("NFD", nfc["sources"][0]["title"])
    assert encode(nfc) != encode(nfd) and author_fingerprint(nfc) != author_fingerprint(nfd)
    assert run(encode(nfc), fingerprint=author_fingerprint(nfc)).sources[0].title == "가é"
    assert run(encode(nfd), fingerprint=author_fingerprint(nfd)).sources[0].title != "가é"


@pytest.mark.parametrize("target_first", (False, True))
def test_exact_revision_selection_and_no_other_entry_hash_fallback(target_first):
    raw = encode(payload())
    other = record_values(acceptance_ref="SYNTH-OTHER", acceptance_version="a0002")
    good = bundle(raw, extras=((other, "0" * 64),), target_first=target_first)
    assert run(raw, prepared=good).sources[0].source_document_id == "SYNTH-Z"
    bad = bundle(raw, expected_hash="0" * 64, extras=((other, FIXED_RAW_SHA256),), target_first=target_first)
    error("HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH", raw, prepared=bad)


def test_100_repetitions_immutability_and_input_isolation():
    raw = encode(payload()); prepared = bundle(raw); artifact, record = prepared
    before = (raw, artifact.to_dict(), record.to_dict())
    results = [run(raw, prepared=prepared) for _ in range(100)]
    assert all(result == results[0] and result.to_dict() == payload() for result in results)
    assert before == (raw, artifact.to_dict(), record.to_dict())
    for obj in (results[0], *results[0].sources, *results[0].sources[0].locators):
        assert not hasattr(obj, "__dict__")
        for f in fields(obj):
            with pytest.raises(FrozenInstanceError):
                setattr(obj, f.name, getattr(obj, f.name))
    snapshot = results[0].to_dict(); snapshot["sources"][0]["previous_urls"].clear()
    assert len(results[0].sources[0].previous_urls) == 2


@pytest.mark.parametrize("field", ("raw_bytes", "artifact", "expected_acceptance"))
@pytest.mark.parametrize("bad", (None, True, 0, "x", [], {}, bytearray(b"x")))
def test_exact_input_types(field, bad):
    raw = encode(payload()); artifact, record = bundle(raw)
    values = {"raw_bytes": raw, "artifact": artifact, "expected_acceptance": record, field: bad}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_SOURCE_REGISTRY_LOADER_INPUT: " + field + ":"):
        load_historical_source_registry_bytes(**values)


@pytest.mark.parametrize("field", ("raw_bytes", "artifact", "expected_acceptance"))
def test_input_subclasses_are_not_coerced(field):
    raw = encode(payload()); artifact, record = bundle(raw)
    values = {"raw_bytes": raw, "artifact": artifact, "expected_acceptance": record}
    old = values[field]; subtype = type("SyntheticSubclass", (type(old),), {})
    values[field] = subtype(raw) if field == "raw_bytes" else subtype(**{f.name: getattr(old, f.name) for f in fields(old)})
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_SOURCE_REGISTRY_LOADER_INPUT:"):
        load_historical_source_registry_bytes(**values)


@pytest.mark.parametrize("kind", ("copy", "root", "missing", "revision", "revoked"))
def test_entry_identity_errors_precede_bytes(kind):
    raw = encode(payload()); artifact, record = bundle(raw)
    if kind == "copy": record = replace(record)
    elif kind == "root": record = replace(record, review_artifact_ref="acceptance-review:sha256:" + "0" * 64)
    elif kind == "missing": record = replace(record, acceptance_ref="MISSING")
    elif kind == "revision": record = replace(record, acceptance_ref="OTHER", acceptance_version="a0002")
    else:
        artifact, record = bundle(raw, changes={"status": BenefitAcceptanceStatus.REVOKED,
            "revokes_acceptance_ref": "PREVIOUS"})
    error("HISTORICAL_SOURCE_REGISTRY_REVIEW_BINDING_MISMATCH", b"invalid", prepared=(artifact, record))


@pytest.mark.parametrize("bad", (None, "path", {"path": "x", "sha256": "f" * 64}))
def test_missing_or_wrong_ref_rejected_at_entry_model_boundary_without_damage(bad):
    artifact, _ = bundle(encode(payload()))
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT:"):
        replace(artifact.entries[0], source_registry_ref=bad)


@pytest.mark.parametrize("bad", ("", "f" * 63, "F" * 64, "g" * 64, None, True))
def test_expected_raw_hash_format_uses_existing_artifact_constructor(bad):
    with pytest.raises(PolicyDataError, match="INVALID_MANIFEST_HASH"):
        ArtifactReference("synthetic/registry.json", bad)


@pytest.mark.parametrize("field", ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"))
@pytest.mark.parametrize("bad", ("", "F" * 64, "g" * 64, "1" * 63, None))
def test_malformed_acceptance_fingerprints_rejected_by_existing_record(field, bad):
    _, record = bundle(encode(payload()))
    with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE:"):
        replace(record, **{field: bad})


@pytest.mark.parametrize("field", ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"))
def test_one_leg_only_contradiction_rejected_by_same_release_model(field):
    _, record = bundle(encode(payload()))
    with pytest.raises(PolicyDataError, match="^INVALID_BENEFIT_ACCEPTANCE:"):
        replace(record, **{field: "0" * 64})


def test_duplicate_entry_is_existing_constructor_error():
    artifact, _ = bundle(encode(payload()))
    with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT:"):
        replace(artifact, entries=artifact.entries * 2)


@pytest.mark.parametrize("raw", (b"{", b"\xff", b"\xef\xbb\xbf{}", b"", b"not json"))
def test_sha_mismatch_prevents_json_parser_and_both_helpers(raw, monkeypatch):
    prepared = bundle(raw, expected_hash="0" * 64)
    def forbidden(*args, **kwargs): pytest.fail("SHA mismatch 후 parsing/helper를 실행했습니다")
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", forbidden)
        patch.setattr(domain, "parse_source_registry", forbidden)
        patch.setattr(domain, "fingerprint_source_registry", forbidden)
        error("HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH", raw, prepared=prepared)


def test_byte_change_and_domain_fp_cannot_replace_raw_hash():
    raw = encode(payload()); prepared = bundle(raw)
    error("HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH", raw + b"\n", prepared=prepared)
    error("HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH", raw, expected_hash=FIXED_DOMAIN_FP)
    error("HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH", raw, fingerprint=FIXED_RAW_SHA256)


@pytest.mark.parametrize("raw", (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xef\xbb\xbf{}"))
def test_encoding_with_independently_authored_matching_hash(raw):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_ENCODING", raw)


@pytest.mark.parametrize("raw", (b"", b"{", b"{bad}", b"{}{}", b'{"x":01}', b'{"x":+1}', b'[1,]', b'{"x":}'))
def test_malformed_json(raw):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_JSON", raw)


@pytest.mark.parametrize("token", ("NaN", "Infinity", "-Infinity", "1.0", "1e0", "1E+1", "0.1", "9" * 5000))
def test_invalid_number_tokens(token):
    raw = encode(payload()).replace(b'"page":2', ('"page":' + token).encode(), 1)
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_NUMBER", raw)


def test_json_decoder_recursion_error_is_explicit():
    depth = 20000  # 이 CPython JSON decoder의 별도 C 재귀 한도를 넘는 합성 입력.
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_JSON", ("[" * depth + "0" + "]" * depth).encode())


@pytest.mark.parametrize("path,required,optional", OBJECT_KEYS)
def test_duplicate_keys_at_every_object_depth(path, required, optional):
    body = payload(); row = at(body, path); raw_row = encode(row); key = required[0]
    duplicate = raw_row[:-1] + b"," + encode(key) + b":" + encode(row[key]) + b"}"
    error("DUPLICATE_HISTORICAL_SOURCE_REGISTRY_JSON_KEY", encode(body).replace(raw_row, duplicate, 1))


@pytest.mark.parametrize("raw", (b'{"x":"\\ud800"}', b'{"\\udfff":0}', b'["\\ud800"]'))
def test_invalid_unicode_scalars(raw):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_UNICODE", raw)


@pytest.mark.parametrize("kind", ("pretty", "space", "newline", "ordering", "ascii", "slash", "negative_zero"))
def test_noncanonical_representations(kind):
    body = payload(); raw = encode(body)
    if kind == "pretty": raw = json.dumps(body, ensure_ascii=False, indent=2).encode()
    elif kind == "space": raw = b" " + raw
    elif kind == "newline": raw += b"\n"
    elif kind == "ordering": raw = json.dumps(body, ensure_ascii=False, sort_keys=False, separators=(",", ":")).encode()
    elif kind == "ascii": raw = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    elif kind == "slash": raw = raw.replace(b"https://", b"https:\\/\\/")
    else: raw = raw.replace(b'"page":2', b'"page":-0', 1)
    error("NONCANONICAL_HISTORICAL_SOURCE_REGISTRY_BYTES", raw)


@pytest.mark.parametrize("path,key", tuple((p, k) for p, req, opt in OBJECT_KEYS for k in req))
def test_missing_required_fields_including_nullable_dates(path, key):
    body = payload(); del at(body, path)[key]
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,required,optional", OBJECT_KEYS)
def test_extra_fields_at_every_depth(path, required, optional):
    body = payload(); at(body, path)["extra"] = None
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,required,optional", OBJECT_KEYS)
@pytest.mark.parametrize("bad", (None, [], "x", 0, True))
def test_object_types(path, required, optional, bad):
    body = change(payload(), path, bad) if path else bad
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,bad", tuple((p, bad) for p in STRING_PATHS for bad in (None, 0, True, [], {})
                                         if not (bad is None and p in NULLABLE_STRINGS)))
def test_string_primitive_types(path, bad):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", encode(change(payload(), path, bad)), field=path_name(path))


@pytest.mark.parametrize("path", ARRAY_PATHS)
@pytest.mark.parametrize("bad", (None, {}, "x", 0, True))
def test_array_types_do_not_coerce(path, bad):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", encode(change(payload(), path, bad)), field=path_name(path))


@pytest.mark.parametrize("path", tuple(p + ("previous_urls", 0) for p in DOC_PATHS)
    + tuple(p + ("applicable_policy_ids", 0) for p in EVIDENCE_PATHS))
@pytest.mark.parametrize("bad", (None, {}, [], 0, True))
def test_string_array_items(path, bad):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", encode(change(payload(), path, bad)), field=path_name(path))


@pytest.mark.parametrize("bad", (True, False, "2", [], {}))
def test_page_exact_integer_type(bad):
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", encode(change(payload(), E + ("page",), bad)))


@pytest.mark.parametrize("value", ("", "source-registry-2.0", "historical-source-registry-1.0", "SOURCE-REGISTRY-1.0"))
def test_schema_version_is_not_invented_or_guessed(value):
    error("UNSUPPORTED_HISTORICAL_SOURCE_REGISTRY_SCHEMA", encode(change(payload(), ("schema_version",), value)))


MODEL_BAD_VALUES = (
    (("sources",), []), (D + ("locators",), []), (E + ("applicable_policy_ids",), []),
    *((D + ("source_document_id",), v) for v in ("", "bad", "A_B", "-A")),
    *((D + ("document_version",), v) for v in ("d0000", "d1", "d00001", "D0001")),
    *((E + ("locator_id",), v) for v in ("", "A", "a_b", "-a")),
    *((E + ("applicable_policy_ids",), [v]) for v in ("", "bad_id", "a")),
    *((D + (k,), " ") for k in ("issuer", "title", "notice_number")),
    *((E + (k,), " ") for k in ("section", "meaning_summary", "table_position")),
    *((D + (k,), v) for k in ("publication_date", "verified_at", "effective_from", "effective_to")
      for v in ("2026-02-29", "2026-1-01", "2026-01-01T00:00:00", "0000-01-01")),
    *((E + ("verified_at",), v) for v in ("bad", "2026-02-29", "2026-01-09Z")),
    (E + ("page",), 0), (E + ("page",), -1),
    *((D + (k,), v) for k in ("official_url", "attachment_url")
      for v in ("http://example.invalid", "https://u:p@example.invalid", "https://example.invalid:0", "https://")),
    *((D + ("content_sha256",), v) for v in ("", "a" * 63, "A" * 64, "g" * 64)),
    *((D + (k,), v) for k in ("source_type", "status", "verification_status") for v in ("bad", "ACTIVE ")),
    *((E + (k,), v) for k in ("status", "verification_status") for v in ("bad", "ACTIVE ")),
    (D + ("effective_from",), "2031-01-01"), (E + ("verified_at",), "2026-01-11"),
    (D + ("verified_at",), None), (E + ("verified_at",), None),
    (E + ("applicable_policy_ids",), ["SYNTH-POLICY", "SYNTH-POLICY"]),
    (D + ("previous_urls",), ["https://x.example.invalid", "https://x.example.invalid"]),
    (D + ("supersedes",), [{"source_document_id": "SYNTH-Z", "document_version": "d0002"}]),
    (D + ("supersedes",), [{"source_document_id": "SYNTH-OLD", "document_version": "d0000"}]),
)


@pytest.mark.parametrize("path,value", MODEL_BAD_VALUES)
def test_existing_model_value_contracts_and_no_fp_after_parser_failure(path, value, monkeypatch):
    raw = encode(change(payload(), path, value)); prepared = bundle(raw)
    def forbidden(*args, **kwargs): pytest.fail("parser 실패 후 fingerprint를 호출했습니다")
    monkeypatch.setattr(domain, "fingerprint_source_registry", forbidden)
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL", raw, prepared=prepared)


@pytest.mark.parametrize("kind", ("source_same", "source_other_version", "locator", "supersedes", "cycle"))
def test_duplicate_references_and_exact_in_bundle_cycle_are_not_repaired(kind):
    body = payload(); doc = body["sources"][0]
    if kind.startswith("source"):
        row = deepcopy(doc)
        if kind == "source_other_version": row["document_version"] = "d0003"
        body["sources"].append(row)
    elif kind == "locator": doc["locators"].append(deepcopy(doc["locators"][0]))
    elif kind == "supersedes": doc["supersedes"].append(deepcopy(doc["supersedes"][0]))
    else:
        doc["supersedes"] = [{"source_document_id": "SYNTH-SRC", "document_version": "d0001"}]
        body["sources"][1]["supersedes"] = [{"source_document_id": "SYNTH-Z", "document_version": "d0002"}]
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL", encode(body))


@pytest.mark.parametrize("path,value", (
    (D + ("title",), "새 합성 제목"), (D + ("official_url",), "https://new.example.invalid/n"),
    (D + ("verified_at",), "2026-01-12"), (D + ("document_version",), "d0003"),
    (D + ("status",), "WITHDRAWN"), (E + ("meaning_summary",), "다른 합성 의미"),
    (E + ("page",), 4), (E + ("verification_status",), "STALE"),
))
def test_metadata_and_evidence_changes_detected_by_real_domain_fp(path, value):
    body = change(payload(), path, value)
    assert author_fingerprint(body) != FIXED_DOMAIN_FP
    error("HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH", encode(body),
          field="expected_acceptance.coverage_source_registry_fingerprint")


def test_parser_and_fp_called_once_same_root_same_result_then_both_bindings(monkeypatch):
    raw = encode(payload()); prepared = bundle(raw)
    real_parse, real_fp, real_loads = domain.parse_source_registry, domain.fingerprint_source_registry, domain.json.loads
    real_get = PolicyBenefitAcceptance.__getattribute__
    captured, events = {}, []
    def loads(text, **kwargs):
        assert text.encode("utf-8") == raw
        result = real_loads(text, **kwargs); captured["root"] = result; captured["before"] = deepcopy(result)
        return result
    def parser(root):
        events.append("parser"); assert root is captured["root"] and root == captured["before"]
        captured["registry"] = real_parse(root)
        assert root == captured["before"]
        return captured["registry"]
    def fp(registry):
        events.append("fingerprint"); assert registry is captured["registry"]
        return real_fp(registry)
    def observe(record, name):
        if name in ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"):
            events.append(name)
        return real_get(record, name)
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", loads)
        patch.setattr(domain, "parse_source_registry", parser)
        patch.setattr(domain, "fingerprint_source_registry", fp)
        patch.setattr(PolicyBenefitAcceptance, "__getattribute__", observe)
        result = run(raw, prepared=prepared)
    assert result is captured["registry"]
    assert events == ["parser", "fingerprint", "coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"]


@pytest.mark.parametrize("helper,prefix", (("parse_source_registry", "INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL"),
    ("fingerprint_source_registry", "INVALID_HISTORICAL_SOURCE_REGISTRY_FINGERPRINT")))
def test_helper_known_errors_keep_category_and_unexpected_programming_errors_propagate(helper, prefix, monkeypatch):
    raw = encode(payload()); prepared = bundle(raw)
    def known(*args): raise SourceValidationError("SYNTHETIC_SOURCE_ERROR", "locators")
    with monkeypatch.context() as patch:
        patch.setattr(domain, helper, known)
        msg = error(prefix, raw, prepared=prepared, field="locators")
        assert msg.endswith(": SYNTHETIC_SOURCE_ERROR")
    def unexpected(*args): raise RuntimeError("programming error")
    monkeypatch.setattr(domain, helper, unexpected)
    with pytest.raises(RuntimeError, match="programming error"):
        run(raw, prepared=prepared)


@pytest.mark.parametrize("first,second,prefix", (
    ((("schema_version",), "bad"), (D + ("source_type",), "bad"), "UNSUPPORTED_HISTORICAL_SOURCE_REGISTRY_SCHEMA"),
    ((D + ("source_type",), "bad"), (D + ("source_document_id",), "bad"), "INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL"),
    ((D + ("publication_date",), "bad"), (E + ("locator_id",), "bad_id"), "INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL"),
))
def test_schema_and_parser_precedence(first, second, prefix):
    body = payload(); change(body, *first); change(body, *second)
    msg = error(prefix, encode(body))
    if first[0] == D + ("source_type",): assert "INVALID_SOURCE_ENUM" in msg
    if first[0] == D + ("publication_date",): assert "INVALID_SOURCE_DATE" in msg


def test_missing_before_canonical_before_model_before_fp():
    body = change(payload(), D + ("publication_date",), "bad")
    error("NONCANONICAL_HISTORICAL_SOURCE_REGISTRY_BYTES", encode(body) + b"\n")
    del body["sources"][0]["verified_at"]
    error("INVALID_HISTORICAL_SOURCE_REGISTRY_FIELDS", encode(body) + b"\n")
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_SOURCE_REGISTRY_LOADER_INPUT: raw_bytes:"):
        load_historical_source_registry_bytes(raw_bytes=bytearray(), artifact=None, expected_acceptance=None)


def test_exact_16_error_prefixes_match_approved_spec():
    source = inspect.getsource(domain)
    prefixes = set(re.findall(r'"([A-Z][A-Z0-9_]+)"', source))
    doc = (Path(__file__).resolve().parents[1] / "docs/HISTORICAL_SOURCE_REGISTRY_ARTIFACT_PREPARATION_SPEC.md").read_text(encoding="utf-8")
    declared = set(re.findall(r'^\| \d+ \| P\d \| ([A-Z_]+) \|', doc, re.M))
    assert prefixes == declared and len(prefixes) == 16


def test_pure_loader_does_not_read_originals_manifest_sources_or_evaluate_usage(monkeypatch):
    import builtins
    import os
    import socket
    import subprocess
    from backend.policy_engine import sources
    from backend.policy_engine.sources import loader as source_loader
    from backend.policy_engine.policy_data import validation
    raw = encode(payload()); prepared = bundle(raw)
    tree = ast.parse(inspect.getsource(domain))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names)
    assert imports <= {"hashlib", "json", "errors", "sources", "benefit_acceptance", "benefit_acceptance_review_artifact", "manifest"}
    own = [v for v in vars(domain).values() if inspect.isfunction(v) and v.__module__ == domain.__name__]
    assert [f.__name__ for f in own if not f.__name__.startswith("_")] == ["load_historical_source_registry_bytes"]
    assert not any(isinstance(v, (dict, list, set)) for k, v in vars(domain).items() if not k.startswith("__"))
    assert not any(isinstance(n, ast.Attribute) and n.attr in ("now", "today", "utcnow") for n in ast.walk(tree))
    def forbidden(*args, **kwargs): pytest.fail("Registry 복원 범위 밖 I/O/사용 gate를 실행했습니다")
    with monkeypatch.context() as patch:
        for obj, name in ((builtins, "open"), (Path, "open"), (Path, "read_bytes"), (os, "getenv"),
            (socket, "create_connection"), (subprocess, "run"), (SourceRegistry, "get_source"),
            (SourceRegistry, "has_source"), (SourceRegistry, "has_evidence"), (SourceRegistry, "resolve"),
            (source_loader, "load_source_registry"), (sources, "load_source_registry"), (sources, "validate_evidence_refs")):
            patch.setattr(obj, name, forbidden)
        for module, names in (
            (policy_data, ("load_acceptance_review_artifact_bytes", "load_historical_benefit_snapshot_bytes",
                "load_historical_eligibility_coverage_bytes", "load_historical_policy_envelope_bytes",
                "load_historical_coverage_review_context_bytes", "load_historical_dataset_manifest_bytes",
                "evaluate_eligibility_coverage")),
            (validation, ("validate_dataset_manifest", "validate_envelope_sources")),
        ):
            for name in names: patch.setattr(module, name, forbidden)
        result = run(raw, prepared=prepared)
    assert result.to_dict() == payload()
    assert not any(hasattr(result, name) for name in ("usable", "source_verified", "is_full", "matched", "amount"))

