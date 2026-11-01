"""과거 승인·철회 revision의 불변 값. 구조 유효성은 실제 검토 사실을 인증하지 않는다."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re

from ..errors import PolicyDataError
from .eligibility_coverage import ApplicabilityScope


class BenefitAcceptanceStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"


def _invalid(field: str, reason: str) -> PolicyDataError:
    return PolicyDataError(f"INVALID_BENEFIT_ACCEPTANCE: {field}: {reason}")


def _nonblank(value: object, field: str) -> None:
    if type(value) is not str or not value.strip():
        raise _invalid(field, "정확한 비공백 문자열이 필요합니다")


def _identifier(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        raise _invalid(field, "정확한 canonical 식별자 문자열이 필요합니다")


def _version(value: object, prefix: str, field: str) -> None:
    # 기존 Inventory/Benefit의 양의 버전 문법을 유지한다. 동결 모델에는 공유 helper가 없다.
    if (type(value) is not str
            or re.fullmatch(prefix + r"(?:[0-9]{4}|[1-9][0-9]{4,})", value) is None
            or value == prefix + "0000"):
        raise _invalid(field, prefix + "0001부터의 명시적 버전이 필요합니다")


def _fingerprint(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise _invalid(field, "정확한 소문자16진64자리 문자열이 필요합니다")


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyBenefitAcceptance:
    """명시21필드의 결정 기록. 현재 사용 가능성·외부 이력·근거 존재는 확인하지 않는다."""

    acceptance_ref: str
    acceptance_version: str
    status: BenefitAcceptanceStatus
    policy_id: str
    scope: ApplicabilityScope
    benefit_id: str
    coverage_inventory_version: str
    coverage_inventory_fingerprint: str
    coverage_rule_version: str
    coverage_policy_tree_fingerprint: str
    coverage_dataset_version: str
    coverage_source_registry_fingerprint: str
    coverage_implementation_fingerprint: str
    benefit_version: str
    benefit_fingerprint: str
    benefit_dataset_version: str
    benefit_source_registry_fingerprint: str
    reviewed_at: date
    valid_until: date
    review_artifact_ref: str
    revokes_acceptance_ref: str | None

    def __post_init__(self) -> None:
        _nonblank(self.acceptance_ref, "acceptance_ref")
        _version(self.acceptance_version, "a", "acceptance_version")
        if type(self.status) is not BenefitAcceptanceStatus:
            raise _invalid("status", "정확한 BenefitAcceptanceStatus가 필요합니다")
        _identifier(self.policy_id, "policy_id")
        if type(self.scope) is not ApplicabilityScope:
            raise _invalid("scope", "정확한 ApplicabilityScope가 필요합니다")
        _identifier(self.benefit_id, "benefit_id")
        _version(self.coverage_inventory_version, "i", "coverage_inventory_version")
        _fingerprint(self.coverage_inventory_fingerprint, "coverage_inventory_fingerprint")
        _nonblank(self.coverage_rule_version, "coverage_rule_version")
        _fingerprint(self.coverage_policy_tree_fingerprint, "coverage_policy_tree_fingerprint")
        _nonblank(self.coverage_dataset_version, "coverage_dataset_version")
        _fingerprint(self.coverage_source_registry_fingerprint, "coverage_source_registry_fingerprint")
        _fingerprint(self.coverage_implementation_fingerprint, "coverage_implementation_fingerprint")
        _version(self.benefit_version, "b", "benefit_version")
        _fingerprint(self.benefit_fingerprint, "benefit_fingerprint")
        _nonblank(self.benefit_dataset_version, "benefit_dataset_version")
        _fingerprint(self.benefit_source_registry_fingerprint, "benefit_source_registry_fingerprint")
        if type(self.reviewed_at) is not date:
            raise _invalid("reviewed_at", "정확한 date가 필요합니다")
        if type(self.valid_until) is not date:
            raise _invalid("valid_until", "정확한 date가 필요합니다")
        _nonblank(self.review_artifact_ref, "review_artifact_ref")
        if self.revokes_acceptance_ref is not None:
            _nonblank(self.revokes_acceptance_ref, "revokes_acceptance_ref")

        if self.reviewed_at > self.valid_until:
            raise _invalid("valid_until", "reviewed_at 이상이어야 합니다")
        if self.coverage_dataset_version != self.benefit_dataset_version:
            raise _invalid("benefit_dataset_version", "Coverage와 같은 dataset이어야 합니다")
        if self.coverage_source_registry_fingerprint != self.benefit_source_registry_fingerprint:
            raise _invalid("benefit_source_registry_fingerprint", "Coverage와 같은 Registry 지문이어야 합니다")
        if self.status is BenefitAcceptanceStatus.ACCEPTED:
            if self.revokes_acceptance_ref is not None:
                raise _invalid("revokes_acceptance_ref", "ACCEPTED에는 None이어야 합니다")
        else:
            if self.revokes_acceptance_ref is None:
                raise _invalid("revokes_acceptance_ref", "REVOKED에는 철회 대상 ref가 필요합니다")
            if self.revokes_acceptance_ref == self.acceptance_ref:
                raise _invalid("revokes_acceptance_ref", "자기 자신을 철회할 수 없습니다")

    def to_dict(self) -> dict[str, object]:
        """저장21key와 새 Scope dict·ISO 날짜만 반환한다. 조회·현재 상태 계산은 없다."""
        return {
            "acceptance_ref": self.acceptance_ref,
            "acceptance_version": self.acceptance_version,
            "status": self.status.value,
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "benefit_id": self.benefit_id,
            "coverage_inventory_version": self.coverage_inventory_version,
            "coverage_inventory_fingerprint": self.coverage_inventory_fingerprint,
            "coverage_rule_version": self.coverage_rule_version,
            "coverage_policy_tree_fingerprint": self.coverage_policy_tree_fingerprint,
            "coverage_dataset_version": self.coverage_dataset_version,
            "coverage_source_registry_fingerprint": self.coverage_source_registry_fingerprint,
            "coverage_implementation_fingerprint": self.coverage_implementation_fingerprint,
            "benefit_version": self.benefit_version,
            "benefit_fingerprint": self.benefit_fingerprint,
            "benefit_dataset_version": self.benefit_dataset_version,
            "benefit_source_registry_fingerprint": self.benefit_source_registry_fingerprint,
            "reviewed_at": self.reviewed_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "review_artifact_ref": self.review_artifact_ref,
            "revokes_acceptance_ref": self.revokes_acceptance_ref,
        }
