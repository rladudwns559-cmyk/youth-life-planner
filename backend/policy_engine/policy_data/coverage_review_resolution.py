"""제공된 검토 집합의 exact ref → typed record 조회. 현재 대상과 matching하지 않는다."""

from ..errors import PolicyDataError
from .coverage_review import InventoryCompletenessReview
from .coverage_review_context import CoverageReviewContext
from .implementation_review import ImplementationBindingReview


def _validate_resolution_input(context: CoverageReviewContext, review_ref: str) -> None:
    if type(context) is not CoverageReviewContext:
        raise PolicyDataError("INVALID_MATCH_INPUT: context는 정확한 CoverageReviewContext여야 합니다")
    if type(review_ref) is not str or not review_ref.strip():
        raise PolicyDataError("INVALID_MATCH_INPUT: review_ref는 비어 있지 않은 정확한 문자열이어야 합니다")


def _resolve_inventory_review(context: CoverageReviewContext, review_ref: str) -> InventoryCompletenessReview:
    """Context의 종류·전역 ref 유일성 불변조건을 전제로 원래 Inventory record를 반환한다."""
    _validate_resolution_input(context, review_ref)
    for record in context.inventory_reviews:
        if record.review_ref == review_ref:
            return record
    if any(record.review_ref == review_ref for record in context.implementation_reviews):
        raise PolicyDataError("WRONG_REVIEW_TYPE: Inventory 검토 참조가 Implementation record를 가리킵니다")
    raise PolicyDataError("REVIEW_REF_NOT_FOUND: 제공된 Context에 명시적 검토 참조가 없습니다")


def _resolve_implementation_review(context: CoverageReviewContext, review_ref: str) -> ImplementationBindingReview:
    """Context의 종류·전역 ref 유일성 불변조건을 전제로 원래 Implementation record를 반환한다."""
    _validate_resolution_input(context, review_ref)
    for record in context.implementation_reviews:
        if record.review_ref == review_ref:
            return record
    if any(record.review_ref == review_ref for record in context.inventory_reviews):
        raise PolicyDataError("WRONG_REVIEW_TYPE: Implementation 검토 참조가 Inventory record를 가리킵니다")
    raise PolicyDataError("REVIEW_REF_NOT_FOUND: 제공된 Context에 명시적 검토 참조가 없습니다")
