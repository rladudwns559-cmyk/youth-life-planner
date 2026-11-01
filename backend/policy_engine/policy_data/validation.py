"""edition과 명시적 registry 사이의 순수 무결성 검증. 운영 승인·freshness는 판정하지 않는다."""

from ..models import ENGINE_VERSION, RuleGroup, walk_nodes
from ..sources import SourceRegistry, validate_evidence_refs
from .envelope import EnvelopeValidationError, PolicyEnvelope
from .manifest import (
    DatasetManifest, ManifestValidationError, fingerprint_policy_envelope, fingerprint_source_registry,
)


def validate_envelope_sources(envelope: PolicyEnvelope, registry: SourceRegistry) -> None:
    """전체 검증 성공 시 None. 입력 변경·정책 평가·부분 성공 결과 없음."""
    if type(envelope) is not PolicyEnvelope:
        raise EnvelopeValidationError("INVALID_ENVELOPE", "envelope")
    if type(registry) is not SourceRegistry:
        raise EnvelopeValidationError("INVALID_ENVELOPE_REGISTRY", "registry")
    for binding in envelope.source_bindings:
        document = registry.get_source(binding.source_document_id)
        if document.document_version != binding.document_version:
            raise EnvelopeValidationError("SOURCE_VERSION_MISMATCH", "source_bindings")
    dates = []
    for leaf in walk_nodes(envelope.root):
        if type(leaf) is RuleGroup:
            continue
        evidence = validate_evidence_refs(leaf.evidence_refs, registry)
        for item in evidence:
            if envelope.policy_id not in item.applicable_policy_ids:
                raise EnvelopeValidationError("POLICY_EVIDENCE_MISMATCH", "applicable_policy_ids")
            # 더 최근인 문서 확인일로 오래된 locator 확인일을 덮어쓰지 않는다.
            dates.append(item.verified_at)
    expected = None if any(value is None for value in dates) else min(dates)
    if envelope.last_verified_at != expected:
        raise EnvelopeValidationError("LAST_VERIFIED_DATE_MISMATCH", "last_verified_at")


def validate_dataset_manifest(
    manifest: DatasetManifest,
    envelopes: tuple[PolicyEnvelope, ...],
    registry: SourceRegistry,
) -> None:
    """명시적 배포 선택 목록과 객체의 전체 일치만 확인한다. 파일 해시는 재계산하지 않는다."""
    if type(manifest) is not DatasetManifest:
        raise ManifestValidationError("INVALID_DATASET_MANIFEST", "manifest")
    if (type(envelopes) is not tuple
            or any(type(item) is not PolicyEnvelope for item in envelopes)):
        raise ManifestValidationError("INVALID_DATASET_ENVELOPES", "envelopes")
    if type(registry) is not SourceRegistry:
        raise ManifestValidationError("INVALID_MANIFEST_REGISTRY", "registry")
    if manifest.engine_version != ENGINE_VERSION:
        raise ManifestValidationError("ENGINE_COMPATIBILITY_MISMATCH", "engine_version")
    by_id = {item.policy_id: item for item in envelopes}
    if len(by_id) != len(envelopes):
        raise ManifestValidationError("DUPLICATE_DATASET_POLICY", "envelopes")
    if set(by_id) != {ref.policy_id for ref in manifest.policy_versions}:
        raise ManifestValidationError("POLICY_REFERENCE_SET_MISMATCH", "policy_versions")
    actual_sources = {(item.source_document_id, item.document_version) for item in registry.sources}
    if actual_sources != {(item.source_document_id, item.document_version) for item in manifest.source_versions}:
        raise ManifestValidationError("SOURCE_REFERENCE_SET_MISMATCH", "source_versions")
    if fingerprint_source_registry(registry) != manifest.source_registry.fingerprint:
        raise ManifestValidationError("REGISTRY_FINGERPRINT_MISMATCH", "source_registry")
    rule_ids = set()
    for ref in manifest.policy_versions:
        envelope = by_id[ref.policy_id]
        if envelope.dataset_version != manifest.dataset_version:
            raise ManifestValidationError("DATASET_VERSION_MISMATCH", "dataset_version")
        for field in ("edition_id", "rule_version", "schema_version", "rule_schema_version"):
            if getattr(envelope, field) != getattr(ref, field):
                raise ManifestValidationError("POLICY_REFERENCE_MISMATCH", field)
        validate_envelope_sources(envelope, registry)
        if fingerprint_policy_envelope(envelope) != ref.fingerprint:
            raise ManifestValidationError("POLICY_FINGERPRINT_MISMATCH", "policy_versions")
        for node in walk_nodes(envelope.root):
            if node.rule_id in rule_ids:
                raise ManifestValidationError("DUPLICATE_DATASET_RULE", "rule_id")
            rule_ids.add(node.rule_id)
