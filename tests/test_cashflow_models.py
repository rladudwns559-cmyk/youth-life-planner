"""현금흐름 값 모델의 타입·부호·불변성 계약. 실제 계산은 수행하지 않는다."""

from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
from enum import IntEnum
import json
from pathlib import Path
import subprocess
import sys

import pytest

from backend.cashflow import CashflowInput, CashflowResult, CashflowValidationError


INPUT_NAMES = (
    "monthly_income", "monthly_rent", "monthly_fixed_expenses", "other_monthly_expenses",
    "user_savings_capacity", "monthly_policy_cash_benefit",
)
RESULT_NAMES = (
    "monthly_income", "essential_monthly_expenses", "other_monthly_expenses",
    "total_monthly_expenses", "policy_benefit_applied", "total_monthly_income",
    "disposable_before_policy", "disposable_after_policy", "user_savings_capacity", "savable_amount",
)
DISPOSABLE = ("disposable_before_policy", "disposable_after_policy")


def input_values():
    return dict(monthly_income=2_000_000, monthly_rent=500_000,
                monthly_fixed_expenses=300_000, other_monthly_expenses=200_000)


def result_values():
    # 명시적 수동 결과 예시. Input에서 결과를 만드는 계산 helper가 아니다.
    return dict(monthly_income=2_000_000, essential_monthly_expenses=800_000,
                other_monthly_expenses=200_000, total_monthly_expenses=1_000_000,
                policy_benefit_applied=100_000, total_monthly_income=2_100_000,
                disposable_before_policy=1_000_000, disposable_after_policy=1_100_000,
                user_savings_capacity=400_000, savable_amount=400_000)


class IntSubclass(int):
    pass


class IntMember(IntEnum):
    ZERO = 0


WRONG_TYPES = [0.0, 1.5, float("nan"), float("inf"), True, False, "1000000", "",
               Decimal("100"), [], {}, (), object(), IntSubclass(1), IntMember.ZERO]


def test_exact_fields_defaults_and_explicit_values():
    model = CashflowInput(**input_values())
    assert tuple(f.name for f in fields(model)) == INPUT_NAMES
    assert model.user_savings_capacity is None
    assert model.monthly_policy_cash_benefit == 0
    assert model.to_dict() == {**input_values(), "user_savings_capacity": None, "monthly_policy_cash_benefit": 0}
    result = CashflowResult(**result_values())
    assert tuple(f.name for f in fields(result)) == RESULT_NAMES
    assert result.to_dict() == result_values()


@pytest.mark.parametrize("field", INPUT_NAMES)
@pytest.mark.parametrize("value", [0, 1, 10**30])
def test_each_input_accepts_exact_nonnegative_int_without_coercion(field, value):
    data = input_values()
    data[field] = value
    model = CashflowInput(**data)
    assert getattr(model, field) == value
    assert type(model.to_dict()[field]) is int


@pytest.mark.parametrize("field", INPUT_NAMES)
@pytest.mark.parametrize("value", WRONG_TYPES)
def test_each_input_rejects_non_exact_int(field, value):
    data = input_values()
    data[field] = value
    with pytest.raises(CashflowValidationError) as caught:
        CashflowInput(**data)
    assert caught.value.code == "INVALID_KRW_TYPE"
    assert caught.value.field == field


@pytest.mark.parametrize("field", INPUT_NAMES)
def test_each_input_rejects_negative_amount(field):
    with pytest.raises(CashflowValidationError) as caught:
        CashflowInput(**{**input_values(), field: -1})
    assert caught.value.code == "NEGATIVE_KRW_AMOUNT"
    assert caught.value.field == field


@pytest.mark.parametrize("field", [name for name in INPUT_NAMES if name != "user_savings_capacity"])
def test_none_is_rejected_on_all_nonnullable_input_fields(field):
    with pytest.raises(CashflowValidationError):
        CashflowInput(**{**input_values(), field: None})


@pytest.mark.parametrize("field", INPUT_NAMES[:4])
def test_each_required_input_argument_must_be_present(field):
    data = input_values()
    del data[field]
    with pytest.raises(TypeError):
        CashflowInput(**data)


def test_capacity_missing_none_and_zero_remain_distinct():
    default = CashflowInput(**input_values())
    explicit = CashflowInput(**input_values(), user_savings_capacity=None)
    zero = CashflowInput(**input_values(), user_savings_capacity=0)
    assert default == explicit
    assert default != zero
    assert default.to_dict()["user_savings_capacity"] is None
    assert zero.to_dict()["user_savings_capacity"] == 0


def test_benefit_missing_is_zero_but_explicit_none_is_error():
    default = CashflowInput(**input_values())
    assert default == CashflowInput(**input_values(), monthly_policy_cash_benefit=0)
    with pytest.raises(CashflowValidationError):
        CashflowInput(**input_values(), monthly_policy_cash_benefit=None)
    # 양수는 구조적으로 보존할 뿐 실제 정책 승인을 검증한 것이 아니다.
    assert CashflowInput(**input_values(), monthly_policy_cash_benefit=123).monthly_policy_cash_benefit == 123


@pytest.mark.parametrize("field", RESULT_NAMES)
@pytest.mark.parametrize("value", [0, 1, 10**30])
def test_each_result_field_preserves_nonnegative_exact_int(field, value):
    model = CashflowResult(**{**result_values(), field: value})
    assert getattr(model, field) == value
    assert type(model.to_dict()[field]) is int


@pytest.mark.parametrize("field", RESULT_NAMES)
@pytest.mark.parametrize("value", WRONG_TYPES)
def test_each_result_field_rejects_non_exact_int(field, value):
    with pytest.raises(CashflowValidationError) as caught:
        CashflowResult(**{**result_values(), field: value})
    assert caught.value.code == "INVALID_KRW_TYPE"
    assert caught.value.field == field


@pytest.mark.parametrize("field", [name for name in RESULT_NAMES if name not in DISPOSABLE])
def test_each_nonnegative_result_field_rejects_negative_value(field):
    with pytest.raises(CashflowValidationError) as caught:
        CashflowResult(**{**result_values(), field: -1})
    assert caught.value.code == "NEGATIVE_KRW_AMOUNT"
    assert caught.value.field == field


@pytest.mark.parametrize("field", DISPOSABLE)
@pytest.mark.parametrize("value", [-1, -200_000, -(10**30)])
def test_disposable_fields_preserve_deficit_without_clamping(field, value):
    result = CashflowResult(**{**result_values(), field: value})
    assert getattr(result, field) == value
    assert result.to_dict()[field] == value


@pytest.mark.parametrize("field", [name for name in RESULT_NAMES if name != "user_savings_capacity"])
def test_result_requires_nonnull_calculated_values(field):
    with pytest.raises(CashflowValidationError):
        CashflowResult(**{**result_values(), field: None})


@pytest.mark.parametrize("field", RESULT_NAMES)
def test_every_result_argument_is_required_including_nullable_capacity(field):
    data = result_values()
    del data[field]
    with pytest.raises(TypeError):
        CashflowResult(**data)


@pytest.mark.parametrize("capacity", [None, 0, 500_000])
def test_result_capacity_is_preserved(capacity):
    result = CashflowResult(**{**result_values(), "user_savings_capacity": capacity})
    assert result.to_dict()["user_savings_capacity"] == capacity


@pytest.mark.parametrize("disposable", [1_000_000, 0, -200_000])
def test_manually_constructed_surplus_break_even_and_deficit_results(disposable):
    data = result_values()
    data.update(disposable_before_policy=disposable, disposable_after_policy=disposable,
                savable_amount=0, user_savings_capacity=None)
    result = CashflowResult(**data)
    assert result.disposable_after_policy == disposable
    assert result.savable_amount == 0


@pytest.mark.parametrize(("model", "values", "names"), [
    (CashflowInput, input_values(), INPUT_NAMES),
    (CashflowResult, result_values(), RESULT_NAMES),
])
def test_models_are_frozen_slotted_equal_and_snapshot_is_independent(model, values, names):
    first, second = model(**values), model(**values)
    assert first == second and hash(first) == hash(second)
    assert not hasattr(first, "__dict__")
    for name in names:
        with pytest.raises(FrozenInstanceError):
            setattr(first, name, 99)
        with pytest.raises(FrozenInstanceError):
            delattr(first, name)
    snapshot = first.to_dict()
    assert tuple(snapshot) == names
    assert json.loads(json.dumps(snapshot)) == snapshot
    snapshot.clear()
    values["monthly_income"] = 0
    assert first == second
    assert first.to_dict() == second.to_dict()


def test_zero_values_and_huge_int_roundtrip_keep_none_capacity():
    assert CashflowInput(0, 0, 0, 0).to_dict() == {
        "monthly_income": 0, "monthly_rent": 0, "monthly_fixed_expenses": 0,
        "other_monthly_expenses": 0, "user_savings_capacity": None, "monthly_policy_cash_benefit": 0,
    }
    data = {name: 10**30 for name in RESULT_NAMES}
    data["user_savings_capacity"] = None
    result = CashflowResult(**data)
    assert json.loads(json.dumps(result.to_dict())) == data


def test_constructor_does_not_recalculate_results_or_enforce_calculator_relations():
    # 산술적으로 불일치해도 타입·부호가 유효한 수동 snapshot은 허용한다.
    # 결과의 계산 정확성과 저축 상한 관계는 후속 calculator 테스트의 책임이다.
    result = CashflowResult(**{**result_values(), "total_monthly_income": 1,
        "disposable_after_policy": -200_000, "user_savings_capacity": 0, "savable_amount": 999})
    assert result.total_monthly_income == 1
    assert result.disposable_after_policy == -200_000
    assert result.savable_amount == 999


def test_replace_constructs_independent_input_and_revalidates():
    before = CashflowInput(**input_values())
    after = replace(before, monthly_rent=700_000)
    assert before.monthly_rent == 500_000 and after.monthly_rent == 700_000
    with pytest.raises(CashflowValidationError):
        replace(before, monthly_income=True)


@pytest.mark.parametrize("model,values", [(CashflowInput, input_values()), (CashflowResult, result_values())])
@pytest.mark.parametrize("extra", ["status", "policy_evaluation", "restricted_benefit", "quarterly_benefit"])
def test_policy_status_and_unsupported_benefits_are_not_model_fields(model, values, extra):
    with pytest.raises(TypeError):
        model(**{**values, extra: 1})


def test_error_has_stable_code_field_and_does_not_echo_raw_value():
    secret = "private-income-payload"
    with pytest.raises(CashflowValidationError) as caught:
        CashflowInput(**{**input_values(), "monthly_income": secret})
    assert isinstance(caught.value, ValueError)
    assert CashflowValidationError.__bases__ == (ValueError,)
    assert caught.value.code == "INVALID_KRW_TYPE" and caught.value.field == "monthly_income"
    assert secret not in str(caught.value)


def test_clean_interpreter_can_import_and_construct_with_policy_engine_import_blocked():
    # 별도 프로세스로 이미 import된 정책 모듈의 영향을 제거한다.
    script = '''
import builtins, sys
sys.path.insert(0, sys.argv[1])
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith("backend.policy_engine"):
        raise AssertionError("policy engine dependency")
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import backend.cashflow as domain
model = domain.CashflowInput(0, 0, 0, 0)
assert model.to_dict()["user_savings_capacity"] is None
assert not any(name.startswith("backend.policy_engine") for name in sys.modules)
assert set(domain.__all__) == {"CashflowInput", "CashflowResult", "CashflowValidationError"}
assert not hasattr(domain, "calculate_cashflow")
'''
    process = subprocess.run([sys.executable, "-I", "-c", script, str(Path(__file__).resolve().parents[1])],
                             capture_output=True, text=True, timeout=10)
    assert process.returncode == 0, process.stderr
