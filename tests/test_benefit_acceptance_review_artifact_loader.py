"""합성 bytes만 검증한다. 정책 원문·실제 검토·현재 usability를 인증하지 않는다."""

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date
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
    BenefitReviewClaim, PolicyBenefitAcceptance, SourceBinding, load_acceptance_review_artifact_bytes,
)
from backend.policy_engine.policy_data import benefit_acceptance_review_artifact_loader as domain
from backend.policy_engine.sources import SourceRegistry


CLAIMS = ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")
RAW_KEYS = (
    "acceptance_ref", "acceptance_version", "status", "policy_id", "scope", "benefit_id",
    "coverage_inventory_version", "coverage_inventory_fingerprint", "coverage_rule_version",
    "coverage_policy_tree_fingerprint", "coverage_dataset_version", "coverage_source_registry_fingerprint",
    "coverage_implementation_fingerprint", "benefit_version", "benefit_fingerprint",
    "benefit_dataset_version", "benefit_source_registry_fingerprint", "reviewed_at", "valid_until",
    "revokes_acceptance_ref",
)
REFERENCES = (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref",
)
ENTRY_KEYS = ("acceptance", *REFERENCES, "claim_evidence", "source_bindings", "source_documents",
              "prepared_by", "reviewed_by", "review_note", "manual_scenario_ids")


def acceptance_payload(**changes):
    # raw20 fixture는 production to_dict나 loader 내부 helper로 만들지 않는다.
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001", "status": "ACCEPTED",
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "benefit_id": "SYNTH-BENEFIT", "coverage_inventory_version": "i0001",
        "coverage_inventory_fingerprint": "1" * 64, "coverage_rule_version": "r0001",
        "coverage_policy_tree_fingerprint": "2" * 64, "coverage_dataset_version": "SYNTH-D1",
        "coverage_source_registry_fingerprint": "3" * 64, "coverage_implementation_fingerprint": "4" * 64,
        "benefit_version": "b0001", "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": "2026-01-01",
        "valid_until": "2026-12-31", "revokes_acceptance_ref": None, **changes,
    }


def raw_reference(path="synthetic/missing-original.json"):
    return {"path": path, "sha256": "b" * 64}


def raw_entry(*, revoked=False, acceptance_changes=None):
    acceptance = acceptance_payload(**({
        "acceptance_ref": "SYNTH-REVOKE-B", "acceptance_version": "a0002", "status": "REVOKED",
        "revokes_acceptance_ref": "SYNTH-ACCEPT-A",
    } if revoked else {}))
    acceptance.update(acceptance_changes or {})
    binding = {"source_document_id": "SYNTH-SOURCE", "document_version": "d0001"}
    return {
        "acceptance": acceptance,
        **{key: None if revoked else raw_reference() for key in REFERENCES},
        "claim_evidence": [] if revoked else [{"claim": claim, "evidence_refs": [
            "SYNTH-SOURCE#second", "SYNTH-SOURCE#first"]} for claim in CLAIMS],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding),
                                                 "artifact": raw_reference("synthetic/missing-source.pdf")}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
        "review_note": "합성 검토 기록", "manual_scenario_ids": ["RL01", "RL07"],
    }


def payload(*, revoked=False):
    return {"schema_version": "benefit-acceptance-review-1.0", "entries": [raw_entry(revoked=revoked)]}


def encode(body):
    # 테스트 authoring의 독립 encoder이며 production canonical helper를 호출하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def expected_record(raw, *, revoked=False, **changes):
    # payload를 파싱하지 않고 외부의 명시 metadata로 기대 원본을 만든다.
    digest = hashlib.sha256(raw).hexdigest()
    values = {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": date(2026, 1, 1),
        "valid_until": date(2026, 12, 31), "review_artifact_ref": "acceptance-review:sha256:" + digest,
        "revokes_acceptance_ref": None,
    }
    if revoked:
        values.update(acceptance_ref="SYNTH-REVOKE-B", acceptance_version="a0002",
                      status=BenefitAcceptanceStatus.REVOKED, revokes_acceptance_ref="SYNTH-ACCEPT-A")
    return PolicyBenefitAcceptance(**{**values, **changes})


_UNSET = object()


def run(body=None, *, raw=_UNSET, expected=_UNSET):
    if raw is _UNSET:
        raw = encode(payload() if body is None else body)
    if expected is _UNSET:
        expected = (expected_record(raw),)
    return load_acceptance_review_artifact_bytes(raw_bytes=raw, expected_acceptances=expected)


def error(prefix, body=None, *, raw=_UNSET, expected=_UNSET, field=None, reason=None):
    with pytest.raises(PolicyDataError) as caught:
        run(body, raw=raw, expected=expected)
    assert type(caught.value) is PolicyDataError
    message = str(caught.value)
    assert message.startswith(prefix + ": "), message
    if field is not None:
        assert message.startswith(prefix + ": " + field + ": "), message
    if reason is not None:
        assert message.endswith(": " + reason), message
    return message


def at(body, path):
    for key in path:
        body = body[key]
    return body


def path_name(path):
    if not path:
        return "root"
    output = ""
    for key in path:
        output += f"[{key}]" if type(key) is int else ("." if output else "") + key
    return output


def set_value(body, path, value):
    at(body, path[:-1])[path[-1]] = value
    return body


OBJECT_SCHEMAS = (
    ((), ("schema_version", "entries")),
    (("entries", 0), ENTRY_KEYS),
    (("entries", 0, "acceptance"), RAW_KEYS),
    (("entries", 0, "acceptance", "scope"), ("edition_id", "quarter")),
    *((('entries', 0, key), ("path", "sha256")) for key in REFERENCES),
    (("entries", 0, "claim_evidence", 0), ("claim", "evidence_refs")),
    (("entries", 0, "source_bindings", 0), ("source_document_id", "document_version")),
    (("entries", 0, "source_documents", 0), ("binding", "artifact")),
    (("entries", 0, "source_documents", 0, "binding"), ("source_document_id", "document_version")),
    (("entries", 0, "source_documents", 0, "artifact"), ("path", "sha256")),
)


def test_public_api_exact_two_required_keyword_only_types_and_one_export():
    fn = load_acceptance_review_artifact_bytes
    assert fn is domain.load_acceptance_review_artifact_bytes
    assert policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "expected_acceptances")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "expected_acceptances": tuple[PolicyBenefitAcceptance, ...],
                                  "return": AcceptanceReviewArtifact}
    for kwargs in ({}, {"raw_bytes": b""}, {"expected_acceptances": ()}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", ())
    with pytest.raises(TypeError):
        fn(raw_bytes=b"", expected_acceptances=(), skip_hash=True)


def test_raw_schema_allowlists_match_approved_tables_and_actual_loader_constants():
    text = (Path(__file__).resolve().parents[1] / "docs/BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md").read_text(
        encoding="utf-8")
    for number, names, actual in ((7, ENTRY_KEYS, domain._ENTRY_KEYS), (8, RAW_KEYS, domain._RAW_ACCEPTANCE_KEYS)):
        table = text.split(f"## {number}. ", 1)[1].split(f"## {number + 1}. ", 1)[0]
        assert re.findall(r"^\| (\d+) \| ([a-z_]+) \|", table, re.M) == [
            (str(i), name) for i, name in enumerate(names, 1)]
        assert actual == names


def test_valid_accepted_exact_types_unicode_order_and_original_identity():
    body = payload()
    raw = encode(body)
    original = expected_record(raw)
    before = original.to_dict()
    result = run(raw=raw, expected=(original,))
    entry = result.entries[0]
    assert entry.acceptance is original
    assert original.to_dict() == before
    assert result.review_artifact_ref == original.review_artifact_ref
    assert type(result) is AcceptanceReviewArtifact
    assert type(entry.accepted_terms_ref) is ArtifactReference
    assert type(entry.source_bindings[0]) is SourceBinding
    assert type(entry.acceptance.scope) is ApplicabilityScope
    assert type(entry.acceptance.reviewed_at) is date
    assert entry.acceptance.status is BenefitAcceptanceStatus.ACCEPTED
    assert tuple(row.claim.value for row in entry.claim_evidence) == CLAIMS
    assert entry.claim_evidence[0].claim is BenefitReviewClaim.AMOUNT
    assert all(row.evidence_refs == ("SYNTH-SOURCE#second", "SYNTH-SOURCE#first") for row in entry.claim_evidence)
    assert entry.review_note == "합성 검토 기록" and entry.manual_scenario_ids == ("RL01", "RL07")
    assert len(entry.acceptance.to_dict()) == 21
    assert "review_artifact_ref" not in body["entries"][0]["acceptance"]
    assert tuple(body) == ("schema_version", "entries")


def test_fixed_synthetic_fixture_digest_is_independent_of_loader_and_roundtrip():
    raw = encode(payload())
    digest = "809f208a6cdcd6d7dcbf5d2f913bc175ecd1761af07ec6ec5d6a8c0bfbbea197"
    assert len(raw) == 3002
    assert hashlib.sha256(raw).hexdigest() == digest
    original = expected_record(raw, review_artifact_ref="acceptance-review:sha256:" + digest)
    assert run(raw=raw, expected=(original,)).entries[0].acceptance is original


def test_valid_revoked_preserves_explicit_null_and_does_not_lookup_target():
    raw = encode(payload(revoked=True))
    original = expected_record(raw, revoked=True)
    item = run(raw=raw, expected=(original,)).entries[0]
    assert item.acceptance is original
    assert original.revokes_acceptance_ref == "SYNTH-ACCEPT-A"
    assert all(getattr(item, key) is None for key in REFERENCES)
    assert item.claim_evidence == item.source_bindings == item.source_documents == ()
    assert all(item.to_dict()[key] is None for key in REFERENCES)


def test_multiple_targets_historical_versions_revocation_and_expected_permutations():
    body = payload()
    body["entries"] += [raw_entry(revoked=True), raw_entry(acceptance_changes={
        "acceptance_ref": "SYNTH-OTHER", "policy_id": "SYNTH-OTHER-POLICY", "benefit_id": "SYNTH-OTHER-BENEFIT",
        "scope": {"edition_id": "2025", "quarter": None}, "benefit_version": "b0002",
    })]
    raw = encode(body)
    a = expected_record(raw)
    b = expected_record(raw, revoked=True)
    c = expected_record(raw, acceptance_ref="SYNTH-OTHER", policy_id="SYNTH-OTHER-POLICY",
                        benefit_id="SYNTH-OTHER-BENEFIT", scope=ApplicabilityScope("2025", None), benefit_version="b0002")
    for expected in ((a, b, c), (c, b, a), (b, a, c)):
        root = run(raw=raw, expected=expected)
        assert all(item.acceptance is original for item, original in zip(root.entries, (a, b, c)))


@pytest.mark.parametrize("quarter", [None, 1, 2, 3, 4])
def test_exact_scope_values_without_current_year_inference(quarter):
    body = payload()
    body["entries"][0]["acceptance"]["scope"] = {"edition_id": "0000", "quarter": quarter}
    raw = encode(body)
    original = expected_record(raw, scope=ApplicabilityScope("0000", quarter))
    assert run(raw=raw, expected=(original,)).entries[0].acceptance.scope is original.scope


@pytest.mark.parametrize("note", ["한글", unicodedata.normalize("NFD", "한글"), "가😀나", "줄1\n줄2\t끝"])
def test_unicode_scalar_text_is_preserved_without_normalization(note):
    body = payload()
    body["entries"][0]["review_note"] = note
    assert run(body).entries[0].review_note == note


class BytesSubclass(bytes):
    pass


class TupleSubclass(tuple):
    pass


class RecordSubclass(PolicyBenefitAcceptance):
    pass


@pytest.mark.parametrize("raw", [None, "{}", {}, [], bytearray(b"{}"), memoryview(b"{}"), BytesSubclass(b"{}")])
def test_raw_requires_exact_bytes_before_expected_checks(raw):
    error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", raw=raw, expected=(), field="raw_bytes")


@pytest.mark.parametrize("expected", [None, [], {}, (), TupleSubclass(()), (None,), ({},), (True,)])
def test_expected_requires_exact_nonempty_record_tuple(expected):
    error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", raw=b"", expected=expected, field="expected_acceptances")


def test_record_subclass_rejected_before_accessing_expected_fields():
    original = expected_record(b"")
    subclass = RecordSubclass(**{key: getattr(original, key) for key in (*RAW_KEYS, "review_artifact_ref")})
    error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", raw=b"", expected=(subclass,))


@pytest.mark.parametrize("bad", ["opaque", "acceptance-review:sha256:" + "A" * 64,
                                "acceptance-review:sha256:" + "a" * 63,
                                "acceptance-review:sha256:" + "a" * 65,
                                "acceptance-review:sha256:" + "g" * 64,
                                " acceptance-review:sha256:" + "a" * 64,
                                "acceptance-review:sha256:" + "a" * 64 + "\n"])
def test_bad_expected_ref_rejected_without_normalization_before_hash(bad):
    record = replace(expected_record(b""), review_artifact_ref=bad)
    error("INVALID_REVIEW_ARTIFACT_EXPECTED_REF", raw=b"bad json", expected=(record,),
          field="expected_acceptances[0].review_artifact_ref")


def test_expected_relationships_checked_before_hash_and_ref_duplicates_before_revision():
    raw = encode(payload())
    a = expected_record(raw)
    for second, reason in ((a, "duplicate ref"),
                           (replace(a, acceptance_ref="SYNTH-OTHER"), "duplicate revision"),
                           (replace(a, review_artifact_ref="acceptance-review:sha256:" + "f" * 64), "refs differ")):
        error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", raw=b"bad", expected=(a, second), reason=reason)
    # 모든 ref 문법을 먼저 검사하고 그 다음 공통성/중복을 검사한다.
    bad = replace(a, review_artifact_ref="opaque")
    error("INVALID_REVIEW_ARTIFACT_EXPECTED_REF", raw=b"bad", expected=(a, a, bad),
          field="expected_acceptances[2].review_artifact_ref")


@pytest.mark.parametrize("mutation", [lambda raw: raw + b"\n", lambda raw: b" " + raw,
                                     lambda raw: raw.replace(b"SYNTH", b"sYNTH", 1),
                                     lambda raw: b"\xff", lambda raw: b"{broken"])
def test_raw_mutation_keeps_original_expected_ref_and_hash_precedes_encoding_json(mutation):
    raw = encode(payload())
    error("REVIEW_ARTIFACT_BYTES_MISMATCH", raw=mutation(raw), expected=(expected_record(raw),), field="raw_bytes")


def test_exact_same_bytes_hashed_once_before_json_and_no_parse_on_bad_hash(monkeypatch):
    raw = encode(payload())
    expected = (expected_record(raw),)
    sha = hashlib.sha256
    loads = json.loads
    calls = []

    def observe_hash(value):
        assert value is raw
        calls.append("sha256")
        return sha(value)

    def observe_loads(text, **kwargs):
        assert calls == ["sha256"] and text == raw.decode("utf-8")
        calls.append("json")
        return loads(text, **kwargs)

    monkeypatch.setattr(domain.hashlib, "sha256", observe_hash)
    monkeypatch.setattr(domain.json, "loads", observe_loads)
    assert run(raw=raw, expected=expected).entries[0].acceptance is expected[0]
    assert calls == ["sha256", "json"]
    wrong = (replace(expected[0], review_artifact_ref="acceptance-review:sha256:" + "f" * 64),)
    calls.clear()
    error("REVIEW_ARTIFACT_BYTES_MISMATCH", raw=raw, expected=wrong)
    assert calls == ["sha256"]


@pytest.mark.parametrize("raw", [b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xef\xbb\xbf{}"])
def test_encoding_failures_reached_with_independent_matching_expected_digest(raw):
    error("INVALID_REVIEW_ARTIFACT_ENCODING", raw=raw, field="raw_bytes")


@pytest.mark.parametrize("raw", [b"", b"{", b"{}{}", b"[1,]", b'{"a":01}'])
def test_json_syntax_failures(raw):
    error("INVALID_REVIEW_ARTIFACT_JSON", raw=raw, field="json")


def test_decoder_recursion_error_is_converted_without_assuming_runtime_depth_limit(monkeypatch):
    raw = encode(payload())
    original = expected_record(raw)

    def recursion(*args, **kwargs):
        raise RecursionError

    monkeypatch.setattr(domain.json, "loads", recursion)
    error("INVALID_REVIEW_ARTIFACT_JSON", raw=raw, expected=(original,), field="json")


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"outer":{"x":1,"x":2}}',
                                b'{"list":[{"x":1,"x":2}]}', b'{"x":1,"\\u0078":2}'])
def test_duplicate_keys_all_depths_and_equivalent_key_escapes(raw):
    error("DUPLICATE_REVIEW_ARTIFACT_JSON_KEY", raw=raw, field="json")


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1.0", "1e0", "1E999", "-0.25",
                                  pytest.param("9" * 5000, id="integer-limit")])
def test_number_hooks_reject_constants_floats_exponents_and_integer_parse_failure(token):
    error("INVALID_REVIEW_ARTIFACT_NUMBER", raw=("{\"unused\":" + token + "}").encode(), field="json")


@pytest.mark.parametrize("raw", [b'"\\ud800"', b'{"\\udfff":1}', b'["\\ud800",0]'])
def test_unpaired_surrogate_in_values_or_keys_is_rejected(raw):
    error("INVALID_REVIEW_ARTIFACT_UNICODE", raw=raw, field="json")


MISSING_CASES = [(path, key) for path, keys in OBJECT_SCHEMAS for key in keys]


@pytest.mark.parametrize("path,key", MISSING_CASES)
def test_every_required_key_at_every_schema_location_is_required(path, key):
    body = payload()
    del at(body, path)[key]
    error("INVALID_REVIEW_ARTIFACT_FIELDS", body, field=path_name(path), reason="missing " + key)


@pytest.mark.parametrize("path,keys", OBJECT_SCHEMAS)
def test_extra_keys_rejected_at_every_schema_location_without_echoing_unknown_key(path, keys):
    body = payload()
    at(body, path)["SYNTH-private-unknown-key"] = "SYNTH-private-value"
    message = error("INVALID_REVIEW_ARTIFACT_FIELDS", body, field=path_name(path), reason="extra")
    assert "SYNTH-private" not in message


@pytest.mark.parametrize("path,keys", OBJECT_SCHEMAS)
@pytest.mark.parametrize("bad", [[], "raw", 1])
def test_wrong_object_types_at_every_nested_location(path, keys, bad):
    body = payload()
    if path:
        set_value(body, path, bad)
    else:
        body = bad
    error("INVALID_REVIEW_ARTIFACT_TYPE", body, field=path_name(path))


ARRAY_PATHS = (("entries",), ("entries", 0, "claim_evidence"), ("entries", 0, "claim_evidence", 0, "evidence_refs"),
               ("entries", 0, "source_bindings"), ("entries", 0, "source_documents"),
               ("entries", 0, "manual_scenario_ids"))


@pytest.mark.parametrize("path", ARRAY_PATHS)
@pytest.mark.parametrize("bad", [None, {}, "raw", True])
def test_wrong_array_types_rejected_without_coercion(path, bad):
    error("INVALID_REVIEW_ARTIFACT_TYPE", set_value(payload(), path, bad), field=path_name(path))


@pytest.mark.parametrize("path", [
    ("schema_version",), ("entries", 0, "acceptance", "acceptance_ref"),
    ("entries", 0, "acceptance", "reviewed_at"), ("entries", 0, "acceptance", "scope", "edition_id"),
    ("entries", 0, "accepted_terms_ref", "sha256"), ("entries", 0, "claim_evidence", 0, "claim"),
    ("entries", 0, "claim_evidence", 0, "evidence_refs", 0),
    ("entries", 0, "source_bindings", 0, "document_version"),
    ("entries", 0, "prepared_by"), ("entries", 0, "manual_scenario_ids", 0),
])
@pytest.mark.parametrize("bad", [None, 100000, True])
def test_primitive_strings_are_exact_not_null_or_numeric(path, bad):
    error("INVALID_REVIEW_ARTIFACT_TYPE", set_value(payload(), path, bad), field=path_name(path))


@pytest.mark.parametrize("bad", [True, False, "3", [], {}])
def test_quarter_bool_is_not_integer_and_no_implicit_conversion(bad):
    path = ("entries", 0, "acceptance", "scope", "quarter")
    error("INVALID_REVIEW_ARTIFACT_TYPE", set_value(payload(), path, bad), field=path_name(path))


def test_schema_and_diagnostic_raw_self_reference_are_not_accepted():
    body = payload()
    body["schema_version"] = "benefit-acceptance-review-2.0"
    error("INVALID_REVIEW_ARTIFACT_SCHEMA", body, field="schema_version")
    body = payload()
    body["review_artifact_ref"] = "forbidden"
    error("INVALID_REVIEW_ARTIFACT_FIELDS", body, field="root")
    body = payload()
    body["entries"][0]["acceptance"]["review_artifact_ref"] = "forbidden"
    error("INVALID_REVIEW_ARTIFACT_FIELDS", body, field="entries[0].acceptance")


@pytest.mark.parametrize("variant", ["indent", "key_order", "newline", "leading_space", "unicode_escape"])
def test_noncanonical_bytes_rejected_after_matching_hash_and_valid_schema(variant):
    body = payload()
    variants = {
        "indent": json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8"),
        "key_order": json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        "newline": encode(body) + b"\n", "leading_space": b" " + encode(body),
        "unicode_escape": json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(),
    }
    error("NONCANONICAL_REVIEW_ARTIFACT_BYTES", raw=variants[variant], field="raw_bytes")


@pytest.mark.parametrize("path,bad,field", [
    (("entries", 0, "acceptance", "status"), "accepted", "entries[0].acceptance.status"),
    (("entries", 0, "claim_evidence", 0, "claim"), "SOURCE_BINDING", "entries[0].claim_evidence[0].claim"),
    *((('entries', 0, 'acceptance', name), value, 'entries[0].acceptance.' + name)
      for name in ("reviewed_at", "valid_until")
      for value in ("20260101", "2026-W01-1", "2026-02-30", "2026-01-01T00:00:00", "0000-01-01", " 2026-01-01")),
])
def test_enum_and_date_explicit_conversion_failures(path, bad, field):
    error("INVALID_REVIEW_ARTIFACT_VALUE", set_value(payload(), path, bad), field=field)


@pytest.mark.parametrize("key,bad", [
    ("policy_id", "invalid"), ("benefit_id", "invalid"), ("acceptance_version", "a0000"),
    ("coverage_inventory_version", "i0000"), ("benefit_version", "b0000"),
    ("coverage_inventory_fingerprint", "ABC"), ("benefit_fingerprint", "f" * 63),
    ("coverage_dataset_version", "SYNTH-D2"), ("benefit_dataset_version", "SYNTH-D2"),
    ("coverage_source_registry_fingerprint", "c" * 64), ("benefit_source_registry_fingerprint", "c" * 64),
    ("valid_until", "2025-12-31"), ("revokes_acceptance_ref", "SYNTH-OLD"),
])
def test_existing_record_validation_is_wrapped_not_reimplemented(key, bad):
    error("INVALID_REVIEW_ARTIFACT_MODEL", set_value(payload(), ("entries", 0, "acceptance", key), bad),
          field="entries[0].acceptance")


@pytest.mark.parametrize("path,bad,object_path", [
    (("entries", 0, "acceptance", "scope", "quarter"), 0, "entries[0].acceptance.scope"),
    (("entries", 0, "accepted_terms_ref", "path"), "../escape", "entries[0].accepted_terms_ref"),
    (("entries", 0, "accepted_terms_ref", "sha256"), "B" * 64, "entries[0].accepted_terms_ref"),
    (("entries", 0, "source_bindings", 0, "document_version"), "d0000", "entries[0].source_bindings[0]"),
    (("entries", 0, "source_documents", 0, "binding", "source_document_id"), "invalid", "entries[0].source_documents[0].binding"),
    (("entries", 0, "source_documents", 0, "artifact", "path"), "C:/bad", "entries[0].source_documents[0].artifact"),
    (("entries", 0, "claim_evidence", 0, "evidence_refs"), ["malformed"], "entries[0].claim_evidence[0]"),
    (("entries", 0, "claim_evidence", 0, "evidence_refs"), ["SOURCE#one", "SOURCE#one"], "entries[0].claim_evidence[0]"),
])
def test_nested_domain_model_errors_have_stable_constructor_object_path(path, bad, object_path):
    error("INVALID_REVIEW_ARTIFACT_MODEL", set_value(payload(), path, bad), field=object_path)


@pytest.mark.parametrize("change", ["missing_claim", "duplicate_claim", "reordered_claim", "source_mismatch",
                                   "same_reviewer", "empty_scenarios", "missing_reference"])
def test_entry_model_invariants_keep_existing_meaning(change):
    body = payload()
    item = body["entries"][0]
    if change == "missing_claim": item["claim_evidence"].pop()
    elif change == "duplicate_claim": item["claim_evidence"][1] = deepcopy(item["claim_evidence"][0])
    elif change == "reordered_claim": item["claim_evidence"].reverse()
    elif change == "source_mismatch": item["source_documents"][0]["binding"]["document_version"] = "d0002"
    elif change == "same_reviewer": item["reviewed_by"] = item["prepared_by"]
    elif change == "empty_scenarios": item["manual_scenario_ids"] = []
    else: item["accepted_terms_ref"] = None
    error("INVALID_REVIEW_ARTIFACT_MODEL", body, field="entries[0]")


@pytest.mark.parametrize("target", [None, " ", "SYNTH-REVOKE-B"])
def test_revocation_local_link_invariants_only(target):
    body = payload(revoked=True)
    body["entries"][0]["acceptance"]["revokes_acceptance_ref"] = target
    error("INVALID_REVIEW_ARTIFACT_MODEL", body, field="entries[0].acceptance")


@pytest.mark.parametrize("change", ["empty", "same_ref", "same_revision"])
def test_root_model_validates_complete_collection_before_external_binding(change):
    body = payload()
    if change == "empty": body["entries"] = []
    else:
        duplicate = raw_entry()
        if change == "same_revision": duplicate["acceptance"]["acceptance_ref"] = "SYNTH-OTHER"
        body["entries"].append(duplicate)
    error("INVALID_REVIEW_ARTIFACT_MODEL", body, field="root")


BINDING_CHANGES = (
    ("acceptance_version", {"acceptance_version": "a0002"}),
    ("policy_id", {"policy_id": "SYNTH-OTHER-POLICY"}),
    ("scope", {"scope": {"edition_id": "2026", "quarter": 4}}),
    ("benefit_id", {"benefit_id": "SYNTH-OTHER-BENEFIT"}),
    ("coverage_inventory_version", {"coverage_inventory_version": "i0002"}),
    ("coverage_inventory_fingerprint", {"coverage_inventory_fingerprint": "c" * 64}),
    ("coverage_rule_version", {"coverage_rule_version": "arbitrary nonblank version"}),
    ("coverage_policy_tree_fingerprint", {"coverage_policy_tree_fingerprint": "c" * 64}),
    ("coverage_dataset_version", {"coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2"}),
    ("coverage_source_registry_fingerprint", {"coverage_source_registry_fingerprint": "c" * 64,
                                               "benefit_source_registry_fingerprint": "c" * 64}),
    ("coverage_implementation_fingerprint", {"coverage_implementation_fingerprint": "c" * 64}),
    ("benefit_version", {"benefit_version": "b0002"}),
    ("benefit_fingerprint", {"benefit_fingerprint": "c" * 64}),
    ("reviewed_at", {"reviewed_at": "2026-01-02"}),
    ("valid_until", {"valid_until": "2026-12-30"}),
)


@pytest.mark.parametrize("first_key,changes", BINDING_CHANGES)
def test_valid_but_different_record_content_is_rejected_in_raw20_field_order(first_key, changes):
    body = payload()
    body["entries"][0]["acceptance"].update(changes)
    error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", body, field="entries[0].acceptance." + first_key)


def test_status_and_revocation_link_correspondence_are_checked():
    body = payload(revoked=True)
    body["entries"][0]["acceptance"].update(acceptance_ref="SYNTH-ACCEPT-A", acceptance_version="a0001",
                                             revokes_acceptance_ref="SYNTH-OLD")
    error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", body, field="entries[0].acceptance.status")
    body = payload(revoked=True)
    body["entries"][0]["acceptance"]["revokes_acceptance_ref"] = "SYNTH-OTHER"
    raw = encode(body)
    error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", raw=raw, expected=(expected_record(raw, revoked=True),),
          field="entries[0].acceptance.revokes_acceptance_ref")


def test_unlisted_body_then_missing_expected_checked_before_value_mismatch():
    body = payload()
    body["entries"][0]["acceptance"]["acceptance_ref"] = "SYNTH-OTHER"
    error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", body,
          field="entries[0].acceptance.acceptance_ref", reason="unlisted")
    body = payload()
    body["entries"][0]["acceptance"]["benefit_version"] = "b0002"
    raw = encode(body)
    a = expected_record(raw)
    b = expected_record(raw, revoked=True)
    error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", raw=raw, expected=(a, b), field="entries", reason="missing")


def test_multi_entry_checks_last_entry_and_does_not_accept_only_matching_count():
    body = payload()
    body["entries"].append(raw_entry(revoked=True))
    body["entries"][1]["acceptance"]["benefit_version"] = "b0002"
    raw = encode(body)
    expected = (expected_record(raw), expected_record(raw, revoked=True))
    error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", raw=raw, expected=expected,
          field="entries[1].acceptance.benefit_version")


def test_precise_phase_order_across_multiple_errors(monkeypatch):
    bad = replace(expected_record(b""), review_artifact_ref="opaque")
    error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", raw="bad", expected=(bad,), field="raw_bytes")
    error("INVALID_REVIEW_ARTIFACT_EXPECTED_REF", raw=b"broken", expected=(bad,))
    error("REVIEW_ARTIFACT_BYTES_MISMATCH", raw=b"broken", expected=(expected_record(b"other"),))
    body = payload()
    body["entries"][0]["acceptance"]["benefit_version"] = "b0000"
    body["entries"].append(raw_entry(revoked=True))
    del body["entries"][1]["review_note"]
    error("INVALID_REVIEW_ARTIFACT_FIELDS", body, field="entries[1]")
    body = payload()
    del body["schema_version"]
    body["unknown"] = True
    error("INVALID_REVIEW_ARTIFACT_FIELDS", body, field="root", reason="missing schema_version")
    body = payload()
    body["entries"][0]["acceptance"]["benefit_version"] = "b0002"
    body["entries"].append(deepcopy(body["entries"][0]))
    error("INVALID_REVIEW_ARTIFACT_MODEL", body, field="root")
    # P4에서 number callback은 object pairs 완성보다 먼저 실행된다.
    error("INVALID_REVIEW_ARTIFACT_NUMBER", raw=b'{"x":1,"x":2,"y":NaN}')


def test_one_hundred_runs_preserve_input_objects_and_isolate_outputs():
    raw = encode(payload())
    original = expected_record(raw)
    expected = (original,)
    before = original.to_dict()
    first = run(raw=raw, expected=expected)
    snapshot = first.to_dict()
    for _ in range(100):
        result = run(raw=raw, expected=expected)
        assert result == first and result.to_dict() == snapshot
        assert result.entries[0].acceptance is original
        assert expected == (original,) and original.to_dict() == before
        output = result.to_dict()
        output["entries"][0]["acceptance"]["scope"].clear()
        output["entries"][0]["claim_evidence"][0]["evidence_refs"].clear()
        output["entries"][0]["source_documents"][0]["artifact"].clear()
        assert result.to_dict() == snapshot
    with pytest.raises(FrozenInstanceError):
        first.review_artifact_ref = "changed"


def test_errors_do_not_echo_payload_paths_hashes_or_unknown_keys():
    secret = "SYNTH-private-secret"
    body = payload()
    body["entries"][0]["accepted_terms_ref"]["path"] = "../" + secret
    message = error("INVALID_REVIEW_ARTIFACT_MODEL", body)
    assert secret not in message and "../" not in message
    body = payload()
    body["entries"][0]["acceptance"]["acceptance_ref"] = secret
    message = error("REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH", body)
    assert secret not in message


def test_loader_has_no_io_environment_cache_or_external_validation(monkeypatch):
    raw = encode(payload())
    expected = (expected_record(raw),)
    tree = ast.parse(inspect.getsource(domain))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    assert imports <= {"dataclasses", "datetime", "hashlib", "json", "re", "errors", "benefit_acceptance",
                       "benefit_acceptance_review_artifact", "eligibility_coverage", "envelope", "manifest"}
    defined = [obj for obj in vars(domain).values() if inspect.isfunction(obj) and obj.__module__ == domain.__name__]
    assert [fn.__name__ for fn in defined if not fn.__name__.startswith("_")] == ["load_acceptance_review_artifact_bytes"]
    assert all(not isinstance(value, (dict, list, set)) for name, value in vars(domain).items()
               if not name.startswith("__"))

    def forbidden(*args, **kwargs):
        pytest.fail("bytes loader가 외부 준비/내용 검증을 실행했습니다")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(SourceRegistry, "get_source", forbidden)
    monkeypatch.setattr(SourceRegistry, "resolve", forbidden)
    monkeypatch.setattr(policy_data, "fingerprint_benefit_snapshot", forbidden)
    monkeypatch.setattr(policy_data, "evaluate_eligibility_coverage", forbidden)
    result = run(raw=raw, expected=expected)
    # 원문 파일/Registry/실제 claim 증명 없이 구조 복원만 성공한다.
    assert result.entries[0].acceptance is expected[0]
    assert not any(hasattr(result, name) for name in ("usable", "reviewed", "policy_verified", "source_verified",
                                                    "bridge_supported", "cashflow_applicable"))
