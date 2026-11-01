"""정책 평가와 독립적인 주민등록·생년월일 사실 모델 및 입력 검증."""

from .birth import BirthFact, BirthFactValidationError, BirthSource

from .resident_registration import (
    CANONICAL_REGION_PAIRS,
    INTERNAL_REGION_NAMESPACE,
    RegionRef,
    RegistrationSource,
    ResidentRegistrationFact,
    ResidentRegistrationValidationError,
)

__all__ = [
    "BirthFact",
    "BirthFactValidationError",
    "BirthSource",
    "CANONICAL_REGION_PAIRS",
    "INTERNAL_REGION_NAMESPACE",
    "RegionRef",
    "RegistrationSource",
    "ResidentRegistrationFact",
    "ResidentRegistrationValidationError",
]
