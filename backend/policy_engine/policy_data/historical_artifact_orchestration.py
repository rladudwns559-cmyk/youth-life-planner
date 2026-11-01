"""동일 호출의 Review/raw6 복원과 교차 검증을 연결한다. 사용 적격성을 승인하지 않는다."""

from ..errors import PolicyDataError
from ..sources import SourceRegistry
from .benefit_acceptance import PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .benefit_acceptance_review_artifact_loader import load_acceptance_review_artifact_bytes
from .benefit_snapshot import BenefitSnapshot
from .coverage import EligibilityCoverage
from .coverage_review_context import CoverageReviewContext
from .envelope import PolicyEnvelope
from .historical_benefit_snapshot_loader import load_historical_benefit_snapshot_bytes
from .historical_coverage_review_context_loader import load_historical_coverage_review_context_bytes
from .historical_cross_artifact_validator import _validate_historical_artifact_relationships
from .historical_dataset_manifest_loader import _selected_entry, load_historical_dataset_manifest_bytes
from .historical_eligibility_coverage_loader import load_historical_eligibility_coverage_bytes
from .historical_policy_envelope_loader import load_historical_policy_envelope_bytes
from .historical_source_registry_loader import load_historical_source_registry_bytes
from .manifest import DatasetManifest


def _orchestrate_historical_artifact_validation(
    *,
    expected_acceptance: PolicyBenefitAcceptance,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
    review_artifact_raw_bytes: bytes,
    benefit_raw_bytes: bytes,
    coverage_raw_bytes: bytes,
    policy_envelope_raw_bytes: bytes,
    coverage_reviews_raw_bytes: bytes,
    dataset_manifest_raw_bytes: bytes,
    source_registry_raw_bytes: bytes,
) -> tuple[
    AcceptanceReviewArtifact,
    tuple[
        BenefitSnapshot,
        EligibilityCoverage,
        PolicyEnvelope,
        CoverageReviewContext,
        DatasetManifest,
        SourceRegistry,
    ],
]:
    """원본 A/전체 expected와 raw7을 실제 기존 로더에 결합한다.

    반환 원본은 이 호출의 복원·교차 검사 결과다. 파일 취득/실행 ZIP/공식 원문·
    현재 사용 가능성을 인증하지 않으며, 기존 예외는 그대로 전파한다.
    """
    # P0a~c: 전체 Review 복원 후 명시 A의 원본 identity를 기존 selector로 확인한다.
    if type(expected_acceptance) is not PolicyBenefitAcceptance:
        raise PolicyDataError("INVALID_HISTORICAL_ORCHESTRATION_INPUT: expected_acceptance: 계약을 확인하세요")
    artifact = load_acceptance_review_artifact_bytes(
        raw_bytes=review_artifact_raw_bytes, expected_acceptances=expected_acceptances,
    )
    _selected_entry(artifact, expected_acceptance)

    # P0d: 역할별 exact bytes를 모두 확인한 뒤 첫 Historical 로더를 실행한다.
    for field, raw in (
        ("benefit_raw_bytes", benefit_raw_bytes),
        ("coverage_raw_bytes", coverage_raw_bytes),
        ("policy_envelope_raw_bytes", policy_envelope_raw_bytes),
        ("coverage_reviews_raw_bytes", coverage_reviews_raw_bytes),
        ("dataset_manifest_raw_bytes", dataset_manifest_raw_bytes),
        ("source_registry_raw_bytes", source_registry_raw_bytes),
    ):
        if type(raw) is not bytes:
            raise PolicyDataError(f"INVALID_HISTORICAL_ORCHESTRATION_INPUT: {field}: 계약을 확인하세요")

    # P1~6: 같은 A/R 및 해당 입력 bytes를 순서대로 실제 로더에 전달한다.
    benefit_snapshot = load_historical_benefit_snapshot_bytes(
        raw_bytes=benefit_raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance,
    )
    eligibility_coverage = load_historical_eligibility_coverage_bytes(
        raw_bytes=coverage_raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance,
    )
    policy_envelope = load_historical_policy_envelope_bytes(
        raw_bytes=policy_envelope_raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance,
    )
    coverage_review_context = load_historical_coverage_review_context_bytes(
        raw_bytes=coverage_reviews_raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance,
    )
    dataset_manifest = load_historical_dataset_manifest_bytes(
        raw_bytes=dataset_manifest_raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance,
    )
    source_registry = load_historical_source_registry_bytes(
        raw_bytes=source_registry_raw_bytes, artifact=artifact, expected_acceptance=expected_acceptance,
    )

    # P7~8: 방금 반환된 원본 여섯 개를 검사한 뒤에만 완전한 tuple을 반환한다.
    _validate_historical_artifact_relationships(
        expected_acceptance=expected_acceptance, artifact=artifact,
        benefit_snapshot=benefit_snapshot, eligibility_coverage=eligibility_coverage,
        policy_envelope=policy_envelope, coverage_review_context=coverage_review_context,
        dataset_manifest=dataset_manifest, source_registry=source_registry,
    )
    return artifact, (
        benefit_snapshot, eligibility_coverage, policy_envelope, coverage_review_context,
        dataset_manifest, source_registry,
    )
