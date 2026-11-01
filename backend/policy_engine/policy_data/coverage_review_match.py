"""Review matching 결과의 불변 값. 실제 조회·버전/지문 비교는 수행하지 않는다."""

from dataclasses import dataclass
from enum import Enum
import re

from ..errors import PolicyDataError


class ReviewMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    MISSING = "MISSING"
    STALE = "STALE"


class ReviewMissingReason(str, Enum):
    NO_REVIEW_CONTEXT = "NO_REVIEW_CONTEXT"
    INVENTORY_REVIEW_NOT_DECLARED = "INVENTORY_REVIEW_NOT_DECLARED"


class ReviewStaleReason(str, Enum):
    INVENTORY_VERSION_CHANGED = "INVENTORY_VERSION_CHANGED"
    RULE_VERSION_CHANGED = "RULE_VERSION_CHANGED"
    DATASET_VERSION_CHANGED = "DATASET_VERSION_CHANGED"
    IMPLEMENTATION_CHANGED = "IMPLEMENTATION_CHANGED"


def _validate_reason_tuple(value: object, enum_type: type[Enum], name: str) -> None:
    if type(value) is not tuple or any(type(reason) is not enum_type for reason in value):
        raise PolicyDataError(f"{name}: 정확한 사유 Enum의 tuple이 필요합니다")
    order = tuple(enum_type)
    positions = tuple(order.index(reason) for reason in value)
    if any(left >= right for left, right in zip(positions, positions[1:])):
        raise PolicyDataError(f"{name}: 중복 없이 canonical 순서여야 합니다")


def _validate_outcome(
    review_ref: str | None,
    status: ReviewMatchStatus,
    stale_reasons: tuple[ReviewStaleReason, ...],
    missing_reasons: tuple[ReviewMissingReason, ...],
) -> None:
    if review_ref is not None and (type(review_ref) is not str or not review_ref.strip()):
        raise PolicyDataError("review_ref: 비어 있지 않은 정확한 문자열 또는 None이 필요합니다")
    if type(status) is not ReviewMatchStatus:
        raise PolicyDataError("status: 정확한 ReviewMatchStatus가 필요합니다")
    _validate_reason_tuple(stale_reasons, ReviewStaleReason, "stale_reasons")
    _validate_reason_tuple(missing_reasons, ReviewMissingReason, "missing_reasons")
    if status is ReviewMatchStatus.MATCHED:
        if review_ref is None or stale_reasons or missing_reasons:
            raise PolicyDataError("MATCHED: review_ref가 있고 두 사유 tuple이 비어야 합니다")
    elif status is ReviewMatchStatus.MISSING:
        if stale_reasons or not missing_reasons:
            raise PolicyDataError("MISSING: missing_reasons만 하나 이상 필요합니다")
    elif review_ref is None or not stale_reasons or missing_reasons:
        raise PolicyDataError("STALE: review_ref와 stale_reasons만 하나 이상 필요합니다")


@dataclass(frozen=True, slots=True)
class InventoryReviewMatch:
    """Inventory 검토 결과의 명시 값. 생성 성공은 실제 matching 성공의 인증이 아니다."""

    review_ref: str | None
    status: ReviewMatchStatus
    stale_reasons: tuple[ReviewStaleReason, ...]
    missing_reasons: tuple[ReviewMissingReason, ...]

    def __post_init__(self) -> None:
        _validate_outcome(self.review_ref, self.status, self.stale_reasons, self.missing_reasons)
        if any(reason not in (ReviewStaleReason.INVENTORY_VERSION_CHANGED, ReviewStaleReason.DATASET_VERSION_CHANGED)
               for reason in self.stale_reasons):
            raise PolicyDataError("stale_reasons: Inventory에는 inventory/dataset 변경 사유만 허용합니다")
        if self.status is ReviewMatchStatus.MISSING:
            if self.review_ref is None:
                if ReviewMissingReason.INVENTORY_REVIEW_NOT_DECLARED not in self.missing_reasons:
                    raise PolicyDataError("missing_reasons: ref=None에는 INVENTORY_REVIEW_NOT_DECLARED가 필요합니다")
            elif self.missing_reasons != (ReviewMissingReason.NO_REVIEW_CONTEXT,):
                raise PolicyDataError("missing_reasons: 명시 ref가 있으면 NO_REVIEW_CONTEXT만 허용합니다")

    def to_dict(self) -> dict[str, object]:
        return {
            "review_ref": self.review_ref,
            "status": self.status.value,
            "stale_reasons": [reason.value for reason in self.stale_reasons],
            "missing_reasons": [reason.value for reason in self.missing_reasons],
        }


@dataclass(frozen=True, slots=True)
class ImplementationReviewMatch:
    """한 condition/root의 명시 검토 결과. Binding/Review 객체는 보관하지 않는다."""

    condition_id: str
    rule_root_id: str
    review_ref: str
    status: ReviewMatchStatus
    stale_reasons: tuple[ReviewStaleReason, ...]
    missing_reasons: tuple[ReviewMissingReason, ...]

    def __post_init__(self) -> None:
        if type(self.condition_id) is not str or re.fullmatch(r"[A-Z0-9_]+", self.condition_id) is None:
            raise PolicyDataError("condition_id: 대문자·숫자·밑줄의 비어 있지 않은 문자열이 필요합니다")
        if type(self.rule_root_id) is not str or not self.rule_root_id.strip():
            raise PolicyDataError("rule_root_id: 비어 있지 않은 정확한 문자열이 필요합니다")
        if self.review_ref is None:
            raise PolicyDataError("review_ref: Implementation에는 명시적 참조가 필요합니다")
        _validate_outcome(self.review_ref, self.status, self.stale_reasons, self.missing_reasons)
        if self.status is ReviewMatchStatus.MISSING and self.missing_reasons != (ReviewMissingReason.NO_REVIEW_CONTEXT,):
            raise PolicyDataError("missing_reasons: Implementation에는 NO_REVIEW_CONTEXT만 허용합니다")

    def to_dict(self) -> dict[str, object]:
        return {
            "condition_id": self.condition_id,
            "rule_root_id": self.rule_root_id,
            "review_ref": self.review_ref,
            "status": self.status.value,
            "stale_reasons": [reason.value for reason in self.stale_reasons],
            "missing_reasons": [reason.value for reason in self.missing_reasons],
        }
