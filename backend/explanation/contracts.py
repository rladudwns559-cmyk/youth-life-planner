from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Status = Literal['PASS', 'FAIL', 'UNKNOWN']
SafeText = Annotated[str, Field(min_length=1, max_length=1200)]

class StrictValue(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)

class MoneyFact(StrictValue):
    field: str
    label: str
    before: int | None
    after: int | None
    delta: int | None
    text: SafeText

class RuleFact(StrictValue):
    rule_id: str
    field: str
    before_status: Status
    after_status: Status
    before_reason: str
    after_reason: str
    input_changed: bool
    before_missing: list[str]
    after_missing: list[str]
    source_refs: list[str]

class PolicyFact(StrictValue):
    policy_id: str
    before_status: Status
    after_status: Status
    rules: list[RuleFact]
    text: SafeText

class UnknownFact(StrictValue):
    policy_id: str
    before_status: Status
    after_status: Status
    before_missing_fields: list[str]
    after_missing_fields: list[str]

class NextAction(StrictValue):
    policy_id: str
    field: str
    text: SafeText

class ExplanationFacts(StrictValue):
    synthetic: Literal[True] = True
    test_only: Literal[True] = True
    dataset_version: str
    evaluation_date: str
    changed_input_fields: list[str]
    money_facts: list[MoneyFact]
    policy_facts: list[PolicyFact]
    unknown_information: list[UnknownFact]
    next_actions: list[NextAction]
    benefit_applied_krw: Literal[0] = 0
    assumptions: list[str]

class ExplanationDocument(StrictValue):
    summary: SafeText
    changed_facts: list[MoneyFact]
    policy_explanations: list[PolicyFact]
    unknown_information: list[UnknownFact]
    next_actions: list[NextAction]

class ExplanationResponse(StrictValue):
    synthetic: Literal[True] = True
    test_only: Literal[True] = True
    explanation_text: str
    explanation_source: Literal['deterministic', 'deterministic_fallback', 'llm', 'validated_test_double']
    document: ExplanationDocument
    facts: ExplanationFacts
    related_policy_ids: list[str]
    unknown_information: list[UnknownFact]
    fallback: bool
    fallback_reason: str | None
    ai_attempted: bool
    ai_executed: bool
    ai_success: bool
    validation_passed: bool
    provider_kind: Literal['none', 'ollama_local', 'test_double']
    external_transmission: Literal[False] = False
    disclaimer: str
