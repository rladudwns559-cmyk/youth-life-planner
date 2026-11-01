"""M3.1: 기존 Simulation DTO를 감싸는 비교 전용 전송 값."""
from typing import Literal
from pydantic import BaseModel, ConfigDict
from .schemas import SimulationInput, SimulationResponse

Scalar = int | str | bool | None

class ComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    before: SimulationInput
    after: SimulationInput

class InputChange(BaseModel):
    field: str
    before: Scalar
    after: Scalar

class NumericDeltas(BaseModel):
    monthly_income: int
    monthly_rent: int
    monthly_fixed_expenses: int
    other_monthly_expenses: int
    total_monthly_income: int
    total_monthly_expenses: int
    disposable_before_policy: int
    disposable_after_policy: int
    savable_amount: int
    policy_benefit_applied: Literal[0]
    user_savings_capacity: int | None

class RuleComparison(BaseModel):
    rule_id: str
    field: str
    before: dict
    after: dict
    input_changed: bool
    status_changed: bool
    explanation: str

class PolicyTransition(BaseModel):
    policy_id: str
    policy_name: str
    before_status: Literal["PASS", "FAIL", "UNKNOWN"]
    after_status: Literal["PASS", "FAIL", "UNKNOWN"]
    status_changed: bool
    rules: list[RuleComparison]
    explanation: str

class UnknownInformation(BaseModel):
    policy_id: str
    before_status: str
    after_status: str
    before_missing_fields: list[str]
    after_missing_fields: list[str]

class ComparisonResponse(BaseModel):
    synthetic: Literal[True] = True
    test_only: Literal[True] = True
    before: SimulationResponse
    after: SimulationResponse
    numeric_deltas: NumericDeltas
    policy_transitions: list[PolicyTransition]
    changed_input_fields: list[InputChange]
    explanation_facts: dict
    explanations: list[str]
    unknown_information: list[UnknownInformation]
    benefit_applied_krw: Literal[0] = 0
    disclaimer: str
