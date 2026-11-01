"""자격조건의 의미와 근거만 보존하는 불변 값. 구현 여부나 사용자 상태를 판정하지 않는다."""

from dataclasses import dataclass
from enum import Enum
import re

from ..errors import PolicyDataError
from ..sources.models import parse_evidence_ref


class ConditionRequirement(str, Enum):
    """두 분류 모두 구현 의무가 있으며 INFORMATIONAL은 자격 inventory 밖이다."""

    REQUIRED = "REQUIRED"
    CONDITIONAL = "CONDITIONAL"


@dataclass(frozen=True, slots=True)
class RequiredCondition:
    """조건 identity와 의미 근거. scope와 실제 rule 연결은 후속 모델 책임이다."""

    condition_id: str
    meaning: str
    requirement: ConditionRequirement
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.condition_id) is not str or re.fullmatch(r"[A-Z0-9_]+", self.condition_id) is None:
            raise PolicyDataError("condition_id: 대문자·숫자·밑줄의 비어 있지 않은 문자열이 필요합니다")
        if type(self.meaning) is not str or not self.meaning.strip():
            raise PolicyDataError("meaning: 비어 있지 않은 정확한 문자열이 필요합니다")
        if type(self.requirement) is not ConditionRequirement:
            raise PolicyDataError("requirement: 정확한 ConditionRequirement가 필요합니다")
        if type(self.evidence_refs) is not tuple or not self.evidence_refs:
            raise PolicyDataError("evidence_refs: 하나 이상의 근거 참조 tuple이 필요합니다")
        for ref in self.evidence_refs:
            # 원문 조회 없이 기존 canonical source#locator 형식만 검사한다.
            # 순서·중복은 보존하고 실제 존재/버전 검증은 후속 경계에 둔다.
            parse_evidence_ref(ref)

    def to_dict(self) -> dict[str, object]:
        """Enum은 문자열, refs는 새 list로 표현하는 독립 snapshot이다."""
        return {
            "condition_id": self.condition_id,
            "meaning": self.meaning,
            "requirement": self.requirement.value,
            "evidence_refs": list(self.evidence_refs),
        }
