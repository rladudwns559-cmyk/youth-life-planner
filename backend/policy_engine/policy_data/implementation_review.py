"""조건과 구현 subtree 사이의 검토 대상 확인본 metadata. 구현의 정답을 인증하지 않는다."""

from dataclasses import dataclass
from datetime import date
import re

from ..errors import PolicyDataError
from .eligibility_coverage import ApplicabilityScope


@dataclass(frozen=True, slots=True)
class ImplementationBindingReview:
    """명시적으로 전달한 검토 주장을 보존한다. tree 조회·지문 계산·매칭은 하지 않는다."""

    review_ref: str
    policy_id: str
    scope: ApplicabilityScope
    condition_id: str
    rule_root_id: str
    inventory_version: str
    inventory_fingerprint: str
    rule_version: str
    policy_tree_fingerprint: str
    subtree_fingerprint: str
    dataset_version: str
    source_registry_fingerprint: str
    implementation_fingerprint: str
    reviewed_at: date
    review_artifact_ref: str

    def __post_init__(self) -> None:
        for name in ("review_ref", "rule_root_id", "rule_version", "dataset_version", "review_artifact_ref"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise PolicyDataError(f"{name}: 비어 있지 않은 정확한 문자열이 필요합니다")
        if type(self.policy_id) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", self.policy_id) is None:
            raise PolicyDataError("policy_id: 정확한 정책 식별자 문자열이 필요합니다")
        if type(self.scope) is not ApplicabilityScope:
            raise PolicyDataError("scope: 정확한 ApplicabilityScope가 필요합니다")
        if type(self.condition_id) is not str or re.fullmatch(r"[A-Z0-9_]+", self.condition_id) is None:
            raise PolicyDataError("condition_id: 대문자·숫자·밑줄의 비어 있지 않은 문자열이 필요합니다")
        if (type(self.inventory_version) is not str
                or re.fullmatch(r"i(?:[0-9]{4}|[1-9][0-9]{4,})", self.inventory_version) is None
                or self.inventory_version == "i0000"):
            raise PolicyDataError("inventory_version: i0001부터의 명시적 버전이 필요합니다")
        for name in ("inventory_fingerprint", "policy_tree_fingerprint", "subtree_fingerprint",
                     "source_registry_fingerprint", "implementation_fingerprint"):
            value = getattr(self, name)
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise PolicyDataError(f"{name}: 정확한 소문자16진64자리 문자열이 필요합니다")
        if type(self.reviewed_at) is not date:
            raise PolicyDataError("reviewed_at: 정확한 date가 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """원래 값과 새 scope snapshot, ISO date를 반환한다. 검토 결과는 계산하지 않는다."""
        return {
            "review_ref": self.review_ref,
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "condition_id": self.condition_id,
            "rule_root_id": self.rule_root_id,
            "inventory_version": self.inventory_version,
            "inventory_fingerprint": self.inventory_fingerprint,
            "rule_version": self.rule_version,
            "policy_tree_fingerprint": self.policy_tree_fingerprint,
            "subtree_fingerprint": self.subtree_fingerprint,
            "dataset_version": self.dataset_version,
            "source_registry_fingerprint": self.source_registry_fingerprint,
            "implementation_fingerprint": self.implementation_fingerprint,
            "reviewed_at": self.reviewed_at.isoformat(),
            "review_artifact_ref": self.review_artifact_ref,
        }
