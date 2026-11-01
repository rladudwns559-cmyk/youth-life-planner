"""기존 findings와 원본 참조를 대조하는 불변 결과. 계산 엔진을 실행하지 않는다."""

from dataclasses import InitVar, dataclass, field
from enum import Enum
import re

from ..errors import PolicyDataError
from ..models import Policy
from .coverage import EligibilityCoverage
from .coverage_integration_findings import _CoverageIntegrationFindings
from .coverage_review_context import CoverageReviewContext
from .coverage_review_match import ReviewMatchStatus, ReviewMissingReason
from .eligibility_coverage import ApplicabilityScope


_RESULT_CREATION_TOKEN = object()


class EligibilityCoverageStatus(str, Enum):
    FULL_POLICY = "FULL_POLICY"
    CONDITION_SLICE = "CONDITION_SLICE"


def _invalid(field_name: str, reason: str) -> PolicyDataError:
    return PolicyDataError(f"INVALID_COVERAGE_RESULT: {field_name}: {reason}")


@dataclass(frozen=True, slots=True)
class EligibilityCoverageResult:
    """8개 저장 값만 보존한다. 정상 생성 경계는 모듈 내부 factory다."""

    policy_id: str
    scope: ApplicabilityScope
    inventory_version: str
    rule_version: str
    dataset_version: str | None
    source_registry_fingerprint: str | None
    implementation_fingerprint: str | None
    findings: _CoverageIntegrationFindings
    _creation_token: InitVar[object] = field(default=None, kw_only=True)

    def __post_init__(self, _creation_token: object) -> None:
        if _creation_token is not _RESULT_CREATION_TOKEN:
            raise TypeError("EligibilityCoverageResult는 내부 검증 factory를 통해서만 생성할 수 있습니다")
        if type(self.policy_id) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", self.policy_id) is None:
            raise _invalid("policy_id", "정확한 canonical 정책 ID가 필요합니다")
        if type(self.scope) is not ApplicabilityScope:
            raise _invalid("scope", "정확한 ApplicabilityScope가 필요합니다")
        if (type(self.inventory_version) is not str
                or re.fullmatch(r"i(?:[0-9]{4}|[1-9][0-9]{4,})", self.inventory_version) is None
                or self.inventory_version == "i0000"):
            raise _invalid("inventory_version", "i0001부터의 정확한 버전이 필요합니다")
        if type(self.rule_version) is not str or not self.rule_version.strip():
            raise _invalid("rule_version", "정확한 비공백 문자열이 필요합니다")
        if self.dataset_version is not None and (
            type(self.dataset_version) is not str or not self.dataset_version.strip()
        ):
            raise _invalid("dataset_version", "정확한 비공백 문자열 또는 None이 필요합니다")
        for name in ("source_registry_fingerprint", "implementation_fingerprint"):
            value = getattr(self, name)
            if value is not None and (type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None):
                raise _invalid(name, "정확한 소문자16진64자리 문자열 또는 None이 필요합니다")
        if type(self.findings) is not _CoverageIntegrationFindings:
            raise _invalid("findings", "정확한 _CoverageIntegrationFindings가 필요합니다")

        baseline = (self.dataset_version, self.source_registry_fingerprint, self.implementation_fingerprint)
        if any(value is None for value in baseline) and not all(value is None for value in baseline):
            raise _invalid("review_baseline", "세 값은 모두 None이거나 모두 존재해야 합니다")

        inventory_match = self.findings.inventory_review_match
        implementation_findings = self.findings.implementation_findings
        if self.dataset_version is None:
            expected = (ReviewMissingReason.INVENTORY_REVIEW_NOT_DECLARED if inventory_match.review_ref is None
                        else ReviewMissingReason.NO_REVIEW_CONTEXT,)
            if inventory_match.status is not ReviewMatchStatus.MISSING or inventory_match.missing_reasons != expected:
                raise _invalid("findings.inventory_review_match", "baseline 미제공과 일치하는 MISSING이 필요합니다")
            if any(item.review_match.status is not ReviewMatchStatus.MISSING
                   or item.review_match.missing_reasons != (ReviewMissingReason.NO_REVIEW_CONTEXT,)
                   for item in implementation_findings):
                raise _invalid("findings.implementation_findings", "baseline 미제공이면 모두 NO_REVIEW_CONTEXT여야 합니다")
        else:
            if inventory_match.status is ReviewMatchStatus.MISSING and (
                inventory_match.review_ref is not None
                or inventory_match.missing_reasons != (ReviewMissingReason.INVENTORY_REVIEW_NOT_DECLARED,)
            ):
                raise _invalid("findings.inventory_review_match", "baseline 제공 시 미선언 Inventory MISSING만 허용합니다")
            if any(item.review_match.status is ReviewMatchStatus.MISSING for item in implementation_findings):
                raise _invalid("findings.implementation_findings", "baseline 제공 시 Implementation MISSING은 허용하지 않습니다")

        if not self.findings.missing_condition_ids and not implementation_findings:
            raise _invalid("findings.implementation_findings", "missing이 없으면 하나 이상의 구현 finding이 필요합니다")

    @property
    def status(self) -> EligibilityCoverageStatus:
        """검증된 값의 completeness만 파생한다. 승인/자격 평가 상태가 아니다."""
        facts = self.findings
        if (not facts.missing_condition_ids
                and not facts.unmapped_rule_ids
                and not facts.composition_gap_group_ids
                and facts.inventory_review_match.status is ReviewMatchStatus.MATCHED
                and facts.implementation_findings
                and all(item.review_match.status is ReviewMatchStatus.MATCHED for item in facts.implementation_findings)
                and self.dataset_version is not None
                and self.source_registry_fingerprint is not None
                and self.implementation_fingerprint is not None):
            return EligibilityCoverageStatus.FULL_POLICY
        return EligibilityCoverageStatus.CONDITION_SLICE

    def to_dict(self) -> dict[str, object]:
        """저장8개와 파생 status만 새 중첩 값으로 표현한다."""
        return {
            "policy_id": self.policy_id,
            "scope": self.scope.to_dict(),
            "inventory_version": self.inventory_version,
            "rule_version": self.rule_version,
            "dataset_version": self.dataset_version,
            "source_registry_fingerprint": self.source_registry_fingerprint,
            "implementation_fingerprint": self.implementation_fingerprint,
            "findings": self.findings.to_dict(),
            "status": self.status.value,
        }


def _create_eligibility_coverage_result(
    coverage: EligibilityCoverage,
    policy: Policy,
    review_context: CoverageReviewContext | None,
    findings: _CoverageIntegrationFindings,
) -> EligibilityCoverageResult:
    """이미 계산된 facts의 정확한 대상/참조 대응만 검사한다. gate 성공을 전제한다."""
    if type(coverage) is not EligibilityCoverage:
        raise _invalid("coverage", "정확한 EligibilityCoverage가 필요합니다")
    if type(policy) is not Policy:
        raise _invalid("policy", "정확한 Policy가 필요합니다")
    if review_context is not None and type(review_context) is not CoverageReviewContext:
        raise _invalid("review_context", "정확한 CoverageReviewContext 또는 None이 필요합니다")
    if type(findings) is not _CoverageIntegrationFindings:
        raise _invalid("findings", "정확한 _CoverageIntegrationFindings가 필요합니다")

    inventory = coverage.inventory
    if inventory.policy_id != policy.policy_id:
        raise _invalid("policy_id", "Coverage와 Policy의 policy_id가 다릅니다")
    if review_context is not None:
        if review_context.policy_id != inventory.policy_id:
            raise _invalid("review_context.policy_id", "Context와 Inventory의 policy_id가 다릅니다")
        if review_context.scope != inventory.scope:
            raise _invalid("review_context.scope", "Context와 Inventory의 scope가 다릅니다")

    binding_ids = {binding.condition_id for binding in coverage.bindings}
    missing_ids = tuple(condition.condition_id for condition in inventory.conditions
                        if condition.condition_id not in binding_ids)
    if findings.missing_condition_ids != missing_ids:
        raise _invalid("findings.missing_condition_ids", "원본 Inventory와 Binding의 차집합 순서와 다릅니다")
    expected_rows = tuple((binding.condition_id, binding.rule_root_id, binding.implementation_review_ref)
                          for binding in sorted(coverage.bindings, key=lambda item: item.condition_id))
    actual_rows = tuple((item.review_match.condition_id, item.review_match.rule_root_id, item.review_match.review_ref)
                        for item in findings.implementation_findings)
    if actual_rows != expected_rows:
        raise _invalid("findings.implementation_findings", "원본 Binding의 condition/root/review_ref와 정확히 대응해야 합니다")
    if findings.inventory_review_match.review_ref != inventory.completeness_review_ref:
        raise _invalid("findings.inventory_review_match.review_ref", "원본 Inventory의 검토 참조와 다릅니다")

    return EligibilityCoverageResult(
        policy_id=inventory.policy_id,
        scope=inventory.scope,
        inventory_version=inventory.inventory_version,
        rule_version=policy.rule_version,
        dataset_version=None if review_context is None else review_context.dataset_version,
        source_registry_fingerprint=None if review_context is None else review_context.source_registry_fingerprint,
        implementation_fingerprint=None if review_context is None else review_context.implementation_fingerprint,
        findings=findings,
        _creation_token=_RESULT_CREATION_TOKEN,
    )
