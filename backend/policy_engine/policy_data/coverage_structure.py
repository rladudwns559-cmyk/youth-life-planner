"""현재 Coverage와 Policy의 매핑 구조만 분석한다. 검토·지문·최종 상태는 다루지 않는다."""

import json

from ..errors import PolicyDataError
from ..models import Policy, RuleNode
from .condition_binding import ConditionBinding
from .coverage import EligibilityCoverage
from .coverage_ownership import _validate_binding_ownership_no_overlap
from .coverage_unmapped import _find_unmapped_rule_ids
from .rule_root_resolution import _resolve_rule_root


def _analyze_coverage_structure(
    coverage: EligibilityCoverage,
    policy: Policy,
) -> tuple[
    tuple[str, ...],
    tuple[tuple[ConditionBinding, RuleNode], ...],
    tuple[str, ...],
]:
    """missing은 Inventory 순서, resolved는 condition 순서, unmapped는 tree 순서로 반환한다."""
    if type(coverage) is not EligibilityCoverage:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: coverage: 정확한 EligibilityCoverage가 필요합니다")
    if type(policy) is not Policy:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: policy: 정확한 Policy가 필요합니다")
    if coverage.inventory.policy_id != policy.policy_id:
        raise PolicyDataError("COVERAGE_POLICY_MISMATCH: Coverage와 Policy의 policy_id가 일치해야 합니다")

    bound_ids = {binding.condition_id for binding in coverage.bindings}
    missing_condition_ids = tuple(
        condition.condition_id for condition in coverage.inventory.conditions if condition.condition_id not in bound_ids
    )
    ordered = sorted(coverage.bindings, key=lambda binding: binding.condition_id)
    resolved_bindings = tuple((binding, _resolve_rule_root(policy, binding.rule_root_id)) for binding in ordered)
    _validate_binding_ownership_no_overlap(resolved_bindings)
    unmapped_rule_ids = _find_unmapped_rule_ids(policy, resolved_bindings)

    if not missing_condition_ids and unmapped_rule_ids:
        details = {
            "unmapped_count": len(unmapped_rule_ids),
            "first_unmapped_rule_id": unmapped_rule_ids[0],
        }
        message = json.dumps(details, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        raise PolicyDataError("COVERAGE_UNMAPPED_RULE: " + message)
    return missing_condition_ids, resolved_bindings, unmapped_rule_ids
