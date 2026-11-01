"""합성 fixture → 공개 Policy API / Cashflow Core. 요청 결과를 보관하지 않는다."""

from datetime import date
from functools import lru_cache
from pathlib import Path

from backend.cashflow import CashflowInput
from backend.cashflow.calculator import calculate_cashflow
from backend.policy_engine import EvaluationContext, UserProfile, evaluate_policies, load_policy_set
from .schemas import SimulationInput, SimulationResponse

SYNTHETIC_DATE = date(2026, 10, 20)  # 기존 합성 CLI와 동일한 재현용 평가일
ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def synthetic_policies():
    policies = load_policy_set(ROOT / "data/synthetic/policies.json")
    if not policies.synthetic or not policies.test_only:
        raise RuntimeError("합성 시연 데이터가 필요합니다")
    return policies


def simulate(data: SimulationInput) -> SimulationResponse:
    policies = synthetic_policies()
    profile = UserProfile(
        age=data.age, region=data.region, student_status=data.student_status,
        employment_status=data.employment_status, monthly_income=data.monthly_income,
        policy_facts=(),  # 생활비 소득을 household_income 사실로 변환하지 않는다.
    )
    context = EvaluationContext(as_of=SYNTHETIC_DATE, dataset_version=policies.dataset_version)
    evaluations = evaluate_policies(profile, policies, context)
    results = [dict(result.to_dict(), policy_name=policy.policy_name)
               for policy, result in zip(policies.policies, evaluations, strict=True)]
    cashflow = calculate_cashflow(CashflowInput(
        monthly_income=data.monthly_income, monthly_rent=data.monthly_rent,
        monthly_fixed_expenses=data.monthly_fixed_expenses,
        other_monthly_expenses=data.other_monthly_expenses,
        user_savings_capacity=data.user_savings_capacity,
        monthly_policy_cash_benefit=0,
    ))
    return SimulationResponse(
        dataset_version=policies.dataset_version, evaluation_date=SYNTHETIC_DATE.isoformat(),
        input_summary=data, policies=results, cashflow=cashflow.to_dict(),
    )
