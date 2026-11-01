"""정책·적용범위별 자격조건 목록의 불변 값. 검토 완료나 구현범위를 판정하지 않는다."""

from dataclasses import dataclass
import re

from ..errors import PolicyDataError
from .eligibility_coverage import ApplicabilityScope
from .required_condition import RequiredCondition


@dataclass(frozen=True, slots=True)
class ConditionInventory:
    """공식 의미 검토 대상 목록. review ref의 실제 존재·완결성은 외부 검증 책임이다."""

    policy_id: str
    scope: ApplicabilityScope
    inventory_version: str
    conditions: tuple[RequiredCondition, ...]
    completeness_review_ref: str | None = None

    def __post_init__(self) -> None:
        if type(self.policy_id) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", self.policy_id) is None:
            raise PolicyDataError("policy_id: 정확한 정책 식별자 문자열이 필요합니다")
        if type(self.scope) is not ApplicabilityScope:
            raise PolicyDataError("scope: 정확한 ApplicabilityScope가 필요합니다")
        if (type(self.inventory_version) is not str
                or re.fullmatch(r"i(?:[0-9]{4}|[1-9][0-9]{4,})", self.inventory_version) is None
                or self.inventory_version == "i0000"):
            raise PolicyDataError("inventory_version: i0001부터의 명시적 버전이 필요합니다")
        if type(self.conditions) is not tuple or not self.conditions:
            raise PolicyDataError("conditions: 하나 이상의 RequiredCondition tuple이 필요합니다")
        if any(type(condition) is not RequiredCondition for condition in self.conditions):
            raise PolicyDataError("conditions: 정확한 RequiredCondition만 허용합니다")
        ids = tuple(condition.condition_id for condition in self.conditions)
        if len(set(ids)) != len(ids):
            raise PolicyDataError("conditions: condition_id는 inventory 안에서 유일해야 합니다")
        if self.completeness_review_ref is not None and (
            type(self.completeness_review_ref) is not str or not self.completeness_review_ref.strip()
        ):
            raise PolicyDataError("completeness_review_ref: 비어 있지 않은 정확한 문자열 또는 None이 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """원래 순서를 유지한 새 중첩 snapshot. 원문·검토 기록 조회는 하지 않는다."""
        return {
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "inventory_version": self.inventory_version,
            "conditions": [condition.to_dict() for condition in self.conditions],
            "completeness_review_ref": self.completeness_review_ref,
        }
