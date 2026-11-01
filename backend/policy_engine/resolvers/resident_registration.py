"""정확한 기준일의 주민등록 사실만 판정한다. 외부 I/O·시간 조회·추정 없음."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum

from ..facts import (
    RegionRef,
    RegistrationSource,
    ResidentRegistrationFact,
    ResidentRegistrationValidationError,
)
from ..models import Status


class ResidentRegistrationReasonCode(str, Enum):
    RESIDENT_REGION_MATCH = "RESIDENT_REGION_MATCH"
    RESIDENT_REGION_MISMATCH = "RESIDENT_REGION_MISMATCH"
    RESIDENT_REGISTRATION_MISSING = "RESIDENT_REGISTRATION_MISSING"
    RESIDENT_REGION_MISSING = "RESIDENT_REGION_MISSING"
    RESIDENT_REGISTRATION_DATE_MISSING = "RESIDENT_REGISTRATION_DATE_MISSING"
    RESIDENT_REGISTRATION_DATE_UNPROVEN = "RESIDENT_REGISTRATION_DATE_UNPROVEN"
    RESIDENT_REFERENCE_DATE_MISSING = "RESIDENT_REFERENCE_DATE_MISSING"
    RESIDENT_REFERENCE_DATE_IN_FUTURE = "RESIDENT_REFERENCE_DATE_IN_FUTURE"


@dataclass(frozen=True, slots=True)
class ResidentRegistrationResolution:
    status: Status
    reason_code: ResidentRegistrationReasonCode
    required_region: RegionRef
    reference_date: date | None
    evaluation_date: date
    resolved_region: RegionRef | None
    fact_as_of_date: date | None
    missing_fields: tuple[str, ...]
    used_facts: tuple[ResidentRegistrationFact, ...]

    @property
    def sources(self) -> tuple[RegistrationSource, ...]:
        # 사전순은 출력 재현성 목적이며 출처 신뢰도 우선순위가 아니다.
        return tuple(sorted({fact.source for fact in self.used_facts}, key=lambda source: source.value))

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "reason_code": self.reason_code.value,
            "required_region": self.required_region.to_dict(),
            "reference_date": self.reference_date.isoformat() if self.reference_date is not None else None,
            "evaluation_date": self.evaluation_date.isoformat(),
            "resolved_region": self.resolved_region.to_dict() if self.resolved_region is not None else None,
            "fact_as_of_date": self.fact_as_of_date.isoformat() if self.fact_as_of_date is not None else None,
            "missing_fields": list(self.missing_fields),
            "used_facts": [fact.to_dict() for fact in self.used_facts],
            "sources": [source.value for source in self.sources],
        }


def _validate_inputs(
    facts: Sequence[ResidentRegistrationFact],
    required_region: RegionRef,
    reference_date: date | None,
    evaluation_date: date,
) -> tuple[ResidentRegistrationFact, ...]:
    if type(required_region) is not RegionRef:
        raise ResidentRegistrationValidationError("INVALID_REQUIRED_REGION", "required_region")
    if reference_date is not None and type(reference_date) is not date:
        raise ResidentRegistrationValidationError("INVALID_DATE", "reference_date")
    if type(evaluation_date) is not date:
        raise ResidentRegistrationValidationError("INVALID_EVALUATION_DATE", "evaluation_date")
    if not isinstance(facts, Sequence) or isinstance(facts, (str, bytes, bytearray)):
        raise ResidentRegistrationValidationError("INVALID_RESIDENT_REGISTRATION_FACT", "resident_registration_facts")
    snapshot = tuple(facts)
    if any(type(fact) is not ResidentRegistrationFact for fact in snapshot):
        raise ResidentRegistrationValidationError("INVALID_RESIDENT_REGISTRATION_FACT", "resident_registration_facts")
    return snapshot


def _reject_conflicts(facts: tuple[ResidentRegistrationFact, ...]) -> None:
    regions_by_date: dict[date, RegionRef] = {}
    for fact in facts:
        if fact.as_of_date is None or fact.region is None:
            continue
        previous = regions_by_date.get(fact.as_of_date)
        if previous is not None and previous != fact.region:
            raise ResidentRegistrationValidationError(
                "CONFLICTING_RESIDENT_REGISTRATION_FACTS", "resident_registration_facts",
            )
        regions_by_date[fact.as_of_date] = fact.region


def _canonical_evidence(facts: tuple[ResidentRegistrationFact, ...]) -> tuple[ResidentRegistrationFact, ...]:
    def key(fact: ResidentRegistrationFact) -> tuple[str, str, str, str]:
        return (
            fact.as_of_date.isoformat() if fact.as_of_date is not None else "",
            fact.region.sido if fact.region is not None else "",
            fact.region.sigungu if fact.region is not None else "",
            fact.source.value,
        )

    return tuple(sorted(set(facts), key=key))


def resolve_resident_registration(
    facts: Sequence[ResidentRegistrationFact],
    *,
    required_region: RegionRef,
    reference_date: date | None,
    evaluation_date: date,
) -> ResidentRegistrationResolution:
    """동일 사용자의 fact 묶음을 검토한다. 날짜·지역 별칭을 변환하지 않는다.

    필수 조건값과 모든 후보의 구조를 먼저 검증한다. 알려진 같은 날짜의
    상충 지역은 기준일 밖의 자료라도 오류이며 source로 해결하지 않는다.
    """
    snapshot = _validate_inputs(facts, required_region, reference_date, evaluation_date)
    _reject_conflicts(snapshot)

    def result(
        status: Status,
        reason: ResidentRegistrationReasonCode,
        missing_fields: tuple[str, ...] = (),
        evidence: tuple[ResidentRegistrationFact, ...] = (),
    ) -> ResidentRegistrationResolution:
        used = _canonical_evidence(evidence)
        return ResidentRegistrationResolution(
            status=status,
            reason_code=reason,
            required_region=required_region,
            reference_date=reference_date,
            evaluation_date=evaluation_date,
            resolved_region=used[0].region if used else None,
            fact_as_of_date=used[0].as_of_date if used else None,
            missing_fields=tuple(sorted(set(missing_fields))),
            used_facts=used,
        )

    reasons = ResidentRegistrationReasonCode
    if reference_date is None:
        return result(Status.UNKNOWN, reasons.RESIDENT_REFERENCE_DATE_MISSING, ("reference_date",))
    if reference_date > evaluation_date:
        return result(Status.UNKNOWN, reasons.RESIDENT_REFERENCE_DATE_IN_FUTURE)
    if not snapshot:
        return result(Status.UNKNOWN, reasons.RESIDENT_REGISTRATION_MISSING, ("resident_registration",))

    exact = tuple(fact for fact in snapshot if fact.as_of_date == reference_date)
    if not exact:
        if any(fact.as_of_date is None for fact in snapshot):
            return result(
                Status.UNKNOWN, reasons.RESIDENT_REGISTRATION_DATE_MISSING,
                ("resident_registration.as_of_date",),
            )
        return result(Status.UNKNOWN, reasons.RESIDENT_REGISTRATION_DATE_UNPROVEN)

    known_region = tuple(fact for fact in exact if fact.region is not None)
    if not known_region:
        return result(
            Status.UNKNOWN, reasons.RESIDENT_REGION_MISSING,
            ("resident_registration.region",), exact,
        )

    if known_region[0].region == required_region:
        return result(Status.PASS, reasons.RESIDENT_REGION_MATCH, evidence=known_region)
    return result(Status.FAIL, reasons.RESIDENT_REGION_MISMATCH, evidence=known_region)
