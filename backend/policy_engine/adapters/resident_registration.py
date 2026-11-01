"""주민등록 판정 결과를 손실 없이 표현한다. Resolver 호출/재판정 없음."""

from ..facts import RegionRef, ResidentRegistrationFact
from ..models import RuleEvaluation
from ..resolvers.resident_registration import ResidentRegistrationResolution
from ..result_types import (
    EvaluationEvidence,
    RegionSnapshot,
    ResidentRegistrationCondition,
    ResidentRegistrationDetails,
    ResultValidationError,
)


def _region_snapshot(region: RegionRef | None, field: str) -> RegionSnapshot | None:
    if region is None:
        return None
    if type(region) is not RegionRef:
        raise ResultValidationError("INVALID_RESOLUTION_REGION", field)
    return RegionSnapshot(region.sido, region.sigungu)


def adapt_resident_registration_resolution(
    *,
    rule_id: str,
    resolution: ResidentRegistrationResolution,
    policy_condition: ResidentRegistrationCondition,
    evidence_refs: tuple[str, ...] = (),
) -> RuleEvaluation:
    """검증된 결과를 변환한다. 상태/사유/누락/선택 근거 순서를 유지한다.

    policy_condition은 바인딩의 의미를 명시한다. 요구값 일치는 서로 다른
    변환 입력의 정합성 검사이며, 관찰 지역과 요구 지역의 자격 비교가 아니다.
    날짜 선택/추론 및 Resolver 호출은 하지 않는다. 변환할 수 없는 구조만
    ResultValidationError로 거부하고, 기존 결과 모델 검증 오류도 전파한다.
    """
    if type(resolution) is not ResidentRegistrationResolution:
        raise ResultValidationError("INVALID_RESOLUTION", "resolution")
    if type(policy_condition) is not ResidentRegistrationCondition:
        raise ResultValidationError("INVALID_POLICY_CONDITION", "policy_condition")
    required = _region_snapshot(resolution.required_region, "required_region")
    if required != policy_condition.required_region:
        raise ResultValidationError("RESOLUTION_CONDITION_MISMATCH", "required_region")
    if type(resolution.used_facts) is not tuple or any(
            type(fact) is not ResidentRegistrationFact for fact in resolution.used_facts):
        raise ResultValidationError("INVALID_RESOLUTION_EVIDENCE", "used_facts")

    # 공통 관찰값/날짜와 선택 근거의 중복 메타데이터가 소실되지 않게 한다.
    # 정책 요구와의 지역 일치나 기준일 선택을 다시 판정하는 검사가 아니다.
    if not resolution.used_facts:
        if resolution.fact_as_of_date is not None or resolution.resolved_region is not None:
            raise ResultValidationError("RESOLUTION_EVIDENCE_MISMATCH", "used_facts")
    elif any(fact.as_of_date != resolution.fact_as_of_date for fact in resolution.used_facts):
        raise ResultValidationError("RESOLUTION_EVIDENCE_MISMATCH", "fact_as_of_date")
    elif any(fact.region != resolution.resolved_region for fact in resolution.used_facts):
        raise ResultValidationError("RESOLUTION_EVIDENCE_MISMATCH", "resolved_region")

    observed = _region_snapshot(resolution.resolved_region, "resolved_region")
    evidence = tuple(
        EvaluationEvidence(
            source=fact.source,
            fact_as_of_date=fact.as_of_date,
            region=_region_snapshot(fact.region, "used_facts.region"),
        )
        for fact in resolution.used_facts
    )
    return RuleEvaluation(
        rule_id=rule_id,
        status=resolution.status,
        reason_code=resolution.reason_code,
        evaluated_value=observed,
        expected_condition=policy_condition,
        missing_fields=resolution.missing_fields,
        evidence_refs=evidence_refs,
        details=ResidentRegistrationDetails(
            reference_date=resolution.reference_date,
            evidence=evidence,
        ),
    )
