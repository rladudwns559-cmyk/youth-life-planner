"""M2.71: 합성 원본의 A~C 연결만 검증한다. production 사용 적격성은 판정하지 않는다."""

from dataclasses import replace
from datetime import date, datetime, timezone
from enum import Enum
import hashlib
from io import BytesIO
import json
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.models import ENGINE_VERSION, RuleGroup, walk_nodes
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, ApplicabilityScope, ArtifactReference, BenefitAcceptanceStatus,
    BenefitAmountType, BenefitMedium, BenefitPaymentCadence, BenefitRestriction, BenefitSnapshot,
    ConditionBinding, ConditionInventory, ConditionRequirement, CoverageReviewContext, DatasetManifest,
    EligibilityCoverage, ImplementationBindingReview, InventoryCompletenessReview,
    ManifestValidationError, PolicyBenefitAcceptance, PolicyEditionReference, PolicyEnvelope,
    RequiredCondition, SourceBinding, SourceRegistryReference,
    fingerprint_benefit_snapshot, fingerprint_condition_inventory, fingerprint_policy_envelope,
    fingerprint_policy_tree, fingerprint_rule_subtree, fingerprint_source_registry,
    load_acceptance_review_artifact_bytes, load_historical_benefit_snapshot_bytes,
    load_historical_coverage_review_context_bytes, load_historical_dataset_manifest_bytes,
    load_historical_eligibility_coverage_bytes, load_historical_policy_envelope_bytes,
    load_historical_source_registry_bytes, parse_policy_envelope, validate_dataset_manifest,
)
from backend.policy_engine.policy_data.coverage_review_matching import (
    _match_implementation_review, _match_inventory_review,
)
from backend.policy_engine.policy_data.coverage_review_resolution import (
    _resolve_implementation_review, _resolve_inventory_review,
)
from backend.policy_engine.policy_data.coverage_structure import _analyze_coverage_structure
from backend.policy_engine.sources import (
    SourceRegistry, SourceValidationError, parse_source_registry, validate_evidence_refs,
)


LOADERS = {
    "benefit": load_historical_benefit_snapshot_bytes,
    "coverage": load_historical_eligibility_coverage_bytes,
    "envelope": load_historical_policy_envelope_bytes,
    "reviews": load_historical_coverage_review_context_bytes,
    "manifest": load_historical_dataset_manifest_bytes,
    "registry": load_historical_source_registry_bytes,
}
REF_FIELDS = dict(zip(LOADERS, (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref",
)))
TYPES = (BenefitSnapshot, EligibilityCoverage, PolicyEnvelope, CoverageReviewContext, DatasetManifest, SourceRegistry)
BYTE_ERRORS = dict(zip(LOADERS, (
    "HISTORICAL_BENEFIT_BYTES_MISMATCH", "HISTORICAL_COVERAGE_BYTES_MISMATCH",
    "HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", "HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH",
    "HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH", "HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH",
)))
POLICY_ID = "SYNTH-M271"
DAY = date(2026, 1, 2)
CLAIMS = ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")
# 기본 합성 fixture 저작 완료 시 고정한 raw H. 기존 GV/BV golden과는 별개다.
SYNTHETIC_RAW_SHA256 = {
    "benefit": "ee2dd9425eeaa2f461a20619b293deb0deae6b399961f93e7b54b5c819ab5ea6",
    "coverage": "555eef751ec54ae40cfd3a9bed52b32d49f77532f12f454f79e664918fec6710",
    "envelope": "0efa33b9a64d3efa0109547f3d57e89c310601a81109badbb4c4456cd0b1c7a5",
    "reviews": "1b9d2693d1c850bf5cc104522fbfe7b4401f42fbf4a302ebfb51775c74c0d685",
    "manifest": "7494bfebfed624062b3018c2fb105e15a2d731a0f9a64f0d852b291a11ba76ce",
    "registry": "678c3c241b133eaddf12d67d3ecf07b86de6c9b8d4a749e3f98eea1b0f55e892",
}
SYNTHETIC_REVIEW_SHA256 = "a62a90341c403c0837b6b22714c2373c04fd735e91904dc21df98e487bc0732a"


def canonical(body):
    """합성 저작 전용 encoder. 소비 loader의 private helper를 사용하지 않는다."""
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", errors="strict")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def reference(path, raw):
    return {"path": path, "sha256": sha(raw)}


def binding_dict(binding):
    return {"source_document_id": binding.source_document_id, "document_version": binding.document_version}


def synthetic_zip():
    # 실행 코드가 없는 증거용 ZIP. 날짜/압축 방식을 고정해 실제 bytes만 해시한다.
    stream = BytesIO()
    info = ZipInfo("TEST_ONLY.txt", date_time=(2026, 1, 2, 0, 0, 0))
    info.create_system = 3  # 운영체제에 따라 ZIP 중앙 디렉터리 bytes가 바뀌지 않게 고정한다.
    info.compress_type = ZIP_STORED
    info.external_attr = 0o600 << 16
    with ZipFile(stream, "w") as archive:
        archive.writestr(info, b"M2.71 SYNTHETIC ONLY; NO EXECUTABLE ENGINE; NO PRODUCTION CLAIM\n")
    return stream.getvalue()


def definitions(revision=1, *, swap_bindings=False, title="합성 정책"):
    """의존성 DAG를 저작한다. 소비 시점의 기대 H를 반환값으로부터 만들지 않는다."""
    dataset = f"SYNTH-D{revision}"
    version = revision + 1
    scope = ApplicabilityScope("2026", 3)
    source_bytes = {source_id: f"M2.71 TEST_ONLY {source_id} original revision {revision}\n".encode()
                    for source_id in ("SYNTH-A", "SYNTH-B")}
    implementation_bytes = synthetic_zip()
    review_evidence = b"M2.71 TEST_ONLY review metadata; no real human approval\n"
    review_evidence_ref = "synthetic-review:sha256:" + sha(review_evidence)
    bindings = tuple(SourceBinding(key, "d0001") for key in source_bytes)
    sources = []
    for source_id, original in source_bytes.items():
        sources.append({
            "source_document_id": source_id, "document_version": "d0001", "source_type": "OFFICIAL_NOTICE",
            "issuer": "SYNTHETIC TEST ISSUER", "title": "공식 자료가 아닌 합성 근거",
            "official_url": f"https://synthetic.example.invalid/{source_id}",
            "publication_date": "2026-01-01", "verified_at": None, "verification_status": "DRAFT",
            "status": "ACTIVE", "content_sha256": sha(original),
            "locators": [{"locator_id": locator, "section": locator, "meaning_summary": "합성 정의",
                          "applicable_policy_ids": [POLICY_ID], "verified_at": None,
                          "verification_status": "DRAFT", "status": "ACTIVE"}
                         for locator in ("age", "student", "benefit")],
        })
    registry = parse_source_registry({"schema_version": "source-registry-1.0", "sources": sources})
    registry_fp = fingerprint_source_registry(registry)
    evidence = lambda locator: tuple(f"{key}#{locator}" for key in source_bytes)
    envelope_body = {
        "schema_version": "policy-data-1.0", "rule_schema_version": "m1.1", "policy_id": POLICY_ID,
        "policy": {"policy_id": POLICY_ID, "policy_name": title, "rule_version": f"r{version:04d}",
                   "synthetic": True, "test_only": True,
                   "root": {"kind": "group", "rule_id": "ROOT", "operator": "ALL", "children": [
                       {"kind": "rule", "rule_type": "atomic", "rule_id": "RULE_AGE", "field": "age",
                        "operator": "gte", "value": 19, "evidence_refs": list(evidence("age"))},
                       {"kind": "rule", "rule_type": "atomic", "rule_id": "RULE_STUDENT",
                        "field": "student_status", "operator": "eq", "value": True,
                        "evidence_refs": list(evidence("student"))}]}},
        "edition_id": "2026", "jurisdiction": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
        "category": "YOUTH_SUPPORT", "dataset_version": dataset, "evaluation_scope": "CONDITION_SLICE",
        "coverage": {"included_rule_ids": ["RULE_AGE", "RULE_STUDENT"],
                     "excluded_conditions": ["합성 범위 밖의 조건"]},
        "source_bindings": [binding_dict(item) for item in bindings], "verification_status": "DRAFT",
        "last_verified_at": None, "lifecycle_status": "ACTIVE", "synthetic": True, "test_only": True,
    }
    envelope = parse_policy_envelope(envelope_body)
    inventory = ConditionInventory(POLICY_ID, scope, f"i{version:04d}", (
        RequiredCondition("COND_AGE", "합성 나이 조건", ConditionRequirement.REQUIRED, evidence("age")),
        RequiredCondition("COND_STUDENT", "합성 학생 조건", ConditionRequirement.REQUIRED, evidence("student")),
    ), "INV-CURRENT")
    roots = ("RULE_STUDENT", "RULE_AGE") if swap_bindings else ("RULE_AGE", "RULE_STUDENT")
    coverage = EligibilityCoverage(inventory, tuple(
        ConditionBinding(condition.condition_id, root_id, f"IMPL-{condition.condition_id}")
        for condition, root_id in zip(inventory.conditions, roots)))
    benefit = BenefitSnapshot(
        policy_id=POLICY_ID, scope=scope, benefit_id="SYNTH-BENEFIT", benefit_version=f"b{version:04d}",
        amount_type=BenefitAmountType.FIXED, amount_krw=100000 * revision, amount_description=None,
        payment_cadence=BenefitPaymentCadence.MONTHLY, benefit_medium=BenefitMedium.UNRESTRICTED_CASH,
        restriction=BenefitRestriction.UNRESTRICTED, restriction_details=None, applicable_months=("2026-09",),
        benefit_evidence_refs=evidence("benefit"), source_bindings=bindings, dataset_version=dataset,
        source_registry_fingerprint=registry_fp,
    )
    inv_fp = fingerprint_condition_inventory(inventory)
    tree_fp = fingerprint_policy_tree(envelope.policy)
    inv_review = InventoryCompletenessReview(
        "INV-CURRENT", POLICY_ID, scope, inventory.inventory_version, inv_fp, dataset, registry_fp,
        DAY, review_evidence_ref)
    old_inventory = replace(inventory, inventory_version="i0001")
    old_inv_review = replace(inv_review, review_ref="INV-OLD", inventory_version="i0001",
                             inventory_fingerprint=fingerprint_condition_inventory(old_inventory))
    impl_reviews = []
    for binding in coverage.bindings:
        node = next(node for node in walk_nodes(envelope.root) if node.rule_id == binding.rule_root_id)
        impl_reviews.append(ImplementationBindingReview(
            binding.implementation_review_ref, POLICY_ID, scope, binding.condition_id, binding.rule_root_id,
            inventory.inventory_version, inv_fp, envelope.rule_version, tree_fp, fingerprint_rule_subtree(node),
            dataset, registry_fp, sha(implementation_bytes), DAY, review_evidence_ref))
    old_impl = replace(impl_reviews[0], review_ref="IMPL-OLD", inventory_version="i0001",
                       inventory_fingerprint=fingerprint_condition_inventory(old_inventory),
                       rule_version="r0001", policy_tree_fingerprint=fingerprint_policy_tree(
                           replace(envelope.policy, rule_version="r0001")))
    reviews = CoverageReviewContext(POLICY_ID, scope, dataset, registry_fp, sha(implementation_bytes),
                                    (old_inv_review, inv_review), (impl_reviews[1], old_impl, impl_reviews[0]))
    bodies = {
        "benefit": {"schema_version": "historical-benefit-snapshot-1.0", "snapshot": benefit.to_dict()},
        "coverage": {"schema_version": "historical-eligibility-coverage-1.0", "coverage": coverage.to_dict()},
        "envelope": envelope_body,
        "reviews": {"schema_version": "historical-coverage-review-context-1.0", "review_context": reviews.to_dict()},
        "registry": registry.to_dict(),
    }
    paths = {name: f"synthetic/r{revision}/{name}.json" for name in LOADERS}
    manifest = DatasetManifest(
        schema_version="dataset-manifest-1.0", dataset_id="SYNTH-M271-DATASET", dataset_version=dataset,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), freshness_max_age_days=7,
        engine_version=ENGINE_VERSION, engine_artifact_sha256=sha(implementation_bytes),
        policy_versions=(PolicyEditionReference(policy_id=POLICY_ID, edition_id="2026",
            rule_version=envelope.rule_version,
            artifact=ArtifactReference(**reference(paths["envelope"], canonical(envelope_body))),
            fingerprint=fingerprint_policy_envelope(envelope)),),
        source_registry=SourceRegistryReference(
            artifact=ArtifactReference(**reference(paths["registry"], canonical(bodies["registry"]))),
            fingerprint=registry_fp), source_versions=bindings,
    )
    bodies["manifest"] = {"schema_version": "historical-dataset-manifest-1.0", "manifest": manifest.to_dict()}
    values = {
        "acceptance_ref": f"SYNTH-ACCEPT-{revision}", "acceptance_version": f"a{revision:04d}",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": POLICY_ID, "scope": scope,
        "benefit_id": benefit.benefit_id, "coverage_inventory_version": inventory.inventory_version,
        "coverage_inventory_fingerprint": inv_fp, "coverage_rule_version": envelope.rule_version,
        "coverage_policy_tree_fingerprint": tree_fp, "coverage_dataset_version": dataset,
        "coverage_source_registry_fingerprint": registry_fp, "coverage_implementation_fingerprint": sha(implementation_bytes),
        "benefit_version": benefit.benefit_version, "benefit_fingerprint": fingerprint_benefit_snapshot(benefit),
        "benefit_dataset_version": dataset, "benefit_source_registry_fingerprint": registry_fp,
        "reviewed_at": DAY, "valid_until": date(2026, 12, 31), "revokes_acceptance_ref": None,
    }
    return {"bodies": bodies, "values": values, "paths": paths, "source_bytes": source_bytes,
            "implementation_bytes": implementation_bytes, "review_evidence": review_evidence,
            "authored": dict(zip(LOADERS, (benefit, coverage, envelope, reviews, manifest, registry)))}


def raw20(values):
    result = {}
    for name, value in values.items():
        assert name != "review_artifact_ref"  # 최종 A를 생성할 때만 이 필드를 추가한다.
        if isinstance(value, Enum):
            value = value.value
        elif type(value) is ApplicabilityScope:
            value = value.to_dict()
        elif type(value) is date:
            value = value.isoformat()
        result[name] = value
    assert len(result) == 20
    return result


def prepare(*specs):
    """합성 저작 단계에서 H를 확정하고, 소비 API에는 같은 원본 A/R를 전달한다."""
    rows, raws = [], []
    for spec in specs:
        raw = {name: canonical(spec["bodies"][name]) for name in LOADERS}
        refs = {REF_FIELDS[name]: reference(spec["paths"][name], raw[name]) for name in LOADERS}
        refs["implementation_artifact_ref"] = reference("synthetic/implementation.zip", spec["implementation_bytes"])
        sources = [binding_dict(item) for item in spec["authored"]["benefit"].source_bindings]
        rows.append({
            "acceptance": raw20(spec["values"]), **refs,
            "claim_evidence": [{"claim": claim, "evidence_refs": list(spec["authored"]["benefit"].benefit_evidence_refs)}
                               for claim in CLAIMS],
            "source_bindings": sources,
            "source_documents": [{"binding": binding,
                "artifact": reference(f"synthetic/{binding['source_document_id']}.txt",
                                      spec["source_bytes"][binding["source_document_id"]])} for binding in sources],
            "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
            "review_note": "M2.71 TEST_ONLY; 실제 검토 또는 사용 승인 아님", "manual_scenario_ids": ["M271-SYNTH"],
        })
        raws.append(raw)
    review_raw = canonical({"schema_version": "benefit-acceptance-review-1.0", "entries": rows})
    root_ref = "acceptance-review:sha256:" + sha(review_raw)
    originals = tuple(PolicyBenefitAcceptance(**spec["values"], review_artifact_ref=root_ref) for spec in specs)
    artifact = load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=originals)
    assert type(artifact) is AcceptanceReviewArtifact
    assert all(entry.acceptance is original for entry, original in zip(artifact.entries, originals))
    return artifact, originals, tuple(raws), review_raw


def restore(artifact, original, raws):
    # 각 로더에 같은 원본 객체를 전달한다.
    return {name: loader(raw_bytes=raws[name], artifact=artifact, expected_acceptance=original)
            for name, loader in LOADERS.items()}


@pytest.fixture
def coherent():
    spec = definitions()
    artifact, originals, raws, review_raw = prepare(spec)
    return spec, artifact, originals[0], raws[0], review_raw


def test_same_originals_and_exact_domain_return_types(coherent, monkeypatch):
    spec, artifact, original, raws, _ = coherent
    calls = []
    for name, real_loader in tuple(LOADERS.items()):
        def observed(*, raw_bytes, artifact, expected_acceptance, _name=name, _real=real_loader):
            calls.append((_name, raw_bytes, artifact, expected_acceptance))
            return _real(raw_bytes=raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance)
        monkeypatch.setitem(LOADERS, name, observed)
    restored = restore(artifact, original, raws)
    assert len(calls) == 6
    assert artifact.entries[0].acceptance is original
    for (name, raw, actual_artifact, actual_original), expected_type in zip(calls, TYPES):
        assert actual_artifact is artifact and actual_original is original and raw is raws[name]
        assert type(restored[name]) is expected_type
        assert restored[name] == spec["authored"][name]


def test_content_addressed_review_raw20_and_acyclic_references(coherent):
    spec, artifact, original, raws, review_raw = coherent
    body = json.loads(review_raw)
    entry = artifact.entries[0]
    assert body["entries"][0]["acceptance"] == raw20(spec["values"])
    assert len(body["entries"][0]["acceptance"]) == 20
    assert "review_artifact_ref" not in body["entries"][0]["acceptance"]
    assert original.review_artifact_ref == artifact.review_artifact_ref == "acceptance-review:sha256:" + sha(review_raw)
    assert sha(review_raw) == SYNTHETIC_REVIEW_SHA256
    assert canonical(body) == review_raw
    for name, raw in raws.items():
        ref = getattr(entry, REF_FIELDS[name])
        assert ref.path == spec["paths"][name] and ref.sha256 == sha(raw)
        assert original.review_artifact_ref.encode() not in raw
    assert entry.implementation_artifact_ref.sha256 == sha(spec["implementation_bytes"])
    for source in entry.source_documents:
        assert source.artifact.sha256 == sha(spec["source_bytes"][source.binding.source_document_id])


@pytest.mark.parametrize("name", LOADERS)
def test_six_independently_pinned_raw_hashes(coherent, name):
    _, artifact, _, raws, _ = coherent
    assert sha(raws[name]) == SYNTHETIC_RAW_SHA256[name]
    assert getattr(artifact.entries[0], REF_FIELDS[name]).sha256 == SYNTHETIC_RAW_SHA256[name]


def test_direct_domain_bindings_and_cross_dataset_registry_identity(coherent):
    _, artifact, original, raws, _ = coherent
    d = restore(artifact, original, raws)
    b, c, p, r, m, s = (d[name] for name in LOADERS)
    assert b.policy_id == c.inventory.policy_id == p.policy_id == r.policy_id == original.policy_id
    assert b.scope == c.inventory.scope == r.scope == original.scope
    assert b.benefit_id == original.benefit_id and b.benefit_version == original.benefit_version
    assert fingerprint_benefit_snapshot(b) == original.benefit_fingerprint
    assert c.inventory.inventory_version == original.coverage_inventory_version
    assert fingerprint_condition_inventory(c.inventory) == original.coverage_inventory_fingerprint
    assert p.edition_id == original.scope.edition_id  # 연도 일치는 Q3 적용의 증명이 아니다.
    assert p.rule_version == original.coverage_rule_version
    assert fingerprint_policy_tree(p.policy) == original.coverage_policy_tree_fingerprint
    assert b.dataset_version == p.dataset_version == r.dataset_version == m.dataset_version
    assert m.dataset_version == original.benefit_dataset_version == original.coverage_dataset_version
    # Coverage에는 dataset_version 필드가 없다.
    registry_fp = fingerprint_source_registry(s)
    assert registry_fp == b.source_registry_fingerprint == r.source_registry_fingerprint == m.source_registry.fingerprint
    assert registry_fp == original.benefit_source_registry_fingerprint == original.coverage_source_registry_fingerprint
    assert r.implementation_fingerprint == original.coverage_implementation_fingerprint
    selected = next(ref for ref in m.policy_versions if ref.policy_id == original.policy_id)
    assert (selected.edition_id, selected.rule_version) == (p.edition_id, p.rule_version)
    assert selected.artifact == artifact.entries[0].policy_envelope_ref
    assert m.source_registry.artifact == artifact.entries[0].source_registry_ref
    assert selected.fingerprint == fingerprint_policy_envelope(p)
    assert selected.fingerprint != fingerprint_policy_tree(p.policy)
    assert b.source_bindings == p.source_bindings == artifact.entries[0].source_bindings == m.source_versions


def test_existing_manifest_validator_on_complete_synthetic_inputs(coherent):
    spec, artifact, original, raws, _ = coherent
    d = restore(artifact, original, raws)
    assert validate_dataset_manifest(d["manifest"], (d["envelope"],), d["registry"]) is None
    assert d["manifest"].engine_artifact_sha256 == artifact.entries[0].implementation_artifact_ref.sha256
    assert d["reviews"].implementation_fingerprint == sha(spec["implementation_bytes"])


def test_multiple_evidence_and_explicit_historical_review_selection(coherent):
    spec, artifact, original, raws, _ = coherent
    d = restore(artifact, original, raws)
    c, p, r, s = (d[name] for name in ("coverage", "envelope", "reviews", "registry"))
    missing, resolved, unmapped = _analyze_coverage_structure(c, p.policy)
    assert missing == unmapped == () and len(resolved) == 2
    assert len(r.inventory_reviews) == 2 and len(r.implementation_reviews) == 3
    inv_review = _resolve_inventory_review(r, c.inventory.completeness_review_ref)
    assert inv_review is r.inventory_reviews[1] and inv_review.inventory_version == c.inventory.inventory_version
    assert inv_review.inventory_fingerprint == fingerprint_condition_inventory(c.inventory)
    for binding, node in resolved:
        assert node is next(n for n in walk_nodes(p.root) if n.rule_id == binding.rule_root_id)
        review = _resolve_implementation_review(r, binding.implementation_review_ref)
        assert any(review is item for item in r.implementation_reviews)
        assert review.rule_root_id == node.rule_id and review.condition_id == binding.condition_id
        assert review.subtree_fingerprint == fingerprint_rule_subtree(node)
        assert review.policy_tree_fingerprint == fingerprint_policy_tree(p.policy)
        assert review.review_artifact_ref == "synthetic-review:sha256:" + sha(spec["review_evidence"])
    refs_groups = [d["benefit"].benefit_evidence_refs]
    refs_groups += [condition.evidence_refs for condition in c.inventory.conditions]
    refs_groups += [node.evidence_refs for node in walk_nodes(p.root) if type(node) is not RuleGroup]
    refs_groups += [claim.evidence_refs for claim in artifact.entries[0].claim_evidence]
    for refs in refs_groups:
        assert len(refs) == 2 and len(validate_evidence_refs(refs, s)) == 2
        assert all(original.policy_id in item.applicable_policy_ids for item in validate_evidence_refs(refs, s))
    for binding in d["benefit"].source_bindings + p.source_bindings + d["manifest"].source_versions:
        assert s.get_source(binding.source_document_id).document_version == binding.document_version
    for source in artifact.entries[0].source_documents:
        assert s.get_source(source.binding.source_document_id).content_sha256 == source.artifact.sha256


def test_one_hundred_replays_preserve_inputs_and_values(coherent):
    spec, artifact, original, raws, review_raw = coherent
    before = canonical({"artifact": artifact.to_dict(), "original": original.to_dict(),
                        "bodies": spec["bodies"], "authored": {k: v.to_dict() for k, v in spec["authored"].items()}})
    raw_before = dict(raws)
    first = restore(artifact, original, raws)
    expected = {key: value.to_dict() for key, value in first.items()}
    for _ in range(100):
        actual = restore(artifact, original, raws)
        assert actual == first
        assert {key: value.to_dict() for key, value in actual.items()} == expected
        assert validate_dataset_manifest(actual["manifest"], (actual["envelope"],), actual["registry"]) is None
        assert artifact.entries[0].acceptance is original
    assert raws == raw_before and all(raws[key] is raw_before[key] for key in raws)
    assert review_raw == canonical(json.loads(review_raw))
    assert before == canonical({"artifact": artifact.to_dict(), "original": original.to_dict(),
        "bodies": spec["bodies"], "authored": {k: v.to_dict() for k, v in spec["authored"].items()}})


@pytest.mark.parametrize("reverse", (False, True))
def test_multi_entry_explicit_revision_not_tuple_position(reverse):
    specs = (definitions(), definitions(2))
    if reverse:
        specs = specs[::-1]
    artifact, originals, raw_sets, _ = prepare(*specs)
    for index, (spec, original, raws) in enumerate(zip(specs, originals, raw_sets)):
        assert artifact.entries[index].acceptance is original
        d = restore(artifact, original, raws)
        assert d == spec["authored"]
        assert d["benefit"].benefit_version == original.benefit_version
        assert d["manifest"].dataset_version == original.coverage_dataset_version


@pytest.mark.parametrize("name", LOADERS)
def test_other_revision_or_entry_bytes_are_rejected(name):
    artifact, originals, raw_sets, _ = prepare(definitions(), definitions(2))
    with pytest.raises(PolicyDataError, match="^" + BYTE_ERRORS[name] + ":"):
        LOADERS[name](raw_bytes=raw_sets[1][name], artifact=artifact, expected_acceptance=originals[0])


@pytest.mark.parametrize("name", LOADERS)
def test_wrong_raw_sha_rejected_before_domain_parsing(coherent, name):
    _, artifact, original, raws, _ = coherent
    with pytest.raises(PolicyDataError, match="^" + BYTE_ERRORS[name] + ":"):
        LOADERS[name](raw_bytes=raws[name] + b" ", artifact=artifact, expected_acceptance=original)


@pytest.mark.parametrize("name", LOADERS)
def test_equal_but_reconstructed_acceptance_is_not_original(coherent, name):
    _, artifact, original, raws, _ = coherent
    copied = replace(original)
    assert copied == original and copied is not original
    with pytest.raises(PolicyDataError, match="entry.acceptance"):
        LOADERS[name](raw_bytes=raws[name], artifact=artifact, expected_acceptance=copied)


@pytest.mark.parametrize("name", LOADERS)
def test_artifact_from_another_call_cannot_be_paired_with_original(coherent, name):
    _, _, original, raws, _ = coherent
    other_artifact, _, _, _ = prepare(definitions(2))
    with pytest.raises(PolicyDataError, match="artifact.review_artifact_ref"):
        LOADERS[name](raw_bytes=raws[name], artifact=other_artifact, expected_acceptance=original)


def set_at(body, path, value):
    for item in path[:-1]:
        body = body[item]
    body[path[-1]] = value


# 변경된 bytes의 H를 R에 고정해 raw hash 검사를 통과시킨 뒤 domain binding을 검증한다.
# A의 기대 내용은 유지한다. 동일 버전의 내용 모순도 이 경계에서 거부되어야 한다.
BINDING_MISMATCHES = (
    ("benefit", ("snapshot", "benefit_version"), "b0003", "HISTORICAL_BENEFIT_IDENTITY_MISMATCH"),
    ("benefit", ("snapshot", "amount_krw"), 123456, "HISTORICAL_BENEFIT_FINGERPRINT_MISMATCH"),
    ("benefit", ("snapshot", "dataset_version"), "SYNTH-D2", "HISTORICAL_BENEFIT_DATASET_MISMATCH"),
    ("benefit", ("snapshot", "source_registry_fingerprint"), sha(b"other-registry"), "HISTORICAL_BENEFIT_REGISTRY_MISMATCH"),
    ("benefit", ("snapshot", "scope", "quarter"), 4, "HISTORICAL_BENEFIT_IDENTITY_MISMATCH"),
    ("coverage", ("coverage", "inventory", "inventory_version"), "i0003", "HISTORICAL_COVERAGE_INVENTORY_VERSION_MISMATCH"),
    ("coverage", ("coverage", "inventory", "conditions", 0, "meaning"), "다른 의미", "HISTORICAL_COVERAGE_INVENTORY_FINGERPRINT_MISMATCH"),
    ("coverage", ("coverage", "inventory", "scope", "quarter"), 4, "HISTORICAL_COVERAGE_IDENTITY_MISMATCH"),
    ("envelope", ("policy", "rule_version"), "r0003", "HISTORICAL_POLICY_ENVELOPE_RULE_VERSION_MISMATCH"),
    ("envelope", ("policy", "root", "children", 0, "value"), 20, "HISTORICAL_POLICY_ENVELOPE_TREE_FINGERPRINT_MISMATCH"),
    ("envelope", ("dataset_version",), "SYNTH-D2", "HISTORICAL_POLICY_ENVELOPE_DATASET_MISMATCH"),
    ("reviews", ("review_context", "dataset_version"), "SYNTH-D2", "HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATASET_MISMATCH"),
    ("reviews", ("review_context", "source_registry_fingerprint"), sha(b"other-registry"), "HISTORICAL_COVERAGE_REVIEW_CONTEXT_REGISTRY_FINGERPRINT_MISMATCH"),
    ("reviews", ("review_context", "implementation_fingerprint"), sha(b"other-implementation"), "HISTORICAL_COVERAGE_REVIEW_CONTEXT_IMPLEMENTATION_FINGERPRINT_MISMATCH"),
    ("manifest", ("manifest", "dataset_version"), "SYNTH-D2", "HISTORICAL_DATASET_MANIFEST_DATASET_MISMATCH"),
    ("manifest", ("manifest", "policy_versions", 0, "policy_id"), "SYNTH-OTHER", "HISTORICAL_DATASET_MANIFEST_POLICY_MEMBERSHIP_MISMATCH"),
    ("manifest", ("manifest", "policy_versions", 0, "edition_id"), "2025", "HISTORICAL_DATASET_MANIFEST_EDITION_MISMATCH"),
    ("manifest", ("manifest", "policy_versions", 0, "rule_version"), "r0003", "HISTORICAL_DATASET_MANIFEST_RULE_VERSION_MISMATCH"),
    ("manifest", ("manifest", "source_registry", "fingerprint"), sha(b"other registry domain"), "HISTORICAL_DATASET_MANIFEST_REGISTRY_FINGERPRINT_MISMATCH"),
    ("manifest", ("manifest", "source_registry", "artifact", "path"), "synthetic/other-registry.json", "HISTORICAL_DATASET_MANIFEST_REGISTRY_REFERENCE_MISMATCH"),
    ("manifest", ("manifest", "source_registry", "artifact", "sha256"), sha(b"other-registry-bytes"), "HISTORICAL_DATASET_MANIFEST_REGISTRY_REFERENCE_MISMATCH"),
    ("registry", ("sources", 0, "title"), "같은 문서 버전의 다른 내용", "HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH"),
)


@pytest.mark.parametrize("name,path,value,error", BINDING_MISMATCHES)
def test_resealed_hash_still_rejects_domain_binding_mismatch(name, path, value, error):
    spec = definitions()
    set_at(spec["bodies"][name], path, value)
    artifact, originals, raw_sets, _ = prepare(spec)
    assert sha(raw_sets[0][name]) == getattr(artifact.entries[0], REF_FIELDS[name]).sha256
    with pytest.raises(PolicyDataError, match="^" + error + ":"):
        LOADERS[name](raw_bytes=raw_sets[0][name], artifact=artifact, expected_acceptance=originals[0])


def test_different_review_scope_resealed_with_all_nested_records():
    spec = definitions()
    context = spec["bodies"]["reviews"]["review_context"]
    context["scope"]["quarter"] = 4
    for row in context["inventory_reviews"] + context["implementation_reviews"]:
        row["scope"]["quarter"] = 4
    artifact, originals, raws, _ = prepare(spec)
    with pytest.raises(PolicyDataError, match="^HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCOPE_MISMATCH:"):
        LOADERS["reviews"](raw_bytes=raws[0]["reviews"], artifact=artifact, expected_acceptance=originals[0])


@pytest.mark.parametrize("kind,error", (
    ("policy", "HISTORICAL_DATASET_MANIFEST_POLICY_REFERENCE_MISMATCH"),
    ("registry", "HISTORICAL_DATASET_MANIFEST_REGISTRY_REFERENCE_MISMATCH"),
))
def test_other_entry_reference_in_manifest_is_rejected(kind, error):
    specs = (definitions(), definitions(2))
    artifact, _, _, _ = prepare(*specs)
    other = artifact.entries[1]
    ref = other.policy_envelope_ref if kind == "policy" else other.source_registry_ref
    manifest = specs[0]["bodies"]["manifest"]["manifest"]
    target = manifest["policy_versions"][0] if kind == "policy" else manifest["source_registry"]
    target["artifact"] = {"path": ref.path, "sha256": ref.sha256}
    artifact, originals, raws, _ = prepare(*specs)
    with pytest.raises(PolicyDataError, match="^" + error + ":"):
        LOADERS["manifest"](raw_bytes=raws[0]["manifest"], artifact=artifact, expected_acceptance=originals[0])


@pytest.mark.parametrize("kind", ("source_versions", "envelope_fingerprint", "engine_version"))
def test_all_six_can_succeed_but_existing_manifest_validator_rejects(kind):
    spec = definitions()
    body = spec["bodies"]["manifest"]["manifest"]
    if kind == "source_versions":
        body["source_versions"][0]["document_version"] = "d0002"
        expected = "SOURCE_REFERENCE_SET_MISMATCH"
    elif kind == "envelope_fingerprint":
        body["policy_versions"][0]["fingerprint"] = fingerprint_policy_envelope(definitions(title="다른 제목")["authored"]["envelope"])
        expected = "POLICY_FINGERPRINT_MISMATCH"
    else:
        body["engine_version"] = "historical-other-engine"
        expected = "ENGINE_COMPATIBILITY_MISMATCH"
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    with pytest.raises(ManifestValidationError) as caught:
        validate_dataset_manifest(d["manifest"], (d["envelope"],), d["registry"])
    assert caught.value.code == expected


def test_all_six_can_succeed_but_manifest_engine_artifact_disagrees():
    spec = definitions()
    spec["bodies"]["manifest"]["manifest"]["engine_artifact_sha256"] = sha(b"different synthetic ZIP")
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    # 기존 집합 검증 함수도 구현 Artifact의 raw hash 대응은 검사하지 않는다.
    assert validate_dataset_manifest(d["manifest"], (d["envelope"],), d["registry"]) is None
    with pytest.raises(AssertionError, match="implementation artifact"):
        assert d["manifest"].engine_artifact_sha256 == artifact.entries[0].implementation_artifact_ref.sha256, "implementation artifact"


@pytest.mark.parametrize("kind", ("root", "inventory_ref", "implementation_ref"))
def test_all_six_can_succeed_but_explicit_binding_resolution_rejects(kind):
    spec = definitions()
    coverage = spec["bodies"]["coverage"]["coverage"]
    if kind == "root":
        coverage["bindings"][0]["rule_root_id"] = "RULE_MISSING"
    elif kind == "inventory_ref":
        coverage["inventory"]["completeness_review_ref"] = "INV-MISSING"
    else:
        coverage["bindings"][0]["implementation_review_ref"] = "IMPL-MISSING"
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    c, p, r = (d[name] for name in ("coverage", "envelope", "reviews"))
    with pytest.raises(PolicyDataError, match="^(RULE_ROOT_NOT_FOUND|REVIEW_REF_NOT_FOUND):"):
        if kind == "root":
            _analyze_coverage_structure(c, p.policy)
        elif kind == "inventory_ref":
            _resolve_inventory_review(r, c.inventory.completeness_review_ref)
        else:
            _resolve_implementation_review(r, c.bindings[0].implementation_review_ref)


@pytest.mark.parametrize("field,error", (
    ("inventory_fingerprint", "INVENTORY_FINGERPRINT_CONFLICT"),
    ("policy_tree_fingerprint", "POLICY_TREE_FINGERPRINT_CONFLICT"),
    ("subtree_fingerprint", "SUBTREE_FINGERPRINT_CONFLICT"),
    ("source_registry_fingerprint", "SOURCE_REGISTRY_FINGERPRINT_CONFLICT"),
))
def test_same_version_review_conflict_needs_existing_matcher(field, error):
    spec = definitions()
    rows = spec["bodies"]["reviews"]["review_context"]["implementation_reviews"]
    selected = next(row for row in rows if row["review_ref"] == "IMPL-COND_AGE")
    selected[field] = sha(b"synthetic contradictory review metadata")
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    c, p, r = (d[name] for name in ("coverage", "envelope", "reviews"))
    _, resolved, _ = _analyze_coverage_structure(c, p.policy)
    binding, node = resolved[0]
    with pytest.raises(PolicyDataError, match="^" + error + ":"):
        _match_implementation_review(c.inventory, binding, r,
            current_inventory_fingerprint=fingerprint_condition_inventory(c.inventory),
            current_rule_version=p.rule_version, current_policy_tree_fingerprint=fingerprint_policy_tree(p.policy),
            current_subtree_fingerprint=fingerprint_rule_subtree(node))


def test_same_version_inventory_review_conflict_needs_existing_matcher():
    spec = definitions()
    spec["bodies"]["reviews"]["review_context"]["inventory_reviews"][1]["inventory_fingerprint"] = sha(b"other inventory review")
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    with pytest.raises(PolicyDataError, match="^INVENTORY_FINGERPRINT_CONFLICT:"):
        _match_inventory_review(d["coverage"].inventory, d["reviews"],
            current_inventory_fingerprint=fingerprint_condition_inventory(d["coverage"].inventory))


def test_different_successful_calls_mixed_revisions_fail_test_only_dataset_comparison():
    a1, records1, raw1, _ = prepare(definitions())
    a2, records2, raw2, _ = prepare(definitions(2))
    d1 = restore(a1, records1[0], raw1[0])
    d2 = restore(a2, records2[0], raw2[0])
    mixed = {**d1, "benefit": d2["benefit"]}
    with pytest.raises(AssertionError, match="mixed dataset"):
        assert mixed["benefit"].dataset_version == mixed["manifest"].dataset_version, "mixed dataset"


def test_same_axes_successful_calls_mixed_binding_review_fail_existing_matcher():
    a1, records1, raw1, _ = prepare(definitions())
    a2, records2, raw2, _ = prepare(definitions(swap_bindings=True))
    d1 = restore(a1, records1[0], raw1[0])
    d2 = restore(a2, records2[0], raw2[0])
    # Inventory와 Tree가 같아도 Binding은 Inventory 지문에 포함되지 않는다.
    assert records1[0].coverage_inventory_fingerprint == records2[0].coverage_inventory_fingerprint
    assert records1[0].coverage_policy_tree_fingerprint == records2[0].coverage_policy_tree_fingerprint
    assert d1["coverage"].bindings != d2["coverage"].bindings
    _, resolved, _ = _analyze_coverage_structure(d2["coverage"], d2["envelope"].policy)
    for binding, node in resolved:
        selected = _resolve_implementation_review(d2["reviews"], binding.implementation_review_ref)
        assert selected.rule_root_id == node.rule_id  # 각 묶음 내부의 명시적 연결은 일치한다.
    binding, node = resolved[0]
    with pytest.raises(PolicyDataError, match="^REVIEW_RULE_ROOT_MISMATCH:"):
        _match_implementation_review(d2["coverage"].inventory, binding, d1["reviews"],
            current_inventory_fingerprint=fingerprint_condition_inventory(d2["coverage"].inventory),
            current_rule_version=d2["envelope"].rule_version,
            current_policy_tree_fingerprint=fingerprint_policy_tree(d2["envelope"].policy),
            current_subtree_fingerprint=fingerprint_rule_subtree(node))


def test_same_tree_different_envelope_domain_mixed_across_calls_rejected_by_existing_validator():
    a1, records1, raw1, _ = prepare(definitions())
    a2, records2, raw2, _ = prepare(definitions(title="다른 합성 정책 제목"))
    d1, d2 = restore(a1, records1[0], raw1[0]), restore(a2, records2[0], raw2[0])
    assert records1[0].coverage_policy_tree_fingerprint == records2[0].coverage_policy_tree_fingerprint
    with pytest.raises(ManifestValidationError) as caught:
        validate_dataset_manifest(d2["manifest"], (d1["envelope"],), d1["registry"])
    assert caught.value.code == "POLICY_FINGERPRINT_MISMATCH"


def test_resealed_benefit_source_version_not_enforced_against_restored_registry():
    spec = definitions()
    benefit = replace(spec["authored"]["benefit"], source_bindings=(SourceBinding("SYNTH-A", "d0002"), SourceBinding("SYNTH-B", "d0001")))
    spec["authored"]["benefit"] = benefit
    spec["bodies"]["benefit"]["snapshot"] = benefit.to_dict()
    spec["values"]["benefit_fingerprint"] = fingerprint_benefit_snapshot(benefit)
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    with pytest.raises(AssertionError, match="benefit source version"):
        for binding in d["benefit"].source_bindings:
            assert d["registry"].get_source(binding.source_document_id).document_version == binding.document_version, "benefit source version"


def test_legal_but_missing_benefit_locator_needs_existing_source_resolution():
    spec = definitions()
    benefit = replace(spec["authored"]["benefit"], benefit_evidence_refs=("SYNTH-A#missing", "SYNTH-B#benefit"))
    spec["authored"]["benefit"] = benefit
    spec["bodies"]["benefit"]["snapshot"] = benefit.to_dict()
    spec["values"]["benefit_fingerprint"] = fingerprint_benefit_snapshot(benefit)
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    with pytest.raises(SourceValidationError) as caught:
        validate_evidence_refs(d["benefit"].benefit_evidence_refs, d["registry"])
    assert caught.value.code == "LOCATOR_NOT_FOUND"


def test_review_source_original_hash_not_automatically_bound_to_registry_content_sha():
    spec = definitions()
    # 원본 bytes와 Entry의 H는 일치하지만 Registry는 이전 원본의 지문을 보유한다.
    spec["source_bytes"]["SYNTH-A"] = b"a different TEST_ONLY source original\n"
    artifact, originals, raws, _ = prepare(spec)
    d = restore(artifact, originals[0], raws[0])
    source = artifact.entries[0].source_documents[0]
    assert source.artifact.sha256 == sha(spec["source_bytes"][source.binding.source_document_id])
    with pytest.raises(AssertionError, match="source original"):
        assert d["registry"].get_source(source.binding.source_document_id).content_sha256 == source.artifact.sha256, "source original"
