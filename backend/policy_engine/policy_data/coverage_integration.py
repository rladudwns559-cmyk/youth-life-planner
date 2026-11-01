"""구조·결합·현재 지문·명시 검토를 조립한다. 최종 Coverage 상태는 파생하지 않는다."""

import json

from ..errors import PolicyDataError
from ..models import Policy
from .coverage import EligibilityCoverage
from .coverage_composition import _find_composition_gap_group_ids
from .coverage_fingerprint import fingerprint_condition_inventory, fingerprint_policy_tree, fingerprint_rule_subtree
from .coverage_integration_findings import _CoverageIntegrationFindings, _ImplementationIntegrationFinding
from .coverage_review_context import CoverageReviewContext
from .coverage_review_matching import _match_implementation_review, _match_inventory_review
from .coverage_structure import _analyze_coverage_structure


def _collect_coverage_integration_findings(
    coverage: EligibilityCoverage,
    policy: Policy,
    review_context: CoverageReviewContext | None,
) -> _CoverageIntegrationFindings:
    """현재 입력의 facts와 정상 Review outcomes를 불변 findings로 반환한다."""
    if type(coverage) is not EligibilityCoverage:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: coverage: 정확한 EligibilityCoverage가 필요합니다")
    if type(policy) is not Policy:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: policy: 정확한 Policy가 필요합니다")
    if review_context is not None and type(review_context) is not CoverageReviewContext:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: review_context: 정확한 CoverageReviewContext 또는 None이 필요합니다")

    missing_ids, resolved_bindings, unmapped_ids = _analyze_coverage_structure(coverage, policy)
    gap_ids = _find_composition_gap_group_ids(policy, resolved_bindings)
    if not missing_ids and gap_ids:
        details = {"composition_gap_count": len(gap_ids), "first_composition_gap_group_id": gap_ids[0]}
        message = json.dumps(details, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        raise PolicyDataError("COVERAGE_COMPOSITION_GAP: " + message)

    if review_context is not None:
        if review_context.policy_id != coverage.inventory.policy_id:
            raise PolicyDataError("REVIEW_POLICY_MISMATCH: Context와 현재 Inventory의 policy_id가 다릅니다")
        if review_context.scope != coverage.inventory.scope:
            raise PolicyDataError("REVIEW_SCOPE_MISMATCH: Context와 현재 Inventory의 scope가 다릅니다")

    inventory_fp = fingerprint_condition_inventory(coverage.inventory)
    tree_fp = fingerprint_policy_tree(policy)
    rows = tuple((binding, root, fingerprint_rule_subtree(root)) for binding, root in resolved_bindings)
    inventory_match = _match_inventory_review(
        coverage.inventory, review_context, current_inventory_fingerprint=inventory_fp,
    )
    implementation_matches = tuple(
        (subtree_fp, _match_implementation_review(
            coverage.inventory, binding, review_context,
            current_inventory_fingerprint=inventory_fp,
            current_rule_version=policy.rule_version,
            current_policy_tree_fingerprint=tree_fp,
            current_subtree_fingerprint=subtree_fp,
        ))
        for binding, _, subtree_fp in rows
    )
    implementation_findings = tuple(
        _ImplementationIntegrationFinding(subtree_fingerprint=subtree_fp, review_match=match)
        for subtree_fp, match in implementation_matches
    )
    return _CoverageIntegrationFindings(
        missing_condition_ids=missing_ids,
        unmapped_rule_ids=unmapped_ids,
        composition_gap_group_ids=gap_ids,
        inventory_fingerprint=inventory_fp,
        policy_tree_fingerprint=tree_fp,
        inventory_review_match=inventory_match,
        implementation_findings=implementation_findings,
    )
