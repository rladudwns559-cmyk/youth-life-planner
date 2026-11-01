"""Inventory·Implementation 검토와 현재 확인본의 순수 비교. 지문은 호출자가 공급한다."""

import re

from ..errors import PolicyDataError
from .condition_binding import ConditionBinding
from .condition_inventory import ConditionInventory
from .coverage_review_context import CoverageReviewContext
from .coverage_review_match import (
    ImplementationReviewMatch, InventoryReviewMatch, ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason,
)
from .coverage_review_resolution import _resolve_implementation_review, _resolve_inventory_review


def _match_inventory_review(
    inventory: ConditionInventory,
    review_context: CoverageReviewContext | None,
    *,
    current_inventory_fingerprint: str,
) -> InventoryReviewMatch:
    """명시 ref 하나를 비교한다. 생성된 Context의 종류·소속·ref 유일성을 전제한다."""
    if type(inventory) is not ConditionInventory:
        raise PolicyDataError("INVALID_MATCH_INPUT: inventory는 정확한 ConditionInventory여야 합니다")
    if review_context is not None and type(review_context) is not CoverageReviewContext:
        raise PolicyDataError("INVALID_MATCH_INPUT: review_context는 정확한 CoverageReviewContext 또는 None이어야 합니다")
    if (type(current_inventory_fingerprint) is not str
            or re.fullmatch(r"[0-9a-f]{64}", current_inventory_fingerprint) is None):
        raise PolicyDataError("INVALID_MATCH_INPUT: current_inventory_fingerprint는 정확한 소문자16진64자리 문자열이어야 합니다")

    review_ref = inventory.completeness_review_ref
    if review_ref is None:
        return InventoryReviewMatch(None, ReviewMatchStatus.MISSING, (),
                                    (ReviewMissingReason.INVENTORY_REVIEW_NOT_DECLARED,))
    if review_context is None:
        return InventoryReviewMatch(review_ref, ReviewMatchStatus.MISSING, (),
                                    (ReviewMissingReason.NO_REVIEW_CONTEXT,))

    review = _resolve_inventory_review(review_context, review_ref)
    # Context가 보장하는 record 소속을 이용해 현재 Inventory 대상과 한 번 대조한다.
    if review.policy_id != inventory.policy_id:
        raise PolicyDataError("REVIEW_POLICY_MISMATCH: 검토 기록과 현재 Inventory의 policy_id가 다릅니다")
    if review.scope != inventory.scope:
        raise PolicyDataError("REVIEW_SCOPE_MISMATCH: 검토 기록과 현재 Inventory의 scope가 다릅니다")

    stale_reasons = []
    if review.inventory_version != inventory.inventory_version:
        stale_reasons.append(ReviewStaleReason.INVENTORY_VERSION_CHANGED)
    elif review.inventory_fingerprint != current_inventory_fingerprint:
        raise PolicyDataError("INVENTORY_FINGERPRINT_CONFLICT: 같은 inventory version의 지문이 다릅니다")

    # 앞의 stale 후보가 독립적인 dataset/source 모순 검사를 생략하게 해서는 안 된다.
    if review.dataset_version != review_context.dataset_version:
        stale_reasons.append(ReviewStaleReason.DATASET_VERSION_CHANGED)
    elif review.source_registry_fingerprint != review_context.source_registry_fingerprint:
        raise PolicyDataError("SOURCE_REGISTRY_FINGERPRINT_CONFLICT: 같은 dataset version의 source registry 지문이 다릅니다")

    return InventoryReviewMatch(
        review_ref,
        ReviewMatchStatus.STALE if stale_reasons else ReviewMatchStatus.MATCHED,
        tuple(stale_reasons),
        (),
    )


def _match_implementation_review(
    inventory: ConditionInventory,
    binding: ConditionBinding,
    review_context: CoverageReviewContext | None,
    *,
    current_inventory_fingerprint: str,
    current_rule_version: str,
    current_policy_tree_fingerprint: str,
    current_subtree_fingerprint: str,
) -> ImplementationReviewMatch:
    """Binding의 명시 검토를 공급된 현재 확인본과 비교한다. root 소속·존재는 상위 책임이다."""
    if type(inventory) is not ConditionInventory:
        raise PolicyDataError("INVALID_MATCH_INPUT: inventory는 정확한 ConditionInventory여야 합니다")
    if type(binding) is not ConditionBinding:
        raise PolicyDataError("INVALID_MATCH_INPUT: binding은 정확한 ConditionBinding이어야 합니다")
    if review_context is not None and type(review_context) is not CoverageReviewContext:
        raise PolicyDataError("INVALID_MATCH_INPUT: review_context는 정확한 CoverageReviewContext 또는 None이어야 합니다")
    if type(current_rule_version) is not str or not current_rule_version.strip():
        raise PolicyDataError("INVALID_MATCH_INPUT: current_rule_version은 비어 있지 않은 정확한 문자열이어야 합니다")
    for name, value in (
        ("current_inventory_fingerprint", current_inventory_fingerprint),
        ("current_policy_tree_fingerprint", current_policy_tree_fingerprint),
        ("current_subtree_fingerprint", current_subtree_fingerprint),
    ):
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise PolicyDataError(f"INVALID_MATCH_INPUT: {name}는 정확한 소문자16진64자리 문자열이어야 합니다")

    review_ref = binding.implementation_review_ref
    if review_context is None:
        return ImplementationReviewMatch(
            binding.condition_id, binding.rule_root_id, review_ref, ReviewMatchStatus.MISSING,
            (), (ReviewMissingReason.NO_REVIEW_CONTEXT,),
        )

    review = _resolve_implementation_review(review_context, review_ref)
    if review.policy_id != inventory.policy_id:
        raise PolicyDataError("REVIEW_POLICY_MISMATCH: 검토 기록과 현재 Inventory의 policy_id가 다릅니다")
    if review.scope != inventory.scope:
        raise PolicyDataError("REVIEW_SCOPE_MISMATCH: 검토 기록과 현재 Inventory의 scope가 다릅니다")
    if review.condition_id != binding.condition_id:
        raise PolicyDataError("REVIEW_CONDITION_MISMATCH: 검토 기록과 현재 Binding의 condition_id가 다릅니다")
    if review.rule_root_id != binding.rule_root_id:
        raise PolicyDataError("REVIEW_RULE_ROOT_MISMATCH: 검토 기록과 현재 Binding의 rule_root_id가 다릅니다")

    stale_reasons = []
    if review.inventory_version != inventory.inventory_version:
        stale_reasons.append(ReviewStaleReason.INVENTORY_VERSION_CHANGED)
    elif review.inventory_fingerprint != current_inventory_fingerprint:
        raise PolicyDataError("INVENTORY_FINGERPRINT_CONFLICT: 같은 inventory version의 지문이 다릅니다")

    if review.rule_version != current_rule_version:
        stale_reasons.append(ReviewStaleReason.RULE_VERSION_CHANGED)
    else:
        if review.policy_tree_fingerprint != current_policy_tree_fingerprint:
            raise PolicyDataError("POLICY_TREE_FINGERPRINT_CONFLICT: 같은 rule version의 전체 tree 지문이 다릅니다")
        if review.subtree_fingerprint != current_subtree_fingerprint:
            raise PolicyDataError("SUBTREE_FINGERPRINT_CONFLICT: 같은 rule version의 subtree 지문이 다릅니다")

    if review.dataset_version != review_context.dataset_version:
        stale_reasons.append(ReviewStaleReason.DATASET_VERSION_CHANGED)
    elif review.source_registry_fingerprint != review_context.source_registry_fingerprint:
        raise PolicyDataError("SOURCE_REGISTRY_FINGERPRINT_CONFLICT: 같은 dataset version의 source registry 지문이 다릅니다")

    # 독립적인 다른 version/내용 쌍의 모순을 통과한 뒤에만 정상 결과를 만든다.
    if review.implementation_fingerprint != review_context.implementation_fingerprint:
        stale_reasons.append(ReviewStaleReason.IMPLEMENTATION_CHANGED)

    return ImplementationReviewMatch(
        binding.condition_id, binding.rule_root_id, review_ref,
        ReviewMatchStatus.STALE if stale_reasons else ReviewMatchStatus.MATCHED,
        tuple(stale_reasons), (),
    )
