"""명시적인 정책 요구 leaf 모델. 평가 routing은 제공하지 않는다."""

from .resident_registration import ResidentRegistrationRule
from .birth_date import BirthDateRule

__all__ = ["ResidentRegistrationRule", "BirthDateRule"]
