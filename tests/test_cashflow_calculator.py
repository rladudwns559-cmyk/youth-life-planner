"""같은 월의 가상 금액으로 계산 계약을 검증한다."""

from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
import subprocess
import sys

import pytest

from backend.cashflow import CashflowInput, CashflowResult, CashflowValidationError
from backend.cashflow.calculator import calculate_cashflow


def test_manual_example_matches_all_ten_fields():
    result = calculate_cashflow(CashflowInput(
        2_000_000, 500_000, 300_000, 400_000,
        user_savings_capacity=600_000, monthly_policy_cash_benefit=100_000,
    ))
    expected = {
        "monthly_income": 2_000_000,
        "essential_monthly_expenses": 800_000,
        "other_monthly_expenses": 400_000,
        "total_monthly_expenses": 1_200_000,
        "policy_benefit_applied": 100_000,
        "total_monthly_income": 2_100_000,
        "disposable_before_policy": 800_000,
        "disposable_after_policy": 900_000,
        "user_savings_capacity": 600_000,
        "savable_amount": 600_000,
    }
    assert type(result) is CashflowResult
    assert result == CashflowResult(**expected)
    assert result.to_dict() == expected


@pytest.mark.parametrize("income,rent,fixed,other,benefit,essential,expenses,before,total,after,saving", [
    (1000, 200, 100, 100, 0, 300, 400, 600, 1000, 600, 600),
    (1000, 200, 100, 100, 200, 300, 400, 600, 1200, 800, 800),
    (1000, 0, 0, 0, 0, 0, 0, 1000, 1000, 1000, 1000),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 100, 20, 30, 0, 120, 150, -150, 0, -150, 0),
    (500, 200, 100, 200, 0, 300, 500, 0, 500, 0, 0),
    (1000, 800, 200, 200, 100, 1000, 1200, -200, 1100, -100, 0),
    (1000, 800, 200, 200, 200, 1000, 1200, -200, 1200, 0, 0),
    (1000, 800, 200, 200, 500, 1000, 1200, -200, 1500, 300, 300),
    (0, 100, 20, 30, 200, 120, 150, -150, 200, 50, 50),
    (10**100, 10**90, 2*10**90, 3*10**90, 10**90,
     3*10**90, 6*10**90, 10**100-6*10**90, 10**100+10**90,
     10**100-5*10**90, 10**100-5*10**90),
])
def test_independent_expected_arithmetic(
    income, rent, fixed, other, benefit, essential, expenses, before, total, after, saving,
):
    result = calculate_cashflow(CashflowInput(
        income, rent, fixed, other, monthly_policy_cash_benefit=benefit,
    ))
    assert result.to_dict() == dict(
        monthly_income=income, essential_monthly_expenses=essential,
        other_monthly_expenses=other, total_monthly_expenses=expenses,
        policy_benefit_applied=benefit, total_monthly_income=total,
        disposable_before_policy=before, disposable_after_policy=after,
        user_savings_capacity=None, savable_amount=saving,
    )
    assert all(type(value) is int for value in result.to_dict().values() if value is not None)


@pytest.mark.parametrize("income,capacity,expected", [
    (800, None, 300), (500, None, 0), (200, None, 0),
    (800, 0, 0), (800, 200, 200), (800, 300, 300), (800, 500, 300),
    (200, 100, 0), (500, 100, 0), (200, 0, 0),
])
def test_savings_capacity_boundaries(income, capacity, expected):
    result = calculate_cashflow(CashflowInput(income, 200, 100, 200, capacity))
    assert result.savable_amount == expected
    assert result.user_savings_capacity == capacity
    assert result.disposable_after_policy == income - 500


@pytest.mark.parametrize("capacity,expected", [(None, 500), (400, 400), (0, 0)])
def test_explicit_benefit_can_increase_saving_without_increasing_capacity(capacity, expected):
    baseline = CashflowInput(700, 200, 100, 100, capacity)
    before = calculate_cashflow(baseline)
    after = calculate_cashflow(replace(baseline, monthly_policy_cash_benefit=200))
    assert before.savable_amount == (0 if capacity == 0 else 300)
    assert after.savable_amount == expected
    assert after.user_savings_capacity == before.user_savings_capacity == capacity


@pytest.mark.parametrize("income,rent,fixed,other,benefit", [
    (0, 0, 0, 0, 0), (0, 1, 2, 3, 1), (6, 1, 2, 3, 0),
    (6, 1, 2, 3, 1), (20, 1, 2, 3, 4), (1, 10, 20, 30, 100),
    (10**100, 10**80, 10**70, 10**60, 10**90),
])
@pytest.mark.parametrize("capacity", [None, 0, 1, 10, 10**110])
def test_arithmetic_invariants_and_input_preservation(income, rent, fixed, other, benefit, capacity):
    original = CashflowInput(income, rent, fixed, other, capacity, benefit)
    snapshot = original.to_dict()
    result = calculate_cashflow(original)
    assert original.to_dict() == snapshot
    assert result.essential_monthly_expenses == rent + fixed
    assert result.total_monthly_expenses == result.essential_monthly_expenses + other
    assert result.total_monthly_income == income + benefit
    assert result.disposable_after_policy - result.disposable_before_policy == benefit
    assert result.savable_amount >= 0
    assert result.savable_amount <= max(0, result.disposable_after_policy)
    if capacity is not None:
        assert result.savable_amount <= capacity
    assert result.monthly_income == income
    assert result.other_monthly_expenses == other
    assert result.user_savings_capacity == capacity
    assert calculate_cashflow(original) == result
    assert calculate_cashflow(original).to_dict() == result.to_dict()


@pytest.mark.parametrize("name", [field.name for field in fields(CashflowResult)])
def test_calculated_result_is_immutable(name):
    result = calculate_cashflow(CashflowInput(1000, 100, 200, 300))
    with pytest.raises(FrozenInstanceError):
        setattr(result, name, 123)
    snapshot = result.to_dict()
    snapshot[name] = 999
    assert result.to_dict()[name] != 999


class InputSubclass(CashflowInput):
    pass


@pytest.mark.parametrize("wrong", [None, True, 42, "private-income", {}, object(), InputSubclass(0, 0, 0, 0)])
def test_wrong_object_type_uses_existing_domain_error(wrong):
    with pytest.raises(CashflowValidationError) as caught:
        calculate_cashflow(wrong)
    assert caught.value.code == "INVALID_CASHFLOW_INPUT_TYPE"
    assert caught.value.field == "cashflow_input"
    assert "private-income" not in str(caught.value)


def test_calculation_in_clean_process_without_policy_import_or_external_operations():
    script = '''
import builtins, sys, socket, random, time
sys.path.insert(0, sys.argv[1])
original_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith("backend.policy_engine"):
        raise AssertionError("policy engine dependency")
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded
from backend.cashflow import CashflowInput
from backend.cashflow.calculator import calculate_cashflow
def forbidden(*args, **kwargs):
    raise AssertionError("external operation")
builtins.open = forbidden
socket.socket = forbidden
random.random = forbidden
time.time = forbidden
value = CashflowInput(1000, 100, 200, 300)
for _ in range(3):
    assert calculate_cashflow(value).savable_amount == 400
assert not any(name.startswith("backend.policy_engine") for name in sys.modules)
'''
    process = subprocess.run(
        [sys.executable, "-I", "-c", script, str(Path(__file__).resolve().parents[1])],
        capture_output=True, text=True, timeout=10,
    )
    assert process.returncode == 0, process.stderr
