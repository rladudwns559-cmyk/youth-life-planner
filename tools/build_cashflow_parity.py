"""Write the Python results the browser cashflow port must reproduce exactly.

The public site has no server, so `frontend/src/cashflow.ts` mirrors
`backend.cashflow.calculator.calculate_cashflow` (policy cash benefit fixed at 0).
This file is the single source of expected values: pytest regenerates it and compares,
vitest runs the TypeScript port against it. Change the Python first, then rerun this tool.

Usage (repo root):  python -m tools.build_cashflow_parity
"""
import json
import random
from pathlib import Path

from backend.cashflow.calculator import calculate_cashflow
from backend.cashflow.models import CashflowInput

OUTPUT = Path(__file__).resolve().parents[1] / 'frontend' / 'src' / 'testing' / 'cashflow-parity.json'
MAX_KRW = 1_000_000_000_000
EDGE = [
    (0, 0, 0, 0, None), (0, 0, 0, 0, 0), (1500000, 450000, 200000, 350000, 300000),
    (1500000, 450000, 200000, 350000, None), (1500000, 450000, 200000, 350000, 0),
    (1000000, 700000, 300000, 200000, 300000), (1000000, 700000, 300000, 200000, None),
    (2000000, 500000, 300000, 200000, 5000000), (2000000, 500000, 300000, 200000, 1000000),
    (2000000, 500000, 300000, 200000, 999999), (1, 0, 0, 0, None), (0, 1, 0, 0, None),
    (MAX_KRW, 0, 0, 0, None), (0, MAX_KRW, MAX_KRW, MAX_KRW, None), (MAX_KRW, MAX_KRW, MAX_KRW, MAX_KRW, MAX_KRW),
]


def cases() -> list[dict]:
    rng = random.Random(20261111)
    rows = list(EDGE)
    for _ in range(200):
        income = rng.choice([0, rng.randrange(0, 6_000_000), rng.randrange(0, 6_000_000) // 10_000 * 10_000])
        rows.append((income, rng.randrange(0, 1_500_000), rng.randrange(0, 900_000), rng.randrange(0, 1_500_000),
                     rng.choice([None, 0, rng.randrange(0, 2_000_000)])))
    out = []
    for income, rent, fixed, other, capacity in rows:
        given = CashflowInput(monthly_income=income, monthly_rent=rent, monthly_fixed_expenses=fixed,
                              other_monthly_expenses=other, user_savings_capacity=capacity)
        out.append({'input': {k: v for k, v in given.to_dict().items() if k != 'monthly_policy_cash_benefit'},
                    'expected': calculate_cashflow(given).to_dict()})
    return out


def build() -> dict:
    return {'source': 'backend.cashflow.calculator.calculate_cashflow', 'policy_cash_benefit': 0, 'cases': cases()}


if __name__ == '__main__':
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f"{len(build()['cases'])} cases -> {OUTPUT}")
