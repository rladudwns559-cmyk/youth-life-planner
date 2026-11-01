"""M1.6G 불변 평가 입력. 바인딩/사실 선택/정책 평가를 수행하지 않는다."""

from dataclasses import dataclass, field
from datetime import date

from .errors import ContextValidationError, ProfileValidationError
from .facts import BirthFact, ResidentRegistrationFact


@dataclass(frozen=True, slots=True)
class PolicyReferenceContext:
    policy_id: str
    application_date: date | None = None

    def __post_init__(self) -> None:
        if type(self.policy_id) is not str or not self.policy_id.strip():
            raise ContextValidationError("policy_id: 비어 있지 않은 문자열이 필요합니다")
        if self.application_date is not None and type(self.application_date) is not date:
            raise ContextValidationError("application_date: date 또는 None이 필요합니다")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "policy_id": self.policy_id,
            "application_date": self.application_date.isoformat() if self.application_date is not None else None,
        }


@dataclass(frozen=True, slots=True)
class EvaluationFacts:
    resident_registrations: tuple[ResidentRegistrationFact, ...] = ()
    birth: BirthFact | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        if type(self.resident_registrations) is not tuple or any(
                type(fact) is not ResidentRegistrationFact for fact in self.resident_registrations):
            raise ProfileValidationError("resident_registrations: ResidentRegistrationFact의 tuple이 필요합니다")
        if self.birth is not None and type(self.birth) is not BirthFact:
            raise ProfileValidationError("birth: BirthFact 또는 None이 필요합니다")

    def to_dict(self) -> dict[str, object]:
        # 선택/정렬/중복 제거 없이 호출자가 제공한 의미와 순서를 보존한다.
        result: dict[str, object] = {"resident_registrations": [fact.to_dict() for fact in self.resident_registrations]}
        if self.birth is not None:
            result["birth"] = self.birth.to_dict()
        return result
