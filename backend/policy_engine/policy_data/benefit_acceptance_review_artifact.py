"""검토 자료의 불변 구조만 표현한다. bytes·원본 대응·실제 검토를 인증하지 않는다."""

from dataclasses import dataclass
from enum import Enum
import re

from ..errors import PolicyDataError
from ..sources.models import parse_evidence_ref
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .envelope import SourceBinding
from .manifest import ArtifactReference


class BenefitReviewClaim(str, Enum):
    AMOUNT = "AMOUNT"
    CADENCE = "CADENCE"
    MEDIUM = "MEDIUM"
    RESTRICTION = "RESTRICTION"
    APPLICABLE_MONTHS = "APPLICABLE_MONTHS"


def _invalid(field: str, reason: str) -> PolicyDataError:
    return PolicyDataError(f"INVALID_ACCEPTANCE_REVIEW_ARTIFACT: {field}: {reason}")


def _nonblank(value: object, field: str) -> None:
    if type(value) is not str or not value.strip():
        raise _invalid(field, "정확한 비공백 문자열이 필요합니다")


def _typed_tuple(value: object, item_type: type, field: str) -> None:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise _invalid(field, "정확한 원소 타입의 tuple이 필요합니다")


def _binding_dict(binding: SourceBinding) -> dict[str, str]:
    return {"source_document_id": binding.source_document_id, "document_version": binding.document_version}


def _artifact_dict(artifact: ArtifactReference | None) -> dict[str, str] | None:
    return None if artifact is None else {"path": artifact.path, "sha256": artifact.sha256}


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimEvidenceMapping:
    claim: BenefitReviewClaim
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.claim) is not BenefitReviewClaim:
            raise _invalid("claim", "정확한 BenefitReviewClaim이 필요합니다")
        _typed_tuple(self.evidence_refs, str, "evidence_refs")
        if not self.evidence_refs:
            raise _invalid("evidence_refs", "비어 있지 않은 근거 목록이 필요합니다")
        for ref in self.evidence_refs:
            try:
                parse_evidence_ref(ref)
            except PolicyDataError:
                raise _invalid("evidence_refs", "canonical 근거 ref가 필요합니다") from None
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise _invalid("evidence_refs", "행 내부 중복 근거는 허용하지 않습니다")

    def to_dict(self) -> dict[str, object]:
        return {"claim": self.claim.value, "evidence_refs": list(self.evidence_refs)}


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewSourceOriginal:
    binding: SourceBinding
    artifact: ArtifactReference

    def __post_init__(self) -> None:
        if type(self.binding) is not SourceBinding:
            raise _invalid("binding", "정확한 SourceBinding이 필요합니다")
        if type(self.artifact) is not ArtifactReference:
            raise _invalid("artifact", "정확한 ArtifactReference가 필요합니다")

    def to_dict(self) -> dict[str, object]:
        return {"binding": _binding_dict(self.binding), "artifact": _artifact_dict(self.artifact)}


_REFERENCE_FIELDS = (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceReviewEntry:
    acceptance: PolicyBenefitAcceptance
    accepted_terms_ref: ArtifactReference | None
    coverage_snapshot_ref: ArtifactReference | None
    policy_envelope_ref: ArtifactReference | None
    coverage_reviews_ref: ArtifactReference | None
    dataset_manifest_ref: ArtifactReference | None
    source_registry_ref: ArtifactReference | None
    implementation_artifact_ref: ArtifactReference | None
    claim_evidence: tuple[ClaimEvidenceMapping, ...]
    source_bindings: tuple[SourceBinding, ...]
    source_documents: tuple[ReviewSourceOriginal, ...]
    prepared_by: str
    reviewed_by: str
    review_note: str
    manual_scenario_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.acceptance) is not PolicyBenefitAcceptance:
            raise _invalid("acceptance", "정확한 PolicyBenefitAcceptance가 필요합니다")
        for field in _REFERENCE_FIELDS:
            value = getattr(self, field)
            if value is not None and type(value) is not ArtifactReference:
                raise _invalid(field, "정확한 ArtifactReference 또는 None이 필요합니다")
        _typed_tuple(self.claim_evidence, ClaimEvidenceMapping, "claim_evidence")
        _typed_tuple(self.source_bindings, SourceBinding, "source_bindings")
        _typed_tuple(self.source_documents, ReviewSourceOriginal, "source_documents")
        for field in ("prepared_by", "reviewed_by", "review_note"):
            _nonblank(getattr(self, field), field)
        _typed_tuple(self.manual_scenario_ids, str, "manual_scenario_ids")
        if not self.manual_scenario_ids:
            raise _invalid("manual_scenario_ids", "검토 사례를 명시해야 합니다")
        for scenario in self.manual_scenario_ids:
            _nonblank(scenario, "manual_scenario_ids")
        if self.prepared_by == self.reviewed_by:
            raise _invalid("reviewed_by", "준비자와 다른 검토자 handle이 필요합니다")
        if len(set(self.manual_scenario_ids)) != len(self.manual_scenario_ids):
            raise _invalid("manual_scenario_ids", "중복 사례는 허용하지 않습니다")

        if self.acceptance.status is BenefitAcceptanceStatus.REVOKED:
            for field in _REFERENCE_FIELDS:
                if getattr(self, field) is not None:
                    raise _invalid(field, "REVOKED에는 None이어야 합니다")
            for field in ("claim_evidence", "source_bindings", "source_documents"):
                if getattr(self, field):
                    raise _invalid(field, "REVOKED에는 빈 tuple이어야 합니다")
            return

        for field in _REFERENCE_FIELDS:
            if getattr(self, field) is None:
                raise _invalid(field, "ACCEPTED에는 원본 참조가 필요합니다")
        if tuple(row.claim for row in self.claim_evidence) != tuple(BenefitReviewClaim):
            raise _invalid("claim_evidence", "정확한 5개 claim을 명세 순서로 명시해야 합니다")
        if not self.source_bindings:
            raise _invalid("source_bindings", "ACCEPTED에는 source binding이 필요합니다")
        source_ids = tuple(binding.source_document_id for binding in self.source_bindings)
        if source_ids != tuple(sorted(source_ids)):
            raise _invalid("source_bindings", "source ID 정렬 순서가 필요합니다")
        if len(set(source_ids)) != len(source_ids):
            raise _invalid("source_bindings", "source ID는 유일해야 합니다")
        if tuple(original.binding for original in self.source_documents) != self.source_bindings:
            raise _invalid("source_documents", "binding과 같은 개수·순서·값의 원문 참조가 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """저장15key의 진단 snapshot. raw hash 대상 body/20key projection은 아니다."""
        return {
            "acceptance": self.acceptance.to_dict(),
            **{field: _artifact_dict(getattr(self, field)) for field in _REFERENCE_FIELDS},
            "claim_evidence": [row.to_dict() for row in self.claim_evidence],
            "source_bindings": [_binding_dict(binding) for binding in self.source_bindings],
            "source_documents": [original.to_dict() for original in self.source_documents],
            "prepared_by": self.prepared_by,
            "reviewed_by": self.reviewed_by,
            "review_note": self.review_note,
            "manual_scenario_ids": list(self.manual_scenario_ids),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceReviewArtifact:
    review_artifact_ref: str
    entries: tuple[AcceptanceReviewEntry, ...]

    def __post_init__(self) -> None:
        if (type(self.review_artifact_ref) is not str
                or re.fullmatch(r"acceptance-review:sha256:[0-9a-f]{64}", self.review_artifact_ref) is None):
            raise _invalid("review_artifact_ref", "정확한 content-addressed ref가 필요합니다")
        _typed_tuple(self.entries, AcceptanceReviewEntry, "entries")
        if not self.entries:
            raise _invalid("entries", "명시한 revision entry가 필요합니다")
        refs = tuple(entry.acceptance.acceptance_ref for entry in self.entries)
        if len(set(refs)) != len(refs):
            raise _invalid("entries", "acceptance_ref는 전체에서 유일해야 합니다")
        revisions = tuple((entry.acceptance.policy_id, entry.acceptance.scope, entry.acceptance.benefit_id,
                           entry.acceptance.acceptance_version) for entry in self.entries)
        if len(set(revisions)) != len(revisions):
            raise _invalid("entries", "target/version revision key는 유일해야 합니다")
        if any(entry.acceptance.review_artifact_ref != self.review_artifact_ref for entry in self.entries):
            raise _invalid("entries", "모든 entry의 외부 artifact ref가 root와 같아야 합니다")

    def to_dict(self) -> dict[str, object]:
        """외부 ref를 포함한 진단2key. 자기 hash 대상 raw 본문을 생성하지 않는다."""
        return {"review_artifact_ref": self.review_artifact_ref,
                "entries": [entry.to_dict() for entry in self.entries]}
