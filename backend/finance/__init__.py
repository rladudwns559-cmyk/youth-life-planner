"""합성 금융 계산. 실제 은행 상품/정책 추천을 수행하지 않는다."""
from .recurring import RecurringSavingsInput, RecurringSavingsResult, SavingsValidationError, calculate_recurring_savings

__all__=['RecurringSavingsInput','RecurringSavingsResult','SavingsValidationError','calculate_recurring_savings']
