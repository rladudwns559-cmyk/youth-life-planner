"""합성/test_only manifest의 구조·지문·메모리 일관성만 검증한다. 배포를 발행하지 않는다."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from backend.policy_engine import EvaluationContext, Field, Operator, Policy, PolicyRule, UserProfile, evaluate_policy_tree
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.evaluation_inputs import EvaluationFacts, PolicyReferenceContext
from backend.policy_engine.facts import RegionRef, RegistrationSource, ResidentRegistrationFact
from backend.policy_engine.models import ENGINE_VERSION
from backend.policy_engine.policy_data import (
    ArtifactReference, DatasetManifest, ManifestValidationError, PolicyCoverage, PolicyEditionReference,
    PolicyVerificationStatus, SourceBinding, SourceRegistryReference,
    fingerprint_policy_envelope, fingerprint_source_registry,
    load_policy_envelope, validate_dataset_manifest,
)
from backend.policy_engine.sources import SourceRegistry, SourceStatus, SourceValidationError, load_source_registry


SYNTHETIC = True
TEST_ONLY = True
DATA = Path(__file__).resolve().parents[1] / "data/synthetic"
DAY = date(2026, 1, 10)
CREATED = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
ENGINE_HASH = hashlib.sha256(b"synthetic-test-only-engine-artifact").hexdigest()


def envelope():
    return load_policy_envelope(DATA / "policy_envelope_m11.json")


def registry():
    return load_source_registry(DATA / "sources.json")


def policy_ref(item, **changes):
    if item.policy_id == "SYNTH-POLICY-001":
        artifact_bytes = (DATA / "policy_envelope_m11.json").read_bytes()
    else:
        # 두 번째 객체는 메모리 전용 합성 artifact의 값 bytes다. 실제 release 파일이 아니다.
        artifact_bytes = json.dumps(item.to_dict(), sort_keys=True).encode("utf-8")
    values = dict(policy_id=item.policy_id, edition_id=item.edition_id, rule_version=item.rule_version,
                  artifact=ArtifactReference(f"policies/{item.policy_id}__{item.edition_id}.json",
                                             hashlib.sha256(artifact_bytes).hexdigest()),
                  fingerprint=fingerprint_policy_envelope(item))
    return PolicyEditionReference(**(values | changes))


def manifest(envelopes=None, sources=None, **changes):
    envelopes = (envelope(),) if envelopes is None else envelopes
    sources = registry() if sources is None else sources
    source_sha = hashlib.sha256((DATA / "sources.json").read_bytes()).hexdigest()
    values = dict(
        schema_version="dataset-manifest-1.0", dataset_id="synthetic-youth-test-only",
        dataset_version="synthetic-edition-001", created_at=CREATED, freshness_max_age_days=7,
        engine_version=ENGINE_VERSION, engine_artifact_sha256=ENGINE_HASH,
        policy_versions=tuple(policy_ref(item) for item in envelopes),
        source_registry=SourceRegistryReference(artifact=ArtifactReference("sources.json", source_sha),
                                               fingerprint=fingerprint_source_registry(sources)),
        source_versions=tuple(SourceBinding(item.source_document_id, item.document_version) for item in sources.sources),
    )
    return DatasetManifest(**(values | changes))


def second_envelope():
    first = envelope()
    leaf = PolicyRule("SYNTH-SECOND-ATOM", Field.AGE, Operator.GTE, 19,
                      evidence_refs=("SYNTH-SOURCE-002#eligibility-residence",))
    return replace(first, policy=Policy("SYNTH-POLICY-002", "합성 test_only 두 번째 정책", "r0001", leaf),
                   coverage=PolicyCoverage((leaf.rule_id,), ("합성 제외 조건",)),
                   source_bindings=(SourceBinding("SYNTH-SOURCE-002", "d0001"),), last_verified_at=None)


def test_valid_manifest_from_existing_synthetic_fixtures_and_no_object_ownership():
    item, sources = envelope(), registry()
    release = manifest((item,), sources)
    assert validate_dataset_manifest(release, (item,), sources) is None
    assert release.policy_versions[0].policy_id == item.policy_id
    assert release.source_versions == (SourceBinding("SYNTH-SOURCE-001", "d0001"), SourceBinding("SYNTH-SOURCE-002", "d0001"))
    assert not {field.name for field in fields(release)}.intersection({"envelopes", "registry", "user_input", "results"})
    assert release.review_manifest is None  # 검토가 끝났다고 가장하지 않는다.
    assert release == manifest((item,), sources)
    assert release.fingerprint() == manifest((item,), sources).fingerprint()


def test_multiple_policies_exact_set_and_order_independent_validation():
    items = (envelope(), second_envelope())
    sources = registry()
    release = manifest(items, sources)
    assert validate_dataset_manifest(release, items, sources) is None
    assert validate_dataset_manifest(release, tuple(reversed(items)), sources) is None
    reordered = replace(release, policy_versions=tuple(reversed(release.policy_versions)),
                        source_versions=tuple(reversed(release.source_versions)))
    assert reordered.fingerprint() == release.fingerprint()


@pytest.mark.parametrize("field", ["dataset_id", "dataset_version", "engine_version"])
@pytest.mark.parametrize("value", [None, "", " ", 1, False, [], {}])
def test_identity_and_version_are_nonempty_exact_strings(field, value):
    with pytest.raises(ManifestValidationError, match="INVALID_MANIFEST_TEXT"):
        manifest(**{field: value})


@pytest.mark.parametrize("value", [None, 1, True, "", "dataset-manifest-2.0", "dataset-manifest-1.0 "])
def test_explicit_supported_manifest_schema(value):
    with pytest.raises(ManifestValidationError, match="UNSUPPORTED_MANIFEST_SCHEMA"):
        manifest(schema_version=value)


@pytest.mark.parametrize("value", [None, date(2026, 10, 20), "2026-10-20", datetime(2026, 10, 20), 0, True])
def test_creation_time_requires_exact_timezone_aware_datetime(value):
    with pytest.raises(ManifestValidationError, match="INVALID_MANIFEST_TIMESTAMP"):
        manifest(created_at=value)


def test_same_timestamp_in_different_offsets_has_same_canonical_fingerprint():
    release = manifest()
    offset = CREATED.astimezone(timezone(timedelta(hours=9)))
    assert release.fingerprint() == replace(release, created_at=offset).fingerprint()
    assert release.created_at == CREATED


@pytest.mark.parametrize("value", [None, 0, -1, True, 7.0, "7"])
def test_freshness_metadata_is_typed_but_not_enforced(value):
    with pytest.raises(ManifestValidationError, match="INVALID_FRESHNESS_METADATA"):
        manifest(freshness_max_age_days=value)


@pytest.mark.parametrize("value", [None, "", "a" * 63, "A" * 64, "g" * 64, 0, True])
@pytest.mark.parametrize("target", ["artifact", "policy", "registry", "engine"])
def test_hashes_have_strict_sha256_hex_format(target, value):
    with pytest.raises(ManifestValidationError, match="INVALID_MANIFEST_HASH"):
        if target == "artifact":
            ArtifactReference("sources.json", value)
        elif target == "policy":
            policy_ref(envelope(), fingerprint=value)
        elif target == "registry":
            SourceRegistryReference(artifact=ArtifactReference("sources.json", "a" * 64), fingerprint=value)
        else:
            manifest(engine_artifact_sha256=value)


@pytest.mark.parametrize("path", [None, "", "/sources.json", "../sources.json", "a/../sources.json", "./sources.json", "a//file.json", "C:/file.json", "a\\file.json", "file.json:stream", " sources.json", "a/\x00file"])
def test_artifact_paths_are_release_relative_without_io(path):
    with pytest.raises(ManifestValidationError, match="INVALID_ARTIFACT_PATH"):
        ArtifactReference(path, "a" * 64)


@pytest.mark.parametrize("field", ["policy_versions", "source_versions"])
@pytest.mark.parametrize("value", [None, (), [], (None,), ("reference",)])
def test_reference_collections_are_nonempty_typed_tuples(field, value):
    with pytest.raises(ManifestValidationError):
        manifest(**{field: value})


@pytest.mark.parametrize("edition", ["2026", "2027"])
def test_same_policy_cannot_be_selected_twice_even_for_different_editions(edition):
    ref = policy_ref(envelope())
    with pytest.raises(ManifestValidationError, match="DUPLICATE_MANIFEST_POLICY"):
        manifest(policy_versions=(ref, replace(ref, edition_id=edition)))


def test_duplicate_source_id_with_same_or_other_version_is_error():
    for version in ("d0001", "d0002"):
        with pytest.raises(ManifestValidationError, match="DUPLICATE_MANIFEST_SOURCE"):
            manifest(source_versions=(SourceBinding("SYNTH-SOURCE-001", "d0001"), SourceBinding("SYNTH-SOURCE-001", version)))


def test_same_artifact_path_cannot_identify_two_different_roles():
    ref = policy_ref(envelope(), artifact=ArtifactReference("sources.json", "a" * 64))
    with pytest.raises(ManifestValidationError, match="DUPLICATE_ARTIFACT_PATH"):
        manifest(policy_versions=(ref,))


@pytest.mark.parametrize(("target", "field", "value"), [
    ("policy", "schema_version", "policy-data-2.0"), ("policy", "schema_version", None),
    ("policy", "rule_schema_version", "m1.0"), ("registry", "schema_version", "source-registry-2.0"),
    ("registry", "schema_version", True), ("policy", "artifact", None), ("registry", "artifact", {}),
])
def test_reference_types_and_schema_compatibility(target, field, value):
    with pytest.raises(PolicyDataError):
        if target == "policy":
            policy_ref(envelope(), **{field: value})
        else:
            SourceRegistryReference(**(dict(artifact=ArtifactReference("sources.json", "a" * 64), fingerprint="a" * 64) | {field: value}))


@pytest.mark.parametrize(("field", "value"), [("policy_id", ""), ("policy_id", 1), ("edition_id", "2026-Q1"), ("edition_id", None), ("rule_version", "r0000"), ("rule_version", "v1")])
def test_policy_reference_identifiers_and_versions(field, value):
    with pytest.raises(PolicyDataError):
        policy_ref(envelope(), **{field: value})


def test_registry_and_review_reference_types():
    with pytest.raises(ManifestValidationError, match="INVALID_REGISTRY_REFERENCE"):
        manifest(source_registry=None)
    with pytest.raises(ManifestValidationError, match="INVALID_ARTIFACT_REFERENCE"):
        manifest(review_manifest={})
    ref = ArtifactReference("reviews.json", "b" * 64)
    assert manifest(review_manifest=ref).review_manifest is ref


def test_policy_set_missing_extra_duplicate_and_edition_mismatch():
    first, second, sources = envelope(), second_envelope(), registry()
    release = manifest((first,), sources)
    for items, code in [
        ((), "POLICY_REFERENCE_SET_MISMATCH"), ((second,), "POLICY_REFERENCE_SET_MISMATCH"),
        ((first, second), "POLICY_REFERENCE_SET_MISMATCH"), ((first, first), "DUPLICATE_DATASET_POLICY"),
        ((replace(first, edition_id="2027"),), "POLICY_REFERENCE_MISMATCH"),
    ]:
        with pytest.raises(ManifestValidationError, match=code):
            validate_dataset_manifest(release, items, sources)


def test_rule_version_dataset_version_and_engine_mismatch():
    item, sources = envelope(), registry()
    release = manifest((item,), sources)
    with pytest.raises(ManifestValidationError, match="POLICY_REFERENCE_MISMATCH"):
        validate_dataset_manifest(release, (replace(item, policy=replace(item.policy, rule_version="r0002")),), sources)
    with pytest.raises(ManifestValidationError, match="DATASET_VERSION_MISMATCH"):
        validate_dataset_manifest(release, (replace(item, dataset_version="synthetic-edition-002"),), sources)
    with pytest.raises(ManifestValidationError, match="ENGINE_COMPATIBILITY_MISMATCH"):
        validate_dataset_manifest(replace(release, engine_version="unknown-engine"), (item,), sources)


def test_source_version_set_and_unchanged_version_content_tampering_detected():
    item, sources = envelope(), registry()
    release = manifest((item,), sources)
    changed_version = SourceRegistry((replace(sources.sources[0], document_version="d0002"), sources.sources[1]))
    with pytest.raises(ManifestValidationError, match="SOURCE_REFERENCE_SET_MISMATCH"):
        validate_dataset_manifest(release, (item,), changed_version)
    changed_content = SourceRegistry((replace(sources.sources[0], title="Synthetic changed test_only title"), sources.sources[1]))
    with pytest.raises(ManifestValidationError, match="REGISTRY_FINGERPRINT_MISMATCH"):
        validate_dataset_manifest(release, (item,), changed_content)


def test_policy_content_change_without_version_change_detected():
    item, sources = envelope(), registry()
    changed = replace(item, policy=replace(item.policy, policy_name="합성 변경 이름"))
    with pytest.raises(ManifestValidationError, match="POLICY_FINGERPRINT_MISMATCH"):
        validate_dataset_manifest(manifest((item,), sources), (changed,), sources)


@pytest.mark.parametrize("case", ["missing-source", "missing-locator", "withdrawn", "superseded", "binding-version"])
def test_existing_source_validation_is_reused_for_broken_evidence(case):
    item, sources = envelope(), registry()
    first, second = sources.sources
    if case == "missing-source":
        first = replace(first, source_document_id="SYNTH-SOURCE-OTHER")
    elif case == "missing-locator":
        first = replace(first, locators=first.locators[:1])
    elif case in ("withdrawn", "superseded"):
        first = replace(first, status=SourceStatus(case.upper()))
    else:
        first = replace(first, document_version="d0002")
    sources = SourceRegistry((first, second))
    release = manifest((item,), sources)
    with pytest.raises(PolicyDataError):
        validate_dataset_manifest(release, (item,), sources)


def test_global_rule_id_uniqueness_without_changing_individual_policy_validation():
    first, second = envelope(), second_envelope()
    leaf = replace(second.root, rule_id=first.root.children[0].rule_id)
    second = replace(second, policy=replace(second.policy, root=leaf),
                     coverage=PolicyCoverage((leaf.rule_id,), second.coverage.excluded_conditions))
    sources = registry()
    with pytest.raises(ManifestValidationError, match="DUPLICATE_DATASET_RULE"):
        validate_dataset_manifest(manifest((first, second), sources), (first, second), sources)


@pytest.mark.parametrize("field", ["edition_id", "rule_version"])
def test_manifest_fingerprint_changes_when_policy_reference_changes(field):
    release = manifest()
    value = "2027" if field == "edition_id" else "r0002"
    changed = replace(release, policy_versions=(replace(release.policy_versions[0], **{field: value}),))
    assert changed.fingerprint() != release.fingerprint()


def test_source_release_and_engine_pins_change_manifest_fingerprint():
    release = manifest()
    changed = replace(release, source_versions=(SourceBinding("SYNTH-SOURCE-001", "d0002"), release.source_versions[1]))
    assert changed.fingerprint() != release.fingerprint()
    changed = replace(release, source_registry=replace(release.source_registry, fingerprint="0" * 64))
    assert changed.fingerprint() != release.fingerprint()
    assert replace(release, engine_artifact_sha256="0" * 64).fingerprint() != release.fingerprint()
    assert replace(release, dataset_version="synthetic-edition-002").fingerprint() != release.fingerprint()


def test_registry_order_is_not_semantic_but_rule_child_order_is_retained():
    sources = registry()
    first = replace(sources.sources[0], locators=tuple(reversed(sources.sources[0].locators)))
    reordered = SourceRegistry((sources.sources[1], first))
    assert fingerprint_source_registry(sources) == fingerprint_source_registry(reordered)
    item = envelope()
    reordered_tree = replace(item, policy=replace(item.policy, root=replace(item.root, children=tuple(reversed(item.root.children)))))
    assert fingerprint_policy_envelope(item) != fingerprint_policy_envelope(reordered_tree)
    assert fingerprint_policy_envelope(item) == fingerprint_policy_envelope(replace(item, coverage=replace(item.coverage, included_rule_ids=tuple(reversed(item.coverage.included_rule_ids)))))
    assert validate_dataset_manifest(manifest((item,), sources), (item,), reordered) is None


def test_manifest_references_are_deeply_immutable_and_serialization_copies_values():
    release = manifest()
    original = release.fingerprint()
    for obj, field, value in [(release, "dataset_version", "changed"), (release.policy_versions[0], "rule_version", "r0002"),
                              (release.source_registry.artifact, "path", "changed.json")]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)
    with pytest.raises(AttributeError):
        release.policy_versions.append(release.policy_versions[0])
    value = release.to_dict()
    assert json.loads(json.dumps(value)) == value
    value["policy_versions"].clear()
    value["source_versions"].clear()
    assert release.fingerprint() == original
    assert hash(release) == hash(manifest())


def test_engine_integration_tracks_data_and_engine_context_without_changing_policy():
    item, sources = envelope(), registry()
    release = manifest((item,), sources)
    validate_dataset_manifest(release, (item,), sources)
    context = EvaluationContext(DAY, release.dataset_version, release.engine_version)
    facts = EvaluationFacts((ResidentRegistrationFact(RegionRef("SEOUL", "JONGNO"), DAY, RegistrationSource.SELF_REPORTED),))
    reference = PolicyReferenceContext(item.policy_id, DAY)
    direct = evaluate_policy_tree(UserProfile(age=24), item.policy, context, facts=facts, reference_context=reference)
    validate_dataset_manifest(release, (item,), sources)
    again = evaluate_policy_tree(UserProfile(age=24), item.policy, context, facts=facts, reference_context=reference)
    assert direct == again
    assert direct.overall_status.value == "PASS"
    assert direct.context.dataset_version == release.dataset_version
    assert direct.context.engine_version == release.engine_version


def test_draft_ancient_dates_and_missing_review_are_not_production_acceptance():
    item, sources = envelope(), registry()
    assert item.verification_status is PolicyVerificationStatus.DRAFT
    release = manifest((item,), sources)
    assert validate_dataset_manifest(release, (item,), sources) is None
    assert release.review_manifest is None
    # 검증일은 1월, 생성일은 10월이어도 7일 freshness를 실행하지 않는다.
    assert item.last_verified_at < release.created_at.date()


def test_declared_file_byte_hash_is_not_silently_treated_as_object_fingerprint():
    item, sources = envelope(), registry()
    release = manifest((item,), sources)
    file_hash = hashlib.sha256((DATA / "sources.json").read_bytes()).hexdigest()
    assert release.source_registry.artifact.sha256 == file_hash
    assert file_hash != release.source_registry.fingerprint
    changed = replace(release, source_registry=replace(release.source_registry,
                      artifact=ArtifactReference("sources.json", "f" * 64)))
    assert changed.fingerprint() != release.fingerprint()
    # 파일 bytes는 함수의 입력이 아니다. 형식과 객체 pin만 검사하고 파일 검사 완료를 주장하지 않는다.
    assert validate_dataset_manifest(changed, (item,), sources) is None


def test_validation_and_fingerprints_perform_no_io_or_input_mutation(monkeypatch):
    import builtins
    import socket
    import urllib.request

    item, sources = envelope(), registry()
    release = manifest((item,), sources)
    before = (release.to_dict(), item.to_dict(), sources.to_dict())

    def unexpected(*args, **kwargs):
        pytest.fail("dataset 도메인에서 I/O를 호출했습니다")

    monkeypatch.setattr(builtins, "open", unexpected)
    monkeypatch.setattr(Path, "open", unexpected)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    for _ in range(2):
        assert validate_dataset_manifest(release, (item,), sources) is None
        assert release.fingerprint()
    assert before == (release.to_dict(), item.to_dict(), sources.to_dict())


@pytest.mark.parametrize("target", ["manifest", "envelopes", "registry"])
def test_validator_requires_typed_explicit_inputs(target):
    values = dict(manifest=manifest(), envelopes=(envelope(),), registry=registry())
    values[target] = None
    with pytest.raises(ManifestValidationError):
        validate_dataset_manifest(**values)
