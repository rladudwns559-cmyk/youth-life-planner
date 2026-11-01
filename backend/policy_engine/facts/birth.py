"""생년월일 사실 하나의 불변 표현. 날짜 파싱·나이 계산·정책 판정은 하지 않는다."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from ..errors import ProfileValidationError


class BirthFactValidationError(ProfileValidationError):
    """정보 부족과 구분되는 생년월일 사실 입력 오류."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        # 생년월일이나 입력 전체를 오류 메시지에 복사하지 않는다.
        super().__init__(f"{code}: {field} 입력 계약을 확인하세요")


class BirthSource(str, Enum):
    """생년월일 정보의 출처 표식. 검증 권한이나 판정 우선순위가 아니다."""

    SELF_REPORTED = "SELF_REPORTED"
    MANUALLY_VERIFIED = "MANUALLY_VERIFIED"
    OFFICIAL_DATA = "OFFICIAL_DATA"


@dataclass(frozen=True, slots=True)
class BirthFact:
    birth_date: date | None
    source: BirthSource

    def __post_init__(self) -> None:
        if self.birth_date is not None and type(self.birth_date) is not date:
            raise BirthFactValidationError("INVALID_DATE", "birth.birth_date")
        if type(self.source) is not BirthSource:
            raise BirthFactValidationError("INVALID_SOURCE", "birth.source")

    def to_dict(self) -> dict[str, str | None]:
        """새 JSON 친화 값 표현만 반환한다. parser나 loader가 아니다."""
        return {
            "birth_date": self.birth_date.isoformat() if self.birth_date is not None else None,
            "source": self.source.value,
        }
