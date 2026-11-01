"""명시적 출생일 구간만 비교하는 독립 순수 evaluator. 시각·정책 트리·I/O와 무관하다."""

from .errors import PolicyDataError, ProfileValidationError
from .facts.birth import BirthFact
from .models import RuleEvaluation, Status
from .result_types import BirthDateCondition, BirthDateDetails, BirthDateReasonCode
from .specialized_rules.birth_date import BirthDateRule


def evaluate_birth_date_rule(rule: BirthDateRule, birth_fact: BirthFact | None) -> RuleEvaluation:
    """생성 시 검증된 Rule/Fact를 비교한다. 입력 부재와 잘못된 타입은 구별한다."""
    if type(rule) is not BirthDateRule:
        raise PolicyDataError("rule: BirthDateRule이 필요합니다")
    if birth_fact is not None and type(birth_fact) is not BirthFact:
        raise ProfileValidationError("birth_fact: BirthFact 또는 None이 필요합니다")

    observed = birth_fact.birth_date if birth_fact is not None else None
    source = birth_fact.source if birth_fact is not None else None
    if observed is None:
        status = Status.UNKNOWN
        reason = BirthDateReasonCode.BIRTH_DATE_MISSING
        missing = ("birth.birth_date",)
    elif observed < rule.min_birth_date:
        status = Status.FAIL
        reason = BirthDateReasonCode.BIRTH_DATE_BEFORE_RANGE
        missing = ()
    elif observed > rule.max_birth_date:
        status = Status.FAIL
        reason = BirthDateReasonCode.BIRTH_DATE_AFTER_RANGE
        missing = ()
    else:
        status = Status.PASS
        reason = BirthDateReasonCode.BIRTH_DATE_WITHIN_RANGE
        missing = ()

    return RuleEvaluation(
        rule_id=rule.rule_id, status=status, reason_code=reason,
        evaluated_value=observed,
        expected_condition=BirthDateCondition(rule.min_birth_date, rule.max_birth_date),
        missing_fields=missing, evidence_refs=rule.evidence_refs,
        details=BirthDateDetails(source),
    )
