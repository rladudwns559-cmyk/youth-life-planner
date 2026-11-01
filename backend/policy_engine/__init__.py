"""M1 정책 규칙 엔진의 공개 인터페이스."""

from .errors import ContextValidationError, EngineValidationError, PolicyDataError, ProfileValidationError
from .evaluator import evaluate_policies, evaluate_policy
from .loader import load_policy_set, load_profile, parse_policy_set, parse_profile
from .models import EvaluationContext, FactBasis, Field, GroupOperator, Operator, Policy, PolicyEvaluation, PolicyFact, PolicyRule, PolicySet, ReasonCode, RuleEvaluation, RuleGroup, Status, UserProfile
from .result_types import EvaluationDetails, EvaluationEvidence, EvidenceFactType, ReferenceDateSource, RegionSnapshot, ResidentRegistrationCondition, ResidentRegistrationDetails, ResultValidationError
from .result_types import BirthDateCondition, BirthDateDetails, BirthDateReasonCode
from .evaluation_inputs import EvaluationFacts, PolicyReferenceContext
from .specialized_rules import BirthDateRule, ResidentRegistrationRule
from .routing import evaluate_policy_tree
from .birth_evaluator import evaluate_birth_date_rule

__all__ = [
    "BirthDateRule",
    "evaluate_birth_date_rule",
    "BirthDateCondition", "BirthDateDetails", "BirthDateReasonCode",
    "ContextValidationError", "EngineValidationError", "PolicyDataError", "ProfileValidationError",
    "evaluate_policies", "evaluate_policy", "load_policy_set", "load_profile", "parse_policy_set", "parse_profile",
    "EvaluationContext", "FactBasis", "Field", "GroupOperator", "Operator", "Policy", "PolicyEvaluation",
    "PolicyFact", "PolicyRule", "PolicySet", "ReasonCode", "RuleEvaluation", "RuleGroup", "Status", "UserProfile",
    "EvaluationDetails", "EvaluationEvidence", "EvidenceFactType", "ReferenceDateSource", "RegionSnapshot",
    "ResidentRegistrationCondition", "ResidentRegistrationDetails", "ResultValidationError",
    "EvaluationFacts", "PolicyReferenceContext", "ResidentRegistrationRule",
    "evaluate_policy_tree",
]
