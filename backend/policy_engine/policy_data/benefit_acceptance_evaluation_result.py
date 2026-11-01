"""요청 내부 Acceptance 결과의 구조 값. 실제 gate·철회·기한·발급 사실은 평가하지 않는다."""

from dataclasses import InitVar, dataclass, field
from datetime import date
from enum import Enum
import re

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus
from .eligibility_coverage import ApplicabilityScope


class BenefitAcceptanceEvaluationStatus(str, Enum):
    USABLE = "USABLE"
    UNUSABLE = "UNUSABLE"


class BenefitAcceptanceReason(str, Enum):
    NO_ACCEPTANCE_CONTEXT = "NO_ACCEPTANCE_CONTEXT"
    NO_ACCEPTANCE_RECORDS = "NO_ACCEPTANCE_RECORDS"
    ACCEPTANCE_NOT_SELECTED = "ACCEPTANCE_NOT_SELECTED"
    ACCEPTANCE_REVOKED = "ACCEPTANCE_REVOKED"
    ACCEPTANCE_NOT_YET_VALID = "ACCEPTANCE_NOT_YET_VALID"
    ACCEPTANCE_EXPIRED = "ACCEPTANCE_EXPIRED"
    COVERAGE_NOT_FULL = "COVERAGE_NOT_FULL"
    POLICY_NOT_VERIFIED = "POLICY_NOT_VERIFIED"
    BENEFIT_METADATA_NOT_REVIEWED = "BENEFIT_METADATA_NOT_REVIEWED"
    COVERAGE_SNAPSHOT_CHANGED = "COVERAGE_SNAPSHOT_CHANGED"
    BENEFIT_SNAPSHOT_CHANGED = "BENEFIT_SNAPSHOT_CHANGED"
    BENEFIT_PROVENANCE_CHANGED = "BENEFIT_PROVENANCE_CHANGED"


_RESULT_CREATION_TOKEN = object()
_REASON_ORDER = tuple(BenefitAcceptanceReason)
_NO_SELECTION_REASONS = _REASON_ORDER[:3]
_DATE_REASONS = (
    BenefitAcceptanceReason.ACCEPTANCE_NOT_YET_VALID,
    BenefitAcceptanceReason.ACCEPTANCE_EXPIRED,
)
_SELECTED_ONLY_REASONS = _REASON_ORDER[3:6] + _REASON_ORDER[9:]


def _invalid(name: str, reason: str) -> PolicyDataError:
    return PolicyDataError(f"INVALID_ACCEPTANCE_EVALUATION_RESULT: {name}: {reason}")


def _identifier(value: object, name: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        raise _invalid(name, "정확한 canonical 식별자 문자열이 필요합니다")


def _optional_ref(value: object, name: str) -> None:
    if value is not None and (type(value) is not str or not value.strip()):
        raise _invalid(name, "정확한 비공백 문자열 또는 None이 필요합니다")


@dataclass(frozen=True, slots=True, kw_only=True)
class BenefitAcceptanceEvaluation:
    """9개 결과 값의 로컬 조합만 보장한다. 다른 요청/확인본의 승인 증거로 재사용하지 않는다."""

    policy_id: str
    scope: ApplicabilityScope
    benefit_id: str
    data_use_date: date
    selected_acceptance_ref: str | None
    selected_acceptance_version: str | None
    selected_acceptance_status: BenefitAcceptanceStatus | None
    revocation_acceptance_ref: str | None
    reasons: tuple[BenefitAcceptanceReason, ...]
    _creation_token: InitVar[object] = field(default=None, kw_only=True)

    def __post_init__(self, _creation_token: object) -> None:
        if _creation_token is not _RESULT_CREATION_TOKEN:
            raise TypeError("BenefitAcceptanceEvaluation은 내부 factory를 통해서만 생성할 수 있습니다")

        _identifier(self.policy_id, "policy_id")
        if type(self.scope) is not ApplicabilityScope:
            raise _invalid("scope", "정확한 ApplicabilityScope가 필요합니다")
        _identifier(self.benefit_id, "benefit_id")
        if type(self.data_use_date) is not date:
            raise _invalid("data_use_date", "정확한 date가 필요합니다")
        _optional_ref(self.selected_acceptance_ref, "selected_acceptance_ref")
        if self.selected_acceptance_version is not None and (
            type(self.selected_acceptance_version) is not str
            or re.fullmatch(r"a(?:[0-9]{4}|[1-9][0-9]{4,})", self.selected_acceptance_version) is None
            or self.selected_acceptance_version == "a0000"
        ):
            raise _invalid("selected_acceptance_version", "a0001부터의 명시적 버전 또는 None이 필요합니다")
        if self.selected_acceptance_status is not None and type(self.selected_acceptance_status) is not BenefitAcceptanceStatus:
            raise _invalid("selected_acceptance_status", "정확한 BenefitAcceptanceStatus 또는 None이 필요합니다")
        _optional_ref(self.revocation_acceptance_ref, "revocation_acceptance_ref")
        if type(self.reasons) is not tuple or any(type(reason) is not BenefitAcceptanceReason for reason in self.reasons):
            raise _invalid("reasons", "정확한 BenefitAcceptanceReason의 exact tuple이 필요합니다")

        # 명세15절: 필드 → 사유 순서 → 선택 metadata → 미선택/선택 → 철회 → 기한 사유.
        positions = tuple(_REASON_ORDER.index(reason) for reason in self.reasons)
        if any(left >= right for left, right in zip(positions, positions[1:])):
            raise _invalid("reasons", "사유는 중복 없는 canonical 순서여야 합니다")
        selected = (self.selected_acceptance_ref, self.selected_acceptance_version, self.selected_acceptance_status)
        no_selection = all(value is None for value in selected)
        if any(value is None for value in selected) and not no_selection:
            raise _invalid("selected_acceptance_ref", "선택 ref/version/status는 모두 None이거나 모두 존재해야 합니다")
        selection_reason_count = sum(reason in self.reasons for reason in _NO_SELECTION_REASONS)
        if no_selection:
            if selection_reason_count != 1:
                raise _invalid("reasons", "미선택에는 세 선택 사유 중 정확히 하나가 필요합니다")
            if self.revocation_acceptance_ref is not None:
                raise _invalid("revocation_acceptance_ref", "미선택에는 철회 근거가 없어야 합니다")
            if any(reason in self.reasons for reason in _SELECTED_ONLY_REASONS):
                raise _invalid("reasons", "미선택에 선택 기록 전용 사유를 붙일 수 없습니다")
        elif selection_reason_count:
            raise _invalid("reasons", "선택된 기록에 미선택 사유를 붙일 수 없습니다")

        has_revocation = BenefitAcceptanceReason.ACCEPTANCE_REVOKED in self.reasons
        if (self.revocation_acceptance_ref is not None) != has_revocation:
            raise _invalid("revocation_acceptance_ref", "철회 근거와 철회 사유는 함께 존재해야 합니다")
        if self.selected_acceptance_status is BenefitAcceptanceStatus.REVOKED:
            if self.revocation_acceptance_ref != self.selected_acceptance_ref:
                raise _invalid("revocation_acceptance_ref", "직접 REVOKED 선택의 근거는 선택 ref 자신이어야 합니다")
        elif self.selected_acceptance_status is BenefitAcceptanceStatus.ACCEPTED:
            if self.revocation_acceptance_ref is not None and self.revocation_acceptance_ref == self.selected_acceptance_ref:
                raise _invalid("revocation_acceptance_ref", "ACCEPTED의 철회 근거는 선택 ref와 달라야 합니다")

        if all(reason in self.reasons for reason in _DATE_REASONS):
            raise _invalid("reasons", "기한 전과 기한 후 사유는 동시에 존재할 수 없습니다")
        if any(reason in self.reasons for reason in _DATE_REASONS) and self.selected_acceptance_status is not BenefitAcceptanceStatus.ACCEPTED:
            raise _invalid("reasons", "기한 사유는 선택된 ACCEPTED에만 허용합니다")

    @property
    def status(self) -> BenefitAcceptanceEvaluationStatus:
        """검증된 사유의 유무만 표현한다. 실제 Coverage/검토/철회/기한을 계산하지 않는다."""
        return BenefitAcceptanceEvaluationStatus.UNUSABLE if self.reasons else BenefitAcceptanceEvaluationStatus.USABLE

    def to_dict(self) -> dict[str, object]:
        """저장9key와 마지막 파생 status. 표시용이며 외부 수용 입력/재사용 증명서가 아니다."""
        return {
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "benefit_id": self.benefit_id,
            "data_use_date": self.data_use_date.isoformat(),
            "selected_acceptance_ref": self.selected_acceptance_ref,
            "selected_acceptance_version": self.selected_acceptance_version,
            "selected_acceptance_status": None if self.selected_acceptance_status is None else self.selected_acceptance_status.value,
            "revocation_acceptance_ref": self.revocation_acceptance_ref,
            "reasons": [reason.value for reason in self.reasons],
            "status": self.status.value,
        }


def _create_benefit_acceptance_evaluation(
    *,
    policy_id: str,
    scope: ApplicabilityScope,
    benefit_id: str,
    data_use_date: date,
    selected_acceptance_ref: str | None,
    selected_acceptance_version: str | None,
    selected_acceptance_status: BenefitAcceptanceStatus | None,
    revocation_acceptance_ref: str | None,
    reasons: tuple[BenefitAcceptanceReason, ...],
) -> BenefitAcceptanceEvaluation:
    """명시9개 값을 구조 검사에 전달한다. 합성 생성 성공은 실제 평가/검토 사실의 증명이 아니다."""
    return BenefitAcceptanceEvaluation(
        policy_id=policy_id,
        scope=scope,
        benefit_id=benefit_id,
        data_use_date=data_use_date,
        selected_acceptance_ref=selected_acceptance_ref,
        selected_acceptance_version=selected_acceptance_version,
        selected_acceptance_status=selected_acceptance_status,
        revocation_acceptance_ref=revocation_acceptance_ref,
        reasons=reasons,
        _creation_token=_RESULT_CREATION_TOKEN,
    )
