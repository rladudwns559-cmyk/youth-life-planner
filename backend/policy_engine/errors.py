"""판정 상태와 구분되는 명시적 검증 오류."""


class EngineValidationError(ValueError):
    """엔진 입력/설정의 잘못된 데이터."""


class ProfileValidationError(EngineValidationError):
    """사용자 프로필 타입 또는 값 오류."""


class PolicyDataError(EngineValidationError):
    """정책 규칙 또는 데이터셋 오류."""


class ContextValidationError(EngineValidationError):
    """평가일 또는 데이터 버전 오류."""
