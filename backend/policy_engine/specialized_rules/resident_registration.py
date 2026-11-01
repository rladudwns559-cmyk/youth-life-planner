"""주민등록 정책 요구만 표현한다. 사용자 사실/평가 결과를 보관하지 않는다."""

from dataclasses import dataclass

from ..errors import PolicyDataError
from ..facts import RegionRef
from ..result_types import ReferenceDateSource


@dataclass(frozen=True, slots=True)
class ResidentRegistrationRule:
    rule_id: str
    required_region: RegionRef
    reference_date_source: ReferenceDateSource
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.rule_id) is not str or not self.rule_id.strip():
            raise PolicyDataError("rule_id: 비어 있지 않은 문자열이 필요합니다")
        if type(self.required_region) is not RegionRef:
            raise PolicyDataError("required_region: 완전한 RegionRef가 필요합니다")
        if self.reference_date_source is not ReferenceDateSource.APPLICATION_DATE:
            raise PolicyDataError("reference_date_source: APPLICATION_DATE만 지원합니다")
        if type(self.evidence_refs) is not tuple or not self.evidence_refs:
            raise PolicyDataError("evidence_refs: 하나 이상의 합성 근거 참조 tuple이 필요합니다")
        if any(type(ref) is not str or not ref.strip() for ref in self.evidence_refs):
            raise PolicyDataError("evidence_refs: 비어 있지 않은 문자열이 필요합니다")

    def to_dict(self) -> dict[str, object]:
        """값 표현이며 m1.1 loader 입력이나 실제 정책 JSON이 아니다."""
        return {
            "rule_id": self.rule_id,
            "required_region": self.required_region.to_dict(),
            "reference_date_source": self.reference_date_source.value,
            "evidence_refs": list(self.evidence_refs),
        }
