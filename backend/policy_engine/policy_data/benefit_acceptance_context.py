"""한 혜택 target의 불변 이력과 철회 연결. 현재 사용 가능성·검토 진실성은 판단하지 않는다."""

from dataclasses import dataclass
import re

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .eligibility_coverage import ApplicabilityScope


_SNAPSHOT_BINDING_FIELDS = (
    "coverage_inventory_version", "coverage_inventory_fingerprint", "coverage_rule_version",
    "coverage_policy_tree_fingerprint", "coverage_dataset_version",
    "coverage_source_registry_fingerprint", "coverage_implementation_fingerprint",
    "benefit_version", "benefit_fingerprint", "benefit_dataset_version",
    "benefit_source_registry_fingerprint",
)


def _invalid(code: str, field: str, reason: str) -> PolicyDataError:
    return PolicyDataError(f"{code}: {field}: {reason}")


def _identifier(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        raise _invalid("INVALID_ACCEPTANCE_CONTEXT_INPUT", field, "정확한 canonical 식별자 문자열이 필요합니다")


def _revision_key(version: str) -> tuple[int, str]:
    """record에서 검증된 a suffix만 비교한다. int 변환·새 문법·자리수 상한은 없다."""
    suffix = version[1:]
    return len(suffix), suffix


@dataclass(frozen=True, slots=True, kw_only=True)
class BenefitAcceptanceContext:
    """공급된 한 target의 이력 snapshot. 최신 선택·현재 철회 효과·승인 인증은 제공하지 않는다."""

    policy_id: str
    scope: ApplicabilityScope
    benefit_id: str
    records: tuple[PolicyBenefitAcceptance, ...]

    def __post_init__(self) -> None:
        # 1~5: Context 필드와 전체 원소 타입을 관계 검사 전에 확인한다.
        _identifier(self.policy_id, "policy_id")
        if type(self.scope) is not ApplicabilityScope:
            raise _invalid("INVALID_ACCEPTANCE_CONTEXT_INPUT", "scope", "정확한 ApplicabilityScope가 필요합니다")
        _identifier(self.benefit_id, "benefit_id")
        if type(self.records) is not tuple:
            raise _invalid("INVALID_ACCEPTANCE_CONTEXT_INPUT", "records", "정확한 tuple이 필요합니다")
        if any(type(record) is not PolicyBenefitAcceptance for record in self.records):
            raise _invalid("INVALID_ACCEPTANCE_CONTEXT_INPUT", "records", "정확한 PolicyBenefitAcceptance만 허용합니다")

        # 6: 각 record의 target은 값으로 일치하며 원본 객체는 보존한다.
        for record in self.records:
            for name in ("policy_id", "scope", "benefit_id"):
                if getattr(record, name) != getattr(self, name):
                    raise _invalid("ACCEPTANCE_CONTEXT_TARGET_MISMATCH", "records." + name,
                                   "record의 target은 Context와 일치해야 합니다")

        # 7~8: ref와 revision 유일성을 별도 전체 phase로 검사한다.
        by_ref = {}
        for record in self.records:
            if record.acceptance_ref in by_ref:
                raise _invalid("DUPLICATE_ACCEPTANCE_REF", "records.acceptance_ref", "참조는 Context 안에서 유일해야 합니다")
            by_ref[record.acceptance_ref] = record
        versions = set()
        for record in self.records:
            if record.acceptance_version in versions:
                raise _invalid("DUPLICATE_ACCEPTANCE_VERSION", "records.acceptance_version",
                               "revision은 target 안에서 유일해야 합니다")
            versions.add(record.acceptance_version)

        # 9: 전체 ref 집합을 사용하므로 철회 대상의 tuple 위치에 의존하지 않는다.
        revoked_records = tuple(record for record in self.records if record.status is BenefitAcceptanceStatus.REVOKED)
        for record in revoked_records:
            if record.revokes_acceptance_ref not in by_ref:
                raise _invalid("REVOCATION_TARGET_NOT_FOUND", "records.revokes_acceptance_ref",
                               "철회 대상이 제공된 Context에 없습니다")
        edges = tuple((record, by_ref[record.revokes_acceptance_ref]) for record in revoked_records)

        # 10~11: 대상 상태와 정확한 과거 확인본을 각각 전체 edge에 대조한다.
        for _, target in edges:
            if target.status is not BenefitAcceptanceStatus.ACCEPTED:
                raise _invalid("INVALID_REVOCATION_TARGET_STATUS", "records.revokes_acceptance_ref",
                               "철회 대상은 ACCEPTED여야 합니다")
        for record, target in edges:
            for name in _SNAPSHOT_BINDING_FIELDS:
                if getattr(record, name) != getattr(target, name):
                    raise _invalid("REVOCATION_SNAPSHOT_MISMATCH", "records." + name,
                                   "철회 대상과 같은 snapshot binding이어야 합니다")

        # 12: 하나의 ACCEPTED를 직접 철회하는 edge는 최대 한 개다.
        revoked_refs = set()
        for record, _ in edges:
            if record.revokes_acceptance_ref in revoked_refs:
                raise _invalid("DUPLICATE_REVOCATION_TARGET", "records.revokes_acceptance_ref",
                               "하나의 승인 revision을 중복 철회할 수 없습니다")
            revoked_refs.add(record.revokes_acceptance_ref)

        # 13~14: version 전체 phase가 날짜 전체 phase보다 먼저다.
        for record, target in edges:
            if _revision_key(record.acceptance_version) <= _revision_key(target.acceptance_version):
                raise _invalid("INVALID_REVOCATION_ORDER", "records.acceptance_version",
                               "철회 revision은 대상 revision보다 뒤여야 합니다")
        for record, target in edges:
            if record.reviewed_at < target.reviewed_at:
                raise _invalid("INVALID_REVOCATION_ORDER", "records.reviewed_at",
                               "철회 검토일은 대상 검토일 이상이어야 합니다")

    def to_dict(self) -> dict[str, object]:
        """입력 순서의 새4key snapshot. 조회·최신 선택·현재 사용 판정은 하지 않는다."""
        return {
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "benefit_id": self.benefit_id,
            "records": [record.to_dict() for record in self.records],
        }
