"""순수 함수에 가까운 결정적 정책 평가. 외부 I/O 없음."""

from .errors import ContextValidationError, PolicyDataError
from .models import EvaluationContext, ExpectedCondition, Field, GroupCondition, GroupOperator, Operator, Policy, PolicyEvaluation, PolicyRule, PolicySet, ReasonCode, RuleEvaluation, RuleGroup, RuleNode, Status, UserProfile


def _evaluate_atom(profile: UserProfile, rule: PolicyRule) -> RuleEvaluation:
    basis = None
    if rule.field is Field.HOUSEHOLD_INCOME:
        fact = next((f for f in profile.policy_facts if f.field is rule.field), None)
        value = fact.value if fact is not None else None
        basis = fact.fact_basis if fact is not None else None
    else:
        value = getattr(profile, rule.field.value)

    reason = None
    if value is None:
        reason = ReasonCode.MISSING_FIELD
    elif rule.field is Field.HOUSEHOLD_INCOME:
        if basis is None:
            reason = ReasonCode.FACT_BASIS_MISSING
        elif basis != rule.fact_basis:
            reason = ReasonCode.FACT_BASIS_MISMATCH

    if reason is not None:
        status = Status.UNKNOWN
        missing = (rule.field.value,)
    else:
        # 모델 검증이 타입을 확정했다. false와 0의 혼용을 허용하지 않는다.
        if rule.operator is Operator.EQ:
            met = type(value) is type(rule.value) and value == rule.value
        elif rule.operator is Operator.IN:
            met = any(type(value) is type(candidate) and value == candidate for candidate in rule.value)
        elif rule.operator is Operator.GTE:
            met = value >= rule.value
        else:  # 검증된 유일한 나머지 연산자: LTE
            met = value <= rule.value
        status = Status.PASS if met else Status.FAIL
        reason = ReasonCode.CONDITION_MET if met else ReasonCode.CONDITION_NOT_MET
        missing = ()
    return RuleEvaluation(
        rule.rule_id, status, reason, value,
        ExpectedCondition(rule.field, rule.operator, rule.value, rule.fact_basis),
        missing, rule.evidence_refs,
    )


def _aggregate(operator: GroupOperator, statuses: tuple[Status, ...]) -> Status:
    if operator is GroupOperator.NOT:
        return {Status.PASS: Status.FAIL, Status.FAIL: Status.PASS, Status.UNKNOWN: Status.UNKNOWN}[statuses[0]]
    if operator is GroupOperator.ALL:
        if Status.FAIL in statuses:
            return Status.FAIL
        return Status.PASS if all(s is Status.PASS for s in statuses) else Status.UNKNOWN
    if Status.PASS in statuses:
        return Status.PASS
    return Status.FAIL if all(s is Status.FAIL for s in statuses) else Status.UNKNOWN


def _evaluate_node(profile: UserProfile, node: RuleNode) -> tuple[RuleEvaluation, ...]:
    if type(node) is PolicyRule:
        return (_evaluate_atom(profile, node),)
    if type(node) is not RuleGroup:
        raise PolicyDataError("기존 평가 경로는 PolicyRule과 RuleGroup만 지원합니다")
    child_results = tuple(_evaluate_node(profile, child) for child in node.children)
    return _assemble_group_result(node, child_results)


def _assemble_group_result(
    node: RuleGroup, child_results: tuple[tuple[RuleEvaluation, ...], ...],
) -> tuple[RuleEvaluation, ...]:
    """기존/혼합 경로가 공유하는 그룹 결과 조립. 판정은 Status만 집계한다."""
    flat = tuple(result for subtree in child_results for result in subtree)
    status = _aggregate(node.operator, tuple(subtree[0].status for subtree in child_results))
    group_result = RuleEvaluation(
        node.rule_id, status, ReasonCode(f"{node.operator.value}_{status.value}"), None,
        GroupCondition(node.operator, tuple(child.rule_id for child in node.children)),
        tuple(sorted({field for result in flat for field in result.missing_fields})),
        tuple(sorted({ref for result in flat for ref in result.evidence_refs})),
    )
    return (group_result, *flat)


def evaluate_policy(profile: UserProfile, policy: Policy, context: EvaluationContext) -> PolicyEvaluation:
    results = _evaluate_node(profile, policy.root)
    return _assemble_policy_result(policy, context, results)


def _assemble_policy_result(
    policy: Policy, context: EvaluationContext, results: tuple[RuleEvaluation, ...],
) -> PolicyEvaluation:
    """기존 순서·사유·누락 합집합과 정책 context를 공통으로 보존한다."""
    return PolicyEvaluation(
        policy.policy_id, results[0].status, results,
        tuple(sorted({field for result in results for field in result.missing_fields})),
        tuple(sorted({r.reason_code for r in results}, key=lambda r: r.value)),
        context, policy.rule_version,
    )


def evaluate_policies(profile: UserProfile, policy_set: PolicySet, context: EvaluationContext) -> tuple[PolicyEvaluation, ...]:
    if context.dataset_version != policy_set.dataset_version:
        raise ContextValidationError("컨텍스트와 정책 데이터셋 버전이 다릅니다")
    return tuple(evaluate_policy(profile, policy, context) for policy in policy_set.policies)
