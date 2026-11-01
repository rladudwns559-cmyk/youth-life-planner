"""PolicyRule에 연결하지 않은 독립 사실 판정 함수."""

from .resident_registration import (
    ResidentRegistrationReasonCode,
    ResidentRegistrationResolution,
    resolve_resident_registration,
)

__all__ = [
    "ResidentRegistrationReasonCode",
    "ResidentRegistrationResolution",
    "resolve_resident_registration",
]
