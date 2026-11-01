"""조건 의미 ID와 구현 subtree root ID 사이의 불변 참조 값."""

from dataclasses import dataclass
import re

from ..errors import PolicyDataError


@dataclass(frozen=True, slots=True)
class ConditionBinding:
    """참조 구조만 검증한다. inventory·tree·검토 기록의 존재는 확인하지 않는다."""

    condition_id: str
    rule_root_id: str
    implementation_review_ref: str

    def __post_init__(self) -> None:
        if type(self.condition_id) is not str or re.fullmatch(r"[A-Z0-9_]+", self.condition_id) is None:
            raise PolicyDataError("condition_id: 대문자·숫자·밑줄의 비어 있지 않은 문자열이 필요합니다")
        if type(self.rule_root_id) is not str or not self.rule_root_id.strip():
            raise PolicyDataError("rule_root_id: 비어 있지 않은 정확한 문자열이 필요합니다")
        if type(self.implementation_review_ref) is not str or not self.implementation_review_ref.strip():
            raise PolicyDataError("implementation_review_ref: 비어 있지 않은 정확한 문자열이 필요합니다")

    def to_dict(self) -> dict[str, str]:
        """원래 세 문자열을 새 snapshot으로 반환한다. parser나 검토 승인 결과가 아니다."""
        return {
            "condition_id": self.condition_id,
            "rule_root_id": self.rule_root_id,
            "implementation_review_ref": self.implementation_review_ref,
        }
