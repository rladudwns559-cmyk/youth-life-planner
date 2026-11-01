"""신뢰된 로컬 NTFS에서 raw7을 확보하고 기존 same-call 검증을 강제한다."""

from ..sources import SourceRegistry
from .benefit_acceptance import PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .benefit_acceptance_review_artifact_loader import _expected_ref, load_acceptance_review_artifact_bytes
from .benefit_snapshot import BenefitSnapshot
from .coverage import EligibilityCoverage
from .coverage_review_context import CoverageReviewContext
from .envelope import PolicyEnvelope
from .historical_artifact_orchestration import _orchestrate_historical_artifact_validation
from .historical_dataset_manifest_loader import _selected_entry
from .historical_windows_file_io import (
    _ENV, _INPUT, _FileSession, _reject, _relative_parts, _root_parts, _supported_windows,
)
from .manifest import DatasetManifest


def _prepare_and_validate_historical_artifacts(
    *,
    expected_acceptance: PolicyBenefitAcceptance,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
    trusted_root: str,
) -> tuple[
    tuple[
        AcceptanceReviewArtifact,
        tuple[
            BenefitSnapshot, EligibilityCoverage, PolicyEnvelope,
            CoverageReviewContext, DatasetManifest, SourceRegistry,
        ],
    ],
    tuple[bytes, bytes, bytes, bytes, bytes, bytes, bytes],
]:
    """파일 I/O 함수이며 순수 함수가 아니다. bytes/반환값은 영구 인증서가 아니다.

    운영 archive 권한/불변 발행·정상 호스트 및 import 전 실행물 신뢰는 외부 전제다.
    """
    # Q0: exact 입력 -> OS -> 기존 기대 ref -> 원본 membership.
    if type(expected_acceptance) is not PolicyBenefitAcceptance:
        _reject(_INPUT, 'expected_acceptance')
    if (type(expected_acceptances) is not tuple or not expected_acceptances
            or any(type(record) is not PolicyBenefitAcceptance for record in expected_acceptances)):
        _reject(_INPUT, 'expected_acceptances')
    if type(trusted_root) is not str:
        _reject(_INPUT, 'trusted_root')
    if not _supported_windows():
        _reject(_ENV, 'platform')
    ref = _expected_ref(expected_acceptances)
    if not any(record is expected_acceptance for record in expected_acceptances):
        _reject(_INPUT, 'expected_acceptance')
    anchor, root_parts = _root_parts(trusted_root)
    session = _FileSession()
    try:
        # Q1~3: 검증된 Review/Entry 없이 참조6의 파일을 열지 않는다.
        session.open_root(anchor, root_parts)
        review_parts = ('acceptance-reviews', ref.rsplit(':', 1)[1] + '.json')
        review_raw = session.read(review_parts, 'review')
        artifact = load_acceptance_review_artifact_bytes(
            raw_bytes=review_raw, expected_acceptances=expected_acceptances,
        )
        entry = _selected_entry(artifact, expected_acceptance)
        references = tuple(getattr(entry, field) for field in (
            'accepted_terms_ref', 'coverage_snapshot_ref', 'policy_envelope_ref',
            'coverage_reviews_ref', 'dataset_manifest_ref', 'source_registry_ref',
        ))
        roles = ('benefit', 'coverage', 'envelope', 'reviews', 'manifest', 'registry')
        paths = tuple(_relative_parts(reference.path, role) for reference, role in zip(references, roles))
        del artifact, entry
        # Q4~6: raw7을 확보·고정한 뒤 기존 C를 정확히 한 번 호출한다.
        raw6 = tuple(session.read(parts, role) for parts, role in zip(paths, roles))
        raw7 = (review_raw, *raw6)
        session.recheck_all()
        result = _orchestrate_historical_artifact_validation(
            expected_acceptance=expected_acceptance, expected_acceptances=expected_acceptances,
            review_artifact_raw_bytes=raw7[0], benefit_raw_bytes=raw7[1], coverage_raw_bytes=raw7[2],
            policy_envelope_raw_bytes=raw7[3], coverage_reviews_raw_bytes=raw7[4],
            dataset_manifest_raw_bytes=raw7[5], source_registry_raw_bytes=raw7[6],
        )
        # Q7~8: 최종 검사·정리가 성공하기 전에는 결과를 노출하지 않는다.
        session.recheck_all()
    except BaseException:
        session.close(preserve_error=True)
        raise
    session.close(preserve_error=False)
    return result, raw7
