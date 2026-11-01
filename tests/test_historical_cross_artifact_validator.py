"""M2.73: 실제 여섯 Loader 반환값과 관계 검증을 연결한다. 운영 orchestration은 아니다.

HXV13~22의 기존 raw/binding 거부는 변경 없는 M2.71 테스트에서 ALREADY_GUARDED다.
아래 DEFERRED/NOT_OBSERVABLE 성공은 해당 검증을 완료했다는 뜻이 아니다.
"""

import ast
import builtins
from copy import deepcopy
from dataclasses import fields, replace
import inspect
import io
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import time
from typing import get_type_hints

import pytest

import test_historical_six_artifact_integration as synthetic
from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.models import walk_nodes
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ArtifactReference, ConditionBinding, CoverageReviewContext,
    PolicyEditionReference, ReviewMatchStatus, SourceBinding,
    fingerprint_benefit_snapshot, fingerprint_policy_envelope, fingerprint_source_registry,
    load_acceptance_review_artifact_bytes, parse_policy_envelope,
)
from backend.policy_engine.policy_data import historical_cross_artifact_validator as domain
from backend.policy_engine.sources import SourceRegistry, SourceValidationError, parse_source_registry, validate_evidence_refs


# 문서화 분류 문자열이다. 운영 Enum/인증 모델이 아니다. R01~R36의 기본 책임을 추적한다.
RELATION_CLASSIFICATION = {
    "R01": "ALREADY_GUARDED", "R02": "ALREADY_GUARDED", "R03": "CROSS_VALIDATED",
    "R04": "ALREADY_GUARDED", "R05": "ALREADY_GUARDED", "R06": "ALREADY_GUARDED",
    "R07": "ALREADY_GUARDED", "R08": "ALREADY_GUARDED", "R09": "ALREADY_GUARDED",
    "R10": "CROSS_VALIDATED", "R11": "CROSS_VALIDATED", "R12": "CROSS_VALIDATED",
    "R13": "CROSS_VALIDATED", "R14": "CROSS_VALIDATED", "R15": "CROSS_VALIDATED",
    "R16": "DEFERRED", "R17": "DEFERRED", "R18": "CROSS_VALIDATED",
    "R19": "CROSS_VALIDATED", "R20": "CROSS_VALIDATED", "R21": "CROSS_VALIDATED",
    "R22": "CROSS_VALIDATED", "R23": "CROSS_VALIDATED", "R24": "CROSS_VALIDATED",
    "R25": "CROSS_VALIDATED", "R26": "CROSS_VALIDATED", "R27": "DEFERRED",
    "R28": "DEFERRED", "R29": "CROSS_VALIDATED", "R30": "DEFERRED",
    "R31": "DEFERRED", "R32": "DEFERRED", "R33": "CROSS_VALIDATED",
    "R34": "DEFERRED", "R35": "CROSS_VALIDATED", "R36": "CROSS_VALIDATED",
}
# 값이 같은 객체의 raw 출처는 별도 경계이며 R01의 raw 검사와 구별한다.
PROVENANCE_CLASSIFICATION = "NOT_OBSERVABLE"
ARGUMENTS = (
    "expected_acceptance", "artifact", "benefit_snapshot", "eligibility_coverage", "policy_envelope",
    "coverage_review_context", "dataset_manifest", "source_registry",
)
DOMAIN_ARGUMENTS = dict(zip(synthetic.LOADERS, ARGUMENTS[2:]))
HELPERS = (
    "_selected_entry", "_bind_manifest", "fingerprint_policy_envelope", "fingerprint_source_registry",
    "_analyze_coverage_structure", "fingerprint_condition_inventory", "fingerprint_policy_tree",
    "fingerprint_rule_subtree", "_match_inventory_review", "_match_implementation_review",
)


def restore_specs(*specs, selected=0, edit_review=None):
    """테스트 저작/복원 helper다. 새 운영 orchestration API가 아니다."""
    artifact, originals, raw_sets, review_raw = synthetic.prepare(*specs)
    if edit_review is not None:
        body = json.loads(review_raw)
        edit_review(body)
        review_raw = synthetic.canonical(body)
        root = "acceptance-review:sha256:" + synthetic.sha(review_raw)
        originals = tuple(replace(original, review_artifact_ref=root) for original in originals)
        artifact = load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=originals)
    original = originals[selected]
    assert artifact.entries[selected].acceptance is original
    restored = synthetic.restore(artifact, original, raw_sets[selected])  # 실제 여섯 loader 전부 성공 필수
    kwargs = {"expected_acceptance": original, "artifact": artifact,
              **{DOMAIN_ARGUMENTS[name]: value for name, value in restored.items()}}
    assert all(type(restored[name]) is expected for name, expected in zip(synthetic.LOADERS, synthetic.TYPES))
    return kwargs


@pytest.fixture
def inputs():
    return restore_specs(synthetic.definitions())


def validate(kwargs):
    return domain._validate_historical_artifact_relationships(**kwargs)


def assert_error(kwargs, prefix, field=None):
    with pytest.raises(PolicyDataError) as caught:
        validate(kwargs)
    if field is None:
        assert str(caught.value).startswith(prefix + ":"), str(caught.value)
    else:
        assert type(caught.value) is PolicyDataError
        assert str(caught.value) == f"{prefix}: {field}: 계약을 확인하세요"
    return caught.value


def refresh_envelope(spec):
    envelope = parse_policy_envelope(spec["bodies"]["envelope"])
    spec["authored"]["envelope"] = envelope
    selected = spec["bodies"]["manifest"]["manifest"]["policy_versions"][0]
    selected["fingerprint"] = fingerprint_policy_envelope(envelope)
    selected["artifact"] = synthetic.reference(spec["paths"]["envelope"], synthetic.canonical(spec["bodies"]["envelope"]))


def rewrite_registry(spec, edit):
    """합성 저작 중의 의존 자료 갱신이다. 소비 함수의 자동 보정이 아니다."""
    body = deepcopy(spec["bodies"]["registry"])
    edit(body)
    registry = parse_source_registry(body)
    registry_fp = fingerprint_source_registry(registry)
    spec["bodies"]["registry"] = registry.to_dict()
    spec["authored"]["registry"] = registry
    benefit = replace(spec["authored"]["benefit"], source_registry_fingerprint=registry_fp)
    spec["authored"]["benefit"] = benefit
    spec["bodies"]["benefit"]["snapshot"] = benefit.to_dict()
    context = spec["authored"]["reviews"]
    context = replace(context, source_registry_fingerprint=registry_fp,
        inventory_reviews=tuple(replace(row, source_registry_fingerprint=registry_fp) for row in context.inventory_reviews),
        implementation_reviews=tuple(replace(row, source_registry_fingerprint=registry_fp) for row in context.implementation_reviews))
    spec["authored"]["reviews"] = context
    spec["bodies"]["reviews"]["review_context"] = context.to_dict()
    manifest = replace(spec["authored"]["manifest"], source_registry=replace(
        spec["authored"]["manifest"].source_registry, fingerprint=registry_fp,
        artifact=ArtifactReference(**synthetic.reference(spec["paths"]["registry"], synthetic.canonical(registry.to_dict())))),
        source_versions=tuple(SourceBinding(row.source_document_id, row.document_version) for row in registry.sources))
    spec["authored"]["manifest"] = manifest
    spec["bodies"]["manifest"]["manifest"] = manifest.to_dict()
    for key in ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"):
        spec["values"][key] = registry_fp


def current_review(spec, collection="implementation_reviews", ref="IMPL-COND_AGE"):
    return next(row for row in spec["bodies"]["reviews"]["review_context"][collection] if row["review_ref"] == ref)


def watch(monkeypatch):
    """실제 helper를 호출하면서 순서·원본 인자·반환/예외를 관찰한다."""
    calls, outcomes = [], []
    for name in HELPERS:
        real = getattr(domain, name)
        def observed(*args, _name=name, _real=real, **kwargs):
            calls.append((_name, args, kwargs))
            result = _real(*args, **kwargs)
            outcomes.append((_name, result))
            return result
        monkeypatch.setattr(domain, name, observed)
    return calls, outcomes


def test_hxv01_cross_validated_exact_private_api_and_none(inputs):
    function = domain._validate_historical_artifact_relationships
    signature = inspect.signature(function)
    assert tuple(signature.parameters) == ARGUMENTS
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in signature.parameters.values())
    assert get_type_hints(function) == {**{name: type(inputs[name]) for name in ARGUMENTS}, "return": type(None)}
    assert function.__name__ not in policy_data.__all__ and not hasattr(policy_data, function.__name__)
    assert validate(inputs) is None


@pytest.mark.parametrize("name", ARGUMENTS)
@pytest.mark.parametrize("kind", ("none", "dict", "subclass"))
def test_exact_type_is_checked_before_entry_selection(inputs, monkeypatch, name, kind):
    original = inputs[name]
    if kind == "none":
        value = None
    elif kind == "dict":
        value = original.to_dict()
    else:
        derived = type("Derived" + type(original).__name__, (type(original),), {})
        value = derived(**{field.name: getattr(original, field.name) for field in fields(original) if field.init})
    kwargs = {**inputs, name: value}
    calls, _ = watch(monkeypatch)
    assert_error(kwargs, "INVALID_HISTORICAL_ARTIFACT_RELATIONSHIP_INPUT", name)
    assert calls == []


@pytest.mark.parametrize("missing", ARGUMENTS)
def test_missing_argument_is_native_typeerror(inputs, missing):
    kwargs = {key: value for key, value in inputs.items() if key != missing}
    with pytest.raises(TypeError):
        validate(kwargs)


@pytest.mark.parametrize("option", ("skip_hash", "force_verified", "profile", "allow_stale", "full_policy"))
def test_no_extra_override_parameters(inputs, option):
    with pytest.raises(TypeError):
        domain._validate_historical_artifact_relationships(**inputs, **{option: True})


def test_no_positional_arguments(inputs):
    with pytest.raises(TypeError):
        domain._validate_historical_artifact_relationships(*inputs.values())


@pytest.mark.parametrize("left,right", tuple(zip(ARGUMENTS, ARGUMENTS[1:])))
def test_p0_multiple_bad_types_follow_api_order(inputs, monkeypatch, left, right):
    calls, _ = watch(monkeypatch)
    assert_error({**inputs, left: None, right: None}, "INVALID_HISTORICAL_ARTIFACT_RELATIONSHIP_INPUT", left)
    assert calls == []


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("selected", (0, 1))
def test_hxv02_cross_validated_explicit_multi_entry_revision(reverse, selected):
    specs = (synthetic.definitions(), synthetic.definitions(2))
    if reverse:
        specs = specs[::-1]
    kwargs = restore_specs(*specs, selected=selected)
    assert kwargs["artifact"].entries[selected].acceptance is kwargs["expected_acceptance"]
    assert validate(kwargs) is None


@pytest.mark.parametrize("kind", ("copy_acceptance", "other_artifact"))
def test_hxv23_24_cross_validated_original_entry_binding(inputs, kind):
    if kind == "copy_acceptance":
        inputs = {**inputs, "expected_acceptance": replace(inputs["expected_acceptance"])}
        field = "entry.acceptance"
    else:
        other = restore_specs(synthetic.definitions(2))
        inputs = {**inputs, "artifact": other["artifact"]}
        field = "artifact.review_artifact_ref"
    error = assert_error(inputs, "HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH")
    assert str(error).split(": ")[1] == field


def test_hxv01_cross_validated_real_helper_order_and_original_nodes(inputs, monkeypatch):
    calls, outcomes = watch(monkeypatch)
    assert validate(inputs) is None
    assert [row[0] for row in calls] == [
        "_selected_entry", "_bind_manifest", "fingerprint_policy_envelope", "fingerprint_source_registry",
        "_analyze_coverage_structure", "fingerprint_condition_inventory", "fingerprint_policy_tree",
        "fingerprint_rule_subtree", "fingerprint_rule_subtree", "_match_inventory_review",
        "_match_implementation_review", "_match_implementation_review",
    ]
    entry = next(row for row in inputs["artifact"].entries if row.acceptance is inputs["expected_acceptance"])
    assert calls[0][1][0] is inputs["artifact"] and calls[0][1][1] is inputs["expected_acceptance"]
    assert calls[1][1][0] is inputs["dataset_manifest"] and calls[1][1][2] is entry
    structure = next(result for name, result in outcomes if name == "_analyze_coverage_structure")
    assert structure[0] == structure[2] == ()
    resolved = structure[1]
    assert all(binding is next(b for b in inputs["eligibility_coverage"].bindings if b.condition_id == binding.condition_id)
               and root is next(n for n in walk_nodes(inputs["policy_envelope"].root) if n.rule_id == binding.rule_root_id)
               for binding, root in resolved)
    subtree_calls = [args for name, args, _ in calls if name == "fingerprint_rule_subtree"]
    assert all(args[0] is root for args, (_, root) in zip(subtree_calls, resolved))
    inventory_calls = [args for name, args, _ in calls if name == "_match_inventory_review"]
    assert inventory_calls[0][0] is inputs["eligibility_coverage"].inventory
    impl_calls = [args for name, args, _ in calls if name == "_match_implementation_review"]
    assert all(args[1] is binding and args[2] is inputs["coverage_review_context"] for args, (binding, _) in zip(impl_calls, resolved))
    assert all(result.status is ReviewMatchStatus.MATCHED for name, result in outcomes if name.startswith("_match_"))
    # 위 상태는 합성 matcher 반환값의 관찰이며 실제 Review/승인 판정이 아니다.


@pytest.mark.parametrize("helper", HELPERS)
@pytest.mark.parametrize("error_type", (PolicyDataError, RuntimeError))
def test_helper_error_object_is_propagated_unchanged(inputs, monkeypatch, helper, error_type):
    sentinel = error_type("sentinel existing helper failure")
    def fail(*args, **kwargs):
        raise sentinel
    monkeypatch.setattr(domain, helper, fail)
    with pytest.raises(error_type) as caught:
        validate(inputs)
    assert caught.value is sentinel


def test_get_source_original_order_and_reuse_for_content_hash(inputs, monkeypatch):
    calls = []
    real = SourceRegistry.get_source
    def observed(self, source_id):
        calls.append((self, source_id))
        return real(self, source_id)
    monkeypatch.setattr(SourceRegistry, "get_source", observed)
    assert validate(inputs) is None
    assert [source_id for _, source_id in calls] == ["SYNTH-A", "SYNTH-B"] * 3
    assert all(registry is inputs["source_registry"] for registry, _ in calls)


@pytest.mark.parametrize("kind", ("missing", "stale"))
def test_hxv03_06_07_normal_missing_and_stale_are_preserved(monkeypatch, kind):
    spec = synthetic.definitions()
    coverage = spec["bodies"]["coverage"]["coverage"]
    coverage["inventory"]["completeness_review_ref"] = None if kind == "missing" else "INV-OLD"
    coverage["bindings"][0]["implementation_review_ref"] = "IMPL-OLD"
    kwargs = restore_specs(spec)
    _, outcomes = watch(monkeypatch)
    assert validate(kwargs) is None
    inv = next(value for name, value in outcomes if name == "_match_inventory_review")
    impl = [value for name, value in outcomes if name == "_match_implementation_review"]
    assert inv.status is (ReviewMatchStatus.MISSING if kind == "missing" else ReviewMatchStatus.STALE)
    assert impl[0].status is ReviewMatchStatus.STALE and impl[1].status is ReviewMatchStatus.MATCHED
    assert len(kwargs["coverage_review_context"].inventory_reviews) == 2
    assert len(kwargs["coverage_review_context"].implementation_reviews) == 3


@pytest.mark.parametrize("status", ("ACTIVE", "SUPERSEDED", "WITHDRAWN"))
def test_hxv04_05_deferred_source_status_and_dates_are_preserved(status):
    spec = synthetic.definitions()
    def edit(body):
        for source in body["sources"]:
            source["status"] = status
            for locator in source["locators"]:
                locator["status"] = status
    rewrite_registry(spec, edit)
    kwargs = restore_specs(spec)
    assert validate(kwargs) is None
    assert all(source.status.value == status and source.verified_at is None for source in kwargs["source_registry"].sources)
    assert kwargs["policy_envelope"].verification_status.value == "DRAFT"
    assert kwargs["policy_envelope"].evaluation_scope.value == "CONDITION_SLICE"


def test_hxv08_selected_policy_only_is_not_entire_release_validation():
    spec = synthetic.definitions()
    other_body = deepcopy(spec["bodies"]["envelope"])
    other_body["policy_id"] = other_body["policy"]["policy_id"] = "SYNTH-OTHER"
    other = parse_policy_envelope(other_body)
    reference = PolicyEditionReference(policy_id=other.policy_id, edition_id=other.edition_id,
        rule_version=other.rule_version, artifact=ArtifactReference(**synthetic.reference("synthetic/other.json", synthetic.canonical(other_body))),
        fingerprint=fingerprint_policy_envelope(other))
    manifest = spec["bodies"]["manifest"]["manifest"]
    manifest["policy_versions"].insert(0, {
        "policy_id": reference.policy_id, "edition_id": reference.edition_id, "rule_version": reference.rule_version,
        "artifact": {"path": reference.artifact.path, "sha256": reference.artifact.sha256},
        "fingerprint": reference.fingerprint, "schema_version": reference.schema_version, "rule_schema_version": reference.rule_schema_version})
    kwargs = restore_specs(spec)
    assert kwargs["dataset_manifest"].policy_versions[1].policy_id == kwargs["expected_acceptance"].policy_id
    assert validate(kwargs) is None


@pytest.mark.parametrize("kind", ("engine_version", "engine_sha", "missing_locator"))
def test_hxv09_44_45_deferred_checks_remain_outside_validator(kind):
    spec = synthetic.definitions()
    if kind == "engine_version":
        spec["bodies"]["manifest"]["manifest"]["engine_version"] = "historical-other-engine"
    elif kind == "engine_sha":
        spec["bodies"]["manifest"]["manifest"]["engine_artifact_sha256"] = synthetic.sha(b"other engine artifact")
    else:
        benefit = replace(spec["authored"]["benefit"], benefit_evidence_refs=("SYNTH-A#missing", "SYNTH-B#benefit"))
        spec["authored"]["benefit"] = benefit
        spec["bodies"]["benefit"]["snapshot"] = benefit.to_dict()
        spec["values"]["benefit_fingerprint"] = fingerprint_benefit_snapshot(benefit)
    kwargs = restore_specs(spec)
    assert validate(kwargs) is None  # DEFERRED: 이 None은 해당 D 검증의 성공이 아니다.
    if kind == "missing_locator":
        with pytest.raises(SourceValidationError) as caught:
            validate_evidence_refs(kwargs["benefit_snapshot"].benefit_evidence_refs, kwargs["source_registry"])
        assert caught.value.code == "LOCATOR_NOT_FOUND"


def test_hxv10_known_content_hash_is_optional():
    spec = synthetic.definitions()
    rewrite_registry(spec, lambda body: body["sources"][0].update(content_sha256=None))
    kwargs = restore_specs(spec)
    assert kwargs["source_registry"].sources[0].content_sha256 is None
    assert validate(kwargs) is None


def test_hxv11_source_version_set_is_order_independent_without_mutating_tuple():
    spec = synthetic.definitions()
    spec["bodies"]["manifest"]["manifest"]["source_versions"].reverse()
    kwargs = restore_specs(spec)
    before = kwargs["dataset_manifest"].source_versions
    assert validate(kwargs) is None
    assert kwargs["dataset_manifest"].source_versions is before
    assert before[0].source_document_id == "SYNTH-B"


def negative_spec(kind):
    spec = synthetic.definitions()
    body = spec["bodies"]
    if kind in ("source_version", "source_missing", "source_extra"):
        rows = body["manifest"]["manifest"]["source_versions"]
        if kind == "source_version": rows[0]["document_version"] = "d0002"
        elif kind == "source_missing": rows.pop(0)
        else: rows.append({"source_document_id": "SYNTH-C", "document_version": "d0001"})
    elif kind == "envelope_fp":
        body["manifest"]["manifest"]["policy_versions"][0]["fingerprint"] = fingerprint_policy_envelope(
            synthetic.definitions(title="다른 합성 제목")["authored"]["envelope"])
    elif kind == "root": body["coverage"]["coverage"]["bindings"][0]["rule_root_id"] = "RULE_MISSING"
    elif kind == "inventory_ref": body["coverage"]["coverage"]["inventory"]["completeness_review_ref"] = "INV-MISSING"
    elif kind == "implementation_ref": body["coverage"]["coverage"]["bindings"][0]["implementation_review_ref"] = "IMPL-MISSING"
    elif kind == "wrong_inventory_type": body["coverage"]["coverage"]["inventory"]["completeness_review_ref"] = "IMPL-COND_AGE"
    elif kind == "wrong_implementation_type": body["coverage"]["coverage"]["bindings"][0]["implementation_review_ref"] = "INV-CURRENT"
    elif kind in ("inventory_fingerprint", "policy_tree_fingerprint", "subtree_fingerprint", "source_registry_fingerprint"):
        current_review(spec)[kind] = synthetic.sha(b"contradictory synthetic review metadata")
    elif kind == "inventory_review_fp":
        current_review(spec, "inventory_reviews", "INV-CURRENT")["inventory_fingerprint"] = synthetic.sha(b"contradictory inventory metadata")
    elif kind == "review_condition": current_review(spec)["condition_id"] = "COND_STUDENT"
    elif kind == "review_root": current_review(spec)["rule_root_id"] = "RULE_STUDENT"
    elif kind == "benefit_version":
        benefit = replace(spec["authored"]["benefit"], source_bindings=(SourceBinding("SYNTH-A", "d0002"), SourceBinding("SYNTH-B", "d0001")))
        spec["authored"]["benefit"] = benefit
        body["benefit"]["snapshot"] = benefit.to_dict()
        spec["values"]["benefit_fingerprint"] = fingerprint_benefit_snapshot(benefit)
    elif kind == "envelope_version":
        body["envelope"]["source_bindings"][0]["document_version"] = "d0002"
        refresh_envelope(spec)
    elif kind == "source_content": spec["source_bytes"]["SYNTH-A"] = b"a different original TEST_ONLY\n"
    elif kind == "implementation": spec["implementation_bytes"] = b"a different TEST_ONLY implementation artifact\n"
    else: raise AssertionError(kind)
    return spec


CROSS_CASES = (
    ("HXV27_R13", "source_version", "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "dataset_manifest.source_versions"),
    ("HXV27_R13_missing", "source_missing", "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "dataset_manifest.source_versions"),
    ("HXV27_R13_extra", "source_extra", "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "dataset_manifest.source_versions"),
    ("HXV28_R14", "envelope_fp", "HISTORICAL_ARTIFACT_POLICY_MISMATCH", "selected_policy.fingerprint"),
    ("HXV31_R18", "root", "RULE_ROOT_NOT_FOUND", None),
    ("HXV32_R19", "inventory_ref", "REVIEW_REF_NOT_FOUND", None),
    ("HXV33_R20", "implementation_ref", "REVIEW_REF_NOT_FOUND", None),
    ("HXV33_R19_type", "wrong_inventory_type", "WRONG_REVIEW_TYPE", None),
    ("HXV33_R20_type", "wrong_implementation_type", "WRONG_REVIEW_TYPE", None),
    ("HXV34_R21", "inventory_fingerprint", "INVENTORY_FINGERPRINT_CONFLICT", None),
    ("HXV35_R22", "policy_tree_fingerprint", "POLICY_TREE_FINGERPRINT_CONFLICT", None),
    ("HXV36_R22", "subtree_fingerprint", "SUBTREE_FINGERPRINT_CONFLICT", None),
    ("HXV37_R23", "source_registry_fingerprint", "SOURCE_REGISTRY_FINGERPRINT_CONFLICT", None),
    ("HXV38_R21", "inventory_review_fp", "INVENTORY_FINGERPRINT_CONFLICT", None),
    ("HXV39_condition", "review_condition", "REVIEW_CONDITION_MISMATCH", None),
    ("HXV39_root", "review_root", "REVIEW_RULE_ROOT_MISMATCH", None),
    ("HXV41_R26_benefit", "benefit_version", "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "benefit_snapshot.source_bindings[0].document_version"),
    ("HXV41_R26_envelope", "envelope_version", "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "policy_envelope.source_bindings[0].document_version"),
    ("HXV42_R29", "source_content", "HISTORICAL_ARTIFACT_SOURCE_CONTENT_MISMATCH", "entry.source_documents[0].artifact.sha256"),
    ("HXV43_R24", "implementation", "HISTORICAL_ARTIFACT_IMPLEMENTATION_MISMATCH", "coverage_review_context.implementation_fingerprint"),
)


@pytest.mark.parametrize("scenario,kind,prefix,field", CROSS_CASES, ids=[row[0] + "_CROSS_VALIDATED" for row in CROSS_CASES])
def test_all_six_real_loaders_succeed_but_cross_validator_rejects(scenario, kind, prefix, field):
    kwargs = restore_specs(negative_spec(kind))
    assert_error(kwargs, prefix, field)


def test_entry_source_document_version_is_cross_validated():
    def edit(body):
        entry = body["entries"][0]
        entry["source_bindings"][0]["document_version"] = "d0002"
        entry["source_documents"][0]["binding"]["document_version"] = "d0002"
    kwargs = restore_specs(synthetic.definitions(), edit_review=edit)
    assert_error(kwargs, "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "entry.source_documents[0].binding.document_version")


def test_hxv56_none_content_hash_does_not_hide_later_known_conflict():
    spec = synthetic.definitions()
    rewrite_registry(spec, lambda body: body["sources"][0].update(content_sha256=None))
    spec["source_bytes"]["SYNTH-B"] = b"a different second original TEST_ONLY\n"
    kwargs = restore_specs(spec)
    assert_error(kwargs, "HISTORICAL_ARTIFACT_SOURCE_CONTENT_MISMATCH", "entry.source_documents[1].artifact.sha256")


def test_hxv39_same_axes_successful_calls_mixed_binding_review_are_rejected(inputs):
    other = restore_specs(synthetic.definitions(swap_bindings=True))
    assert validate(inputs) is None and validate(other) is None
    assert inputs["expected_acceptance"].coverage_inventory_fingerprint == other["expected_acceptance"].coverage_inventory_fingerprint
    assert_error({**inputs, "eligibility_coverage": other["eligibility_coverage"]}, "REVIEW_RULE_ROOT_MISMATCH")


def test_hxv40_same_tree_different_envelope_domain_is_rejected(inputs):
    other = restore_specs(synthetic.definitions(title="다른 합성 제목"))
    assert validate(other) is None
    assert inputs["expected_acceptance"].coverage_policy_tree_fingerprint == other["expected_acceptance"].coverage_policy_tree_fingerprint
    assert_error({**other, "policy_envelope": inputs["policy_envelope"]}, "HISTORICAL_ARTIFACT_POLICY_MISMATCH", "selected_policy.fingerprint")


def retarget_context(context, **changes):
    nested = {key: value for key, value in changes.items() if key in ("policy_id", "scope")}
    return replace(context, **changes,
        inventory_reviews=tuple(replace(row, **nested) for row in context.inventory_reviews),
        implementation_reviews=tuple(replace(row, **nested) for row in context.implementation_reviews))


@pytest.mark.parametrize("argument,axis,field", (
    ("benefit_snapshot", "policy", "benefit_snapshot.policy_id"),
    ("eligibility_coverage", "policy", "eligibility_coverage.inventory.policy_id"),
    ("policy_envelope", "policy", "policy_envelope.policy_id"),
    ("coverage_review_context", "policy", "coverage_review_context.policy_id"),
    ("benefit_snapshot", "scope", "benefit_snapshot.scope"),
    ("eligibility_coverage", "scope", "eligibility_coverage.inventory.scope"),
    ("coverage_review_context", "scope", "coverage_review_context.scope"),
    ("policy_envelope", "edition", "policy_envelope.edition_id"),
))
def test_hxv25_standalone_valid_objects_with_mixed_identity(inputs, argument, axis, field):
    value = inputs[argument]
    change = {"policy_id": "SYNTH-OTHER"} if axis == "policy" else {"scope": ApplicabilityScope("2026", 4)}
    if argument == "eligibility_coverage": value = replace(value, inventory=replace(value.inventory, **change))
    elif argument == "coverage_review_context": value = retarget_context(value, **change)
    elif argument == "policy_envelope":
        value = replace(value, edition_id="2025") if axis == "edition" else replace(value, policy=replace(value.policy, **change))
    else: value = replace(value, **change)
    assert_error({**inputs, argument: value}, "HISTORICAL_ARTIFACT_IDENTITY_MISMATCH", field)


@pytest.mark.parametrize("argument", ("benefit_snapshot", "policy_envelope", "coverage_review_context", "dataset_manifest"))
def test_hxv26_standalone_mixed_dataset_returns_fixed_field(inputs, argument):
    kwargs = {**inputs, argument: replace(inputs[argument], dataset_version="SYNTH-D2")}
    assert_error(kwargs, "HISTORICAL_ARTIFACT_DATASET_MISMATCH", argument + ".dataset_version")


def test_hxv26_actual_other_revision_benefit_is_not_accepted(inputs):
    other = restore_specs(synthetic.definitions(2))
    assert_error({**inputs, "benefit_snapshot": other["benefit_snapshot"]}, "HISTORICAL_ARTIFACT_DATASET_MISMATCH", "benefit_snapshot.dataset_version")


def test_p1_policy_then_scope_then_edition_comparison_order(inputs):
    scope = ApplicabilityScope("2026", 4)
    kwargs = {**inputs,
        "benefit_snapshot": replace(inputs["benefit_snapshot"], policy_id="SYNTH-OTHER", scope=scope),
        "eligibility_coverage": replace(inputs["eligibility_coverage"], inventory=replace(inputs["eligibility_coverage"].inventory, policy_id="SYNTH-OTHER", scope=scope)),
        "policy_envelope": replace(inputs["policy_envelope"], policy=replace(inputs["policy_envelope"].policy, policy_id="SYNTH-OTHER"), edition_id="2025"),
        "coverage_review_context": retarget_context(inputs["coverage_review_context"], policy_id="SYNTH-OTHER", scope=scope)}
    for argument in ("benefit_snapshot", "eligibility_coverage", "policy_envelope", "coverage_review_context"):
        field = argument + (".inventory.policy_id" if argument == "eligibility_coverage" else ".policy_id")
        assert_error(kwargs, "HISTORICAL_ARTIFACT_IDENTITY_MISMATCH", field)
        value = kwargs[argument]
        if argument == "eligibility_coverage": value = replace(value, inventory=replace(value.inventory, policy_id=synthetic.POLICY_ID))
        elif argument == "policy_envelope": value = replace(value, policy=replace(value.policy, policy_id=synthetic.POLICY_ID))
        elif argument == "coverage_review_context": value = retarget_context(value, policy_id=synthetic.POLICY_ID)
        else: value = replace(value, policy_id=synthetic.POLICY_ID)
        kwargs[argument] = value
    for argument in ("benefit_snapshot", "eligibility_coverage", "coverage_review_context"):
        field = argument + (".inventory.scope" if argument == "eligibility_coverage" else ".scope")
        assert_error(kwargs, "HISTORICAL_ARTIFACT_IDENTITY_MISMATCH", field)
        value = kwargs[argument]
        original_scope = inputs["expected_acceptance"].scope
        if argument == "eligibility_coverage": value = replace(value, inventory=replace(value.inventory, scope=original_scope))
        elif argument == "coverage_review_context": value = retarget_context(value, scope=original_scope)
        else: value = replace(value, scope=original_scope)
        kwargs[argument] = value
    assert_error(kwargs, "HISTORICAL_ARTIFACT_IDENTITY_MISMATCH", "policy_envelope.edition_id")


def test_p2_multiple_bad_datasets_follow_contract_order(inputs):
    kwargs = {**inputs, **{name: replace(inputs[name], dataset_version="SYNTH-D2")
        for name in ("benefit_snapshot", "policy_envelope", "coverage_review_context", "dataset_manifest")}}
    for name in ("benefit_snapshot", "policy_envelope", "coverage_review_context", "dataset_manifest"):
        assert_error(kwargs, "HISTORICAL_ARTIFACT_DATASET_MISMATCH", name + ".dataset_version")
        kwargs[name] = inputs[name]
    assert validate(kwargs) is None


def test_complete_registry_can_include_unused_sources_with_declared_versions():
    spec = synthetic.definitions()
    def edit(body):
        extra = deepcopy(body["sources"][0])
        extra.update(source_document_id="SYNTH-C", content_sha256=None)
        body["sources"].append(extra)
    rewrite_registry(spec, edit)
    kwargs = restore_specs(spec)
    assert len(kwargs["source_registry"].sources) == len(kwargs["dataset_manifest"].source_versions) == 3
    assert len(kwargs["benefit_snapshot"].source_bindings) == 2
    assert validate(kwargs) is None


@pytest.mark.parametrize("kind", ("policy_path", "policy_sha", "registry_path", "registry_sha", "membership", "edition", "rule", "registry_fp"))
def test_hxv29_manifest_binding_is_delegated_with_original_prefix(inputs, kind):
    manifest = inputs["dataset_manifest"]
    selected = manifest.policy_versions[0]
    suffix = {"membership": "POLICY_MEMBERSHIP", "edition": "EDITION", "rule": "RULE_VERSION",
              "registry_fp": "REGISTRY_FINGERPRINT"}.get(kind)
    if kind.startswith("policy_"):
        ref = replace(selected.artifact, **({"path": "synthetic/other-policy.json"} if kind.endswith("path") else {"sha256": synthetic.sha(b"other policy bytes")}))
        manifest = replace(manifest, policy_versions=(replace(selected, artifact=ref),))
        suffix = "POLICY_REFERENCE"
    elif kind.startswith("registry_") and kind != "registry_fp":
        reference = manifest.source_registry
        ref = replace(reference.artifact, **({"path": "synthetic/other-registry.json"} if kind.endswith("path") else {"sha256": synthetic.sha(b"other registry bytes")}))
        manifest = replace(manifest, source_registry=replace(reference, artifact=ref))
        suffix = "REGISTRY_REFERENCE"
    elif kind == "registry_fp": manifest = replace(manifest, source_registry=replace(manifest.source_registry, fingerprint=synthetic.sha(b"other registry domain")))
    else:
        change = {"policy_id": "SYNTH-OTHER"} if kind == "membership" else {"edition_id": "2025"} if kind == "edition" else {"rule_version": "r0003"}
        manifest = replace(manifest, policy_versions=(replace(selected, **change),))
    assert_error({**inputs, "dataset_manifest": manifest}, "HISTORICAL_DATASET_MANIFEST_" + suffix + "_MISMATCH")


def test_selected_policy_rule_compares_actual_envelope(inputs):
    envelope = replace(inputs["policy_envelope"], policy=replace(inputs["policy_envelope"].policy, rule_version="r0003"))
    assert_error({**inputs, "policy_envelope": envelope}, "HISTORICAL_ARTIFACT_POLICY_MISMATCH", "selected_policy.rule_version")


@pytest.mark.parametrize("axis", ("benefit", "context", "manifest"))
def test_hxv30_standalone_registry_fingerprint_comparison_order(inputs, axis):
    registry = replace(inputs["source_registry"], sources=(replace(inputs["source_registry"].sources[0], title="다른 합성 문서"), inputs["source_registry"].sources[1]))
    fingerprint = fingerprint_source_registry(registry)
    kwargs = {**inputs, "source_registry": registry}
    if axis in ("context", "manifest"):
        kwargs["benefit_snapshot"] = replace(inputs["benefit_snapshot"], source_registry_fingerprint=fingerprint)
    if axis == "manifest":
        kwargs["coverage_review_context"] = replace(inputs["coverage_review_context"], source_registry_fingerprint=fingerprint)
    field = {"benefit": "benefit_snapshot.source_registry_fingerprint", "context": "coverage_review_context.source_registry_fingerprint",
             "manifest": "dataset_manifest.source_registry.fingerprint"}[axis]
    assert_error(kwargs, "HISTORICAL_ARTIFACT_REGISTRY_MISMATCH", field)


def test_source_lookup_error_is_not_wrapped(inputs, monkeypatch):
    sentinel = SourceValidationError("SOURCE_NOT_FOUND", "source_document_id")
    def fail(*args, **kwargs): raise sentinel
    monkeypatch.setattr(SourceRegistry, "get_source", fail)
    assert assert_error(inputs, "SOURCE_NOT_FOUND") is sentinel


@pytest.mark.parametrize("kind", ("manifest", "registry"))
def test_duplicate_source_ids_are_already_guarded_by_models(inputs, kind):
    with pytest.raises(PolicyDataError) as caught:
        if kind == "manifest":
            binding = inputs["dataset_manifest"].source_versions[0]
            replace(inputs["dataset_manifest"], source_versions=(binding, replace(binding, document_version="d0002")))
        else:
            document = inputs["source_registry"].sources[0]
            replace(inputs["source_registry"], sources=(document, replace(document, document_version="d0002")))
    assert caught.value.code == ("DUPLICATE_MANIFEST_SOURCE" if kind == "manifest" else "DUPLICATE_SOURCE_ID")


@pytest.mark.parametrize("stage", ("P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"))
def test_hxv49_54_multiple_error_precedence(inputs, monkeypatch, stage):
    if stage == "P0":
        kwargs = {**inputs, "expected_acceptance": replace(inputs["expected_acceptance"]), "source_registry": None}
        prefix, field, absent = "INVALID_HISTORICAL_ARTIFACT_RELATIONSHIP_INPUT", "source_registry", "_selected_entry"
    elif stage == "P1":
        kwargs = {**inputs, "benefit_snapshot": replace(inputs["benefit_snapshot"], policy_id="SYNTH-OTHER", dataset_version="OTHER")}
        prefix, field, absent = "HISTORICAL_ARTIFACT_IDENTITY_MISMATCH", "benefit_snapshot.policy_id", "_bind_manifest"
    elif stage == "P2":
        kwargs = restore_specs(negative_spec("root"))
        kwargs["benefit_snapshot"] = replace(kwargs["benefit_snapshot"], dataset_version="SYNTH-D2")
        prefix, field, absent = "HISTORICAL_ARTIFACT_DATASET_MISMATCH", "benefit_snapshot.dataset_version", "_bind_manifest"
    elif stage == "P3":
        spec = negative_spec("envelope_fp")
        spec["bodies"]["manifest"]["manifest"]["source_versions"][0]["document_version"] = "d0002"
        kwargs = restore_specs(spec)
        prefix, field, absent = "HISTORICAL_ARTIFACT_POLICY_MISMATCH", "selected_policy.fingerprint", "fingerprint_source_registry"
    elif stage == "P4":
        spec = negative_spec("source_version")
        spec["implementation_bytes"] = b"different implementation\n"
        kwargs = restore_specs(spec)
        prefix, field, absent = "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "dataset_manifest.source_versions", "_analyze_coverage_structure"
    elif stage == "P5":
        spec = negative_spec("implementation")
        spec["source_bytes"]["SYNTH-A"] = b"different original\n"
        kwargs = restore_specs(spec)
        prefix, field, absent = "HISTORICAL_ARTIFACT_IMPLEMENTATION_MISMATCH", "coverage_review_context.implementation_fingerprint", "_analyze_coverage_structure"
    elif stage == "P6":
        spec = negative_spec("root")
        spec["bodies"]["coverage"]["coverage"]["bindings"][0]["implementation_review_ref"] = "IMPL-MISSING"
        kwargs = restore_specs(spec)
        prefix, field, absent = "RULE_ROOT_NOT_FOUND", None, "fingerprint_condition_inventory"
    else:
        spec = negative_spec("inventory_review_fp")
        current_review(spec)["rule_root_id"] = "RULE_STUDENT"
        kwargs = restore_specs(spec)
        prefix, field, absent = "INVENTORY_FINGERPRINT_CONFLICT", None, "_match_implementation_review"
    calls, _ = watch(monkeypatch)
    assert_error(kwargs, prefix, field)
    assert absent not in [name for name, _, _ in calls]


@pytest.mark.parametrize("inventory_ref", (None, "INV-OLD"))
def test_hxv55_normal_missing_stale_do_not_hide_later_conflict(monkeypatch, inventory_ref):
    spec = synthetic.definitions()
    coverage = spec["bodies"]["coverage"]["coverage"]
    coverage["inventory"]["completeness_review_ref"] = inventory_ref
    coverage["bindings"][0]["implementation_review_ref"] = "IMPL-OLD"
    current_review(spec, ref="IMPL-COND_STUDENT")["subtree_fingerprint"] = synthetic.sha(b"conflicting student subtree")
    kwargs = restore_specs(spec)
    calls, outcomes = watch(monkeypatch)
    assert_error(kwargs, "SUBTREE_FINGERPRINT_CONFLICT")
    impl = [args[1].condition_id for name, args, _ in calls if name == "_match_implementation_review"]
    assert impl == ["COND_AGE", "COND_STUDENT"]
    assert next(value for name, value in outcomes if name == "_match_implementation_review").status is ReviewMatchStatus.STALE


def test_canonical_binding_order_and_all_fingerprints_before_matchers(monkeypatch):
    spec = synthetic.definitions()
    spec["bodies"]["coverage"]["coverage"]["bindings"].reverse()
    current_review(spec)["subtree_fingerprint"] = synthetic.sha(b"age conflict")
    current_review(spec, ref="IMPL-COND_STUDENT")["subtree_fingerprint"] = synthetic.sha(b"student conflict")
    kwargs = restore_specs(spec)
    calls, _ = watch(monkeypatch)
    assert_error(kwargs, "SUBTREE_FINGERPRINT_CONFLICT")
    assert [args[1].condition_id for name, args, _ in calls if name == "_match_implementation_review"] == ["COND_AGE"]
    names = [name for name, _, _ in calls]
    assert names.count("fingerprint_rule_subtree") == 2
    assert max(i for i, name in enumerate(names) if name == "fingerprint_rule_subtree") < names.index("_match_inventory_review")


def test_partial_coverage_remains_partial_without_new_full_gate():
    spec = synthetic.definitions()
    spec["bodies"]["coverage"]["coverage"]["bindings"].pop()
    kwargs = restore_specs(spec)
    assert validate(kwargs) is None
    assert len(kwargs["eligibility_coverage"].bindings) == 1


def snapshot(kwargs):
    return synthetic.canonical({key: value.to_dict() for key, value in kwargs.items()})


@pytest.mark.parametrize("kind", ("normal", "conflict"))
def test_hxv12_one_hundred_replays_preserve_every_input(kind):
    kwargs = restore_specs(synthetic.definitions() if kind == "normal" else negative_spec("source_version"))
    before = snapshot(kwargs)
    originals = dict(kwargs)
    for _ in range(100):
        if kind == "normal": assert validate(kwargs) is None
        else: assert_error(kwargs, "HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH", "dataset_manifest.source_versions")
        assert all(kwargs[key] is value for key, value in originals.items())
        assert next(entry for entry in kwargs["artifact"].entries if entry.acceptance is kwargs["expected_acceptance"]).acceptance is kwargs["expected_acceptance"]
    assert snapshot(kwargs) == before


def test_hxv48_not_observable_equal_objects_are_not_raw_origin_certificates(inputs):
    kwargs = {**inputs, **{key: replace(inputs[key]) for key in ARGUMENTS[2:]}}
    assert all(kwargs[key] is not inputs[key] and kwargs[key] == inputs[key] for key in ARGUMENTS[2:])
    assert validate(kwargs) is None  # NOT_OBSERVABLE: 값 일치는 raw decoder 실행 증명이 아니다.


def test_pure_call_does_not_use_io_environment_clock_network_or_process(inputs, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError("forbidden side effect")
    class NoEnvironment(dict):
        def __getitem__(self, key): return forbidden()
        def get(self, *args): return forbidden()
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(io, "open", forbidden)
        patch.setattr(os, "environ", NoEnvironment())
        patch.setattr(os, "getenv", forbidden)
        patch.setattr(time, "time", forbidden)
        patch.setattr(time, "monotonic", forbidden)
        patch.setattr(random, "random", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(subprocess, "run", forbidden)
        result = validate(inputs)
    assert result is None


def test_one_internal_function_without_new_runtime_models_or_forbidden_dependencies():
    tree = ast.parse(inspect.getsource(domain))
    assert [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))] == ["_validate_historical_artifact_relationships"]
    assert not any(isinstance(node, (ast.ClassDef, ast.Global, ast.Nonlocal)) for node in ast.walk(tree))
    forbidden = {"os", "pathlib", "io", "time", "datetime", "random", "socket", "subprocess", "zipfile", "requests"}
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert imported.isdisjoint(forbidden)
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert calls.isdisjoint({"open", "eval", "exec", "__import__", "validate_dataset_manifest", "evaluate_eligibility_coverage"})
