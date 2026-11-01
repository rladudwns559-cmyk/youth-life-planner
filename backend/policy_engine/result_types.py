"""M1.6D 결과 전용 불변 값. Fact/Resolution/프로필을 보유하지 않는다."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .errors import EngineValidationError
from .facts.birth import BirthSource
from .facts.resident_registration import CANONICAL_REGION_PAIRS, RegistrationSource


class ResultValidationError(EngineValidationError):
    """정상 상태가 아닌 결과 표현 계약 위반. 원본 값을 메시지에 넣지 않는다."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field} 결과 계약을 확인하세요")


def validate_optional_date(value: object, field: str) -> None:
    if value is not None and type(value) is not date:
        raise ResultValidationError("INVALID_RESULT_DATE", field)


@dataclass(frozen=True, slots=True)
class RegionSnapshot:
    """완전한 내부 지역 값의 결과 스냅샷. 공식 행정코드가 아니다."""

    sido: str
    sigungu: str

    def __post_init__(self) -> None:
        if (type(self.sido) is not str or type(self.sigungu) is not str
                or (self.sido, self.sigungu) not in CANONICAL_REGION_PAIRS):
            raise ResultValidationError("INVALID_RESULT_REGION", "region")


class ReferenceDateSource(str, Enum):
    APPLICATION_DATE = "APPLICATION_DATE"


class EvidenceFactType(str, Enum):
    RESIDENT_REGISTRATION = "RESIDENT_REGISTRATION"


@dataclass(frozen=True, slots=True)
class ResidentRegistrationCondition:
    required_region: RegionSnapshot
    reference_date_source: ReferenceDateSource

    def __post_init__(self) -> None:
        if type(self.required_region) is not RegionSnapshot:
            raise ResultValidationError("INVALID_RESULT_REGION", "required_region")
        if type(self.reference_date_source) is not ReferenceDateSource:
            raise ResultValidationError("INVALID_REFERENCE_DATE_SOURCE", "reference_date_source")


@dataclass(frozen=True, slots=True)
class EvaluationEvidence:
    """선택된 사용자 사실 한 개의 최소 값. 정책 원문 근거와 구분한다."""

    source: RegistrationSource
    fact_as_of_date: date | None
    region: RegionSnapshot | None
    fact_type: EvidenceFactType = EvidenceFactType.RESIDENT_REGISTRATION
    field_path: str = "resident_registration.region"

    def __post_init__(self) -> None:
        if type(self.source) is not RegistrationSource:
            raise ResultValidationError("INVALID_EVIDENCE_SOURCE", "source")
        validate_optional_date(self.fact_as_of_date, "fact_as_of_date")
        if self.region is not None and type(self.region) is not RegionSnapshot:
            raise ResultValidationError("INVALID_RESULT_REGION", "evidence.region")
        if type(self.fact_type) is not EvidenceFactType:
            raise ResultValidationError("INVALID_EVIDENCE_FACT_TYPE", "fact_type")
        if type(self.field_path) is not str or self.field_path != "resident_registration.region":
            raise ResultValidationError("INVALID_EVIDENCE_FIELD_PATH", "field_path")


@dataclass(frozen=True, slots=True)
class ResidentRegistrationDetails:
    """정책 기준일과 선택된 근거. 평가일은 PolicyEvaluation.context에 둔다."""

    reference_date: date | None = None
    evidence: tuple[EvaluationEvidence, ...] = ()

    def __post_init__(self) -> None:
        validate_optional_date(self.reference_date, "reference_date")
        if type(self.evidence) is not tuple or any(type(e) is not EvaluationEvidence for e in self.evidence):
            raise ResultValidationError("INVALID_RESULT_EVIDENCE", "evidence")
        # 선택 근거는 요구 날짜의 스냅샷이어야 한다. 누락/다른 날을 보간하지 않는다.
        if self.evidence and (self.reference_date is None or any(
                e.fact_as_of_date != self.reference_date for e in self.evidence)):
            raise ResultValidationError("RESULT_EVIDENCE_DATE_MISMATCH", "evidence")
        regions = {e.region for e in self.evidence if e.region is not None}
        if len(regions) > 1:
            raise ResultValidationError("CONFLICTING_RESULT_EVIDENCE", "evidence")


class BirthDateReasonCode(str, Enum):
    BIRTH_DATE_WITHIN_RANGE = "BIRTH_DATE_WITHIN_RANGE"
    BIRTH_DATE_BEFORE_RANGE = "BIRTH_DATE_BEFORE_RANGE"
    BIRTH_DATE_AFTER_RANGE = "BIRTH_DATE_AFTER_RANGE"
    BIRTH_DATE_MISSING = "BIRTH_DATE_MISSING"


@dataclass(frozen=True, slots=True)
class BirthDateCondition:
    """양끝을 포함하는 요구 구간. 사용자 사실이나 기준일은 보관하지 않는다."""

    min_birth_date: date
    max_birth_date: date

    def __post_init__(self) -> None:
        for field in ("min_birth_date", "max_birth_date"):
            if type(getattr(self, field)) is not date:
                raise ResultValidationError("INVALID_RESULT_DATE", field)
        if self.min_birth_date > self.max_birth_date:
            raise ResultValidationError("INVALID_BIRTH_DATE_RANGE", "min_birth_date/max_birth_date")


@dataclass(frozen=True, slots=True)
class BirthDateDetails:
    """사용자 사실의 출처만 보관한다. 날짜와 정책 근거는 중복하지 않는다."""

    birth_source: BirthSource | None

    def __post_init__(self) -> None:
        if self.birth_source is not None and type(self.birth_source) is not BirthSource:
            raise ResultValidationError("INVALID_BIRTH_SOURCE", "birth_source")


EvaluationDetails = ResidentRegistrationDetails | BirthDateDetails
