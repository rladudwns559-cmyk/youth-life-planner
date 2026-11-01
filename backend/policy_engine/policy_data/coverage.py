"""Inventory와 Binding 주장을 묶는 구조 모델. tree·검토·구현범위를 판정하지 않는다."""

from dataclasses import dataclass

from ..errors import PolicyDataError
from .condition_binding import ConditionBinding
from .condition_inventory import ConditionInventory


@dataclass(frozen=True, slots=True)
class EligibilityCoverage:
    """생성 성공은 참조의 로컬 정합성만 뜻하며 구현 완료나 검토 승인이 아니다."""

    inventory: ConditionInventory
    bindings: tuple[ConditionBinding, ...]

    def __post_init__(self) -> None:
        if type(self.inventory) is not ConditionInventory:
            raise PolicyDataError("inventory: 정확한 ConditionInventory가 필요합니다")
        if type(self.bindings) is not tuple:
            raise PolicyDataError("bindings: 정확한 ConditionBinding tuple이 필요합니다")
        if any(type(binding) is not ConditionBinding for binding in self.bindings):
            raise PolicyDataError("bindings: 정확한 ConditionBinding만 허용합니다")
        inventory_ids = {condition.condition_id for condition in self.inventory.conditions}
        seen = set()
        for binding in self.bindings:
            if binding.condition_id in seen:
                raise PolicyDataError("bindings: condition_id 중복 binding은 허용하지 않습니다")
            if binding.condition_id not in inventory_ids:
                raise PolicyDataError("bindings: condition_id는 inventory에 존재해야 합니다")
            seen.add(binding.condition_id)

    def to_dict(self) -> dict[str, object]:
        """입력 순서를 보존한 새 중첩 snapshot. 판정 결과나 파생 ID 목록은 넣지 않는다."""
        return {
            "inventory": self.inventory.to_dict(),
            "bindings": [binding.to_dict() for binding in self.bindings],
        }
