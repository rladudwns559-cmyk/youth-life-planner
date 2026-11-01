"""혜택 정의의 불변 값. 구조만 검증하며 검토·수용·지급·현금흐름은 판정하지 않는다."""

from dataclasses import dataclass
from enum import Enum
import re

from ..errors import PolicyDataError
from ..sources import parse_evidence_ref
from .eligibility_coverage import ApplicabilityScope
from .envelope import SourceBinding


class BenefitAmountType(str, Enum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"
    UNKNOWN = "UNKNOWN"


class BenefitPaymentCadence(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMIANNUAL = "SEMIANNUAL"
    ANNUAL = "ANNUAL"
    ONE_TIME = "ONE_TIME"
    IRREGULAR = "IRREGULAR"
    UNKNOWN = "UNKNOWN"


class BenefitMedium(str, Enum):
    UNRESTRICTED_CASH = "UNRESTRICTED_CASH"
    RESTRICTED_CASH_EQUIVALENT = "RESTRICTED_CASH_EQUIVALENT"
    LOCAL_CURRENCY = "LOCAL_CURRENCY"
    POINTS = "POINTS"
    VOUCHER = "VOUCHER"
    IN_KIND = "IN_KIND"
    SAVINGS_MATCH = "SAVINGS_MATCH"
    LOAN = "LOAN"
    INTEREST_SUPPORT = "INTEREST_SUPPORT"
    UNKNOWN = "UNKNOWN"


class BenefitRestriction(str, Enum):
    UNRESTRICTED = "UNRESTRICTED"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


def _invalid(field: str, reason: str) -> PolicyDataError:
    return PolicyDataError(f"INVALID_BENEFIT_SNAPSHOT: {field}: {reason}")


def _identifier(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        raise _invalid(field, "정확한 canonical 식별자 문자열이 필요합니다")


@dataclass(frozen=True, slots=True, kw_only=True)
class BenefitSnapshot:
    """고정 자료의 정규화된 정의. 생성 성공은 검토 완료나 Acceptance를 뜻하지 않는다."""

    policy_id: str
    scope: ApplicabilityScope
    benefit_id: str
    benefit_version: str
    amount_type: BenefitAmountType
    amount_krw: int | None
    amount_description: str | None
    payment_cadence: BenefitPaymentCadence
    benefit_medium: BenefitMedium
    restriction: BenefitRestriction
    restriction_details: str | None
    applicable_months: tuple[str, ...] | None
    benefit_evidence_refs: tuple[str, ...]
    source_bindings: tuple[SourceBinding, ...]
    dataset_version: str
    source_registry_fingerprint: str

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "policy_id")
        if type(self.scope) is not ApplicabilityScope:
            raise _invalid("scope", "정확한 ApplicabilityScope가 필요합니다")
        _identifier(self.benefit_id, "benefit_id")
        if (type(self.benefit_version) is not str
                or re.fullmatch(r"b(?:[0-9]{4}|[1-9][0-9]{4,})", self.benefit_version) is None
                or self.benefit_version == "b0000"):
            raise _invalid("benefit_version", "b0001부터의 명시적 버전이 필요합니다")
        if type(self.amount_type) is not BenefitAmountType:
            raise _invalid("amount_type", "정확한 BenefitAmountType이 필요합니다")
        if self.amount_krw is not None and (type(self.amount_krw) is not int or self.amount_krw < 0):
            raise _invalid("amount_krw", "0 이상 정확한 int 또는 None이 필요합니다")
        if self.amount_description is not None and (
            type(self.amount_description) is not str or not self.amount_description.strip()
        ):
            raise _invalid("amount_description", "비공백 정확한 str 또는 None이 필요합니다")
        if type(self.payment_cadence) is not BenefitPaymentCadence:
            raise _invalid("payment_cadence", "정확한 BenefitPaymentCadence가 필요합니다")
        if type(self.benefit_medium) is not BenefitMedium:
            raise _invalid("benefit_medium", "정확한 BenefitMedium이 필요합니다")
        if type(self.restriction) is not BenefitRestriction:
            raise _invalid("restriction", "정확한 BenefitRestriction이 필요합니다")
        if self.restriction_details is not None and (
            type(self.restriction_details) is not str or not self.restriction_details.strip()
        ):
            raise _invalid("restriction_details", "비공백 정확한 str 또는 None이 필요합니다")
        if self.applicable_months is not None:
            months = self.applicable_months
            if type(months) is not tuple or not months:
                raise _invalid("applicable_months", "비어 있지 않은 정확한 tuple 또는 None이 필요합니다")
            for month in months:
                if (type(month) is not str
                        or re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", month) is None
                        or month[:4] == "0000"):
                    raise _invalid("applicable_months", "유효한 YYYY-MM 문자열이 필요합니다")
            if any(left >= right for left, right in zip(months, months[1:])):
                raise _invalid("applicable_months", "중복 없는 오름차순이어야 합니다")
        if type(self.benefit_evidence_refs) is not tuple or not self.benefit_evidence_refs:
            raise _invalid("benefit_evidence_refs", "하나 이상의 정확한 참조 tuple이 필요합니다")
        source_ids = {parse_evidence_ref(ref)[0] for ref in self.benefit_evidence_refs}
        if (type(self.source_bindings) is not tuple or not self.source_bindings
                or any(type(binding) is not SourceBinding for binding in self.source_bindings)):
            raise _invalid("source_bindings", "하나 이상의 정확한 SourceBinding tuple이 필요합니다")
        binding_ids = tuple(binding.source_document_id for binding in self.source_bindings)
        if any(left >= right for left, right in zip(binding_ids, binding_ids[1:])):
            raise _invalid("source_bindings", "source ID가 중복 없는 오름차순이어야 합니다")
        if type(self.dataset_version) is not str or not self.dataset_version.strip():
            raise _invalid("dataset_version", "정확한 비공백 문자열이 필요합니다")
        if (type(self.source_registry_fingerprint) is not str
                or re.fullmatch(r"[0-9a-f]{64}", self.source_registry_fingerprint) is None):
            raise _invalid("source_registry_fingerprint", "정확한 소문자16진64자리 문자열이 필요합니다")

        if self.amount_type is BenefitAmountType.FIXED:
            if self.amount_krw is None:
                raise _invalid("amount_krw", "FIXED에는 고정 금액이 필요합니다")
            if self.amount_description is not None:
                raise _invalid("amount_description", "FIXED에는 None이어야 합니다")
        elif self.amount_type is BenefitAmountType.VARIABLE:
            if self.amount_krw is not None:
                raise _invalid("amount_krw", "VARIABLE에는 None이어야 합니다")
            if self.amount_description is None:
                raise _invalid("amount_description", "VARIABLE에는 정의 설명이 필요합니다")
        else:
            if self.amount_krw is not None:
                raise _invalid("amount_krw", "UNKNOWN에는 None이어야 합니다")
            if self.amount_description is not None:
                raise _invalid("amount_description", "UNKNOWN에는 None이어야 합니다")

        if self.restriction is BenefitRestriction.RESTRICTED:
            if self.restriction_details is None:
                raise _invalid("restriction_details", "RESTRICTED에는 제한 설명이 필요합니다")
        elif self.restriction_details is not None:
            raise _invalid("restriction_details", "UNRESTRICTED/UNKNOWN에는 None이어야 합니다")
        if (self.benefit_medium is BenefitMedium.UNRESTRICTED_CASH
                and self.restriction is not BenefitRestriction.UNRESTRICTED):
            raise _invalid("restriction", "UNRESTRICTED_CASH와 제한 분류가 모순됩니다")
        if (self.benefit_medium is BenefitMedium.RESTRICTED_CASH_EQUIVALENT
                and self.restriction is not BenefitRestriction.RESTRICTED):
            raise _invalid("restriction", "RESTRICTED_CASH_EQUIVALENT와 제한 분류가 모순됩니다")
        if (self.payment_cadence is BenefitPaymentCadence.ONE_TIME
                and self.applicable_months is not None and len(self.applicable_months) != 1):
            raise _invalid("applicable_months", "ONE_TIME의 알려진 지급월은 하나여야 합니다")
        if source_ids != set(binding_ids):
            raise _invalid("source_bindings", "근거 참조의 source 집합과 정확히 대응해야 합니다")

    def to_dict(self) -> dict[str, object]:
        """저장16필드만 새 중첩 값으로 반환한다. 추론·조회·파생 상태는 없다."""
        return {
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "benefit_id": self.benefit_id,
            "benefit_version": self.benefit_version,
            "amount_type": self.amount_type.value,
            "amount_krw": self.amount_krw,
            "amount_description": self.amount_description,
            "payment_cadence": self.payment_cadence.value,
            "benefit_medium": self.benefit_medium.value,
            "restriction": self.restriction.value,
            "restriction_details": self.restriction_details,
            "applicable_months": None if self.applicable_months is None else list(self.applicable_months),
            "benefit_evidence_refs": list(self.benefit_evidence_refs),
            "source_bindings": [
                {"source_document_id": binding.source_document_id, "document_version": binding.document_version}
                for binding in self.source_bindings
            ],
            "dataset_version": self.dataset_version,
            "source_registry_fingerprint": self.source_registry_fingerprint,
        }
