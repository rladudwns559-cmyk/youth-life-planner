"""M1.6A 불변 사실 모델. 지역 키는 공식 행정코드가 아닌 내부 값이다.

지역 별칭 변환, 날짜 파싱, 기준일 선택 및 정책 판정은 이 모듈의 책임이 아니다.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from ..errors import EngineValidationError

INTERNAL_REGION_NAMESPACE = "MVP_INTERNAL_REGION_V1"

# 초기 MVP/검증용 최소 목록. 전국 행정구역 데이터가 아니다.
# 세 번째 조합은 각 키는 유효하지만 지역 쌍이 모순인 입력을 검증하기 위해 포함한다.
CANONICAL_REGION_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("GYEONGGI", "ANSAN"),
    ("GYEONGGI", "SUWON"),
    ("SEOUL", "JONGNO"),
})
_SIDO_KEYS = frozenset(sido for sido, _ in CANONICAL_REGION_PAIRS)
_SIGUNGU_KEYS = frozenset(sigungu for _, sigungu in CANONICAL_REGION_PAIRS)


class ResidentRegistrationValidationError(EngineValidationError):
    """정상 상태나 정보 부족과 구분되는 주민등록 모델 검증 오류."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        # 입력값·프로필 전체를 오류 메시지에 복사하지 않는다.
        super().__init__(f"{code}: {field} 입력 계약을 확인하세요")


@dataclass(frozen=True, slots=True)
class RegionRef:
    """완전한 내부 지역 참조. 부분 정보는 Fact.region=None으로 남긴다."""

    sido: str
    sigungu: str

    def __post_init__(self) -> None:
        for field, allowed in (("sido", _SIDO_KEYS), ("sigungu", _SIGUNGU_KEYS)):
            value = getattr(self, field)
            if type(value) is not str or value not in allowed:
                raise ResidentRegistrationValidationError("INVALID_REGION", f"region.{field}")
        if (self.sido, self.sigungu) not in CANONICAL_REGION_PAIRS:
            raise ResidentRegistrationValidationError("INVALID_REGION", "region")

    def to_dict(self) -> dict[str, str]:
        return {"sido": self.sido, "sigungu": self.sigungu}


class RegistrationSource(str, Enum):
    """사실의 출처 메타데이터. 정책 상태나 검증 권한을 나타내지 않는다."""

    SELF_REPORTED = "SELF_REPORTED"
    MANUALLY_VERIFIED = "MANUALLY_VERIFIED"
    OFFICIAL_DATA = "OFFICIAL_DATA"


@dataclass(frozen=True, slots=True)
class ResidentRegistrationFact:
    """지정한 날짜의 주민등록 사실. 누락은 허용하지만 잘못된 타입은 거부한다."""

    region: RegionRef | None
    as_of_date: date | None
    source: RegistrationSource

    def __post_init__(self) -> None:
        if self.region is not None and type(self.region) is not RegionRef:
            raise ResidentRegistrationValidationError("INVALID_REGION", "resident_registration.region")
        if self.as_of_date is not None and type(self.as_of_date) is not date:
            raise ResidentRegistrationValidationError("INVALID_DATE", "resident_registration.as_of_date")
        if type(self.source) is not RegistrationSource:
            raise ResidentRegistrationValidationError("INVALID_SOURCE", "resident_registration.source")

    def to_dict(self) -> dict[str, object]:
        """Enum과 날짜를 명시적으로 표현한다. 입력 파서나 정책 JSON 로더는 아니다."""
        return {
            "region": self.region.to_dict() if self.region is not None else None,
            "as_of_date": self.as_of_date.isoformat() if self.as_of_date is not None else None,
            "source": self.source.value,
        }
