"""현금흐름 도메인의 타입·값 검증 오류."""


class CashflowValidationError(ValueError):
    """원본 금액을 노출하지 않고 code와 field로 오류를 식별한다."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field} 원 단위 정수 계약을 확인하세요")
