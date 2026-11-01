"""현재 tree의 실행 leaf와 미매핑 ID만 분석한다. 완결성이나 상태를 판정하지 않는다."""

from ..errors import PolicyDataError
from ..models import BirthDateRule, Policy, PolicyRule, ResidentRegistrationRule, RuleGroup, RuleNode, walk_nodes
from .condition_binding import ConditionBinding
from .coverage_ownership import _collect_owned_rule_ids


def _collect_policy_coverage_target_rule_ids(policy: Policy) -> tuple[str, ...]:
    """전체 node의 타입·ID 유일성을 확인하고 세 leaf ID만 원래 pre-order로 반환한다."""
    if type(policy) is not Policy:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: policy: 정확한 Policy가 필요합니다")

    target_ids = []
    seen_ids = set()
    has_duplicate = False
    for node in walk_nodes(policy.root):
        if type(node) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
            raise PolicyDataError("UNSUPPORTED_RULE_NODE: 현재 지원하는 정확한 RuleNode가 필요합니다")
        node_id = node.rule_id
        if node_id in seen_ids:
            has_duplicate = True
        seen_ids.add(node_id)
        if type(node) in (PolicyRule, ResidentRegistrationRule, BirthDateRule):
            target_ids.append(node_id)
    # 뒤쪽 미지원 타입도 먼저 확인하도록 중복 오류는 전체 순회 후 확정한다.
    if has_duplicate:
        raise PolicyDataError("DUPLICATE_RULE_NODE_ID: Policy tree의 rule_id는 유일해야 합니다")
    return tuple(target_ids)


def _find_unmapped_rule_ids(
    policy: Policy,
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> tuple[str, ...]:
    """같은 Policy의 원본 roots·비겹침이 준비됐다는 전제에서 미소유 leaf만 반환한다."""
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

    targets = _collect_policy_coverage_target_rule_ids(policy)
    owned_all: set[str] = set()
    for _, root in ordered:
        owned_all.update(_collect_owned_rule_ids(root))
    return tuple(rule_id for rule_id in targets if rule_id not in owned_all)
