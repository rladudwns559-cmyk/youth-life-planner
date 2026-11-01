"""합성 Coverage 입력의 동일 bytes 복원만 검증한다. Historical FULL 검증이 아니다."""

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
    ConditionBinding, ConditionInventory, ConditionRequirement, EligibilityCoverage,
    PolicyBenefitAcceptance, RequiredCondition, fingerprint_condition_inventory,
    load_acceptance_review_artifact_bytes, load_historical_eligibility_coverage_bytes,
)
from backend.policy_engine.policy_data import historical_eligibility_coverage_loader as domain
from backend.policy_engine.policy_data import coverage_fingerprint, coverage_review_matching, validation
from backend.policy_engine.policy_data import eligibility_coverage_result
from backend.policy_engine.sources import SourceRegistry


FIXED_INVENTORY_FP = "abf20d120e93265b5b2e85851707d255693f833ee2dbdab8cd5741115fdf572a"  # 기존 GV01
FIXED_RAW_SHA256 = "240ec48137b395eb5bdcccda9883c4eefa21b736e959b85f720f0b46cfa7339e"
INVENTORY_KEYS = ("policy_id", "scope", "inventory_version", "conditions", "completeness_review_ref")
CONDITION_KEYS = ("condition_id", "meaning", "requirement", "evidence_refs")
BINDING_KEYS = ("condition_id", "rule_root_id", "implementation_review_ref")
REFERENCES = (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref",
)


def condition_b():
    return {"condition_id": "COND_B", "meaning": "학생 조건", "requirement": "CONDITIONAL",
            "evidence_refs": ["SYNTH-SRC#c"]}


def binding_b():
    return {"condition_id": "COND_B", "rule_root_id": "ROOT_B", "implementation_review_ref": "SYNTH-IMPLEMENTATION-B"}


def payload():
    return {"schema_version": "historical-eligibility-coverage-1.0", "coverage": {
        "inventory": {
            "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
            "inventory_version": "i0001", "conditions": [{
                "condition_id": "COND_A", "meaning": "소득 조건", "requirement": "REQUIRED",
                "evidence_refs": ["SYNTH-SRC#a", "SYNTH-SRC#b"]}],
            "completeness_review_ref": "SYNTH-INVENTORY",
        },
        "bindings": [{"condition_id": "COND_A", "rule_root_id": "ROOT_A",
                      "implementation_review_ref": "SYNTH-IMPLEMENTATION-A"}],
    }}


def encode(body):
    # fixture 저작용 독립 encoder. production loader/canonical helper는 사용하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def inventory_fp_for_fixture(inventory):
    # fixture 저작 단계의 기대값. 소비 loader에서는 이 계산이나 actual→expected 대체를 하지 않는다.
    projection = {key: inventory[key] for key in ("policy_id", "scope", "inventory_version")}
    projection.update(fingerprint_schema="coverage-inventory-1.0",
                      conditions=sorted(inventory["conditions"], key=lambda row: row["condition_id"]))
    return hashlib.sha256(encode(projection)).hexdigest()


def matching_changes(body):
    inventory = body["coverage"]["inventory"]
    return {"policy_id": inventory["policy_id"], "scope": ApplicabilityScope(**inventory["scope"]),
            "coverage_inventory_version": inventory["inventory_version"],
            "coverage_inventory_fingerprint": inventory_fp_for_fixture(inventory)}


def record_values(**changes):
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": FIXED_INVENTORY_FP,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64,
        "reviewed_at": date(2026, 1, 1), "valid_until": date(2026, 12, 31),
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


def raw_entry(values, coverage_hash):
    revoked = values["status"] is BenefitAcceptanceStatus.REVOKED
    references = {key: None if revoked else {"path": f"synthetic/{key}.json", "sha256": "b" * 64}
                  for key in REFERENCES}
    if not revoked:
        references["coverage_snapshot_ref"] = {"path": "synthetic/missing-coverage.json", "sha256": coverage_hash}
    binding = {"source_document_id": "SYNTH-SRC", "document_version": "d0001"}
    return {
        "acceptance": raw_record(values), **references,
        "claim_evidence": [] if revoked else [{"claim": claim, "evidence_refs": ["SYNTH-SRC#a"]}
            for claim in ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding), "artifact": {
            "path": "synthetic/missing-source.pdf", "sha256": "a" * 64}}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
        "review_note": "합성 Coverage 원본 대응", "manual_scenario_ids": ["HC01"],
    }


def bundle(raw, *, changes=None, coverage_hash=None, extras=(), target_first=False):
    # 실제 M2.57 반환값만 정상 end-to-end 입력으로 공급한다. hash 저작은 호출 전에 완료한다.
    target = record_values(**(changes or {}))
    specs = [(target, coverage_hash if coverage_hash is not None else hashlib.sha256(raw).hexdigest())]
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
    return load_historical_eligibility_coverage_bytes(raw_bytes=raw, artifact=root, expected_acceptance=original)


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


def path_name(path):
    result = ""
    for part in path:
        result += f"[{part}]" if type(part) is int else ("." if result else "") + part
    return result or "root"


def set_value(body, path, value):
    at(body, path[:-1])[path[-1]] = value
    return body


OBJECTS = (
    ((), ("schema_version", "coverage")), (("coverage",), ("inventory", "bindings")),
    (("coverage", "inventory"), INVENTORY_KEYS),
    (("coverage", "inventory", "scope"), ("edition_id", "quarter")),
    (("coverage", "inventory", "conditions", 0), CONDITION_KEYS),
    (("coverage", "bindings", 0), BINDING_KEYS),
)


def test_exact_public_api_and_schema_correspond_to_existing_models():
    fn = load_historical_eligibility_coverage_bytes
    assert fn is domain.load_historical_eligibility_coverage_bytes
    assert policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "artifact", "expected_acceptance")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "artifact": AcceptanceReviewArtifact,
                                  "expected_acceptance": PolicyBenefitAcceptance, "return": EligibilityCoverage}
    for cls, names in ((EligibilityCoverage, domain._COVERAGE_KEYS), (ConditionInventory, domain._INVENTORY_KEYS),
                       (RequiredCondition, domain._CONDITION_KEYS), (ConditionBinding, domain._BINDING_KEYS)):
        assert tuple(f.name for f in fields(cls)) == names
    for kwargs in ({}, {"raw_bytes": b""}, {"raw_bytes": b"", "artifact": None}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", None, None)
    for option in ("allow_incomplete", "force_full", "ignore_fingerprint", "fallback_policy", "skip_hash",
                   "current_review_context", "expected_artifact_ref"):
        with pytest.raises(TypeError):
            fn(raw_bytes=b"", artifact=None, expected_acceptance=None, **{option: True})


def test_pinned_raw_sha_and_gv01_inventory_restore_existing_input_models():
    raw = encode(payload())
    assert len(raw) == 478 and hashlib.sha256(raw).hexdigest() == FIXED_RAW_SHA256
    root, original = bundle(raw, coverage_hash=FIXED_RAW_SHA256)
    result = run(raw, prepared=(root, original))
    assert type(result) is EligibilityCoverage and type(result.inventory) is ConditionInventory
    assert type(result.inventory.scope) is ApplicabilityScope
    assert type(result.inventory.conditions) is tuple and type(result.bindings) is tuple
    assert type(result.inventory.conditions[0]) is RequiredCondition
    assert result.inventory.conditions[0].requirement is ConditionRequirement.REQUIRED
    assert type(result.bindings[0]) is ConditionBinding
    assert result.to_dict() == payload()["coverage"]
    assert fingerprint_condition_inventory(result.inventory) == FIXED_INVENTORY_FP
    assert inventory_fp_for_fixture(payload()["coverage"]["inventory"]) == FIXED_INVENTORY_FP
    assert root.entries[0].acceptance is original
    assert root.entries[0].coverage_snapshot_ref.sha256 == FIXED_RAW_SHA256 != FIXED_INVENTORY_FP
    assert root.entries[0].accepted_terms_ref.sha256 != FIXED_RAW_SHA256
    assert not hasattr(result, "status")


@pytest.mark.parametrize("binding_count", [0, 1, 2])
@pytest.mark.parametrize("completeness", [None, "SYNTH-INVENTORY", "  opaque inventory ref  "])
def test_valid_incomplete_and_all_bindings_reconstruct_without_full_result(binding_count, completeness):
    body = payload()
    inv = body["coverage"]["inventory"]
    inv["conditions"].append(condition_b())
    inv["completeness_review_ref"] = completeness
    body["coverage"]["bindings"] = (body["coverage"]["bindings"] + [binding_b()])[:binding_count]
    result = run(encode(body), changes=matching_changes(body))
    assert result.to_dict() == body["coverage"]
    assert len(result.bindings) == binding_count
    assert result.inventory.completeness_review_ref == completeness
    assert not any(hasattr(result, name) for name in ("status", "full_policy", "usable", "reviewed", "findings"))


def test_condition_and_binding_order_preserved_even_when_inventory_fingerprint_normalizes_order():
    first = payload()
    first["coverage"]["inventory"]["conditions"].append(condition_b())
    first["coverage"]["bindings"].append(binding_b())
    second = deepcopy(first)
    second["coverage"]["inventory"]["conditions"].reverse()
    second["coverage"]["bindings"].reverse()
    results = []
    for body in (first, second):
        result = run(encode(body), changes=matching_changes(body))
        assert result.to_dict() == body["coverage"]
        assert fingerprint_condition_inventory(result.inventory) == (
            "3d0d97fc12200929459413e8bee59d9126a47749e34826a520529c80c6269946")  # 기존 GV02/GV03
        results.append(result)
    assert results[0] != results[1] and encode(first) != encode(second)


def test_evidence_duplicates_unicode_and_opaque_binding_refs_are_preserved():
    fingerprints = []
    for meaning in ("소득 조건", unicodedata.normalize("NFD", "소득 조건"), "  소득 조건  "):
        body = payload()
        row = body["coverage"]["inventory"]["conditions"][0]
        row.update(meaning=meaning, evidence_refs=["SYNTH-SRC#b", "SYNTH-SRC#a", "SYNTH-SRC#b"])
        body["coverage"]["bindings"][0].update(rule_root_id="  absent root  ",
                                                 implementation_review_ref="  opaque review  ")
        result = run(encode(body), changes=matching_changes(body))
        assert result.to_dict() == body["coverage"]
        assert result.inventory.conditions[0].evidence_refs == ("SYNTH-SRC#b", "SYNTH-SRC#a", "SYNTH-SRC#b")
        fingerprints.append(fingerprint_condition_inventory(result.inventory))
    assert len(set(fingerprints)) == 3


@pytest.mark.parametrize("scope", [{"edition_id": "2026", "quarter": None}, {"edition_id": "0000", "quarter": 4}])
def test_existing_scope_contract_including_annual_and_zero_edition_is_unchanged(scope):
    body = payload()
    body["coverage"]["inventory"].update(scope=scope, inventory_version="i10000")
    assert run(encode(body), changes=matching_changes(body)).to_dict() == body["coverage"]


@pytest.mark.parametrize("target_first", [True, False])
def test_explicit_selection_in_multi_entry_artifact_including_same_benefit_and_shared_raw(target_first):
    raw = encode(payload())
    changed = encode(set_value(payload(), ("coverage", "inventory", "conditions", 0, "meaning"), "변경된 소득 조건"))
    extras = (
        (record_values(acceptance_ref="SYNTH-C", acceptance_version="a0003"), hashlib.sha256(changed).hexdigest()),
        (record_values(acceptance_ref="SYNTH-D", acceptance_version="a0004"), FIXED_RAW_SHA256),
        (record_values(acceptance_ref="SYNTH-OTHER", policy_id="SYNTH-OTHER", benefit_id="SYNTH-OTHER"), "a" * 64),
    )
    root, original = bundle(raw, coverage_hash=FIXED_RAW_SHA256, extras=extras, target_first=target_first)
    assert run(raw, prepared=(root, original)).to_dict() == payload()["coverage"]
    shared = next(e.acceptance for e in root.entries if e.acceptance.acceptance_ref == "SYNTH-D")
    assert run(raw, prepared=(root, shared)).to_dict() == payload()["coverage"]
    error("HISTORICAL_COVERAGE_BYTES_MISMATCH", changed, prepared=(root, original))


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
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_LOADER_INPUT: " + field + ": "):
        load_historical_eligibility_coverage_bytes(**kwargs)


@pytest.mark.parametrize("field", ["artifact", "expected_acceptance"])
def test_model_subclass_inputs_are_not_implicitly_accepted(field):
    raw = encode(payload())
    root, original = bundle(raw)
    obj = root if field == "artifact" else original
    derived = type("Derived", (type(obj),), {})(**{f.name: getattr(obj, f.name) for f in fields(obj)})
    kwargs = {"raw_bytes": raw, "artifact": root, "expected_acceptance": original, field: derived}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_LOADER_INPUT: " + field):
        load_historical_eligibility_coverage_bytes(**kwargs)


@pytest.mark.parametrize("changes,field", [
    ({}, "entry.acceptance"), ({"acceptance_version": "a0002"}, "entry.acceptance"),
    ({"policy_id": "SYNTH-OTHER"}, "entry.acceptance"), ({"benefit_id": "SYNTH-OTHER"}, "entry.acceptance"),
    ({"scope": ApplicabilityScope("2026", None)}, "entry.acceptance"),
    ({"acceptance_ref": "SYNTH-ABSENT"}, "artifact.entries"),
    ({"review_artifact_ref": "acceptance-review:sha256:" + "e" * 64}, "artifact.review_artifact_ref"),
])
def test_record_copies_other_revisions_targets_absent_entry_and_root_are_not_originals(changes, field):
    raw = encode(payload())
    root, original = bundle(raw)
    error("HISTORICAL_COVERAGE_REVIEW_BINDING_MISMATCH", raw,
          prepared=(root, replace(original, **changes)), field=field)


def test_revoked_subject_is_rejected_without_reconstructing_fake_coverage():
    raw = b"not-json"
    prepared = bundle(raw, changes={"status": BenefitAcceptanceStatus.REVOKED,
                                    "revokes_acceptance_ref": "SYNTH-OLDER"})
    assert prepared[0].entries[0].coverage_snapshot_ref is None
    error("HISTORICAL_COVERAGE_REVIEW_BINDING_MISMATCH", raw, prepared=prepared,
          field="expected_acceptance.status")


def test_duplicate_entries_and_invalid_selected_ref_are_blocked_by_existing_models():
    raw = encode(payload())
    root, original = bundle(raw)
    entry = root.entries[0]
    for second in (entry, replace(entry), replace(entry, acceptance=replace(original, acceptance_version="a0002"))):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: entries:"):
            AcceptanceReviewArtifact(review_artifact_ref=root.review_artifact_ref, entries=(entry, second))
    for bad in (None, "wrong-ref", {}):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: coverage_snapshot_ref:"):
            replace(entry, coverage_snapshot_ref=bad)
    # frozen 모델을 강제로 바꾸지 않는다. 이 상태들은 정상 loader 입력으로 만들 수 없다.


def test_hash_failure_stops_before_decode_parse_construction_and_inventory_fingerprint(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw, coverage_hash=FIXED_RAW_SHA256)
    wrong_h = bundle(raw, coverage_hash="a" * 64)

    def forbidden(*args, **kwargs):
        pytest.fail("SHA 실패 뒤 parsing/복원/지문 계산을 실행했습니다")

    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", forbidden)
        patch.setattr(domain, "_load_coverage", forbidden)
        patch.setattr(domain, "fingerprint_condition_inventory", forbidden)
        for bad in (raw.replace(b"ROOT_A", b"ROOT_B"), b"\xff", raw + b"\n", b"broken"):
            error("HISTORICAL_COVERAGE_BYTES_MISMATCH", bad, prepared=prepared)
        error("HISTORICAL_COVERAGE_BYTES_MISMATCH", raw, prepared=wrong_h)
    assert prepared[0].entries[0].coverage_snapshot_ref.path == wrong_h[0].entries[0].coverage_snapshot_ref.path


@pytest.mark.parametrize("path,value", [
    (("coverage", "bindings", 0, "rule_root_id"), "OTHER_ROOT"),
    (("coverage", "bindings", 0, "implementation_review_ref"), "OTHER_REVIEW"),
    (("coverage", "inventory", "completeness_review_ref"), None),
    (("coverage", "bindings"), []),
])
def test_raw_sha_binds_fields_that_are_excluded_from_inventory_fingerprint(path, value):
    raw = encode(payload())
    changed_body = set_value(payload(), path, value)
    changed = encode(changed_body)
    assert inventory_fp_for_fixture(changed_body["coverage"]["inventory"]) == FIXED_INVENTORY_FP
    error("HISTORICAL_COVERAGE_BYTES_MISMATCH", changed, prepared=bundle(raw, coverage_hash=FIXED_RAW_SHA256))
    # 별도로 고정된 synthetic 검토 원본은 바뀐 bytes를 가리킬 수 있지만 old 원본과 혼동하지 않는다.
    assert run(changed).to_dict() == changed_body["coverage"]


@pytest.mark.parametrize("raw", [b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xef\xbb\xbf{}"])
def test_invalid_utf8_and_bom_after_successful_sha(raw):
    error("INVALID_HISTORICAL_COVERAGE_ENCODING", raw)


@pytest.mark.parametrize("raw", [b"", b"{", b"{}{}", b"[] trailing", b'{"a":}', b"+Infinity"])
def test_malformed_json(raw):
    error("INVALID_HISTORICAL_COVERAGE_JSON", raw)


@pytest.mark.parametrize("path,keys", OBJECTS)
def test_duplicate_json_keys_at_each_actual_schema_depth(path, keys):
    body = payload()
    key = keys[0]
    original = encode(at(body, path))
    repeated = ('{"' + key + '":null,').encode() + original[1:]
    raw = encode(body).replace(original, repeated, 1)
    error("DUPLICATE_HISTORICAL_COVERAGE_JSON_KEY", raw)


@pytest.mark.parametrize("raw", [b'{"x":0,"\\u0078":1}', b'{"a":[{"x":0,"x":1}]}'])
def test_duplicate_keys_use_decoded_names_before_schema_validation(raw):
    error("DUPLICATE_HISTORICAL_COVERAGE_JSON_KEY", raw)


@pytest.mark.parametrize("token", [b"1.0", b"1e0", b"NaN", b"Infinity", b"-Infinity"])
def test_invalid_numeric_tokens_are_not_coerced_to_quarter(token):
    raw = encode(payload()).replace(b'"quarter":3', b'"quarter":' + token)
    error("INVALID_HISTORICAL_COVERAGE_NUMBER", raw)


@pytest.mark.parametrize("raw", [b'{"\\ud800":0}', b'{"a":["\\udfff"]}', b'"\\ud800"'])
def test_unpaired_surrogates_in_keys_and_values(raw):
    error("INVALID_HISTORICAL_COVERAGE_UNICODE", raw)


def test_parser_recursion_and_int_limits_map_errors_without_global_changes(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    limit, recursion = sys.get_int_max_str_digits(), sys.getrecursionlimit()

    def failure(*args, **kwargs):
        raise RecursionError("synthetic parser failure")

    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", failure)
        error("INVALID_HISTORICAL_COVERAGE_JSON", raw, prepared=prepared)
    if limit:
        error("INVALID_HISTORICAL_COVERAGE_NUMBER", b'{"a":' + b"9" * (limit + 1) + b"}")
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_NUMBER:"):
        domain._integer("invalid-token")
    assert (sys.get_int_max_str_digits(), sys.getrecursionlimit()) == (limit, recursion)


@pytest.mark.parametrize("path,key", [(path, key) for path, keys in OBJECTS for key in keys])
def test_every_required_key_including_nullable_ref_must_be_present(path, key):
    body = payload()
    del at(body, path)[key]
    error("INVALID_HISTORICAL_COVERAGE_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,keys", OBJECTS)
def test_extra_keys_are_rejected_at_every_schema_depth(path, keys):
    body = payload()
    at(body, path)["private-secret-key"] = True
    message = error("INVALID_HISTORICAL_COVERAGE_FIELDS", encode(body), field=path_name(path))
    assert "private-secret-key" not in message


@pytest.mark.parametrize("schema", ["historical-eligibility-coverage-2.0", "coverage-inventory-1.0", "", "1.0"])
def test_unapproved_schema_versions_are_rejected(schema):
    body = payload()
    body["schema_version"] = schema
    error("INVALID_HISTORICAL_COVERAGE_SCHEMA", encode(body), field="schema_version")


STRING_PATHS = (
    ("schema_version",), ("coverage", "inventory", "policy_id"),
    ("coverage", "inventory", "scope", "edition_id"), ("coverage", "inventory", "inventory_version"),
    *(("coverage", "inventory", "conditions", 0, key) for key in ("condition_id", "meaning", "requirement")),
    ("coverage", "inventory", "conditions", 0, "evidence_refs", 0),
    *(("coverage", "bindings", 0, key) for key in BINDING_KEYS),
)
TYPE_CASES = (
    *((path, bad) for path, _ in OBJECTS for bad in (None, [], "object", 1, True)),
    *((path, bad) for path in STRING_PATHS for bad in (None, 1, True, [], {})),
    *((('coverage', 'inventory', 'scope', 'quarter'), bad) for bad in (True, False, "3", [], {})),
    *((('coverage', 'inventory', 'completeness_review_ref'), bad) for bad in (1, True, [], {})),
    *((path, bad) for path in (("coverage", "inventory", "conditions"), ("coverage", "bindings"),
                              ("coverage", "inventory", "conditions", 0, "evidence_refs"))
      for bad in (None, 1, True, "array", {})),
)


@pytest.mark.parametrize("path,bad", TYPE_CASES)
def test_exact_raw_types_and_nullable_rules(path, bad):
    body = payload()
    body = set_value(body, path, bad) if path else bad
    error("INVALID_HISTORICAL_COVERAGE_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("kind", ["whitespace", "key_order", "newline", "unicode_escape", "surrogate_pair", "negative_zero"])
def test_noncanonical_bytes_rejected_without_repair(kind):
    body = payload()
    raw = encode(body)
    if kind == "whitespace": raw = raw.replace(b":", b": ", 1)
    elif kind == "key_order": raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    elif kind == "newline": raw += b"\n"
    elif kind == "unicode_escape": raw = raw.replace("소득 조건".encode("utf-8"), b"\\uc18c\\ub4dd \\uc870\\uac74")
    elif kind == "surrogate_pair":
        body["coverage"]["inventory"]["conditions"][0]["meaning"] = "💡"
        raw = encode(body).replace("💡".encode("utf-8"), b"\\ud83d\\udca1")
    else: raw = raw.replace(b'"quarter":3', b'"quarter":-0')
    error("NONCANONICAL_HISTORICAL_COVERAGE_BYTES", raw)


@pytest.mark.parametrize("bad", ["wrong", "required", "REQUIRED ", "INFORMATIONAL", ""])
def test_invalid_requirement_enums_are_not_normalized(bad):
    body = set_value(payload(), ("coverage", "inventory", "conditions", 0, "requirement"), bad)
    error("INVALID_HISTORICAL_COVERAGE_VALUE", encode(body),
          field="coverage.inventory.conditions[0].requirement")


MODEL_CASES = (
    (("coverage", "inventory", "policy_id"), "bad_id"),
    *((('coverage', 'inventory', 'inventory_version'), bad) for bad in ("i0000", "i1", "i00001", "r0001")),
    *((('coverage', 'inventory', 'scope', 'quarter'), bad) for bad in (0, 5, -1)),
    *((('coverage', 'inventory', 'scope', 'edition_id'), bad) for bad in ("202", "２０２６", "year")),
    *((('coverage', 'inventory', 'conditions', 0, 'condition_id'), bad) for bad in ("", "bad", "COND-A")),
    (("coverage", "inventory", "conditions", 0, "meaning"), "  "),
    (("coverage", "inventory", "conditions"), []),
    (("coverage", "inventory", "conditions", 0, "evidence_refs"), []),
    *((('coverage', 'inventory', 'conditions', 0, 'evidence_refs'), refs) for refs in (
        ["missing-locator"], ["SYNTH-SRC#Upper"], ["SYNTH-SRC#two#parts"], ["bad#a"])),
    (("coverage", "inventory", "completeness_review_ref"), "  "),
    (("coverage", "bindings", 0, "condition_id"), "COND_UNKNOWN"),
    (("coverage", "bindings", 0, "condition_id"), "bad-id"),
    (("coverage", "bindings", 0, "rule_root_id"), "  "),
    (("coverage", "bindings", 0, "implementation_review_ref"), "  "),
)


@pytest.mark.parametrize("path,bad", MODEL_CASES)
def test_existing_model_invariants_are_reused(path, bad):
    error("INVALID_HISTORICAL_COVERAGE_MODEL", encode(set_value(payload(), path, bad)))


@pytest.mark.parametrize("kind", ["duplicate_condition", "duplicate_binding", "unknown_binding"])
def test_reference_contradictions_are_data_errors_not_normal_incomplete(kind):
    body = payload()
    if kind == "duplicate_condition":
        body["coverage"]["inventory"]["conditions"] *= 2
    elif kind == "duplicate_binding":
        body["coverage"]["bindings"] *= 2
    else:
        body["coverage"]["bindings"][0]["condition_id"] = "COND_UNKNOWN"
    error("INVALID_HISTORICAL_COVERAGE_MODEL", encode(body))


@pytest.mark.parametrize("path,bad,prefix,field", [
    (("coverage", "inventory", "policy_id"), "SYNTH-OTHER", "HISTORICAL_COVERAGE_IDENTITY_MISMATCH", "coverage.inventory.policy_id"),
    (("coverage", "inventory", "scope", "quarter"), None, "HISTORICAL_COVERAGE_IDENTITY_MISMATCH", "coverage.inventory.scope"),
    (("coverage", "inventory", "inventory_version"), "i0002", "HISTORICAL_COVERAGE_INVENTORY_VERSION_MISMATCH", "coverage.inventory.inventory_version"),
    (("coverage", "inventory", "conditions", 0, "meaning"), "변경된 소득 조건", "HISTORICAL_COVERAGE_INVENTORY_FINGERPRINT_MISMATCH", "coverage.inventory"),
])
def test_acceptance_inventory_binding_axes_are_independently_checked(path, bad, prefix, field):
    error(prefix, encode(set_value(payload(), path, bad)), field=field)


@pytest.mark.parametrize("changes", [
    {"coverage_rule_version": "r0002"}, {"coverage_policy_tree_fingerprint": "c" * 64},
    {"coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2"},
    {"coverage_source_registry_fingerprint": "d" * 64, "benefit_source_registry_fingerprint": "d" * 64},
    {"coverage_implementation_fingerprint": "e" * 64},
])
def test_out_of_scope_tree_release_implementation_values_are_not_falsely_verified(changes):
    result = run(encode(payload()), changes=changes)
    assert result.to_dict() == payload()["coverage"] and not hasattr(result, "status")
    # 이 성공은 위 provenance/Tree를 검증했다는 의미가 아니다.


def test_compound_error_precedence_across_phases():
    raw = encode(payload())
    root, original = bundle(raw)
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_COVERAGE_LOADER_INPUT: raw_bytes:"):
        load_historical_eligibility_coverage_bytes(raw_bytes=None, artifact=None, expected_acceptance=None)
    error("HISTORICAL_COVERAGE_REVIEW_BINDING_MISMATCH", b"\xff", prepared=(root, replace(original)))
    error("HISTORICAL_COVERAGE_BYTES_MISMATCH", b"\xff", prepared=(root, original))
    body = payload()
    del body["coverage"]["inventory"]["policy_id"]
    body["coverage"]["inventory"]["extra"] = True
    message = error("INVALID_HISTORICAL_COVERAGE_FIELDS", encode(body))
    assert message.endswith("missing policy_id")
    enum_raw = encode(set_value(payload(), ("coverage", "inventory", "conditions", 0, "requirement"), "bad"))
    error("NONCANONICAL_HISTORICAL_COVERAGE_BYTES", enum_raw + b"\n")
    body = payload()
    body["coverage"]["inventory"]["scope"]["edition_id"] = "bad"
    body["coverage"]["inventory"]["conditions"][0]["requirement"] = "bad"
    error("INVALID_HISTORICAL_COVERAGE_MODEL", encode(body), field="coverage.inventory.scope")
    body = payload()
    inv = body["coverage"]["inventory"]
    inv.update(policy_id="SYNTH-OTHER", scope={"edition_id": "2026", "quarter": None}, inventory_version="i0002")
    inv["conditions"][0]["meaning"] = "변경된 의미"
    for key in ("policy_id", "scope"):
        error("HISTORICAL_COVERAGE_IDENTITY_MISMATCH", encode(body), field="coverage.inventory." + key)
        inv[key] = payload()["coverage"]["inventory"][key]
    error("HISTORICAL_COVERAGE_INVENTORY_VERSION_MISMATCH", encode(body))
    inv["inventory_version"] = "i0001"
    error("HISTORICAL_COVERAGE_INVENTORY_FINGERPRINT_MISMATCH", encode(body))


def test_existing_inventory_fingerprint_called_once_on_returned_inventory(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    seen = []
    original = domain.fingerprint_condition_inventory

    def spy(inventory):
        seen.append(inventory)
        return original(inventory)

    monkeypatch.setattr(domain, "fingerprint_condition_inventory", spy)
    result = run(raw, prepared=prepared)
    assert len(seen) == 1 and seen[0] is result.inventory


def test_fingerprint_data_error_mapping_does_not_hide_programming_errors(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)

    def data_failure(inventory):
        raise PolicyDataError("private detail")

    with monkeypatch.context() as patch:
        patch.setattr(domain, "fingerprint_condition_inventory", data_failure)
        message = error("INVALID_HISTORICAL_COVERAGE_FINGERPRINT", raw, prepared=prepared)
        assert "private detail" not in message

    def unexpected(inventory):
        raise RuntimeError("programming error")

    monkeypatch.setattr(domain, "fingerprint_condition_inventory", unexpected)
    with pytest.raises(RuntimeError):
        run(raw, prepared=prepared)


def test_one_hundred_runs_preserve_all_inputs_and_frozen_slots_serialization():
    raw = encode(payload())
    root, original = bundle(raw, coverage_hash=FIXED_RAW_SHA256)
    before_raw, before_root, before_original = raw, root.to_dict(), original.to_dict()
    entry, ref = root.entries[0], root.entries[0].coverage_snapshot_ref
    first = run(raw, prepared=(root, original))
    for _ in range(100):
        result = run(raw, prepared=(root, original))
        assert result == first and result is not first
        output = result.to_dict()
        output["inventory"]["scope"].clear()
        output["inventory"]["conditions"][0]["evidence_refs"].clear()
        output["bindings"][0].clear()
        assert result.to_dict() == payload()["coverage"]
        assert raw is before_raw and root.to_dict() == before_root and original.to_dict() == before_original
        assert root.entries[0] is entry and entry.coverage_snapshot_ref is ref and entry.acceptance is original
    for obj, name, bad in ((first, "bindings", ()), (first.inventory, "conditions", ()),
                           (first.inventory.scope, "quarter", 1), (first.bindings[0], "rule_root_id", "new")):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, name, bad)
        assert not hasattr(obj, "__dict__")


def test_current_coverage_is_not_substituted_and_invalid_values_are_not_echoed():
    raw = encode(payload())
    old = run(raw)
    current = replace(old, inventory=replace(old.inventory, inventory_version="i0002"))
    error("HISTORICAL_COVERAGE_BYTES_MISMATCH", encode({"schema_version": "historical-eligibility-coverage-1.0",
          "coverage": current.to_dict()}), prepared=bundle(raw, coverage_hash=FIXED_RAW_SHA256))
    message = error("HISTORICAL_COVERAGE_IDENTITY_MISMATCH", encode(set_value(
        payload(), ("coverage", "inventory", "policy_id"), "SYNTH-PRIVATE-SECRET")))
    assert "SYNTH-PRIVATE-SECRET" not in message and old.inventory.inventory_version == "i0001"


def test_pure_reconstruction_never_executes_tree_reviews_manifest_result_or_other_services(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    tree = ast.parse(inspect.getsource(domain))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names)
    assert imports <= {"hashlib", "json", "errors", "benefit_acceptance", "benefit_acceptance_review_artifact",
                       "condition_binding", "condition_inventory", "coverage", "coverage_fingerprint",
                       "eligibility_coverage", "manifest", "required_condition"}
    own = [v for v in vars(domain).values() if inspect.isfunction(v) and v.__module__ == domain.__name__]
    assert [fn.__name__ for fn in own if not fn.__name__.startswith("_")] == [
        "load_historical_eligibility_coverage_bytes"]
    assert all(not isinstance(v, (dict, list, set)) for k, v in vars(domain).items() if not k.startswith("__"))

    def forbidden(*args, **kwargs):
        pytest.fail("입력 복원 loader가 외부/Tree/Review/Result 평가를 실행했습니다")

    with monkeypatch.context() as patch:
        for cls, name in ((Path, "open"), (Path, "read_bytes"), (SourceRegistry, "resolve"),
                          (SourceRegistry, "get_source"), (EligibilityCoverage, "to_dict")):
            patch.setattr(cls, name, forbidden)
        for module, names in (
            (policy_data, ("evaluate_eligibility_coverage", "load_acceptance_review_artifact_bytes",
                           "load_historical_benefit_snapshot_bytes")),
            (coverage_fingerprint, ("fingerprint_policy_tree", "fingerprint_rule_subtree")),
            (coverage_review_matching, ("_match_inventory_review", "_match_implementation_review")),
            (validation, ("validate_dataset_manifest", "validate_envelope_sources")),
            (eligibility_coverage_result, ("_create_eligibility_coverage_result",)),
        ):
            for name in names:
                patch.setattr(module, name, forbidden)
        result = run(raw, prepared=prepared)
    assert type(result) is EligibilityCoverage and not hasattr(result, "status")


def test_nineteen_error_prefixes_remain_exact_without_fabricating_impossible_models():
    spec = (Path(__file__).resolve().parents[1] /
            "docs/HISTORICAL_ELIGIBILITY_COVERAGE_ARTIFACT_PREPARATION_SPEC.md").read_text(encoding="utf-8")
    prefixes = re.findall(r"^\| P\d[a-c]? \| ([A-Z_]+) \|", spec, re.M)
    assert len(prefixes) == len(set(prefixes)) == 19
    code = inspect.getsource(domain)
    assert all('"' + prefix + '"' in code for prefix in prefixes)
    # EXPECTED_REF/중복 Entry는 정상 모델에서 도달 불가이므로 위의 생성 단계 차단을 별도 검증한다.
