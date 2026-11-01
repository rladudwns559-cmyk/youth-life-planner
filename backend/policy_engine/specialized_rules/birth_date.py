"""양끝을 포함하는 출생일 구간의 정책 요구. 사용자 사실을 평가하지 않는다."""

from dataclasses import dataclass
from datetime import date

from ..errors import PolicyDataError


@dataclass(frozen=True, slots=True)
class BirthDateRule:
    """min_birth_date <= birth_date <= max_birth_date라는 고정 의미의 구조 모델."""

    rule_id: str
    min_birth_date: date
    max_birth_date: date
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.rule_id) is not str or not self.rule_id.strip():
            raise PolicyDataError("rule_id: 비어 있지 않은 문자열이 필요합니다")
        for field in ("min_birth_date", "max_birth_date"):
            if type(getattr(self, field)) is not date:
                raise PolicyDataError(f"{field}: 정확한 date가 필요합니다")
        if self.min_birth_date > self.max_birth_date:
            raise PolicyDataError("min_birth_date는 max_birth_date 이하여야 합니다")
        # 기존 specialized rule의 구조 계약을 유지한다. 출처 조회는 하지 않는다.
        if type(self.evidence_refs) is not tuple or not self.evidence_refs:
            raise PolicyDataError("evidence_refs: 하나 이상의 근거 참조 tuple이 필요합니다")
        if any(type(ref) is not str or not ref.strip() for ref in self.evidence_refs):
            raise PolicyDataError("evidence_refs: 비어 있지 않은 문자열이 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """새 값 표현이며 현재 JSON loader가 지원하는 입력 형식이 아니다."""
        return {
            "rule_id": self.rule_id,
            "min_birth_date": self.min_birth_date.isoformat(),
            "max_birth_date": self.max_birth_date.isoformat(),
            "evidence_refs": list(self.evidence_refs),
        }
