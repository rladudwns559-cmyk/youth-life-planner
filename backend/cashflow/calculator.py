"""검증된 월 금액만 사용하는 결정적 현금흐름 계산."""

from .errors import CashflowValidationError
from .models import CashflowInput, CashflowResult


def calculate_cashflow(cashflow_input: CashflowInput) -> CashflowResult:
    """적자는 보존하고 저축 투입액만 제한한다. 혜택의 적격성은 외부 계약이다."""
    if type(cashflow_input) is not CashflowInput:
        raise CashflowValidationError("INVALID_CASHFLOW_INPUT_TYPE", "cashflow_input")

    essential = cashflow_input.monthly_rent + cashflow_input.monthly_fixed_expenses
    expenses = essential + cashflow_input.other_monthly_expenses
    benefit = cashflow_input.monthly_policy_cash_benefit
    income = cashflow_input.monthly_income + benefit
    before = cashflow_input.monthly_income - expenses
    after = income - expenses
    capacity = cashflow_input.user_savings_capacity
    savable = max(0, after) if capacity is None else max(0, min(after, capacity))

    return CashflowResult(
        monthly_income=cashflow_input.monthly_income,
        essential_monthly_expenses=essential,
        other_monthly_expenses=cashflow_input.other_monthly_expenses,
        total_monthly_expenses=expenses,
        policy_benefit_applied=benefit,
        total_monthly_income=income,
        disposable_before_policy=before,
        disposable_after_policy=after,
        user_savings_capacity=capacity,
        savable_amount=savable,
    )
