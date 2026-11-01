"""Coverage 검토 대상의 불변 metadata. 실제 검토·내용 일치·완결성을 인증하지 않는다."""

from dataclasses import dataclass
from datetime import date
import re

from ..errors import PolicyDataError
from .eligibility_coverage import ApplicabilityScope


@dataclass(frozen=True, slots=True)
class InventoryCompletenessReview:
    """검토했다고 기록한 snapshot의 명시적 값. 해시 계산이나 artifact 조회는 하지 않는다."""

    review_ref: str
    policy_id: str
    scope: ApplicabilityScope
    inventory_version: str
    inventory_fingerprint: str
    dataset_version: str
    source_registry_fingerprint: str
    reviewed_at: date
    review_artifact_ref: str

    def __post_init__(self) -> None:
        for name in ("review_ref", "dataset_version", "review_artifact_ref"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise PolicyDataError(f"{name}: 비어 있지 않은 정확한 문자열이 필요합니다")
        if type(self.policy_id) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", self.policy_id) is None:
            raise PolicyDataError("policy_id: 정확한 정책 식별자 문자열이 필요합니다")
        if type(self.scope) is not ApplicabilityScope:
            raise PolicyDataError("scope: 정확한 ApplicabilityScope가 필요합니다")
        if (type(self.inventory_version) is not str
                or re.fullmatch(r"i(?:[0-9]{4}|[1-9][0-9]{4,})", self.inventory_version) is None
                or self.inventory_version == "i0000"):
            raise PolicyDataError("inventory_version: i0001부터의 명시적 버전이 필요합니다")
        for name in ("inventory_fingerprint", "source_registry_fingerprint"):
            value = getattr(self, name)
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise PolicyDataError(f"{name}: 정확한 소문자16진64자리 문자열이 필요합니다")
        if type(self.reviewed_at) is not date:
            raise PolicyDataError("reviewed_at: 정확한 date가 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """Scope는 새 dict, date는 ISO 문자열로 표현한다. 검토 승인/매칭 결과는 없다."""
        return {
            "review_ref": self.review_ref,
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "inventory_version": self.inventory_version,
            "inventory_fingerprint": self.inventory_fingerprint,
            "dataset_version": self.dataset_version,
            "source_registry_fingerprint": self.source_registry_fingerprint,
            "reviewed_at": self.reviewed_at.isoformat(),
            "review_artifact_ref": self.review_artifact_ref,
        }
