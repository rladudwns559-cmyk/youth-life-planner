"""이미 계산된 integration facts의 private 불변 값. 분석·비교·상태 파생은 하지 않는다."""

from dataclasses import dataclass
import re

from ..errors import PolicyDataError
from .coverage_review_match import ImplementationReviewMatch, InventoryReviewMatch


@dataclass(frozen=True, slots=True)
class _ImplementationIntegrationFinding:
    """ID는 review_match에만 보존하고 해당 subtree 지문과 함께 운반한다."""

    subtree_fingerprint: str
    review_match: ImplementationReviewMatch

    def __post_init__(self) -> None:
        if type(self.subtree_fingerprint) is not str or re.fullmatch(r"[0-9a-f]{64}", self.subtree_fingerprint) is None:
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: subtree_fingerprint: 정확한 소문자16진64자리 문자열이 필요합니다")
        if type(self.review_match) is not ImplementationReviewMatch:
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: review_match: 정확한 ImplementationReviewMatch가 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """저장 필드만 새 중첩 snapshot으로 반환한다. 원본 match를 재생성하지 않는다."""
        return {
            "subtree_fingerprint": self.subtree_fingerprint,
            "review_match": self.review_match.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class _CoverageIntegrationFindings:
    """정상 integration이 전달할 facts의 로컬 정합성만 검사한다."""

    missing_condition_ids: tuple[str, ...]
    unmapped_rule_ids: tuple[str, ...]
    composition_gap_group_ids: tuple[str, ...]
    inventory_fingerprint: str
    policy_tree_fingerprint: str
    inventory_review_match: InventoryReviewMatch
    implementation_findings: tuple[_ImplementationIntegrationFinding, ...]

    def __post_init__(self) -> None:
        for name in ("missing_condition_ids", "unmapped_rule_ids", "composition_gap_group_ids"):
            ids = getattr(self, name)
            if type(ids) is not tuple:
                raise PolicyDataError(f"INVALID_INTEGRATION_FINDINGS: {name}: 정확한 tuple이 필요합니다")
            for value in ids:
                if type(value) is not str or not value.strip():
                    raise PolicyDataError(f"INVALID_INTEGRATION_FINDINGS: {name}: 정확한 비공백 문자열이 필요합니다")
                if name == "missing_condition_ids" and re.fullmatch(r"[A-Z0-9_]+", value) is None:
                    raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: missing_condition_ids: canonical condition ID가 필요합니다")
            if len(ids) != len(set(ids)):
                raise PolicyDataError(f"INVALID_INTEGRATION_FINDINGS: {name}: 중복 ID는 허용하지 않습니다")

        for name in ("inventory_fingerprint", "policy_tree_fingerprint"):
            value = getattr(self, name)
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise PolicyDataError(f"INVALID_INTEGRATION_FINDINGS: {name}: 정확한 소문자16진64자리 문자열이 필요합니다")
        if type(self.inventory_review_match) is not InventoryReviewMatch:
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: inventory_review_match: 정확한 InventoryReviewMatch가 필요합니다")
        if type(self.implementation_findings) is not tuple:
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: implementation_findings: 정확한 tuple이 필요합니다")
        if any(type(finding) is not _ImplementationIntegrationFinding for finding in self.implementation_findings):
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: implementation_findings: 정확한 Binding 단위 finding이 필요합니다")

        condition_ids = tuple(finding.review_match.condition_id for finding in self.implementation_findings)
        if any(left >= right for left, right in zip(condition_ids, condition_ids[1:])):
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: implementation_findings: condition_id는 중복 없이 오름차순이어야 합니다")
        if set(self.missing_condition_ids).intersection(condition_ids):
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: missing_condition_ids: existing finding의 condition과 겹칠 수 없습니다")
        if not self.missing_condition_ids and (self.unmapped_rule_ids or self.composition_gap_group_ids):
            raise PolicyDataError("INVALID_INTEGRATION_FINDINGS: missing_condition_ids: 미매핑 또는 gap이 있으면 missing이 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """세 ID 순서를 보존하고 하위 값 표현을 재사용한 새 dict/list를 반환한다."""
        return {
            "missing_condition_ids": list(self.missing_condition_ids),
            "unmapped_rule_ids": list(self.unmapped_rule_ids),
            "composition_gap_group_ids": list(self.composition_gap_group_ids),
            "inventory_fingerprint": self.inventory_fingerprint,
            "policy_tree_fingerprint": self.policy_tree_fingerprint,
            "inventory_review_match": self.inventory_review_match.to_dict(),
            "implementation_findings": [finding.to_dict() for finding in self.implementation_findings],
        }
