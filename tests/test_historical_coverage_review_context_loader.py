"""합성 ReviewContext의 동일 bytes 복원·baseline만 검증한다. MATCHED/FULL 검증이 아니다."""

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
import sys
from typing import get_type_hints
import unicodedata

import pytest

from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, ApplicabilityScope, ArtifactReference, BenefitAcceptanceStatus,
    CoverageReviewContext, ImplementationBindingReview, InventoryCompletenessReview, PolicyBenefitAcceptance,
    load_acceptance_review_artifact_bytes, load_historical_coverage_review_context_bytes,
)
from backend.policy_engine.policy_data import historical_coverage_review_context_loader as domain


FIXED_RAW_SHA256 = "fec6b234759aac68ab6ed851b2a81212c944f263cc28cdac40f90f4fbf886fd2"
CONTEXT_KEYS = ("policy_id", "scope", "dataset_version", "source_registry_fingerprint", "implementation_fingerprint",
                "inventory_reviews", "implementation_reviews")
INVENTORY_KEYS = ("review_ref", "policy_id", "scope", "inventory_version", "inventory_fingerprint", "dataset_version",
                  "source_registry_fingerprint", "reviewed_at", "review_artifact_ref")
IMPLEMENTATION_KEYS = ("review_ref", "policy_id", "scope", "condition_id", "rule_root_id", "inventory_version",
    "inventory_fingerprint", "rule_version", "policy_tree_fingerprint", "subtree_fingerprint", "dataset_version",
    "source_registry_fingerprint", "implementation_fingerprint", "reviewed_at", "review_artifact_ref")
REFERENCES = ("accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
              "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref")
CTX = ("review_context",)
INV = CTX + ("inventory_reviews", 0)
IMPL = CTX + ("implementation_reviews", 0)


def inventory_review(**changes):
    return {"review_ref": "SYNTH-INVENTORY-A", "policy_id": "SYNTH-POLICY",
            "scope": {"edition_id": "2026", "quarter": 3}, "inventory_version": "i0001",
            "inventory_fingerprint": "1" * 64, "dataset_version": "SYNTH-D1",
            "source_registry_fingerprint": "3" * 64, "reviewed_at": "2026-01-01",
            "review_artifact_ref": "합성 목록 검토 원문", **changes}


def implementation_review(**changes):
    return {"review_ref": "SYNTH-IMPLEMENTATION-A", "policy_id": "SYNTH-POLICY",
            "scope": {"edition_id": "2026", "quarter": 3}, "condition_id": "COND_A", "rule_root_id": "ROOT_A",
            "inventory_version": "i0001", "inventory_fingerprint": "1" * 64, "rule_version": "r0001",
            "policy_tree_fingerprint": "2" * 64, "subtree_fingerprint": "6" * 64, "dataset_version": "SYNTH-D1",
            "source_registry_fingerprint": "3" * 64, "implementation_fingerprint": "4" * 64,
            "reviewed_at": "2026-01-02", "review_artifact_ref": "합성 구현 검토 원문", **changes}


def payload():
    return {"schema_version": "historical-coverage-review-context-1.0", "review_context": {
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "dataset_version": "SYNTH-D1", "source_registry_fingerprint": "3" * 64,
        "implementation_fingerprint": "4" * 64, "inventory_reviews": [inventory_review()],
        "implementation_reviews": [implementation_review()],
    }}


def encode(body):
    # fixture 저작용 encoder. 소비 loader의 private helper나 domain serializer를 사용하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def record_values(**changes):
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64,
        "reviewed_at": date(2026, 1, 3), "valid_until": date(2026, 12, 31),
        "review_artifact_ref": "acceptance-review:sha256:" + "f" * 64,
        "revokes_acceptance_ref": None, **changes,
    }


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


def raw_entry(values, context_hash):
    revoked = values["status"] is BenefitAcceptanceStatus.REVOKED
    references = {key: None if revoked else {"path": f"synthetic/{key}.json", "sha256": "b" * 64}
                  for key in REFERENCES}
    if not revoked:
        references["coverage_reviews_ref"] = {"path": "synthetic/missing-reviews.json", "sha256": context_hash}
    binding = {"source_document_id": "SYNTH-SRC", "document_version": "d0001"}
    return {"acceptance": raw_record(values), **references,
        "claim_evidence": [] if revoked else [{"claim": claim, "evidence_refs": ["SYNTH-SRC#a"]}
            for claim in ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding), "artifact": {
            "path": "synthetic/missing-source.pdf", "sha256": "a" * 64}}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
        "review_note": "합성 ReviewContext 원본 대응", "manual_scenario_ids": ["HRC04"],
    }


def bundle(raw, *, changes=None, context_hash=None, extras=(), target_first=False):
    # 외부 fixture 저작에서 H/R을 준비하고 실제 M2.57 반환값과 원본 R을 같은 호출에 전달한다.
    target = record_values(**(changes or {}))
    specs = [(target, context_hash if context_hash is not None else hashlib.sha256(raw).hexdigest())]
    specs = specs + list(extras) if target_first else list(extras) + specs
    review_raw = encode({"schema_version": "benefit-acceptance-review-1.0",
                         "entries": [raw_entry(values, digest) for values, digest in specs]})
    ref = "acceptance-review:sha256:" + hashlib.sha256(review_raw).hexdigest()
    records = tuple(PolicyBenefitAcceptance(**{**values, "review_artifact_ref": ref}) for values, _ in specs)
    root = load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=records)
    original = records[0 if target_first else len(records) - 1]
    assert next(e for e in root.entries if e.acceptance.acceptance_ref == original.acceptance_ref).acceptance is original
    return root, original


def run(raw, *, prepared=None, **fixture_options):
    root, original = prepared if prepared is not None else bundle(raw, **fixture_options)
    return load_historical_coverage_review_context_bytes(raw_bytes=raw, artifact=root, expected_acceptance=original)


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
    for part in path:
        body = body[part]
    return body


def set_value(body, path, value):
    at(body, path[:-1])[path[-1]] = value
    return body


def path_name(path):
    result = ""
    for part in path:
        result += f"[{part}]" if type(part) is int else ("." if result else "") + part
    return result or "root"


def test_exact_public_api_and_existing_stored_fields():
    fn = load_historical_coverage_review_context_bytes
    assert fn is domain.load_historical_coverage_review_context_bytes
    assert policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "artifact", "expected_acceptance")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "artifact": AcceptanceReviewArtifact,
                                 "expected_acceptance": PolicyBenefitAcceptance, "return": CoverageReviewContext}
    for cls, names in ((CoverageReviewContext, CONTEXT_KEYS), (InventoryCompletenessReview, INVENTORY_KEYS),
                       (ImplementationBindingReview, IMPLEMENTATION_KEYS)):
        assert tuple(f.name for f in fields(cls)) == names
    for kwargs in ({}, {"raw_bytes": b""}, {"raw_bytes": b"", "artifact": None}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", None, None)
    for option in ("skip_hash", "force_matched", "force_full", "ignore_implementation", "allow_stale",
                   "use_current_reviews", "fallback_context"):
        with pytest.raises(TypeError):
            fn(raw_bytes=b"", artifact=None, expected_acceptance=None, **{option: True})


def test_fixed_raw_h_sha_and_full_context_record_restoration():
    raw = encode(payload())
    assert len(raw) == 1628
    assert hashlib.sha256(raw).hexdigest() == FIXED_RAW_SHA256
    root, original = bundle(raw, context_hash=FIXED_RAW_SHA256)
    result = run(raw, prepared=(root, original))
    assert type(result) is CoverageReviewContext and result.to_dict() == payload()["review_context"]
    assert type(result.scope) is ApplicabilityScope
    assert type(result.inventory_reviews[0]) is InventoryCompletenessReview
    assert type(result.implementation_reviews[0]) is ImplementationBindingReview
    assert type(result.inventory_reviews[0].reviewed_at) is date
    assert result.inventory_reviews[0].reviewed_at == date(2026, 1, 1)
    assert result.implementation_reviews[0].reviewed_at == date(2026, 1, 2)
    assert result.implementation_reviews[0].review_artifact_ref == "합성 구현 검토 원문"


@pytest.mark.parametrize("inventory_present", (False, True))
@pytest.mark.parametrize("implementation_present", (False, True))
def test_empty_and_each_review_collection_is_independently_valid(inventory_present, implementation_present):
    body = payload()
    if not inventory_present:
        body["review_context"]["inventory_reviews"] = []
    if not implementation_present:
        body["review_context"]["implementation_reviews"] = []
    result = run(encode(body))
    assert result.to_dict() == body["review_context"]
    assert bool(result.inventory_reviews) is inventory_present and bool(result.implementation_reviews) is implementation_present
    assert not hasattr(result, "status") and not hasattr(result, "is_full")


def test_multiple_historical_versions_fingerprints_dates_and_same_targets_coexist_in_original_order():
    body = payload()
    context = body["review_context"]
    context["inventory_reviews"] = [
        inventory_review(review_ref="Z-OLD", inventory_version="i0002", inventory_fingerprint="8" * 64,
                         dataset_version="SYNTH-D0", source_registry_fingerprint="9" * 64, reviewed_at="2020-01-01"),
        inventory_review(review_ref="A-SAME-VERSION", inventory_fingerprint="7" * 64), inventory_review(),
    ]
    context["implementation_reviews"] = [
        implementation_review(review_ref="Z-OLD-IMPL", inventory_version="i0002", rule_version="old version",
            inventory_fingerprint="8" * 64, policy_tree_fingerprint="9" * 64, subtree_fingerprint="a" * 64,
            dataset_version="SYNTH-D0", source_registry_fingerprint="9" * 64, implementation_fingerprint="a" * 64,
            reviewed_at="2020-01-01"),
        implementation_review(review_ref="A-SAME-VERSION-IMPL", policy_tree_fingerprint="a" * 64), implementation_review(),
    ]
    result = run(encode(body))
    assert result.to_dict() == context
    assert [r.review_ref for r in result.inventory_reviews] == ["Z-OLD", "A-SAME-VERSION", "SYNTH-INVENTORY-A"]
    assert [r.review_ref for r in result.implementation_reviews] == ["Z-OLD-IMPL", "A-SAME-VERSION-IMPL", "SYNTH-IMPLEMENTATION-A"]
    assert result.dataset_version == "SYNTH-D1" and result.implementation_fingerprint == "4" * 64


@pytest.mark.parametrize("edition,quarter", (("2026", None), ("2026", 1), ("2026", 3), ("2026", 4), ("0000", 4)))
def test_exact_scope_including_annual_and_zero_edition(edition, quarter):
    body = payload()
    for path in (CTX, INV, IMPL):
        at(body, path)["scope"] = {"edition_id": edition, "quarter": quarter}
    result = run(encode(body), changes={"scope": ApplicabilityScope(edition, quarter)})
    assert result.to_dict() == body["review_context"]


@pytest.mark.parametrize("value", ("0001-01-01", "9999-12-31", "2000-02-29", "2024-02-29"))
@pytest.mark.parametrize("path", (INV, IMPL))
def test_exact_calendar_date_boundaries_without_current_date_or_expiry_rules(path, value):
    body = set_value(payload(), path + ("reviewed_at",), value)
    result = run(encode(body))
    assert result.to_dict() == body["review_context"]


def test_unicode_opaque_refs_spaces_and_one_hundred_immutable_deterministic_runs():
    body = payload()
    at(body, INV).update(review_ref="  한글 검토 ", review_artifact_ref=unicodedata.normalize("NFD", "원문/검토"))
    at(body, IMPL).update(review_ref="한글 검토", rule_version="  원문 규칙 버전 ", review_artifact_ref="내부 검토 원문")
    raw = encode(body)
    root, original = bundle(raw)
    entry, ref = root.entries[0], root.entries[0].coverage_reviews_ref
    before = (raw, deepcopy(root.to_dict()), deepcopy(original.to_dict()))
    results = [run(raw, prepared=(root, original)) for _ in range(100)]
    assert all(r == results[0] and r is not results[0] for r in results[1:])
    assert all(r.to_dict() == body["review_context"] for r in results)
    assert (raw, root.to_dict(), original.to_dict()) == before
    assert root.entries[0] is entry and entry.coverage_reviews_ref is ref and entry.acceptance is original
    first = results[0]
    for obj, name in ((first, "dataset_version"), (first.scope, "quarter"),
                      (first.inventory_reviews[0], "review_ref"), (first.implementation_reviews[0], "rule_root_id")):
        assert not hasattr(obj, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(obj, name, None)
    snapshot = first.to_dict()
    snapshot["scope"].clear()
    snapshot["inventory_reviews"][0].clear()
    snapshot["implementation_reviews"].clear()
    assert first.to_dict() == body["review_context"]


@pytest.mark.parametrize("target_first", (True, False))
def test_explicit_revision_selection_in_multi_entry_artifact_and_shared_bytes(target_first):
    raw = encode(payload())
    changed = encode(set_value(payload(), INV + ("review_artifact_ref",), "다른 확인본"))
    extras = (
        (record_values(acceptance_ref="SYNTH-C", acceptance_version="a0003"), hashlib.sha256(changed).hexdigest()),
        (record_values(acceptance_ref="SYNTH-D", acceptance_version="a0004"), hashlib.sha256(raw).hexdigest()),
        (record_values(acceptance_ref="SYNTH-OTHER", policy_id="SYNTH-OTHER", benefit_id="SYNTH-OTHER"), "a" * 64),
    )
    root, original = bundle(raw, extras=extras, target_first=target_first)
    assert run(raw, prepared=(root, original)).to_dict() == payload()["review_context"]
    shared = next(e.acceptance for e in root.entries if e.acceptance.acceptance_ref == "SYNTH-D")
    assert run(raw, prepared=(root, shared)) == run(raw, prepared=(root, original))
    other = next(e.acceptance for e in root.entries if e.acceptance.acceptance_ref == "SYNTH-C")
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", raw, prepared=(root, other))
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", changed, prepared=(root, original))


@pytest.mark.parametrize("field,bad", [
    ("raw_bytes", None), ("raw_bytes", "{}"), ("raw_bytes", {}), ("raw_bytes", ()),
    ("raw_bytes", bytearray(b"{}")), ("raw_bytes", memoryview(b"{}")),
    ("raw_bytes", type("BytesSubclass", (bytes,), {})(b"{}")),
    ("artifact", None), ("artifact", {}), ("artifact", []),
    ("artifact", ArtifactReference("synthetic/x.json", "a" * 64)),
    ("expected_acceptance", None), ("expected_acceptance", {}), ("expected_acceptance", "ref"),
])
def test_exact_input_types(field, bad):
    raw = encode(payload())
    root, original = bundle(raw)
    kwargs = {"raw_bytes": raw, "artifact": root, "expected_acceptance": original, field: bad}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_INPUT: " + field + ": "):
        load_historical_coverage_review_context_bytes(**kwargs)


@pytest.mark.parametrize("field", ("artifact", "expected_acceptance"))
def test_domain_subclasses_are_not_exact_input_types(field):
    raw = encode(payload())
    root, original = bundle(raw)
    obj = root if field == "artifact" else original
    derived = type("Derived", (type(obj),), {})(**{f.name: getattr(obj, f.name) for f in fields(obj)})
    kwargs = {"raw_bytes": raw, "artifact": root, "expected_acceptance": original, field: derived}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_INPUT: " + field):
        load_historical_coverage_review_context_bytes(**kwargs)


@pytest.mark.parametrize("changes,field", [
    ({}, "entry.acceptance"), ({"acceptance_version": "a0002"}, "entry.acceptance"),
    ({"policy_id": "SYNTH-OTHER"}, "entry.acceptance"), ({"benefit_id": "SYNTH-OTHER"}, "entry.acceptance"),
    ({"scope": ApplicabilityScope("2026", None)}, "entry.acceptance"),
    ({"acceptance_ref": "SYNTH-ABSENT"}, "artifact.entries"),
    ({"review_artifact_ref": "acceptance-review:sha256:" + "e" * 64}, "artifact.review_artifact_ref"),
])
def test_record_copies_other_revision_targets_missing_entry_and_root_mismatch(changes, field):
    raw = encode(payload())
    root, original = bundle(raw)
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_REVIEW_BINDING_MISMATCH", raw,
          prepared=(root, replace(original, **changes)), field=field)


def test_revoked_and_impossible_invalid_entry_ref_states_keep_existing_model_guards():
    raw = b"not-json"
    revoked = bundle(raw, changes={"status": BenefitAcceptanceStatus.REVOKED, "revokes_acceptance_ref": "SYNTH-OLDER"})
    assert revoked[0].entries[0].coverage_reviews_ref is None
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_REVIEW_BINDING_MISMATCH", raw,
          prepared=revoked, field="expected_acceptance.status")
    root, original = bundle(raw)
    entry = root.entries[0]
    for second in (entry, replace(entry), replace(entry, acceptance=replace(original, acceptance_version="a0002"))):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: entries:"):
            AcceptanceReviewArtifact(review_artifact_ref=root.review_artifact_ref, entries=(entry, second))
    for bad in (None, "wrong-ref", {}):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: coverage_reviews_ref:"):
            replace(entry, coverage_reviews_ref=bad)
    for path, digest in (("../x", "a" * 64), ("synthetic/x", "A" * 64), ("C:/x", "a" * 64),
                         ("synthetic/x", "a" * 63), ("synthetic\\x", "a" * 64)):
        with pytest.raises(PolicyDataError):
            ArtifactReference(path, digest)
    # 정상 모델로 생성할 수 없는 Entry를 만들기 위해 frozen 객체를 강제 변조하지 않는다.


def test_hash_failure_precedes_decoding_json_schema_and_construction(monkeypatch):
    raw = encode(payload())
    prepared, wrong_h = bundle(raw), bundle(raw, context_hash="a" * 64)
    def forbidden(*args, **kwargs):
        pytest.fail("SHA 실패 뒤 parsing/복원을 실행했습니다")
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", forbidden)
        patch.setattr(domain, "_load_context", forbidden)
        for bad in (raw.replace(b'"quarter":3', b'"quarter":4', 1), raw + b"\n", b"\xff", b"{broken"):
            error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", bad, prepared=prepared)
        error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", raw, prepared=wrong_h)


@pytest.mark.parametrize("raw,prefix", [
    (b"\xff", "ENCODING"), (b"\xef\xbb\xbf{}", "ENCODING"), (b"\xc0\xaf", "ENCODING"),
    (b"\xed\xa0\x80", "ENCODING"), (b"", "JSON"), (b"{", "JSON"), (b"{}{}", "JSON"),
    (b"[1,]", "JSON"), (b"null trailing", "JSON"), (b'{"x":01}', "JSON"),
    (b'{"x":NaN}', "NUMBER"), (b'{"x":Infinity}', "NUMBER"), (b'{"x":-Infinity}', "NUMBER"),
    (b'{"x":1.0}', "NUMBER"), (b'{"x":1e2}', "NUMBER"), (b'{"x":-0.0}', "NUMBER"),
    (b'{"x":"\\ud800"}', "UNICODE"), (b'{"\\udfff":0}', "UNICODE"),
])
def test_strict_encoding_syntax_numbers_and_unicode(raw, prefix):
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_" + prefix, raw)


def test_json_recursion_and_integer_errors_keep_global_limits(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    limit, recursion = sys.get_int_max_str_digits(), sys.getrecursionlimit()
    def failure(*args, **kwargs):
        raise RecursionError("synthetic parser failure")
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", failure)
        error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON", raw, prepared=prepared)
    if limit:
        error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_NUMBER", b'{"x":' + b"1" * (limit + 1) + b"}")
    assert (sys.get_int_max_str_digits(), sys.getrecursionlimit()) == (limit, recursion)


OBJECTS = (
    ((), ("schema_version", "review_context")), (CTX, CONTEXT_KEYS),
    (CTX + ("scope",), ("edition_id", "quarter")), (INV, INVENTORY_KEYS),
    (INV + ("scope",), ("edition_id", "quarter")), (IMPL, IMPLEMENTATION_KEYS),
    (IMPL + ("scope",), ("edition_id", "quarter")),
)


@pytest.mark.parametrize("path,keys", OBJECTS)
def test_duplicate_json_keys_at_every_object_depth(path, keys):
    body = payload()
    obj = at(body, path)
    key = keys[0]
    original = encode(obj)
    replacement = original[:-1] + b"," + encode(key) + b":" + encode(obj[key]) + b"}"
    raw = encode(body).replace(original, replacement, 1)
    error("DUPLICATE_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON_KEY", raw)


def test_escaped_keys_are_compared_after_decoding():
    error("DUPLICATE_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON_KEY", b'{"x":1,"\\u0078":2}')


@pytest.mark.parametrize("variant", ("pretty", "reverse", "newline", "space", "escaped", "negative-zero", "slash-escape"))
def test_noncanonical_bytes_not_repaired_before_model_construction(variant, monkeypatch):
    body = payload()
    raw = encode(body)
    if variant == "pretty":
        raw = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
    elif variant == "reverse":
        raw = json.dumps(dict(reversed(tuple(body.items()))), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    elif variant == "newline":
        raw += b"\n"
    elif variant == "space":
        raw = b" " + raw
    elif variant == "escaped":
        raw = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    elif variant == "negative-zero":
        raw = raw.replace(b'"quarter":3', b'"quarter":-0', 1)
    else:
        at(body, INV)["review_artifact_ref"] = "합성/검토"
        raw = encode(body).replace(b"/", b"\\/")
    prepared = bundle(raw)
    def forbidden(*args, **kwargs):
        pytest.fail("HRC1 실패 뒤 모델을 복원했습니다")
    monkeypatch.setattr(domain, "_load_context", forbidden)
    error("NONCANONICAL_HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES", raw, prepared=prepared)


@pytest.mark.parametrize("path,key", [(path, key) for path, keys in OBJECTS for key in keys])
def test_every_required_key_including_nullable_quarter(path, key):
    body = payload()
    del at(body, path)[key]
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,keys", OBJECTS)
@pytest.mark.parametrize("key", ("private-secret-extra", "status", "is_full", "verified"))
def test_unknown_keys_not_inferred_and_not_echoed(path, keys, key):
    body = payload()
    at(body, path)[key] = "private-value"
    message = error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", encode(body), field=path_name(path))
    assert key not in message and "private-value" not in message


def typed_paths(value, path=()):
    yield path, type(value)
    if type(value) is dict:
        for key, child in value.items():
            yield from typed_paths(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from typed_paths(child, path + (index,))


WRONG_TYPES = tuple((path, bad) for path, expected in typed_paths(payload())
                    for bad in (None, False, 0, "bad", [], {}) if type(bad) is not expected
                    and not (path and path[-1] == "quarter" and bad is None))


@pytest.mark.parametrize("path,bad", WRONG_TYPES)
def test_exact_nested_primitive_object_array_and_null_types(path, bad):
    body = set_value(payload(), path, bad) if path else bad
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("version", ("historical-coverage-review-context-2.0", "coverage-review-context-1.0", "", "1.0"))
def test_schema_aliases_and_future_versions_rejected(version):
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCHEMA", encode({**payload(), "schema_version": version}), field="schema_version")


@pytest.mark.parametrize("value", ("2026-02-30", "1900-02-29", "2026-1-01", "20260101", "２０２６-01-01",
                                   "2026-01-01T00:00:00", " 2026-01-01", "2026-01-01 ", "0000-01-01", ""))
@pytest.mark.parametrize("path", (INV, IMPL))
def test_strict_ascii_iso_calendar_dates(path, value):
    body = set_value(payload(), path + ("reviewed_at",), value)
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATE", encode(body), field=path_name(path) + ".reviewed_at")


SEMANTIC_ERRORS = (
    [(CTX + (key,), value, "review_context") for key, value in (
        ("policy_id", "lower-case"), ("dataset_version", " "), ("source_registry_fingerprint", "A" * 64),
        ("implementation_fingerprint", "a" * 63))]
    + [(path + ("scope", key), value, path_name(path) + ".scope") for path in (CTX, INV, IMPL)
       for key, value in (("edition_id", "2026/Q3"), ("edition_id", "２０２６"), ("quarter", 0), ("quarter", 5))]
    + [(path + (key,), value, path_name(path)) for path in (INV, IMPL)
       for key, value in (("review_ref", ""), ("review_artifact_ref", " "), ("policy_id", "lower-case"),
           ("inventory_version", "i0000"), ("inventory_version", "i00001"), ("inventory_fingerprint", "A" * 64),
           ("dataset_version", " "), ("source_registry_fingerprint", "bad"))]
    + [(IMPL + (key,), value, path_name(IMPL)) for key, value in (("condition_id", "lower"), ("rule_root_id", " "),
        ("rule_version", ""), ("policy_tree_fingerprint", "bad"), ("subtree_fingerprint", "0" * 63),
        ("implementation_fingerprint", "A" * 64))]
)


@pytest.mark.parametrize("path,value,field", SEMANTIC_ERRORS)
def test_existing_model_semantic_validation_is_reused(path, value, field):
    body = set_value(payload(), path, value)
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", encode(body), field=field)


@pytest.mark.parametrize("kind", ("inventory", "implementation", "cross-kind"))
def test_duplicate_refs_are_rejected_by_final_context_without_dedupe(kind):
    body = payload()
    obj = body["review_context"]
    if kind == "inventory":
        obj["inventory_reviews"].append(inventory_review(reviewed_at="2020-01-01"))
    elif kind == "implementation":
        obj["implementation_reviews"].append(implementation_review(rule_version="old"))
    else:
        obj["implementation_reviews"][0]["review_ref"] = obj["inventory_reviews"][0]["review_ref"]
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", encode(body), field="review_context")


@pytest.mark.parametrize("path", (INV, IMPL))
@pytest.mark.parametrize("key,value", (("policy_id", "SYNTH-OTHER"), ("scope", {"edition_id": "2026", "quarter": None})))
def test_any_record_with_other_policy_or_scope_is_model_error_even_if_unselected(path, key, value):
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", encode(set_value(payload(), path + (key,), value)), field="review_context")


@pytest.mark.parametrize("changes,prefix,field", [
    ({"policy_id": "SYNTH-OTHER"}, "IDENTITY", "policy_id"),
    ({"scope": ApplicabilityScope("2026", None)}, "SCOPE", "scope"),
    ({"coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2"}, "DATASET", "dataset_version"),
    ({"coverage_source_registry_fingerprint": "a" * 64, "benefit_source_registry_fingerprint": "a" * 64},
     "REGISTRY_FINGERPRINT", "source_registry_fingerprint"),
    ({"coverage_implementation_fingerprint": "a" * 64}, "IMPLEMENTATION_FINGERPRINT", "implementation_fingerprint"),
])
def test_five_independent_acceptance_baselines(changes, prefix, field):
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_" + prefix + "_MISMATCH", encode(payload()),
          changes=changes, field="review_context." + field)


def test_flat_snapshot_and_opposite_record_shape_are_not_inferred():
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", encode(payload()["review_context"]), field="root")
    body = payload()
    body["review_context"]["inventory_reviews"] = [implementation_review()]
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", encode(body), field=path_name(INV))


def test_all_raw_metadata_is_hash_bound_even_if_not_compared_to_acceptance():
    raw = encode(payload())
    prepared = bundle(raw)
    for path, value in ((INV + ("review_artifact_ref",), "정정 원문"), (INV + ("reviewed_at",), "2020-01-01"),
                        (IMPL + ("subtree_fingerprint",), "a" * 64)):
        changed = encode(set_value(payload(), path, value))
        error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", changed, prepared=prepared)
        assert run(changed).to_dict() != payload()["review_context"]


def test_phase_and_within_phase_precedence_are_deterministic():
    raw = encode(payload())
    root, original = bundle(raw)
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_INPUT: raw_bytes:"):
        load_historical_coverage_review_context_bytes(raw_bytes=None, artifact=None, expected_acceptance=None)
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_REVIEW_BINDING_MISMATCH", b"\xff", prepared=(root, replace(original)))
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", b"{broken", prepared=(root, original))
    body = payload()
    del body["review_context"]
    body.update(schema_version="wrong", extra=True)
    assert error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", encode(body)).endswith("missing review_context")
    body = set_value(payload(), INV + ("review_ref",), None)
    body["schema_version"] = "wrong"
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCHEMA", encode(body))
    body = set_value(payload(), INV + ("reviewed_at",), "bad-date")
    error("NONCANONICAL_HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES", encode(body) + b"\n")
    at(body, INV)["scope"]["quarter"] = 5
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", encode(body), field=path_name(INV) + ".scope")
    body = set_value(payload(), INV + ("review_ref",), " ")
    at(body, INV)["reviewed_at"] = "bad-date"
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATE", encode(body), field=path_name(INV) + ".reviewed_at")
    body = payload()
    at(body, INV)["reviewed_at"] = None
    at(body, IMPL)["review_ref"] = None
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE", encode(body), field=path_name(INV) + ".reviewed_at")
    body = payload()
    body["review_context"]["inventory_reviews"].append(inventory_review())
    at(body, IMPL)["reviewed_at"] = "bad-date"
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATE", encode(body), field=path_name(IMPL) + ".reviewed_at")
    body = set_value(payload(), INV + ("policy_id",), "SYNTH-OTHER")
    error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", encode(body), field="review_context",
          changes={"coverage_implementation_fingerprint": "a" * 64})
    changes = {"policy_id": "SYNTH-OTHER", "scope": ApplicabilityScope("2025", None),
        "coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2",
        "coverage_source_registry_fingerprint": "a" * 64, "benefit_source_registry_fingerprint": "a" * 64,
        "coverage_implementation_fingerprint": "a" * 64}
    for keys, prefix in ((("policy_id",), "IDENTITY"), (("scope",), "SCOPE"),
                         (("coverage_dataset_version", "benefit_dataset_version"), "DATASET"),
                         (("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"), "REGISTRY_FINGERPRINT")):
        error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_" + prefix + "_MISMATCH", raw, changes=changes)
        for key in keys:
            changes.pop(key)
    error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_IMPLEMENTATION_FINGERPRINT_MISMATCH", raw, changes=changes)


def test_sha_decode_parsed_root_and_constructor_objects_are_the_same_call(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    real_sha, real_loads, real_load_context = domain.hashlib.sha256, domain.json.loads, domain._load_context
    real_scope, real_inv = domain.ApplicabilityScope, domain.InventoryCompletenessReview
    real_impl, real_context, real_date = domain.ImplementationBindingReview, domain.CoverageReviewContext, domain._review_date
    hashed, parsed, built, events = [], [], [], []
    def sha(value):
        hashed.append(value)
        return real_sha(value)
    def loads(text, **kwargs):
        assert hashed == [raw] and hashed[0] is raw and text.encode("utf-8") == raw
        obj = real_loads(text, **kwargs)
        parsed.append((obj, deepcopy(obj)))
        return obj
    def load_context(obj):
        assert len(parsed) == 1 and obj is parsed[0][0]["review_context"]
        return real_load_context(obj)
    def scope(**kwargs):
        events.append("scope")
        return real_scope(**kwargs)
    def review_date(value, field):
        events.append("date")
        return real_date(value, field)
    def inv(**kwargs):
        events.append("inventory")
        value = real_inv(**kwargs)
        built.append(value)
        assert value.scope is kwargs["scope"]
        return value
    def impl(**kwargs):
        events.append("implementation")
        value = real_impl(**kwargs)
        built.append(value)
        return value
    def context(**kwargs):
        events.append("context")
        value = real_context(**kwargs)
        assert value.inventory_reviews[0] is built[0] and value.implementation_reviews[0] is built[1]
        assert value.scope is kwargs["scope"]
        built.append(value)
        return value
    with monkeypatch.context() as patch:
        for name, value in (("_load_context", load_context), ("ApplicabilityScope", scope),
                            ("_review_date", review_date), ("InventoryCompletenessReview", inv),
                            ("ImplementationBindingReview", impl), ("CoverageReviewContext", context)):
            patch.setattr(domain, name, value)
        patch.setattr(domain.hashlib, "sha256", sha)
        patch.setattr(domain.json, "loads", loads)
        result = run(raw, prepared=prepared)
    assert result is built[-1] and parsed[0][0] == parsed[0][1]
    assert events == ["scope", "scope", "date", "inventory", "scope", "date", "implementation", "context"]


@pytest.mark.parametrize("stage,field", (("ApplicabilityScope", "review_context.scope"),
    ("InventoryCompletenessReview", path_name(INV)), ("ImplementationBindingReview", path_name(IMPL)),
    ("CoverageReviewContext", "review_context")))
def test_only_constructor_data_errors_are_mapped_and_programming_errors_propagate(stage, field, monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    def data_failure(**kwargs):
        raise PolicyDataError("private original data")
    with monkeypatch.context() as patch:
        patch.setattr(domain, stage, data_failure)
        message = error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", raw, prepared=prepared, field=field)
        assert "private" not in message and "original" not in message
    def unexpected(**kwargs):
        raise RuntimeError("programming error")
    monkeypatch.setattr(domain, stage, unexpected)
    with pytest.raises(RuntimeError, match="programming error"):
        run(raw, prepared=prepared)


def test_only_twenty_approved_error_prefixes_and_no_result_downgrade():
    source = inspect.getsource(domain)
    prefixes = set(re.findall(r'"([A-Z][A-Z0-9_]+)"', source))
    spec = (Path(__file__).resolve().parents[1] / "docs/HISTORICAL_COVERAGE_REVIEW_CONTEXT_ARTIFACT_PREPARATION_SPEC.md").read_text(encoding="utf-8")
    assert len(prefixes) == 20 and all(prefix in spec for prefix in prefixes)
    assert not any(status in source for status in ("COVERAGE_SNAPSHOT_CHANGED", "BENEFIT_METADATA_NOT_REVIEWED"))


def test_pure_reconstruction_never_runs_review_tree_coverage_manifest_zip_or_external_io(monkeypatch):
    from backend.policy_engine.sources import SourceRegistry
    from backend.policy_engine.policy_data import coverage_fingerprint, coverage_review_matching, coverage_review_resolution
    from backend.policy_engine.policy_data import coverage_integration, eligibility_coverage_result, validation, manifest
    raw = encode(payload())
    prepared = bundle(raw)
    tree = ast.parse(inspect.getsource(domain))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names)
    assert imports <= {"datetime", "hashlib", "json", "re", "errors", "benefit_acceptance",
        "benefit_acceptance_review_artifact", "coverage_review", "coverage_review_context",
        "eligibility_coverage", "implementation_review", "manifest"}
    own = [v for v in vars(domain).values() if inspect.isfunction(v) and v.__module__ == domain.__name__]
    assert [fn.__name__ for fn in own if not fn.__name__.startswith("_")] == ["load_historical_coverage_review_context_bytes"]
    assert all(not isinstance(v, (dict, list, set)) for k, v in vars(domain).items() if not k.startswith("__"))
    def forbidden(*args, **kwargs):
        pytest.fail("순수 복원 경계 밖의 I/O/계산/검증을 실행했습니다")
    with monkeypatch.context() as patch:
        for cls, name in ((Path, "open"), (Path, "read_bytes"), (SourceRegistry, "resolve"), (SourceRegistry, "get_source")):
            patch.setattr(cls, name, forbidden)
        for module, names in (
            (policy_data, ("evaluate_eligibility_coverage", "load_acceptance_review_artifact_bytes",
                "load_historical_benefit_snapshot_bytes", "load_historical_eligibility_coverage_bytes",
                "load_historical_policy_envelope_bytes")),
            (coverage_fingerprint, ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree")),
            (coverage_review_resolution, ("_resolve_inventory_review", "_resolve_implementation_review")),
            (coverage_review_matching, ("_match_inventory_review", "_match_implementation_review")),
            (coverage_integration, ("_collect_coverage_integration_findings",)),
            (eligibility_coverage_result, ("_create_eligibility_coverage_result",)),
            (validation, ("validate_dataset_manifest", "validate_envelope_sources")),
            (manifest, ("fingerprint_source_registry", "fingerprint_policy_envelope")),
        ):
            for name in names:
                patch.setattr(module, name, forbidden)
        result = run(raw, prepared=prepared)
    assert type(result) is CoverageReviewContext and result.to_dict() == payload()["review_context"]
    assert not any(hasattr(result, name) for name in ("status", "matched", "is_full", "usable", "amount"))
