"""어떤 condition도 소유하지 않은 ANY/NOT group의 ID만 분석한다."""

from ..errors import PolicyDataError
from ..models import (
    BirthDateRule, GroupOperator, Policy, PolicyRule, ResidentRegistrationRule, RuleGroup, RuleNode, walk_nodes,
)
from .condition_binding import ConditionBinding
from .coverage_ownership import _collect_owned_rule_ids


def _find_composition_gap_group_ids(
    policy: Policy,
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> tuple[str, ...]:
    """같은 Policy의 원본 roots·비겹침을 전제로 gap 사실을 pre-order로 반환한다."""
    if type(policy) is not Policy:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: policy: 정확한 Policy가 필요합니다")
    if type(resolved_bindings) is not tuple:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: resolved_bindings: 정확한 tuple이 필요합니다")
    for entry in resolved_bindings:
        if type(entry) is not tuple or len(entry) != 2:
            raise PolicyDataError("INVALID_STRUCTURE_INPUT: entry: 정확한 길이2 tuple이 필요합니다")
        binding, root = entry
        if type(binding) is not ConditionBinding:
            raise PolicyDataError("INVALID_STRUCTURE_INPUT: binding: 정확한 ConditionBinding이 필요합니다")
        if type(root) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
            raise PolicyDataError("INVALID_STRUCTURE_INPUT: root: 정확한 RuleNode가 필요합니다")

    condition_ids = tuple(binding.condition_id for binding, _ in resolved_bindings)
    if len(condition_ids) != len(set(condition_ids)):
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: condition_id: 중복 condition은 허용하지 않습니다")
    ordered = sorted(resolved_bindings, key=lambda entry: entry[0].condition_id)
    for binding, root in ordered:
        if root.rule_id != binding.rule_root_id:
            raise PolicyDataError("INVALID_STRUCTURE_INPUT: rule_root_id: Binding과 root의 ID가 일치해야 합니다")

    candidates = []
    seen_ids = set()
    has_duplicate = False
    for node in walk_nodes(policy.root):
        if type(node) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
            raise PolicyDataError("UNSUPPORTED_RULE_NODE: 현재 지원하는 정확한 RuleNode가 필요합니다")
        node_id = node.rule_id
        if node_id in seen_ids:
            has_duplicate = True
        seen_ids.add(node_id)
        if type(node) is RuleGroup:
            if type(node.operator) is not GroupOperator or node.operator not in (
                GroupOperator.ALL, GroupOperator.ANY, GroupOperator.NOT,
            ):
                raise PolicyDataError("UNSUPPORTED_RULE_NODE: 지원하는 정확한 RuleGroup operator가 필요합니다")
            if node.operator in (GroupOperator.ANY, GroupOperator.NOT):
                candidates.append(node_id)
    # 전체 지원 타입/operator 확인을 마친 뒤 중복 ID 오류를 확정한다.
    if has_duplicate:
        raise PolicyDataError("DUPLICATE_RULE_NODE_ID: Policy tree의 rule_id는 유일해야 합니다")

    owned_ids: set[str] = set()
    for _, root in ordered:
        owned_ids.update(_collect_owned_rule_ids(root))
    return tuple(group_id for group_id in candidates if group_id not in owned_ids)
