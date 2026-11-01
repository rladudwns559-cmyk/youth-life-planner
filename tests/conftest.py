from datetime import date
from pathlib import Path

import pytest

from backend.policy_engine import EvaluationContext, FactBasis, load_policy_set, load_profile

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def policy_data_path():
    return ROOT / "data/synthetic/policies.json"


@pytest.fixture
def policy_set(policy_data_path):
    return load_policy_set(policy_data_path)


@pytest.fixture
def profile():
    return load_profile(ROOT / "data/synthetic/profile.json")


@pytest.fixture
def context():
    return EvaluationContext(date(2026, 10, 20), "synthetic-v1")


@pytest.fixture
def income_basis():
    return FactBasis("synthetic_gross", "household", "monthly", 2026, "KRW")
