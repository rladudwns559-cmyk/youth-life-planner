"""이미 resolve된 root의 소유 ID와 condition 간 겹침만 확인하는 private helper."""

import json

from ..errors import PolicyDataError
from ..models import BirthDateRule, PolicyRule, ResidentRegistrationRule, RuleGroup, RuleNode, walk_nodes
from .condition_binding import ConditionBinding


def _collect_owned_rule_ids(root: RuleNode) -> tuple[str, ...]:
    """root와 모든 자손의 ID를 원래 pre-order로 수집한다. ID를 정규화하지 않는다."""
    if type(root) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
        raise PolicyDataError("INVALID_STRUCTURE_INPUT: root: 정확한 RuleNode가 필요합니다")

    owned_ids = []
    seen_ids = set()
    has_duplicate = False
    for node in walk_nodes(root):
        if type(node) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
            raise PolicyDataError("UNSUPPORTED_RULE_NODE: 현재 지원하는 정확한 RuleNode가 필요합니다")
        node_id = node.rule_id
        if node_id in seen_ids:
            has_duplicate = True
        seen_ids.add(node_id)
        owned_ids.append(node_id)
    if has_duplicate:
        raise PolicyDataError("DUPLICATE_RULE_NODE_ID: 소유 subtree의 rule_id는 유일해야 합니다")
    return tuple(owned_ids)


def _validate_binding_ownership_no_overlap(
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> None:
    """같은 Policy에서 준비한 (Binding, 원본 root) 쌍을 전제로 첫 canonical 겹침을 거부한다."""
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

    # 모든 연결 검사와 소유 범위 수집이 성공한 뒤에만 겹침 검사를 시작한다.
    ownerships = [(binding, set(_collect_owned_rule_ids(root))) for binding, root in ordered]
    for index, (binding_a, owned_a) in enumerate(ownerships):
        for binding_b, owned_b in ownerships[index + 1:]:
            overlap = owned_a & owned_b
            if overlap:
                details = {
                    "condition_a": binding_a.condition_id,
                    "rule_root_a": binding_a.rule_root_id,
                    "condition_b": binding_b.condition_id,
                    "rule_root_b": binding_b.rule_root_id,
                    "overlap_count": len(overlap),
                    "first_overlap_rule_id": min(overlap),
                }
                message = json.dumps(details, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
                raise PolicyDataError("COVERAGE_OWNERSHIP_OVERLAP: " + message)
