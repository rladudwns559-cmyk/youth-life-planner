"""월 현금흐름의 불변 값 모델. 계산·정책 판정·혜택 승인은 수행하지 않는다."""

from dataclasses import dataclass, fields

from .errors import CashflowValidationError


def _validate_krw(
    value: object, field: str, *, allow_none: bool = False, allow_negative: bool = False,
) -> None:
    if value is None and allow_none:
        return
    if type(value) is not int:
        raise CashflowValidationError("INVALID_KRW_TYPE", field)
    if value < 0 and not allow_negative:
        raise CashflowValidationError("NEGATIVE_KRW_AMOUNT", field)


@dataclass(frozen=True, slots=True)
class CashflowInput:
    """같은 월의 명시적 금액. 소득은 정책 심사용 소득과 별개다."""

    monthly_income: int
    monthly_rent: int
    monthly_fixed_expenses: int
    other_monthly_expenses: int
    user_savings_capacity: int | None = None
    monthly_policy_cash_benefit: int = 0

    def __post_init__(self) -> None:
        for field in fields(self):
            _validate_krw(getattr(self, field.name), field.name,
                          allow_none=field.name == "user_savings_capacity")

    def to_dict(self) -> dict[str, int | None]:
        """정확한 int/None의 새 snapshot. API parser나 금액 변환기가 아니다."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class CashflowResult:
    """명시적으로 구성한 결과 값. 산술 정합성은 후속 계산 함수의 책임이다."""

    monthly_income: int
    essential_monthly_expenses: int
    other_monthly_expenses: int
    total_monthly_expenses: int
    policy_benefit_applied: int
    total_monthly_income: int
    disposable_before_policy: int
    disposable_after_policy: int
    user_savings_capacity: int | None
    savable_amount: int

    def __post_init__(self) -> None:
        # 타입·부호만 검사한다. 합계·가처분액·저축 상한의 산식을 재실행하지 않는다.
        for field in fields(self):
            _validate_krw(
                getattr(self, field.name), field.name,
                allow_none=field.name == "user_savings_capacity",
                allow_negative=field.name in ("disposable_before_policy", "disposable_after_policy"),
            )

    def to_dict(self) -> dict[str, int | None]:
        """새 primitive snapshot. 사용자 결과를 저장·로그·외부 전송하지 않는다."""
        return {field.name: getattr(self, field.name) for field in fields(self)}
