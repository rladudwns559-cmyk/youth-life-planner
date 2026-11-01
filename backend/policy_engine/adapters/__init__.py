"""독립 resolver 결과의 표현 변환. 정책 평가 routing은 제공하지 않는다."""

from .resident_registration import adapt_resident_registration_resolution

__all__ = ["adapt_resident_registration_resolution"]
