"""합성 원본의 HP1/전체 Tree 복원·Acceptance binding. FULL/검토 인증 테스트가 아니다."""

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
from backend.policy_engine.models import Policy, PolicyRule, RuleGroup
from backend.policy_engine.specialized_rules import BirthDateRule, ResidentRegistrationRule
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, ApplicabilityScope, ArtifactReference, BenefitAcceptanceStatus,
    PolicyBenefitAcceptance, PolicyEnvelope, fingerprint_policy_tree,
    load_acceptance_review_artifact_bytes, load_historical_policy_envelope_bytes,
)
from backend.policy_engine.policy_data import historical_policy_envelope_loader as domain


FIXED_TREE_FP = "e887c0978fdc6e5d652e6982c23913d7d1a2b5570f4d983edd77c953240a63c0"  # GV07
FIXED_RAW_SHA256 = "df9d56456db5fb2c5a20ba3b9783e7f5be2574acdf43466eb1970a382c0a7bd7"
REFERENCES = (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref",
)
ROOT_KEYS = (
    "schema_version", "rule_schema_version", "policy_id", "policy", "edition_id", "jurisdiction",
    "category", "dataset_version", "evaluation_scope", "coverage", "source_bindings",
    "verification_status", "last_verified_at", "lifecycle_status", "synthetic", "test_only",
)
POLICY_KEYS = ("policy_id", "policy_name", "rule_version", "synthetic", "test_only", "root")
ATOMIC_KEYS = ("kind", "rule_type", "rule_id", "field", "operator", "value", "evidence_refs")
RESIDENT_KEYS = ("kind", "rule_type", "rule_id", "required_region", "reference_date_source", "evidence_refs")
BIRTH_KEYS = ("kind", "rule_type", "rule_id", "min_birth_date", "max_birth_date", "evidence_refs")
BASIS_KEYS = ("basis", "subject", "period", "reference_year", "unit")


def atomic(**changes):
    return {"kind": "rule", "rule_type": "atomic", "rule_id": "RULE_A", "field": "age",
            "operator": "gte", "value": 19, "evidence_refs": ["SYNTH-SRC#a"], **changes}


def resident():
    return {"kind": "rule", "rule_type": "resident_registration", "rule_id": "RESIDENT_A",
            "required_region": {"sido": "SEOUL", "sigungu": "JONGNO"},
            "reference_date_source": "APPLICATION_DATE", "evidence_refs": ["SYNTH-SRC#a"]}


def birth():
    return {"kind": "rule", "rule_type": "birth_date", "rule_id": "BIRTH_A",
            "min_birth_date": "2000-01-01", "max_birth_date": "2001-01-01", "evidence_refs": ["SYNTH-SRC#a"]}


def income():
    return atomic(rule_id="INCOME_A", field="household_income", operator="lte", value=2000000,
                  fact_basis={"basis": "SYNTH-BASIS", "subject": "household", "period": "month",
                              "reference_year": 2026, "unit": "KRW"})


def group(children=None, *, operator="ALL", rule_id="GROUP_AB"):
    return {"kind": "group", "rule_id": rule_id, "operator": operator,
            "children": [atomic(), atomic(rule_id="RULE_B", field="student_status", operator="eq",
                                         value=False, evidence_refs=["SYNTH-SRC#b"])] if children is None else children}


def leaves(node):
    if node["kind"] == "group":
        return [leaf for child in node["children"] for leaf in leaves(child)]
    return [node]


def payload(root=None):
    root = atomic() if root is None else root
    return {
        "schema_version": "policy-data-1.0", "rule_schema_version": "m1.1", "policy_id": "SYNTH-POLICY",
        "policy": {"policy_id": "SYNTH-POLICY", "policy_name": "합성 정책", "rule_version": "r0001",
                   "synthetic": True, "test_only": True, "root": root},
        "edition_id": "2026", "jurisdiction": {"sido": "SEOUL", "sigungu": "JONGNO"},
        "category": "YOUTH_SUPPORT", "dataset_version": "SYNTH-D1", "evaluation_scope": "CONDITION_SLICE",
        "coverage": {"included_rule_ids": [leaf["rule_id"] for leaf in leaves(root)],
                     "excluded_conditions": ["합성 미구현 조건"]},
        "source_bindings": [{"source_document_id": "SYNTH-SRC", "document_version": "d0001"}],
        "verification_status": "DRAFT", "last_verified_at": None, "lifecycle_status": "ACTIVE",
        "synthetic": True, "test_only": True,
    }


def encode(body):
    # fixture 저작용 독립 encoder. production helper와 domain serializer를 사용하지 않는다.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def fixture_tree_fp(body):
    # 기대 fixture 저작용 raw projection. base는 기존 GV07 literal로 별도 고정한다.
    def project(node):
        if node["kind"] == "group":
            return {"node_type": "group", "rule_id": node["rule_id"], "operator": node["operator"],
                    "children": [project(child) for child in node["children"]]}
        result = {key: value for key, value in node.items() if key not in ("kind", "rule_type")}
        result["node_type"] = node["rule_type"]
        if node["rule_type"] == "atomic":
            result.setdefault("fact_basis", None)
        return result
    policy = body["policy"]
    return hashlib.sha256(encode({"fingerprint_schema": "coverage-policy-tree-1.0",
        "policy_id": policy["policy_id"], "rule_version": policy["rule_version"],
        "root": project(policy["root"])})).hexdigest()


def matching_changes(body):
    return {"policy_id": body["policy_id"], "scope": ApplicabilityScope(body["edition_id"], 3),
            "coverage_rule_version": body["policy"]["rule_version"],
            "coverage_policy_tree_fingerprint": fixture_tree_fp(body),
            "coverage_dataset_version": body["dataset_version"], "benefit_dataset_version": body["dataset_version"]}


def record_values(**changes):
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": FIXED_TREE_FP,
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


def raw_entry(values, envelope_hash):
    revoked = values["status"] is BenefitAcceptanceStatus.REVOKED
    references = {key: None if revoked else {"path": f"synthetic/{key}.json", "sha256": "b" * 64}
                  for key in REFERENCES}
    if not revoked:
        references["policy_envelope_ref"] = {"path": "synthetic/missing-policy.json", "sha256": envelope_hash}
    binding = {"source_document_id": "SYNTH-SRC", "document_version": "d0001"}
    return {
        "acceptance": raw_record(values), **references,
        "claim_evidence": [] if revoked else [{"claim": claim, "evidence_refs": ["SYNTH-SRC#a"]}
            for claim in ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")],
        "source_bindings": [] if revoked else [dict(binding)],
        "source_documents": [] if revoked else [{"binding": dict(binding), "artifact": {
            "path": "synthetic/missing-source.pdf", "sha256": "a" * 64}}],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
        "review_note": "합성 Policy 원본 대응", "manual_scenario_ids": ["HP01"],
    }


def bundle(raw, *, changes=None, envelope_hash=None, extras=(), target_first=False):
    # 소비 전에 외부 기대 H/R을 준비하고 실제 M2.57 결과와 R 원본을 전달한다.
    target = record_values(**(changes or {}))
    specs = [(target, envelope_hash if envelope_hash is not None else hashlib.sha256(raw).hexdigest())]
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
    return load_historical_policy_envelope_bytes(raw_bytes=raw, artifact=root, expected_acceptance=original)


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


def mixed_payload():
    return payload(group([atomic(), resident(), group([birth(), group([income()], operator="NOT", rule_id="G_NOT")],
                                                     operator="ANY", rule_id="G_ANY")]))


def successful(body, **options):
    return run(encode(body), changes=matching_changes(body), **options)


def test_exact_public_api_and_stored_models():
    fn = load_historical_policy_envelope_bytes
    assert fn is domain.load_historical_policy_envelope_bytes
    assert policy_data.__all__.count(fn.__name__) == 1
    params = inspect.signature(fn).parameters
    assert tuple(params) == ("raw_bytes", "artifact", "expected_acceptance")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty for p in params.values())
    assert get_type_hints(fn) == {"raw_bytes": bytes, "artifact": AcceptanceReviewArtifact,
                                 "expected_acceptance": PolicyBenefitAcceptance, "return": PolicyEnvelope}
    assert len(fields(PolicyEnvelope)) == 15 and len(fields(Policy)) == 6
    for kwargs in ({}, {"raw_bytes": b""}, {"raw_bytes": b"", "artifact": None}):
        with pytest.raises(TypeError):
            fn(**kwargs)
    with pytest.raises(TypeError):
        fn(b"", None, None)
    for option in ("skip_hash", "allow_stale", "force_verified", "force_full", "ignore_scope", "fallback_policy",
                   "current_envelope", "normalize_json"):
        with pytest.raises(TypeError):
            fn(raw_bytes=b"", artifact=None, expected_acceptance=None, **{option: True})


def test_pinned_hp1_bytes_gv07_and_all_envelope_fields():
    raw = encode(payload())
    assert len(raw) == 810
    assert hashlib.sha256(raw).hexdigest() == FIXED_RAW_SHA256
    root, original = bundle(raw, envelope_hash=FIXED_RAW_SHA256)
    result = run(raw, prepared=(root, original))
    assert type(result) is PolicyEnvelope and type(result.policy) is Policy
    assert result.root is result.policy.root and type(result.root) is PolicyRule
    assert result.schema_version == "policy-data-1.0" and result.rule_schema_version == "m1.1"
    assert (result.policy_id, result.policy_name, result.rule_version) == ("SYNTH-POLICY", "합성 정책", "r0001")
    assert result.edition_id == "2026" and result.jurisdiction.to_dict() == {"sido": "SEOUL", "sigungu": "JONGNO"}
    assert (result.category.value, result.dataset_version, result.evaluation_scope.value) == (
        "YOUTH_SUPPORT", "SYNTH-D1", "CONDITION_SLICE")
    assert result.coverage.included_rule_ids == ("RULE_A",)
    assert result.coverage.excluded_conditions == ("합성 미구현 조건",)
    assert [(b.source_document_id, b.document_version) for b in result.source_bindings] == [("SYNTH-SRC", "d0001")]
    assert result.verification_status.value == "DRAFT" and result.last_verified_at is None
    assert result.lifecycle_status.value == "ACTIVE" and result.effective_from is result.effective_to is None
    assert result.synthetic is result.test_only is True
    assert fingerprint_policy_tree(result.policy) == FIXED_TREE_FP


@pytest.mark.parametrize("node,expected_type,fixed", [
    (atomic(), PolicyRule, FIXED_TREE_FP),
    (group(), RuleGroup, "d95f5a2328666f69f7eb72a3e270b6f3ea39c2303197e522123ffdfe81a23a37"),
    (resident(), ResidentRegistrationRule, "cac2f242577922304c63f28bdac4c5c9712d54b2e6948d2cb74206aa5528658d"),
    (birth(), BirthDateRule, "3a08146cbe12770cd371868c11d2d6c1e0b8622f48ff044e2826116833bfdf04"),
    (income(), PolicyRule, "63221aca921c1e31080e1845e4c40c2c4a09671df3bc2276a357aada739ecdbe"),
    (atomic(rule_id="REGION_A", field="region", operator="in", value=["SEOUL", "GYEONGGI"]), PolicyRule,
     "4c971d7417a4b86448c979b54ae8116645a126061d9c3695d69ad567cf9feea4"),
])
def test_existing_tree_golden_nodes(node, expected_type, fixed):
    body = payload(deepcopy(node))
    assert fixture_tree_fp(body) == fixed
    result = run(encode(body), changes={"coverage_policy_tree_fingerprint": fixed})
    assert type(result.root) is expected_type and fingerprint_policy_tree(result.policy) == fixed
    if expected_type is BirthDateRule:
        assert (result.root.min_birth_date, result.root.max_birth_date) == (date(2000, 1, 1), date(2001, 1, 1))
    if expected_type is ResidentRegistrationRule:
        assert result.root.required_region.sido == "SEOUL" and result.root.reference_date_source.value == "APPLICATION_DATE"
    if node.get("fact_basis"):
        assert {f.name: getattr(result.root.fact_basis, f.name) for f in fields(result.root.fact_basis)} == node["fact_basis"]


def test_nested_all_any_not_mixed_tree_order_and_shared_refs():
    body = mixed_payload()
    result = successful(body)
    assert [n.rule_id for n in result.root.children] == ["RULE_A", "RESIDENT_A", "G_ANY"]
    assert type(result.root.children[0]) is PolicyRule and type(result.root.children[1]) is ResidentRegistrationRule
    any_group = result.root.children[2]
    assert any_group.operator.value == "ANY" and type(any_group.children[0]) is BirthDateRule
    assert any_group.children[1].operator.value == "NOT" and any_group.children[1].children[0].value == 2000000
    assert result.root.children[0].evidence_refs == result.root.children[1].evidence_refs == ("SYNTH-SRC#a",)
    reverse = payload(group(list(reversed(group()["children"]))))
    reversed_result = successful(reverse)
    assert [n.rule_id for n in reversed_result.root.children] == ["RULE_B", "RULE_A"]
    assert fingerprint_policy_tree(reversed_result.policy) == "56dc91d1f5ee476f2b7068194dc4dbeb33f1faf77c75ecedaa464f2b63193161"


@pytest.mark.parametrize("left", ("omitted", None, "2025-01-01"))
@pytest.mark.parametrize("right", ("omitted", None, "2027-01-01"))
@pytest.mark.parametrize("basis", ("omitted", None))
def test_optional_missing_and_null_are_distinct_bytes_same_existing_defaults(left, right, basis):
    body = payload()
    for key, value in (("effective_from", left), ("effective_to", right)):
        if value != "omitted":
            body[key] = value
    if basis != "omitted":
        body["policy"]["root"]["fact_basis"] = basis
    result = successful(body)
    assert result.effective_from == (date(2025, 1, 1) if left == "2025-01-01" else None)
    assert result.effective_to == (date(2027, 1, 1) if right == "2027-01-01" else None)
    assert result.root.fact_basis is None
    assert encode(body) != encode({**body, "effective_from": "2024-01-01"})


@pytest.mark.parametrize("quarter", (None, 1, 2, 3, 4))
def test_edition_year_only_does_not_prove_quarter(quarter):
    result = run(encode(payload()), changes={"scope": ApplicabilityScope("2026", quarter)})
    assert result.edition_id == "2026" and not hasattr(result, "quarter") and not hasattr(result, "scope")


@pytest.mark.parametrize("status,last_date,lifecycle", [
    ("DRAFT", None, "ACTIVE"), ("STALE", "2020-01-01", "ENDED"), ("VERIFIED", "2020-01-01", "ENDED"),
])
def test_historical_metadata_restored_without_verification_gate(status, last_date, lifecycle):
    body = payload()
    body.update(edition_id="2020", verification_status=status, last_verified_at=last_date, lifecycle_status=lifecycle,
                effective_from="2020-01-01", effective_to="2020-12-31")
    body["policy"]["rule_version"] = "r0002"
    result = successful(body)
    assert result.verification_status.value == status and result.lifecycle_status.value == lifecycle
    assert result.edition_id == "2020" and result.rule_version == "r0002" and not hasattr(result, "usable")


@pytest.mark.parametrize("flag", (True, False))
def test_existing_tt_ff_paths_preserve_synthetic_authoring_flags(flag):
    body = payload()
    body.update(synthetic=flag, test_only=flag)
    body["policy"].update(synthetic=flag, test_only=flag)
    result = successful(body)
    assert result.synthetic is result.test_only is flag
    assert result.verification_status.value == "DRAFT"


def test_array_duplicates_order_unicode_and_immutable_100_runs():
    body = payload(atomic(field="region", operator="in", value=["GYEONGGI", "SEOUL", "GYEONGGI"],
                          evidence_refs=["SYNTH-SRC#b", "SYNTH-SRC#a"]))
    body["policy"]["policy_name"] = "  합성 " + unicodedata.normalize("NFD", "한글")
    body["coverage"]["excluded_conditions"] = ["미구현", "미구현", "다른 조건"]
    raw = encode(body)
    prepared = bundle(raw, changes=matching_changes(body))
    before = (raw, deepcopy(prepared[0].to_dict()), deepcopy(prepared[1].to_dict()))
    results = [run(raw, prepared=prepared) for _ in range(100)]
    assert all(result == results[0] and result is not results[0] for result in results[1:])
    result = results[0]
    assert result.root.value == ("GYEONGGI", "SEOUL", "GYEONGGI")
    assert result.root.evidence_refs == ("SYNTH-SRC#b", "SYNTH-SRC#a")
    assert result.policy_name == body["policy"]["policy_name"] and result.coverage.excluded_conditions == tuple(body["coverage"]["excluded_conditions"])
    assert (raw, prepared[0].to_dict(), prepared[1].to_dict()) == before and json.loads(raw) == body
    assert not hasattr(result, "__dict__") and not hasattr(result.root, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.dataset_version = "changed"
    snapshot = result.to_dict()
    snapshot["policy"]["root"]["evidence_refs"].clear()
    assert result.root.evidence_refs == ("SYNTH-SRC#b", "SYNTH-SRC#a")


@pytest.mark.parametrize("target_first", (True, False))
def test_explicit_entry_selection_same_benefit_other_revision_and_shared_bytes(target_first):
    raw = encode(payload())
    changed = encode(set_value(payload(), ("policy", "root", "value"), 20))
    extras = (
        (record_values(acceptance_ref="SYNTH-C", acceptance_version="a0003"), hashlib.sha256(changed).hexdigest()),
        (record_values(acceptance_ref="SYNTH-D", acceptance_version="a0004"), hashlib.sha256(raw).hexdigest()),
        (record_values(acceptance_ref="SYNTH-OTHER", policy_id="SYNTH-OTHER", benefit_id="SYNTH-OTHER"), "a" * 64),
    )
    root, original = bundle(raw, extras=extras, target_first=target_first)
    assert run(raw, prepared=(root, original)).policy_id == original.policy_id
    shared = next(e.acceptance for e in root.entries if e.acceptance.acceptance_ref == "SYNTH-D")
    assert run(raw, prepared=(root, shared)) == run(raw, prepared=(root, original))
    error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", changed, prepared=(root, original))
    other = next(e.acceptance for e in root.entries if e.acceptance.acceptance_ref == "SYNTH-C")
    error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", raw, prepared=(root, other))


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
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_POLICY_ENVELOPE_LOADER_INPUT: " + field + ": "):
        load_historical_policy_envelope_bytes(**kwargs)


@pytest.mark.parametrize("field", ("artifact", "expected_acceptance"))
def test_domain_subclasses_rejected(field):
    raw = encode(payload())
    root, original = bundle(raw)
    obj = root if field == "artifact" else original
    derived = type("Derived", (type(obj),), {})(**{f.name: getattr(obj, f.name) for f in fields(obj)})
    kwargs = {"raw_bytes": raw, "artifact": root, "expected_acceptance": original, field: derived}
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_POLICY_ENVELOPE_LOADER_INPUT: " + field):
        load_historical_policy_envelope_bytes(**kwargs)


@pytest.mark.parametrize("changes,field", [
    ({}, "entry.acceptance"), ({"acceptance_version": "a0002"}, "entry.acceptance"),
    ({"policy_id": "SYNTH-OTHER"}, "entry.acceptance"), ({"benefit_id": "SYNTH-OTHER"}, "entry.acceptance"),
    ({"scope": ApplicabilityScope("2026", None)}, "entry.acceptance"),
    ({"acceptance_ref": "SYNTH-ABSENT"}, "artifact.entries"),
    ({"review_artifact_ref": "acceptance-review:sha256:" + "e" * 64}, "artifact.review_artifact_ref"),
])
def test_copies_other_revisions_targets_and_missing_entry(changes, field):
    raw = encode(payload())
    root, original = bundle(raw)
    error("HISTORICAL_POLICY_ENVELOPE_REVIEW_BINDING_MISMATCH", raw,
          prepared=(root, replace(original, **changes)), field=field)


def test_revoked_and_impossible_invalid_entry_states_use_existing_models():
    raw = b"not-json"
    revoked = bundle(raw, changes={"status": BenefitAcceptanceStatus.REVOKED, "revokes_acceptance_ref": "SYNTH-OLDER"})
    assert revoked[0].entries[0].policy_envelope_ref is None
    error("HISTORICAL_POLICY_ENVELOPE_REVIEW_BINDING_MISMATCH", raw, prepared=revoked, field="expected_acceptance.status")
    root, original = bundle(raw)
    entry = root.entries[0]
    for second in (entry, replace(entry), replace(entry, acceptance=replace(original, acceptance_version="a0002"))):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: entries:"):
            AcceptanceReviewArtifact(review_artifact_ref=root.review_artifact_ref, entries=(entry, second))
    for bad in (None, "wrong-ref", {}):
        with pytest.raises(PolicyDataError, match="^INVALID_ACCEPTANCE_REVIEW_ARTIFACT: policy_envelope_ref:"):
            replace(entry, policy_envelope_ref=bad)
    for path, digest in (("../x", "a" * 64), ("synthetic/x", "A" * 64), ("C:/x", "a" * 64),
                         ("synthetic/x", FIXED_TREE_FP[:-1]), ("synthetic\\x", "a" * 64)):
        with pytest.raises(PolicyDataError):
            ArtifactReference(path, digest)


def test_hash_failure_stops_before_all_parsing_and_uses_selected_h(monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    wrong_h = bundle(raw, envelope_hash="a" * 64)

    def forbidden(*args, **kwargs):
        pytest.fail("SHA 실패 뒤 parsing/복원/지문을 실행했습니다")

    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", forbidden)
        patch.setattr(domain, "parse_policy_envelope", forbidden)
        patch.setattr(domain, "fingerprint_policy_tree", forbidden)
        for bad in (raw.replace(b'"value":19', b'"value":18'), b"\xff", raw + b"\n", b"broken"):
            error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", bad, prepared=prepared)
        error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", raw, prepared=wrong_h)


@pytest.mark.parametrize("raw,prefix", [
    (b"\xff", "ENCODING"), (b"\xef\xbb\xbf{}", "ENCODING"), (b"\xc0\xaf", "ENCODING"),
    (b"\xed\xa0\x80", "ENCODING"), (b"", "JSON"), (b"{", "JSON"), (b"{}{}", "JSON"),
    (b"[1,]", "JSON"), (b"null trailing", "JSON"), (b'{"x":01}', "JSON"),
    (b'{"x":NaN}', "NUMBER"), (b'{"x":Infinity}', "NUMBER"), (b'{"x":-Infinity}', "NUMBER"),
    (b'{"x":1.0}', "NUMBER"), (b'{"x":1e2}', "NUMBER"), (b'{"x":-0.0}', "NUMBER"),
    (b'{"x":"\\ud800"}', "UNICODE"), (b'{"\\udfff":0}', "UNICODE"),
])
def test_strict_encoding_json_number_unicode(raw, prefix):
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_" + prefix, raw)


def test_integer_limit_and_parser_recursion_errors_without_global_changes(monkeypatch):
    limit, recursion = sys.get_int_max_str_digits(), sys.getrecursionlimit()
    if limit:
        error("INVALID_HISTORICAL_POLICY_ENVELOPE_NUMBER", b'{"x":' + b"1" * (limit + 1) + b"}")
    raw = encode(payload())
    prepared = bundle(raw)
    def failure(*args, **kwargs):
        raise RecursionError("synthetic parser failure")
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", failure)
        error("INVALID_HISTORICAL_POLICY_ENVELOPE_JSON", raw, prepared=prepared)
    assert (sys.get_int_max_str_digits(), sys.getrecursionlimit()) == (limit, recursion)


@pytest.mark.parametrize("raw", [
    b'{"x":1,"x":2}', b'{"a":{"x":1,"x":2}}', b'{"a":[{"x":1,"x":2}]}',
    b'{"x":1,"\\u0078":2}', b'{"a":{"fact_basis":{"unit":"KRW","unit":"USD"}}}',
])
def test_duplicate_decoded_keys_at_any_depth(raw):
    error("DUPLICATE_HISTORICAL_POLICY_ENVELOPE_JSON_KEY", raw)


@pytest.mark.parametrize("variant", ("pretty", "reverse", "newline", "space", "escaped", "negative-zero", "slash-escape"))
def test_hp1_noncanonical_forms_not_repaired(variant, monkeypatch):
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
        raw = raw.replace(b'"value":19', b'"value":-0')
    else:
        body["policy"]["policy_name"] = "합성/정책"
        raw = encode(body).replace(b"/", b"\\/")
    prepared = bundle(raw)
    def forbidden(*args, **kwargs):
        pytest.fail("HP1 실패 뒤 기존 parser를 실행했습니다")
    monkeypatch.setattr(domain, "parse_policy_envelope", forbidden)
    error("NONCANONICAL_HISTORICAL_POLICY_ENVELOPE_BYTES", raw, prepared=prepared)


TREE = ("policy", "root")
INCOME = TREE + ("children", 2, "children", 1, "children", 0)
RESIDENT = TREE + ("children", 1)
BIRTH = TREE + ("children", 2, "children", 0)
OBJECTS = (
    ((), ROOT_KEYS), (("policy",), POLICY_KEYS), (("jurisdiction",), ("sido", "sigungu")),
    (("coverage",), ("included_rule_ids", "excluded_conditions")),
    (("source_bindings", 0), ("source_document_id", "document_version")),
    (TREE, ("kind", "rule_id", "operator", "children")),
    (TREE + ("children", 0), ATOMIC_KEYS), (RESIDENT, RESIDENT_KEYS),
    (RESIDENT + ("required_region",), ("sido", "sigungu")), (BIRTH, BIRTH_KEYS),
    (INCOME, ATOMIC_KEYS), (INCOME + ("fact_basis",), BASIS_KEYS),
)


@pytest.mark.parametrize("path,key", [(path, key) for path, keys in OBJECTS for key in keys])
def test_every_required_key_at_each_schema_object(path, key):
    body = mixed_payload()
    del at(body, path)[key]
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", encode(body), field=path_name(path))


@pytest.mark.parametrize("path,keys", OBJECTS)
@pytest.mark.parametrize("key", ("private-secret-extra", "quarter", "node_type", "allow_real_data"))
def test_unknown_keys_never_inferred_or_echoed(path, keys, key):
    body = mixed_payload()
    at(body, path)[key] = "private-value"
    message = error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", encode(body), field=path_name(path))
    assert key not in message and "private-value" not in message


def typed_paths(value, path=()):
    yield path, type(value)
    if type(value) is dict:
        for key, child in value.items():
            # atomic.value의 scalar union과 nullable date는 별도 검사한다.
            if key not in ("value", "last_verified_at"):
                yield from typed_paths(child, path + (key,))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from typed_paths(child, path + (index,))


WRONG_TYPES = tuple((path, bad) for path, expected in typed_paths(mixed_payload())
                    for bad in (None, False, 0, "bad", [], {}) if type(bad) is not expected
                    and not (path and path[-1] == "fact_basis" and bad is None))


@pytest.mark.parametrize("path,bad", WRONG_TYPES)
def test_exact_primitive_object_array_types_throughout_schema(path, bad):
    body = mixed_payload()
    if path:
        set_value(body, path, bad)
    else:
        body = bad
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", encode(body), field=path_name(path))


@pytest.mark.parametrize("key", ("last_verified_at", "effective_from", "effective_to"))
@pytest.mark.parametrize("bad", (0, True, [], {}))
def test_nullable_metadata_dates_are_strings_or_null(key, bad):
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", encode({**payload(), key: bad}), field=key)


@pytest.mark.parametrize("bad", (None, {}, [None], [{}], [[19]]))
def test_atomic_value_raw_union_rejects_nested_or_null(bad):
    body = payload(atomic(value=bad))
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", encode(body))


@pytest.mark.parametrize("key,value", [("schema_version", "policy-data-2.0"), ("rule_schema_version", "m1.0"),
                                      ("schema_version", ""), ("rule_schema_version", "m1.1 ")])
def test_unsupported_schema_literals(key, value):
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_SCHEMA", encode({**payload(), key: value}), field=key)


@pytest.mark.parametrize("key,value", [("kind", "atomic"), ("kind", "RULE"), ("kind", ""),
                                      ("rule_type", "residence_history"), ("rule_type", "birth"), ("rule_type", "")])
def test_unsupported_node_discriminators(key, value):
    body = payload(atomic(**{key: value}))
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_NODE", encode(body), field="policy.root." + key)


@pytest.mark.parametrize("path,value", [
    (("policy_id",), "SYNTH-OTHER"), (("policy", "policy_id"), "SYNTH-OTHER"),
    (("policy", "policy_name"), " "), (("policy", "rule_version"), "r0000"),
    (("edition_id",), "2026/Q3"), (("edition_id",), "２０２６"),
    (("jurisdiction", "sido"), "서울"), (("jurisdiction", "sigungu"), "ANSAN"),
    (("category",), "OTHER"), (("dataset_version",), " "), (("evaluation_scope",), "FULL_POLICY"),
    (("coverage", "included_rule_ids"), []), (("coverage", "included_rule_ids"), ["RULE_A", "RULE_A"]),
    (("coverage", "included_rule_ids"), ["RULE_OTHER"]), (("coverage", "excluded_conditions"), []),
    (("source_bindings",), []), (("source_bindings", 0, "source_document_id"), "SYNTH-OTHER"),
    (("source_bindings", 0, "document_version"), "d0000"),
    (("verification_status",), "APPROVED"), (("verification_status",), "VERIFIED"),
    (("last_verified_at",), "2026-02-30"), (("last_verified_at",), "２０２６-01-01"),
    (("lifecycle_status",), "UNKNOWN"), (("effective_from",), "20260101"),
    (("synthetic",), False), (("test_only",), False), (("policy", "synthetic"), False),
    (("policy", "test_only"), False), (TREE + ("rule_id",), " "),
    (TREE + ("field",), "monthly_income"), (TREE + ("operator",), "GT"),
    (TREE + ("value",), True), (TREE + ("value",), "19"), (TREE + ("value",), [19]),
    (TREE + ("value",), -1), (TREE + ("fact_basis",), {"basis": "B", "subject": "household",
        "period": "month", "reference_year": 2026, "unit": "KRW"}),
    (TREE + ("evidence_refs",), []), (TREE + ("evidence_refs",), ["SYNTH-SRC#a", "SYNTH-SRC#a"]),
    (TREE + ("evidence_refs",), ["SYNTH-SRC#한글근거"]), (TREE + ("evidence_refs",), ["not-a-ref"]),
])
def test_existing_domain_parser_owns_semantic_errors(path, value):
    body = payload()
    if len(path) == 1:
        body[path[0]] = value
    else:
        set_value(body, path, value)
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", encode(body), field="root")


@pytest.mark.parametrize("node", [
    group([]), group(operator="X"), group(operator="NOT"), group([atomic(), atomic()]),
    group([atomic(rule_id="GROUP_AB")]),
    atomic(field="region", operator="gte", value="SEOUL"),
    atomic(operator="in", value=[]), atomic(operator="in", value=[19, "20"]),
    atomic(field="student_status", operator="eq", value=1),
    {**resident(), "reference_date_source": "TODAY"},
    {**resident(), "required_region": {"sido": "SEOUL", "sigungu": "ANSAN"}},
    {**birth(), "min_birth_date": "2002-01-01"}, {**birth(), "max_birth_date": "2001-02-30"},
    {**birth(), "min_birth_date": "20000101"},
    {**income(), "fact_basis": None},
    {**income(), "fact_basis": {**income()["fact_basis"], "reference_year": 0}},
    {**income(), "fact_basis": {**income()["fact_basis"], "unit": " "}},
])
def test_semantic_rule_combinations_and_specialized_fields(node):
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", encode(payload(deepcopy(node))), field="root")


def test_cross_field_dates_and_duplicate_sources_stay_model_errors():
    body = payload()
    body.update(effective_from="2026-02-01", effective_to="2026-01-01")
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", encode(body), field="root")
    body = payload()
    body["source_bindings"] *= 2
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", encode(body), field="root")


def test_original_parsed_root_and_returned_policy_used_exactly_once(monkeypatch):
    raw = encode(mixed_payload())
    prepared = bundle(raw, changes=matching_changes(mixed_payload()))
    parsed, envelopes, policies, decoded = [], [], [], []
    real_loads, real_parser, real_fp = domain.json.loads, domain.parse_policy_envelope, domain.fingerprint_policy_tree
    def loads(text, **kwargs):
        decoded.append(text)
        result = real_loads(text, **kwargs)
        parsed.append((result, deepcopy(result)))
        return result
    def parser(obj):
        assert len(parsed) == 1 and obj is parsed[0][0] and obj == parsed[0][1]
        result = real_parser(obj)
        envelopes.append(result)
        return result
    def fingerprint(policy):
        assert len(envelopes) == 1 and policy is envelopes[0].policy
        policies.append(policy)
        return real_fp(policy)
    with monkeypatch.context() as patch:
        patch.setattr(domain.json, "loads", loads)
        patch.setattr(domain, "parse_policy_envelope", parser)
        patch.setattr(domain, "fingerprint_policy_tree", fingerprint)
        result = run(raw, prepared=prepared)
    assert len(envelopes) == len(policies) == len(parsed) == len(decoded) == 1
    assert result is envelopes[0] and result.policy is policies[0]
    assert decoded[0].encode("utf-8") == raw and parsed[0][0] == parsed[0][1]


@pytest.mark.parametrize("stage,prefix,field", [
    ("parse_policy_envelope", "INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", "root"),
    ("fingerprint_policy_tree", "INVALID_HISTORICAL_POLICY_ENVELOPE_FINGERPRINT", "policy"),
])
def test_narrow_data_error_mapping_preserves_unexpected_exceptions(stage, prefix, field, monkeypatch):
    raw = encode(payload())
    prepared = bundle(raw)
    def data_failure(obj):
        raise PolicyDataError("private detail path/secret")
    with monkeypatch.context() as patch:
        patch.setattr(domain, stage, data_failure)
        message = error(prefix, raw, prepared=prepared, field=field)
        assert "private" not in message and "secret" not in message
    def unexpected(obj):
        raise RuntimeError("programming error")
    monkeypatch.setattr(domain, stage, unexpected)
    with pytest.raises(RuntimeError, match="programming error"):
        run(raw, prepared=prepared)


def test_existing_rule_parser_recursion_is_model_error_and_stops_fingerprint(monkeypatch):
    from backend.policy_engine import loader as rule_loader
    raw = encode(payload())
    prepared = bundle(raw)
    def failure(*args, **kwargs):
        raise RecursionError("synthetic rule parser failure")
    def forbidden(*args, **kwargs):
        pytest.fail("모델 복원 실패 뒤 Tree 지문을 실행했습니다")
    monkeypatch.setattr(rule_loader, "_node", failure)
    monkeypatch.setattr(domain, "fingerprint_policy_tree", forbidden)
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", raw, prepared=prepared, field="root")


@pytest.mark.parametrize("changes,prefix", [
    ({"policy_id": "SYNTH-OTHER"}, "IDENTITY"),
    ({"scope": ApplicabilityScope("2025", 3)}, "EDITION"),
    ({"coverage_rule_version": "r0002"}, "RULE_VERSION"),
    ({"coverage_policy_tree_fingerprint": "a" * 64}, "TREE_FINGERPRINT"),
    ({"coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2"}, "DATASET"),
])
def test_all_five_independent_acceptance_axes(changes, prefix):
    error("HISTORICAL_POLICY_ENVELOPE_" + prefix + "_MISMATCH", encode(payload()), changes=changes)


def test_fingerprint_change_same_version_and_dataset_separate_from_tree():
    body = payload(atomic(value=20))
    error("HISTORICAL_POLICY_ENVELOPE_TREE_FINGERPRINT_MISMATCH", encode(body))
    body = payload()
    body["dataset_version"] = "SYNTH-D2"
    assert fixture_tree_fp(body) == FIXED_TREE_FP
    error("HISTORICAL_POLICY_ENVELOPE_DATASET_MISMATCH", encode(body))
    old = successful(payload())
    body = payload(atomic(value=20))
    current = successful(body)
    assert old != current and run(encode(payload())) == old


def test_raw_hash_still_covers_metadata_excluded_from_tree():
    raw = encode(payload())
    prepared = bundle(raw)
    for path, value in ((("policy", "policy_name"), "새 합성 이름"),
                        (("source_bindings", 0, "document_version"), "d0002"),
                        (("coverage", "excluded_conditions"), ["별도 미구현 조건"])):
        body = set_value(payload(), path, value)
        assert fixture_tree_fp(body) == FIXED_TREE_FP
        error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", encode(body), prepared=prepared)
        assert successful(body).policy_id == "SYNTH-POLICY"


def test_phase_and_left_to_right_depth_first_precedence():
    raw = encode(payload())
    root, original = bundle(raw)
    with pytest.raises(PolicyDataError, match="^INVALID_HISTORICAL_POLICY_ENVELOPE_LOADER_INPUT: raw_bytes:"):
        load_historical_policy_envelope_bytes(raw_bytes=None, artifact=None, expected_acceptance=None)
    error("HISTORICAL_POLICY_ENVELOPE_REVIEW_BINDING_MISMATCH", b"\xff", prepared=(root, replace(original)))
    error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", b"{broken", prepared=(root, original))
    body = payload()
    del body["policy_id"]
    body.update(schema_version="wrong", extra=True)
    assert error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", encode(body)).endswith("missing policy_id")
    body = payload(atomic(operator="bad"))
    body["schema_version"] = "wrong"
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_SCHEMA", encode(body))
    body = payload(atomic(operator="bad"))
    error("NONCANONICAL_HISTORICAL_POLICY_ENVELOPE_BYTES", encode(body) + b"\n")
    body = mixed_payload()
    at(body, INCOME)["rule_id"] = None
    at(body, RESIDENT)["reference_date_source"] = None
    body["edition_id"] = None
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", encode(body), field="policy.root.children[1].reference_date_source")
    body = payload(atomic(kind="unsupported", rule_id=None))
    error("INVALID_HISTORICAL_POLICY_ENVELOPE_NODE", encode(body), field="policy.root.kind")
    changes = {"policy_id": "SYNTH-OTHER", "scope": ApplicabilityScope("2025", 3),
               "coverage_rule_version": "r0002", "coverage_policy_tree_fingerprint": "a" * 64,
               "coverage_dataset_version": "SYNTH-D2", "benefit_dataset_version": "SYNTH-D2"}
    for key, prefix in (("policy_id", "IDENTITY"), ("scope", "EDITION"),
                        ("coverage_rule_version", "RULE_VERSION"), ("coverage_policy_tree_fingerprint", "TREE_FINGERPRINT")):
        error("HISTORICAL_POLICY_ENVELOPE_" + prefix + "_MISMATCH", raw, changes=changes)
        changes.pop(key)
    error("HISTORICAL_POLICY_ENVELOPE_DATASET_MISMATCH", raw, changes=changes)


def test_only_21_contract_prefixes_and_no_status_downgrade():
    source = inspect.getsource(domain)
    prefixes = set(re.findall(r'"([A-Z][A-Z0-9_]*HISTORICAL_POLICY_ENVELOPE[A-Z0-9_]*)"', source))
    # HISTORICAL로 시작하는 binding prefix도 포함한다.
    prefixes.update(re.findall(r'"(HISTORICAL_POLICY_ENVELOPE_[A-Z0-9_]+)"', source))
    spec = (Path(__file__).resolve().parents[1] / "docs/HISTORICAL_POLICY_ENVELOPE_ARTIFACT_PREPARATION_SPEC.md").read_text(encoding="utf-8")
    assert len(prefixes) == 21 and all(prefix in spec for prefix in prefixes)
    assert not any(status in source for status in ("COVERAGE_SNAPSHOT_CHANGED", "BENEFIT_METADATA_NOT_REVIEWED"))


def test_pure_loader_has_no_external_or_coverage_execution(monkeypatch):
    from backend.policy_engine import loader as rule_loader
    from backend.policy_engine.sources import SourceRegistry
    from backend.policy_engine.policy_data import coverage_review_matching, validation, eligibility_coverage_result
    from backend.policy_engine.policy_data import loader as envelope_loader
    raw = encode(mixed_payload())
    prepared = bundle(raw, changes=matching_changes(mixed_payload()))
    tree = ast.parse(inspect.getsource(domain))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names)
    assert imports <= {"hashlib", "json", "errors", "benefit_acceptance", "benefit_acceptance_review_artifact",
                       "coverage_fingerprint", "envelope", "loader", "manifest"}
    own = [v for v in vars(domain).values() if inspect.isfunction(v) and v.__module__ == domain.__name__]
    assert [fn.__name__ for fn in own if not fn.__name__.startswith("_")] == ["load_historical_policy_envelope_bytes"]
    assert all(not isinstance(v, (dict, list, set)) for k, v in vars(domain).items() if not k.startswith("__"))
    def forbidden(*args, **kwargs):
        pytest.fail("순수 복원 loader가 외부 I/O나 다른 평가를 실행했습니다")
    with monkeypatch.context() as patch:
        for cls, name in ((Path, "open"), (Path, "read_bytes"), (SourceRegistry, "resolve"), (SourceRegistry, "get_source")):
            patch.setattr(cls, name, forbidden)
        for module, names in (
            (policy_data, ("evaluate_eligibility_coverage", "load_acceptance_review_artifact_bytes",
                           "load_historical_benefit_snapshot_bytes", "load_historical_eligibility_coverage_bytes")),
            (envelope_loader, ("load_policy_envelope",)), (rule_loader, ("load_policy_set",)),
            (coverage_review_matching, ("_match_inventory_review", "_match_implementation_review")),
            (validation, ("validate_dataset_manifest", "validate_envelope_sources")),
            (eligibility_coverage_result, ("_create_eligibility_coverage_result",)),
        ):
            for name in names:
                patch.setattr(module, name, forbidden)
        result = run(raw, prepared=prepared)
    assert type(result) is PolicyEnvelope and not hasattr(result, "status")
