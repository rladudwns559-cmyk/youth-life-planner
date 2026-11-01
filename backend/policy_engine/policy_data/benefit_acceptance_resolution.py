"""검증된 supplied Context의 명시 ref 조회. 과거 기록 반환은 현재 사용 승인이 아니다."""

from ..errors import PolicyDataError
from .benefit_acceptance import PolicyBenefitAcceptance
from .benefit_acceptance_context import BenefitAcceptanceContext


def _resolve_benefit_acceptance(
    context: BenefitAcceptanceContext,
    acceptance_ref: str,
) -> PolicyBenefitAcceptance:
    """원본 기록만 반환한다. 철회된 과거 A도 조회하며 현재 철회 효과·usable은 계산하지 않는다."""
    if type(context) is not BenefitAcceptanceContext:
        raise PolicyDataError("INVALID_ACCEPTANCE_RESOLUTION_INPUT: context: 정확한 BenefitAcceptanceContext가 필요합니다")
    if type(acceptance_ref) is not str or not acceptance_ref.strip():
        raise PolicyDataError("INVALID_ACCEPTANCE_RESOLUTION_INPUT: acceptance_ref: 정확한 비공백 문자열이 필요합니다")
    for record in context.records:
        if record.acceptance_ref == acceptance_ref:
            return record
    raise PolicyDataError("ACCEPTANCE_REF_NOT_FOUND: acceptance_ref: 제공된 Context에 명시적 참조가 없습니다")
