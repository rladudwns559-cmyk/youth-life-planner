"""웹 경계의 입력 검증. 정책의 자격 기준을 정의하지 않는다."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

# JavaScript에서도 모든 합계를 정수로 정확히 다루기 위한 웹 입력 한도.
MAX_KRW = 1_000_000_000_000
Money = Annotated[int, Field(strict=True, ge=0, le=MAX_KRW)]


class SimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    age: Annotated[int, Field(strict=True, ge=0, le=120)] | None = None
    region: Annotated[str, Field(max_length=80)] | None = None
    student_status: bool | None = None
    employment_status: Literal["employed", "unemployed"] | None = None
    monthly_income: Money
    monthly_rent: Money
    monthly_fixed_expenses: Money
    other_monthly_expenses: Money
    user_savings_capacity: Money | None = None

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SimulationResponse(BaseModel):
    synthetic: Literal[True] = True
    test_only: Literal[True] = True
    dataset_version: str
    evaluation_date: str
    input_summary: SimulationInput
    policies: list[dict]
    cashflow: dict
