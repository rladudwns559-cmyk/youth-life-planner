"""단일 합성 Policy의 메모리 내 혼합 트리 평가. JSON/배치 로딩은 하지 않는다."""

from .adapters import adapt_resident_registration_resolution
from .birth_evaluator import evaluate_birth_date_rule
from .errors import ContextValidationError, PolicyDataError, ProfileValidationError
from .evaluation_inputs import EvaluationFacts, PolicyReferenceContext
from .evaluator import _assemble_group_result, _assemble_policy_result, _evaluate_atom
from .models import (
    EvaluationContext, Policy, PolicyEvaluation, PolicyRule, RuleEvaluation, RuleGroup,
    RuleNode, UserProfile, walk_nodes,
)
from .resolvers.resident_registration import ResidentRegistrationResolution, resolve_resident_registration
from .result_types import ReferenceDateSource, RegionSnapshot, ResidentRegistrationCondition, ResultValidationError
from .specialized_rules import BirthDateRule, ResidentRegistrationRule


def _route_node(
    profile: UserProfile,
    node: RuleNode,
    context: EvaluationContext,
    facts: EvaluationFacts,
    reference_context: PolicyReferenceContext | None,
) -> tuple[RuleEvaluation, ...]:
    if type(node) is PolicyRule:
        return (_evaluate_atom(profile, node),)
    if type(node) is ResidentRegistrationRule:
        if reference_context is None:
            raise ContextValidationError("주민등록 조건에는 PolicyReferenceContext가 필요합니다")
        if node.reference_date_source is not ReferenceDateSource.APPLICATION_DATE:
            raise PolicyDataError("reference_date_source: APPLICATION_DATE만 지원합니다")
        resolution = resolve_resident_registration(
            facts.resident_registrations,
            required_region=node.required_region,
            reference_date=reference_context.application_date,
            evaluation_date=context.as_of,
        )
        if type(resolution) is not ResidentRegistrationResolution:
            raise ResultValidationError("INVALID_RESOLUTION", "resolution")
        # 전달한 시간 관점의 반환 여부만 검사한다. 날짜의 정책 충족은 재판정하지 않는다.
        if resolution.evaluation_date != context.as_of:
            raise ResultValidationError("RESOLUTION_EVALUATION_DATE_MISMATCH", "evaluation_date")
        if resolution.reference_date != reference_context.application_date:
            raise ResultValidationError("RESOLUTION_REFERENCE_DATE_MISMATCH", "reference_date")
        condition = ResidentRegistrationCondition(
            RegionSnapshot(node.required_region.sido, node.required_region.sigungu),
            node.reference_date_source,
        )
        return (adapt_resident_registration_resolution(
            rule_id=node.rule_id,
            resolution=resolution,
            policy_condition=condition,
            evidence_refs=node.evidence_refs,
        ),)
    if type(node) is BirthDateRule:
        return (evaluate_birth_date_rule(node, facts.birth),)
    if type(node) is RuleGroup:
        children = tuple(_route_node(profile, child, context, facts, reference_context) for child in node.children)
        return _assemble_group_result(node, children)
    raise PolicyDataError("지원하지 않는 RuleNode 타입입니다")


def evaluate_policy_tree(
    profile: UserProfile,
    policy: Policy,
    context: EvaluationContext,
    *,
    facts: EvaluationFacts | None = None,
    reference_context: PolicyReferenceContext | None = None,
) -> PolicyEvaluation:
    """기존 API와 분리된 단일 Policy entrypoint. 입력은 바꾸지 않는다.

    facts 생략은 빈 사실 묶음이다. 주민등록 leaf에는 해당 정책 context가
    필수지만, 그 context.application_date=None은 Resolver의 정상 미입력이다.
    오류를 정상 상태로 변환하지 않는다. 정책/사실 자료를 저장하지 않는다.
    """
    if type(profile) is not UserProfile:
        raise ProfileValidationError("profile: UserProfile이 필요합니다")
    if type(policy) is not Policy:
        raise PolicyDataError("policy: Policy가 필요합니다")
    if type(context) is not EvaluationContext:
        raise ContextValidationError("context: EvaluationContext가 필요합니다")
    if facts is None:
        facts = EvaluationFacts()
    elif type(facts) is not EvaluationFacts:
        raise ProfileValidationError("facts: EvaluationFacts가 필요합니다")
    if reference_context is not None:
        if type(reference_context) is not PolicyReferenceContext:
            raise ContextValidationError("reference_context: PolicyReferenceContext가 필요합니다")
        if reference_context.policy_id != policy.policy_id:
            raise ContextValidationError("정책과 reference_context의 policy_id가 다릅니다")
    elif any(type(node) is ResidentRegistrationRule for node in walk_nodes(policy.root)):
        raise ContextValidationError("주민등록 조건에는 PolicyReferenceContext가 필요합니다")
    results = _route_node(profile, policy.root, context, facts, reference_context)
    return _assemble_policy_result(policy, context, results)
