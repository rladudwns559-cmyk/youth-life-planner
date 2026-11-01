"""Coverage 검토 대상 Inventory·전체 Rule Tree·subtree의 고정 지문. 검토 상태는 판단하지 않는다."""

import hashlib
import json

from ..errors import PolicyDataError
from ..models import BirthDateRule, Policy, PolicyRule, ResidentRegistrationRule, RuleGroup, RuleNode
from .condition_inventory import ConditionInventory


def _build_inventory_payload(inventory: ConditionInventory) -> dict[str, object]:
    """명시 필드만 선택한다. 조건은 ID순, 근거는 원래 순서·중복을 보존한다."""
    return {
        "fingerprint_schema": "coverage-inventory-1.0",
        "policy_id": inventory.policy_id,
        "scope": {"edition_id": inventory.scope.edition_id, "quarter": inventory.scope.quarter},
        "inventory_version": inventory.inventory_version,
        "conditions": [
            {
                "condition_id": condition.condition_id,
                "meaning": condition.meaning,
                "requirement": condition.requirement.value,
                "evidence_refs": list(condition.evidence_refs),
            }
            for condition in sorted(inventory.conditions, key=lambda condition: condition.condition_id)
        ],
    }


def fingerprint_condition_inventory(inventory: ConditionInventory) -> str:
    """정확한 Inventory → canonical JSON/strict UTF-8 → SHA256 소문자64자리."""
    if type(inventory) is not ConditionInventory:
        raise PolicyDataError("inventory: 정확한 ConditionInventory가 필요합니다")
    payload = _build_inventory_payload(inventory)
    return _digest_payload(payload, "inventory")


def _digest_payload(payload: dict[str, object], label: str) -> str:
    """통제된 payload만 동일한 canonical JSON/strict UTF-8/SHA256으로 인코딩한다."""
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError):
        raise PolicyDataError(f"{label} fingerprint: canonical JSON/UTF-8 인코딩 계약을 확인하세요") from None
    return hashlib.sha256(encoded).hexdigest()


def _build_rule_node_payload(node: RuleNode) -> dict[str, object]:
    """정확한 현재 네 노드의 명시 필드와 계층·순서를 보존한다."""
    if type(node) is PolicyRule:
        basis = node.fact_basis
        return {
            "node_type": "atomic",
            "rule_id": node.rule_id,
            "field": node.field.value,
            "operator": node.operator.value,
            "value": list(node.value) if type(node.value) is tuple else node.value,
            "fact_basis": None if basis is None else {
                "basis": basis.basis,
                "subject": basis.subject,
                "period": basis.period,
                "reference_year": basis.reference_year,
                "unit": basis.unit,
            },
            "evidence_refs": list(node.evidence_refs),
        }
    if type(node) is ResidentRegistrationRule:
        return {
            "node_type": "resident_registration",
            "rule_id": node.rule_id,
            "required_region": {"sido": node.required_region.sido, "sigungu": node.required_region.sigungu},
            "reference_date_source": node.reference_date_source.value,
            "evidence_refs": list(node.evidence_refs),
        }
    if type(node) is BirthDateRule:
        return {
            "node_type": "birth_date",
            "rule_id": node.rule_id,
            "min_birth_date": node.min_birth_date.isoformat(),
            "max_birth_date": node.max_birth_date.isoformat(),
            "evidence_refs": list(node.evidence_refs),
        }
    if type(node) is RuleGroup:
        return {
            "node_type": "group",
            "rule_id": node.rule_id,
            "operator": node.operator.value,
            "children": [_build_rule_node_payload(child) for child in node.children],
        }
    raise PolicyDataError("root: 지원하는 정확한 RuleNode가 필요합니다")


def _build_policy_tree_payload(policy: Policy) -> dict[str, object]:
    return {
        "fingerprint_schema": "coverage-policy-tree-1.0",
        "policy_id": policy.policy_id,
        "rule_version": policy.rule_version,
        "root": _build_rule_node_payload(policy.root),
    }


def fingerprint_policy_tree(policy: Policy) -> str:
    """전체 Policy의 명시 구현 확인본을 계산한다. 평가·검토·subtree 조회는 하지 않는다."""
    if type(policy) is not Policy:
        raise PolicyDataError("policy: 정확한 Policy가 필요합니다")
    return _digest_payload(_build_policy_tree_payload(policy), "policy tree")


def fingerprint_rule_subtree(root: RuleNode) -> str:
    """전달받은 root와 모든 descendant만 고정한다. Policy·부모·root 검색에 의존하지 않는다."""
    return _digest_payload({
        "fingerprint_schema": "coverage-subtree-1.0",
        "root": _build_rule_node_payload(root),
    }, "subtree")
