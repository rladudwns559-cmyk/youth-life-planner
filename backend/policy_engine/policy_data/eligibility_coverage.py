"""명시적인 정책 edition·분기 범위 값. 조건 판정이나 범위 포함관계는 계산하지 않는다."""

from dataclasses import dataclass
import re

from ..errors import PolicyDataError


@dataclass(frozen=True, slots=True)
class ApplicabilityScope:
    """quarter=None은 미입력이 아닌 연간 범위다. 두 인자를 명시해야 한다."""

    edition_id: str
    quarter: int | None

    def __post_init__(self) -> None:
        if type(self.edition_id) is not str or re.fullmatch(r"[0-9]{4}", self.edition_id) is None:
            raise PolicyDataError("edition_id: 정확한 ASCII 4자리 문자열이 필요합니다")
        if self.quarter is not None and (type(self.quarter) is not int or not 1 <= self.quarter <= 4):
            raise PolicyDataError("quarter: 정확한 1~4 정수 또는 None이 필요합니다")

    @property
    def scope_id(self) -> str:
        """두 값에서 파생하는 표시값. 별도 저장하거나 문자열로 파싱하지 않는다."""
        suffix = "ANNUAL" if self.quarter is None else f"Q{self.quarter}"
        return f"{self.edition_id}-{suffix}"

    def to_dict(self) -> dict[str, str | int | None]:
        """새 primitive snapshot이며 loader·API schema가 아니다."""
        return {"edition_id": self.edition_id, "quarter": self.quarter}
