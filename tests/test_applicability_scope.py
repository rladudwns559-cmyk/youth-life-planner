"""가상 edition·명시적 분기로 독립 scope 값 계약만 검증한다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from enum import Enum, IntEnum
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.policy_data import ApplicabilityScope
from backend.policy_engine.policy_data import eligibility_coverage


class StringSubclass(str):
    pass


class IntSubclass(int):
    pass


class QuarterLike(IntEnum):
    Q3 = 3


class StringQuarter(str, Enum):
    Q3 = "Q3"


@pytest.mark.parametrize("edition", ["2026", "2027", "0000", "0001", "9999"])
@pytest.mark.parametrize("quarter", [1, 2, 3, 4, None])
def test_explicit_scope_values_and_serialization(edition, quarter):
    scope = ApplicabilityScope(edition, quarter)
    assert scope.edition_id == edition
    assert scope.quarter == quarter
    assert scope.to_dict() == {"edition_id": edition, "quarter": quarter}
    assert type(scope.edition_id) is str
    assert scope.quarter is None or type(scope.quarter) is int
    assert json.loads(json.dumps(scope.to_dict())) == scope.to_dict()
    assert scope.scope_id == f"{edition}-{'ANNUAL' if quarter is None else 'Q' + str(quarter)}"
    assert scope == ApplicabilityScope(edition, quarter)
    assert scope.to_dict() == scope.to_dict()


@pytest.mark.parametrize("edition", [
    "", " ", "\t", "26", "026", "20260", "abcd", "2026-Q3", " 2026", "2026 ",
    "2026\n", "２０２６", "٢٠٢٦", "+026", 2026, True, None, 2026.0,
    [], {}, StringSubclass("2026"),
])
def test_edition_is_exact_ascii_four_digit_string(edition):
    with pytest.raises(PolicyDataError, match="edition_id") as caught:
        ApplicabilityScope(edition, 3)
    assert isinstance(caught.value, EngineValidationError)


@pytest.mark.parametrize("quarter", [
    "Q3", "q3", "Quarter3", "3", "", 0, -1, 5, 100, True, False, 3.0,
    [], {}, (), object(), IntSubclass(3), QuarterLike.Q3, StringQuarter.Q3,
])
def test_quarter_follows_established_exact_int_contract(quarter):
    with pytest.raises(PolicyDataError, match="quarter"):
        ApplicabilityScope("2026", quarter)


@pytest.mark.parametrize("left,right", [
    (ApplicabilityScope("2026", 3), ApplicabilityScope("2026", None)),
    (ApplicabilityScope("2026", 3), ApplicabilityScope("2027", 3)),
    (ApplicabilityScope("2026", 3), ApplicabilityScope("2026", 4)),
])
def test_scope_identity_preserves_quarter_and_edition(left, right):
    assert left != right
    assert left.to_dict() != right.to_dict()
    assert left.scope_id != right.scope_id
    assert len({left, right}) == 2


@pytest.mark.parametrize("quarter", [3, None])
@pytest.mark.parametrize("name", ["edition_id", "quarter", "scope_id"])
def test_scope_fields_and_derived_display_cannot_change(quarter, name):
    scope = ApplicabilityScope("2026", quarter)
    before = scope.to_dict()
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        setattr(scope, name, "changed")
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        delattr(scope, name)
    assert scope.to_dict() == before


def test_constructor_requires_explicit_quarter_and_has_only_two_fields():
    assert [field.name for field in fields(ApplicabilityScope)] == ["edition_id", "quarter"]
    with pytest.raises(TypeError):
        ApplicabilityScope("2026")
    with pytest.raises(TypeError):
        ApplicabilityScope(quarter=3)
    scope = ApplicabilityScope("2026", None)
    assert not hasattr(scope, "__dict__")
    assert scope.scope_id == "2026-ANNUAL"


@pytest.mark.parametrize("extra", ["application_date", "evaluation_date", "policy_id", "start_date", "condition_ids"])
def test_scope_does_not_accept_other_domain_inputs(extra):
    with pytest.raises(TypeError):
        ApplicabilityScope("2026", 3, **{extra: None})


def test_new_serialization_snapshots_are_independent():
    scope = ApplicabilityScope("2026", 3)
    first, second = scope.to_dict(), scope.to_dict()
    assert first == second and first is not second
    first["edition_id"] = "2027"
    first["quarter"] = None
    assert scope.to_dict() == {"edition_id": "2026", "quarter": 3}
    assert scope.scope_id == "2026-Q3"


def test_replace_revalidates_without_changing_original():
    scope = ApplicabilityScope("2026", 3)
    annual = replace(scope, quarter=None)
    assert scope.quarter == 3 and annual.quarter is None
    with pytest.raises(PolicyDataError):
        replace(scope, quarter=5)


def test_no_scope_ordering_or_containment_is_defined():
    scope, annual = ApplicabilityScope("2026", 3), ApplicabilityScope("2026", None)
    with pytest.raises(TypeError):
        scope < annual
    with pytest.raises(TypeError):
        scope in annual


def test_model_has_no_date_or_other_domain_runtime_dependencies(monkeypatch):
    # 기존 패키지 초기화가 아닌 새 모듈 자체의 의존 경계를 검사한다.
    tree = ast.parse(inspect.getsource(eligibility_coverage))
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert [(node.module, node.level) for node in imports if isinstance(node, ast.ImportFrom)] == [
        ("dataclasses", 0), ("errors", 2),
    ]
    assert [alias.name for node in imports if isinstance(node, ast.Import) for alias in node.names] == ["re"]
    assert {node.name for node in tree.body if isinstance(node, ast.ClassDef)} == {"ApplicabilityScope"}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert calls <= {"dataclass", "type", "PolicyDataError"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"date", "datetime", "PolicyEvaluation", "CashflowInput", "PolicyBenefitAcceptance"}
    def forbidden(*args, **kwargs):
        pytest.fail("scope 값 표현에서 I/O를 호출했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    scope = ApplicabilityScope("2026", 3)
    assert scope.to_dict() == {"edition_id": "2026", "quarter": 3}
