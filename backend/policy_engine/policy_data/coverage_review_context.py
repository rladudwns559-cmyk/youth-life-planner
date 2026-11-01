"""한 정책·범위에 속한 검토 기록 집합. 현재 Coverage와의 일치는 판정하지 않는다."""

from dataclasses import dataclass
import re

from ..errors import PolicyDataError
from .coverage_review import InventoryCompletenessReview
from .eligibility_coverage import ApplicabilityScope
from .implementation_review import ImplementationBindingReview


@dataclass(frozen=True, slots=True)
class CoverageReviewContext:
    """검토 기록의 타입·소속·참조 유일성만 확인하는 불변 collection 값."""

    policy_id: str
    scope: ApplicabilityScope
    dataset_version: str
    source_registry_fingerprint: str
    implementation_fingerprint: str
    inventory_reviews: tuple[InventoryCompletenessReview, ...]
    implementation_reviews: tuple[ImplementationBindingReview, ...]

    def __post_init__(self) -> None:
        if type(self.policy_id) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", self.policy_id) is None:
            raise PolicyDataError("policy_id: 정확한 정책 식별자 문자열이 필요합니다")
        if type(self.scope) is not ApplicabilityScope:
            raise PolicyDataError("scope: 정확한 ApplicabilityScope가 필요합니다")
        if type(self.dataset_version) is not str or not self.dataset_version.strip():
            raise PolicyDataError("dataset_version: 비어 있지 않은 정확한 문자열이 필요합니다")
        for name in ("source_registry_fingerprint", "implementation_fingerprint"):
            value = getattr(self, name)
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise PolicyDataError(f"{name}: 정확한 소문자16진64자리 문자열이 필요합니다")

        collections = (("inventory_reviews", InventoryCompletenessReview),
                       ("implementation_reviews", ImplementationBindingReview))
        for name, record_type in collections:
            records = getattr(self, name)
            if type(records) is not tuple:
                raise PolicyDataError(f"{name}: 정확한 tuple이 필요합니다")
            if any(type(record) is not record_type for record in records):
                raise PolicyDataError(f"{name}: 정확한 검토 기록 타입만 허용합니다")

        seen_refs = set()
        for name, _ in collections:
            for record in getattr(self, name):
                if record.policy_id != self.policy_id:
                    raise PolicyDataError(f"{name}: record의 policy_id는 Context와 일치해야 합니다")
                if record.scope != self.scope:
                    raise PolicyDataError(f"{name}: record의 scope는 Context와 일치해야 합니다")
                if record.review_ref in seen_refs:
                    raise PolicyDataError("review_ref: 두 종류의 전체 검토 기록에서 유일해야 합니다")
                seen_refs.add(record.review_ref)

    def to_dict(self) -> dict[str, object]:
        """입력 순서를 보존한 새 중첩 snapshot. lookup·매칭·상태 파생은 하지 않는다."""
        return {
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "dataset_version": self.dataset_version,
            "source_registry_fingerprint": self.source_registry_fingerprint,
            "implementation_fingerprint": self.implementation_fingerprint,
            "inventory_reviews": [record.to_dict() for record in self.inventory_reviews],
            "implementation_reviews": [record.to_dict() for record in self.implementation_reviews],
        }
