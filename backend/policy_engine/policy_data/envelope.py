"""정책 edition metadata. 실행 Policy와 registry를 소유·변경하는 경계를 분리한다."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re

from ..errors import PolicyDataError
from ..facts import RegionRef
from ..models import Policy, RuleGroup, _jsonable, walk_nodes
from ..sources import parse_evidence_ref


class EnvelopeValidationError(PolicyDataError):
    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field} 정책 edition 계약을 확인하세요")


class PolicyCategory(str, Enum):
    YOUTH_SUPPORT = "YOUTH_SUPPORT"


class EvaluationScope(str, Enum):
    CONDITION_SLICE = "CONDITION_SLICE"


class PolicyVerificationStatus(str, Enum):
    """edition의 검토 상태 선언. 개별 원문의 VerificationStatus와 구분한다."""

    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    STALE = "STALE"


class PolicyLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


def _identifier(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        raise EnvelopeValidationError("INVALID_ENVELOPE_ID", field)


def _version(value: object, prefix: str, field: str) -> None:
    if (type(value) is not str
            or re.fullmatch(prefix + r"(?:[0-9]{4}|[1-9][0-9]{4,})", value) is None
            or value == prefix + "0000"):
        raise EnvelopeValidationError("INVALID_ENVELOPE_VERSION", field)


def _optional_date(value: object, field: str) -> None:
    if value is not None and type(value) is not date:
        raise EnvelopeValidationError("INVALID_ENVELOPE_DATE", field)


@dataclass(frozen=True, slots=True)
class SourceBinding:
    source_document_id: str
    document_version: str

    def __post_init__(self) -> None:
        _identifier(self.source_document_id, "source_document_id")
        _version(self.document_version, "d", "document_version")


@dataclass(frozen=True, slots=True)
class PolicyCoverage:
    included_rule_ids: tuple[str, ...]
    excluded_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("included_rule_ids", "excluded_conditions"):
            values = getattr(self, field)
            if (type(values) is not tuple or not values
                    or any(type(value) is not str or not value.strip() for value in values)):
                raise EnvelopeValidationError("INVALID_POLICY_COVERAGE", field)
        if len(set(self.included_rule_ids)) != len(self.included_rule_ids):
            raise EnvelopeValidationError("DUPLICATE_COVERAGE_RULE", "included_rule_ids")


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyEnvelope:
    schema_version: str
    rule_schema_version: str
    policy: Policy
    edition_id: str
    jurisdiction: RegionRef
    category: PolicyCategory
    dataset_version: str
    evaluation_scope: EvaluationScope
    coverage: PolicyCoverage
    source_bindings: tuple[SourceBinding, ...]
    verification_status: PolicyVerificationStatus
    last_verified_at: date | None
    lifecycle_status: PolicyLifecycleStatus
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != "policy-data-1.0":
            raise EnvelopeValidationError("UNSUPPORTED_ENVELOPE_SCHEMA", "schema_version")
        if type(self.rule_schema_version) is not str or self.rule_schema_version != "m1.1":
            raise EnvelopeValidationError("UNSUPPORTED_RULE_SCHEMA", "rule_schema_version")
        if type(self.policy) is not Policy:
            raise EnvelopeValidationError("INVALID_ENVELOPE_POLICY", "policy")
        _identifier(self.policy_id, "policy_id")
        _version(self.rule_version, "r", "rule_version")
        if type(self.edition_id) is not str or re.fullmatch(r"[0-9]{4}", self.edition_id) is None:
            raise EnvelopeValidationError("INVALID_EDITION_ID", "edition_id")
        if type(self.jurisdiction) is not RegionRef:
            raise EnvelopeValidationError("INVALID_JURISDICTION", "jurisdiction")
        if type(self.category) is not PolicyCategory:
            raise EnvelopeValidationError("INVALID_POLICY_CATEGORY", "category")
        if type(self.dataset_version) is not str or not self.dataset_version.strip():
            raise EnvelopeValidationError("INVALID_DATASET_VERSION", "dataset_version")
        if type(self.evaluation_scope) is not EvaluationScope:
            raise EnvelopeValidationError("INVALID_EVALUATION_SCOPE", "evaluation_scope")
        if type(self.coverage) is not PolicyCoverage:
            raise EnvelopeValidationError("INVALID_POLICY_COVERAGE", "coverage")
        if (type(self.source_bindings) is not tuple or not self.source_bindings
                or any(type(binding) is not SourceBinding for binding in self.source_bindings)):
            raise EnvelopeValidationError("INVALID_SOURCE_BINDINGS", "source_bindings")
        ids = self.source_document_ids
        if len(set(ids)) != len(ids):
            raise EnvelopeValidationError("DUPLICATE_SOURCE_BINDING", "source_bindings")
        if type(self.verification_status) is not PolicyVerificationStatus:
            raise EnvelopeValidationError("INVALID_POLICY_VERIFICATION", "verification_status")
        if type(self.lifecycle_status) is not PolicyLifecycleStatus:
            raise EnvelopeValidationError("INVALID_POLICY_LIFECYCLE", "lifecycle_status")
        for field in ("last_verified_at", "effective_from", "effective_to"):
            _optional_date(getattr(self, field), field)
        if self.verification_status is PolicyVerificationStatus.VERIFIED and self.last_verified_at is None:
            raise EnvelopeValidationError("VERIFIED_DATE_REQUIRED", "last_verified_at")
        if (self.effective_from is not None and self.effective_to is not None
                and self.effective_from > self.effective_to):
            raise EnvelopeValidationError("INVALID_EFFECTIVE_PERIOD", "effective_to")
        leaves = tuple(node for node in walk_nodes(self.policy.root) if type(node) is not RuleGroup)
        if set(self.coverage.included_rule_ids) != {node.rule_id for node in leaves}:
            raise EnvelopeValidationError("COVERAGE_RULE_MISMATCH", "coverage.included_rule_ids")
        used_source_ids = set()
        for leaf in leaves:
            # leaf의 필수 tuple 구조는 기존 PolicyRule/ResidentRegistrationRule 책임이다.
            for ref in leaf.evidence_refs:
                source_id, _ = parse_evidence_ref(ref)
                used_source_ids.add(source_id)
            if len(set(leaf.evidence_refs)) != len(leaf.evidence_refs):
                raise EnvelopeValidationError("DUPLICATE_LEAF_EVIDENCE", "evidence_refs")
        if used_source_ids != set(ids):
            raise EnvelopeValidationError("SOURCE_BINDING_COVERAGE_MISMATCH", "source_bindings")

    @property
    def policy_id(self) -> str:
        return self.policy.policy_id

    @property
    def policy_name(self) -> str:
        return self.policy.policy_name

    @property
    def rule_version(self) -> str:
        return self.policy.rule_version

    @property
    def root(self):
        return self.policy.root

    @property
    def synthetic(self) -> bool:
        return self.policy.synthetic

    @property
    def test_only(self) -> bool:
        return self.policy.test_only

    @property
    def source_document_ids(self) -> tuple[str, ...]:
        return tuple(binding.source_document_id for binding in self.source_bindings)

    def to_dict(self) -> dict:
        """기존 값 serializer의 불변 입력 snapshot. 향후 flat JSON loader 입력이 아니다."""
        return _jsonable(self)
