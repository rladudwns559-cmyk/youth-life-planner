"""복원된 역사 원본 사이의 관계만 검사한다. raw 출처·사용 적격성을 인증하지 않는다."""

from ..errors import PolicyDataError
from ..sources import SourceRegistry
from .benefit_acceptance import PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .benefit_snapshot import BenefitSnapshot
from .coverage import EligibilityCoverage
from .coverage_fingerprint import (
    fingerprint_condition_inventory, fingerprint_policy_tree, fingerprint_rule_subtree,
)
from .coverage_review_context import CoverageReviewContext
from .coverage_review_matching import _match_implementation_review, _match_inventory_review
from .coverage_structure import _analyze_coverage_structure
from .envelope import PolicyEnvelope
from .historical_dataset_manifest_loader import _bind as _bind_manifest, _selected_entry
from .manifest import DatasetManifest, fingerprint_policy_envelope, fingerprint_source_registry


def _validate_historical_artifact_relationships(
    *,
    expected_acceptance: PolicyBenefitAcceptance,
    artifact: AcceptanceReviewArtifact,
    benefit_snapshot: BenefitSnapshot,
    eligibility_coverage: EligibilityCoverage,
    policy_envelope: PolicyEnvelope,
    coverage_review_context: CoverageReviewContext,
    dataset_manifest: DatasetManifest,
    source_registry: SourceRegistry,
) -> None:
    """같은 A/R로 실제 여섯 Loader가 반환한 원본을 즉시 전달하는 내부 경로를 전제한다.

    None은 공급 값의 관계 검사 성공이며 FULL/VERIFIED/USABLE이나 raw 복원 증명이 아니다.
    정상 MISSING/STALE은 유지하고 기존 helper의 데이터 오류는 원본 그대로 전파한다.
    """
    # P0: 전체 exact type 검사 후 기존 helper로 원본 Entry를 선택한다.
    for field, value, expected_type in (
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
        ("artifact", artifact, AcceptanceReviewArtifact),
        ("benefit_snapshot", benefit_snapshot, BenefitSnapshot),
        ("eligibility_coverage", eligibility_coverage, EligibilityCoverage),
        ("policy_envelope", policy_envelope, PolicyEnvelope),
        ("coverage_review_context", coverage_review_context, CoverageReviewContext),
        ("dataset_manifest", dataset_manifest, DatasetManifest),
        ("source_registry", source_registry, SourceRegistry),
    ):
        if type(value) is not expected_type:
            raise PolicyDataError(f"INVALID_HISTORICAL_ARTIFACT_RELATIONSHIP_INPUT: {field}: 계약을 확인하세요")
    entry = _selected_entry(artifact, expected_acceptance)

    # P1: policy -> scope -> edition. 연도에서 quarter를 추론하지 않는다.
    inventory = eligibility_coverage.inventory
    for field, value in (
        ("benefit_snapshot.policy_id", benefit_snapshot.policy_id),
        ("eligibility_coverage.inventory.policy_id", inventory.policy_id),
        ("policy_envelope.policy_id", policy_envelope.policy_id),
        ("coverage_review_context.policy_id", coverage_review_context.policy_id),
    ):
        if value != expected_acceptance.policy_id:
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_IDENTITY_MISMATCH: {field}: 계약을 확인하세요")
    for field, value in (
        ("benefit_snapshot.scope", benefit_snapshot.scope),
        ("eligibility_coverage.inventory.scope", inventory.scope),
        ("coverage_review_context.scope", coverage_review_context.scope),
    ):
        if value != expected_acceptance.scope:
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_IDENTITY_MISMATCH: {field}: 계약을 확인하세요")
    if policy_envelope.edition_id != expected_acceptance.scope.edition_id:
        raise PolicyDataError("HISTORICAL_ARTIFACT_IDENTITY_MISMATCH: policy_envelope.edition_id: 계약을 확인하세요")

    # P2: Coverage에는 dataset 필드가 없으며 Context가 해당 baseline을 보존한다.
    if benefit_snapshot.dataset_version != expected_acceptance.benefit_dataset_version:
        raise PolicyDataError("HISTORICAL_ARTIFACT_DATASET_MISMATCH: benefit_snapshot.dataset_version: 계약을 확인하세요")
    for field, value in (
        ("policy_envelope.dataset_version", policy_envelope.dataset_version),
        ("coverage_review_context.dataset_version", coverage_review_context.dataset_version),
        ("dataset_manifest.dataset_version", dataset_manifest.dataset_version),
    ):
        if value != benefit_snapshot.dataset_version:
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_DATASET_MISMATCH: {field}: 계약을 확인하세요")

    # P3: 기존 Manifest binding 순서를 유지하고 선택 Envelope의 실제 domain을 비교한다.
    _bind_manifest(dataset_manifest, expected_acceptance, entry)
    selected = next(ref for ref in dataset_manifest.policy_versions if ref.policy_id == expected_acceptance.policy_id)
    for field in ("edition_id", "rule_version", "schema_version", "rule_schema_version"):
        if getattr(selected, field) != getattr(policy_envelope, field):
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_POLICY_MISMATCH: selected_policy.{field}: 계약을 확인하세요")
    if fingerprint_policy_envelope(policy_envelope) != selected.fingerprint:
        raise PolicyDataError("HISTORICAL_ARTIFACT_POLICY_MISMATCH: selected_policy.fingerprint: 계약을 확인하세요")

    # P4: raw SHA가 아닌 실제 Registry domain과 문서 집합/version이다.
    registry_fingerprint = fingerprint_source_registry(source_registry)
    for field, value in (
        ("benefit_snapshot.source_registry_fingerprint", benefit_snapshot.source_registry_fingerprint),
        ("coverage_review_context.source_registry_fingerprint", coverage_review_context.source_registry_fingerprint),
        ("dataset_manifest.source_registry.fingerprint", dataset_manifest.source_registry.fingerprint),
    ):
        if value != registry_fingerprint:
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_REGISTRY_MISMATCH: {field}: 계약을 확인하세요")
    declared_sources = {(binding.source_document_id, binding.document_version) for binding in dataset_manifest.source_versions}
    actual_sources = {(document.source_document_id, document.document_version) for document in source_registry.sources}
    if declared_sources != actual_sources:
        raise PolicyDataError("HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH: dataset_manifest.source_versions: 계약을 확인하세요")
    for field, bindings in (
        ("policy_envelope.source_bindings", policy_envelope.source_bindings),
        ("benefit_snapshot.source_bindings", benefit_snapshot.source_bindings),
    ):
        for index, binding in enumerate(bindings):
            document = source_registry.get_source(binding.source_document_id)
            if document.document_version != binding.document_version:
                raise PolicyDataError(f"HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH: {field}[{index}].document_version: 계약을 확인하세요")
    original_documents = []
    for index, original in enumerate(entry.source_documents):
        document = source_registry.get_source(original.binding.source_document_id)
        if document.document_version != original.binding.document_version:
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH: entry.source_documents[{index}].binding.document_version: 계약을 확인하세요")
        original_documents.append(document)

    # P5: 같은 Coverage 구현 역할과 알려진 원문 hash 선언만 비교한다.
    if coverage_review_context.implementation_fingerprint != entry.implementation_artifact_ref.sha256:
        raise PolicyDataError("HISTORICAL_ARTIFACT_IMPLEMENTATION_MISMATCH: coverage_review_context.implementation_fingerprint: 계약을 확인하세요")
    for index, (original, document) in enumerate(zip(entry.source_documents, original_documents)):
        if document.content_sha256 is not None and document.content_sha256 != original.artifact.sha256:
            raise PolicyDataError(f"HISTORICAL_ARTIFACT_SOURCE_CONTENT_MISMATCH: entry.source_documents[{index}].artifact.sha256: 계약을 확인하세요")

    # P6: 원본 Binding/root 쌍과 기존 missing/ownership/unmapped 의미를 재사용한다.
    _, resolved_bindings, _ = _analyze_coverage_structure(eligibility_coverage, policy_envelope.policy)

    # P7: 모든 현재 지문 -> Inventory slot -> canonical Implementation slots.
    inventory_fingerprint = fingerprint_condition_inventory(inventory)
    tree_fingerprint = fingerprint_policy_tree(policy_envelope.policy)
    rows = tuple((binding, fingerprint_rule_subtree(root)) for binding, root in resolved_bindings)
    _match_inventory_review(inventory, coverage_review_context, current_inventory_fingerprint=inventory_fingerprint)
    for binding, subtree_fingerprint in rows:
        _match_implementation_review(
            inventory, binding, coverage_review_context,
            current_inventory_fingerprint=inventory_fingerprint,
            current_rule_version=policy_envelope.rule_version,
            current_policy_tree_fingerprint=tree_fingerprint,
            current_subtree_fingerprint=subtree_fingerprint,
        )
    # P8: 승인이 아닌 관계 검사 성공이다.
    return None
