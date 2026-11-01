"""현재 Policy tree의 명시적 ID를 원본 node로 연결한다. 소유·검토·지문은 판단하지 않는다."""

from ..errors import PolicyDataError
from ..models import BirthDateRule, Policy, PolicyRule, ResidentRegistrationRule, RuleGroup, RuleNode, walk_nodes


def _resolve_rule_root(policy: Policy, rule_root_id: str) -> RuleNode:
    """전체 tree의 지원 타입·ID 유일성을 확인한 뒤 exact target 객체를 반환한다."""
    if type(policy) is not Policy:
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: policy: 정확한 Policy가 필요합니다")
    if type(rule_root_id) is not str or not rule_root_id.strip():
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: rule_root_id: 정확한 비공백 문자열이 필요합니다")

    seen_rule_ids: set[str] = set()
    found: RuleNode | None = None
    has_duplicate = False
    for node in walk_nodes(policy.root):
        if type(node) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
            raise PolicyDataError("UNSUPPORTED_RULE_NODE: 현재 지원하는 정확한 RuleNode가 필요합니다")
        node_id = node.rule_id
        if node_id in seen_rule_ids:
            has_duplicate = True
        seen_rule_ids.add(node_id)
        if node_id == rule_root_id and found is None:
            found = node

    # 중복 오류를 미뤄 뒤쪽 unsupported node도 타입 우선순위대로 확인한다.
    if has_duplicate:
        raise PolicyDataError("DUPLICATE_RULE_NODE_ID: Policy tree의 rule_id는 유일해야 합니다")
    if found is None:
        raise PolicyDataError("RULE_ROOT_NOT_FOUND: 현재 Policy tree에 명시적 rule_root_id가 없습니다")
    return found
