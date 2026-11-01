"""Eligibility Coverage의 공개 순수 진입점."""

from ..models import Policy
from .coverage import EligibilityCoverage
from .coverage_integration import _collect_coverage_integration_findings
from .coverage_review_context import CoverageReviewContext
from .eligibility_coverage_result import EligibilityCoverageResult, _create_eligibility_coverage_result


def evaluate_eligibility_coverage(
    coverage: EligibilityCoverage,
    policy: Policy,
    review_context: CoverageReviewContext | None = None,
) -> EligibilityCoverageResult:
    """자격조건 coverage 완결성을 평가하며 정상 미완료는 CONDITION_SLICE로 반환한다.

    사용자 자격이나 행정 승인을 판정하지 않으며 FULL_POLICY는 VERIFIED가 아니다.
    구조·데이터 모순의 PolicyDataError는 그대로 전파한다.
    """
    findings = _collect_coverage_integration_findings(coverage, policy, review_context)
    result = _create_eligibility_coverage_result(coverage, policy, review_context, findings)
    return result
