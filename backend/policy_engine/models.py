"""불변 M1 도메인. 외부 I/O나 자동 타입 변환을 하지 않는다."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field as dataclass_field, fields, is_dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, TypeAlias, Union

import re

from .errors import ContextValidationError, EngineValidationError, PolicyDataError, ProfileValidationError
from .result_types import (
    BirthDateCondition, BirthDateDetails, BirthDateReasonCode, EvaluationDetails,
    RegionSnapshot, ResidentRegistrationCondition, ResidentRegistrationDetails, ResultValidationError,
)
from .specialized_rules import BirthDateRule, ResidentRegistrationRule

if TYPE_CHECKING:
    from .resolvers.resident_registration import ResidentRegistrationReasonCode

Scalar: TypeAlias = str | int | bool
RuleValue: TypeAlias = Scalar | tuple[Scalar, ...]
ENGINE_VERSION = "m1.0"
SUPPORTED_SCHEMA_VERSIONS = ("m1.0", "m1.1")


def validate_schema_version(value: object) -> str:
    if type(value) is not str or value not in SUPPORTED_SCHEMA_VERSIONS:
        raise PolicyDataError("schema_version: m1.0 또는 m1.1 문자열이 필요합니다")
    return value


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class Field(str, Enum):
    AGE = "age"
    REGION = "region"
    STUDENT_STATUS = "student_status"
    EMPLOYMENT_STATUS = "employment_status"
    HOUSEHOLD_INCOME = "household_income"


class Operator(str, Enum):
    EQ = "eq"
    IN = "in"
    GTE = "gte"
    LTE = "lte"


class GroupOperator(str, Enum):
    ALL = "ALL"
    ANY = "ANY"
    NOT = "NOT"


class ReasonCode(str, Enum):
    CONDITION_MET = "CONDITION_MET"
    CONDITION_NOT_MET = "CONDITION_NOT_MET"
    MISSING_FIELD = "MISSING_FIELD"
    FACT_BASIS_MISSING = "FACT_BASIS_MISSING"
    FACT_BASIS_MISMATCH = "FACT_BASIS_MISMATCH"
    ALL_PASS = "ALL_PASS"
    ALL_FAIL = "ALL_FAIL"
    ALL_UNKNOWN = "ALL_UNKNOWN"
    ANY_PASS = "ANY_PASS"
    ANY_FAIL = "ANY_FAIL"
    ANY_UNKNOWN = "ANY_UNKNOWN"
    NOT_PASS = "NOT_PASS"
    NOT_FAIL = "NOT_FAIL"
    NOT_UNKNOWN = "NOT_UNKNOWN"


# Resolver가 Status를 models에서 가져오므로 런타임 역방향 import는 하지 않는다.
# 정적 타입은 세 Enum의 유한 union이며 주민등록 reason은 지연 import로 검증한다.
EvaluationReasonCode: TypeAlias = Union[ReasonCode, "ResidentRegistrationReasonCode", BirthDateReasonCode]


def _validate_result_reason(reason: object) -> None:
    from .resolvers.resident_registration import ResidentRegistrationReasonCode

    if type(reason) not in (ReasonCode, ResidentRegistrationReasonCode, BirthDateReasonCode):
        raise ResultValidationError("INVALID_RESULT_REASON", "reason_code")


def require_text(value: object, label: str, error: type[EngineValidationError]) -> None:
    if type(value) is not str or not value.strip():
        raise error(f"{label}: 비어 있지 않은 문자열이 필요합니다")


def validate_field_value(field: Field, value: object, error: type[EngineValidationError]) -> None:
    """None 처리 이후의 값 검증. bool은 int로 인정하지 않는다."""
    expected = {
        Field.AGE: int, Field.REGION: str, Field.STUDENT_STATUS: bool,
        Field.EMPLOYMENT_STATUS: str, Field.HOUSEHOLD_INCOME: int,
    }[field]
    if type(value) is not expected:
        raise error(f"{field.value}: {expected.__name__} 타입이 필요합니다")
    if expected is int and value < 0:
        raise error(f"{field.value}: 음수는 허용하지 않습니다")
    if expected is str:
        require_text(value, field.value, error)
    if field is Field.EMPLOYMENT_STATUS and value not in ("employed", "unemployed"):
        raise error("employment_status: M1에서 지원하지 않는 상태입니다")


@dataclass(frozen=True, slots=True)
class FactBasis:
    basis: str
    subject: str
    period: str
    reference_year: int
    unit: str

    def __post_init__(self) -> None:
        for name in ("basis", "subject", "period", "unit"):
            require_text(getattr(self, name), name, EngineValidationError)
        if type(self.reference_year) is not int or self.reference_year < 1:
            raise EngineValidationError("reference_year: 양의 정수가 필요합니다")


@dataclass(frozen=True, slots=True)
class PolicyFact:
    field: Field
    value: Scalar | None
    fact_basis: FactBasis | None = None

    def __post_init__(self) -> None:
        if self.field is not Field.HOUSEHOLD_INCOME:
            raise ProfileValidationError("policy_facts: M1에서는 household_income만 지원합니다")
        if self.value is not None:
            validate_field_value(self.field, self.value, ProfileValidationError)
        if self.fact_basis is not None and type(self.fact_basis) is not FactBasis:
            raise ProfileValidationError("fact_basis: FactBasis가 필요합니다")


@dataclass(frozen=True, slots=True)
class UserProfile:
    age: int | None = None
    region: str | None = None
    student_status: bool | None = None
    employment_status: str | None = None
    monthly_income: int | None = None
    policy_facts: tuple[PolicyFact, ...] = ()

    def __post_init__(self) -> None:
        for field in (Field.AGE, Field.REGION, Field.STUDENT_STATUS, Field.EMPLOYMENT_STATUS):
            value = getattr(self, field.value)
            if value is not None:
                validate_field_value(field, value, ProfileValidationError)
        if self.monthly_income is not None:
            if type(self.monthly_income) is not int or self.monthly_income < 0:
                raise ProfileValidationError("monthly_income: 음수가 아닌 정수가 필요합니다")
        if type(self.policy_facts) is not tuple or any(type(f) is not PolicyFact for f in self.policy_facts):
            raise ProfileValidationError("policy_facts: PolicyFact의 tuple이 필요합니다")
        names = [f.field for f in self.policy_facts]
        if len(names) != len(set(names)):
            raise ProfileValidationError("policy_facts: 필드를 중복 입력할 수 없습니다")


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    field: Field
    operator: Operator
    value: RuleValue
    fact_basis: FactBasis | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.rule_id, "rule_id", PolicyDataError)
        if type(self.field) is not Field or type(self.operator) is not Operator:
            raise PolicyDataError("등록된 Field와 Operator가 필요합니다")
        if self.operator is Operator.IN:
            if type(self.value) is not tuple or not self.value:
                raise PolicyDataError("in: 비어 있지 않은 후보 tuple이 필요합니다")
            values = self.value
        else:
            values = (self.value,)
        for candidate in values:
            validate_field_value(self.field, candidate, PolicyDataError)
        if self.operator in (Operator.GTE, Operator.LTE) and self.field not in (Field.AGE, Field.HOUSEHOLD_INCOME):
            raise PolicyDataError("gte/lte: 정수 필드에만 사용할 수 있습니다")
        if self.field is Field.HOUSEHOLD_INCOME:
            if type(self.fact_basis) is not FactBasis:
                raise PolicyDataError("household_income 규칙에는 FactBasis가 필요합니다")
        elif self.fact_basis is not None:
            raise PolicyDataError("fact_basis: M1에서는 household_income에만 지정합니다")
        if type(self.evidence_refs) is not tuple or not self.evidence_refs:
            raise PolicyDataError("evidence_refs: 하나 이상의 합성 근거 참조가 필요합니다")
        for ref in self.evidence_refs:
            require_text(ref, "evidence_refs", PolicyDataError)


@dataclass(frozen=True, slots=True)
class RuleGroup:
    rule_id: str
    operator: GroupOperator
    children: tuple[RuleNode, ...]

    def __post_init__(self) -> None:
        require_text(self.rule_id, "rule_id", PolicyDataError)
        if type(self.operator) is not GroupOperator:
            raise PolicyDataError("등록된 GroupOperator가 필요합니다")
        if type(self.children) is not tuple or not self.children:
            raise PolicyDataError("RuleGroup: 비어 있지 않은 children tuple이 필요합니다")
        if any(type(child) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup) for child in self.children):
            raise PolicyDataError("children: 지원하는 RuleNode가 필요합니다")
        if self.operator is GroupOperator.NOT and len(self.children) != 1:
            raise PolicyDataError("NOT: 자식은 정확히 하나여야 합니다")
        _validate_unique_nodes(self)


RuleNode: TypeAlias = PolicyRule | ResidentRegistrationRule | BirthDateRule | RuleGroup


def walk_nodes(node: RuleNode):
    yield node
    if type(node) is RuleGroup:
        for child in node.children:
            yield from walk_nodes(child)


def _validate_unique_nodes(node: RuleNode) -> None:
    ids = [child.rule_id for child in walk_nodes(node)]
    if len(ids) != len(set(ids)):
        raise PolicyDataError("중복 rule_id가 있습니다")


def _validate_data_flags(synthetic: object, test_only: object, allow_real_data: object) -> None:
    """기본 합성 경계를 유지한다. 실제 자료 허용은 생성 시 명시해야 한다."""
    if type(allow_real_data) is not bool or type(synthetic) is not bool or type(test_only) is not bool:
        raise PolicyDataError("synthetic/test_only/allow_real_data는 bool이어야 합니다")
    if synthetic is not test_only:
        raise PolicyDataError("synthetic/test_only 혼합 조합은 지원하지 않습니다")
    if not synthetic and not allow_real_data:
        raise PolicyDataError("실제 정책 데이터는 allow_real_data=True를 명시해야 합니다")


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: str
    policy_name: str
    rule_version: str
    root: RuleNode
    synthetic: bool = True
    test_only: bool = True
    allow_real_data: InitVar[bool] = dataclass_field(default=False, kw_only=True)

    def __post_init__(self, allow_real_data: bool) -> None:
        for label in ("policy_id", "policy_name", "rule_version"):
            require_text(getattr(self, label), label, PolicyDataError)
        _validate_data_flags(self.synthetic, self.test_only, allow_real_data)
        if type(self.root) not in (PolicyRule, ResidentRegistrationRule, BirthDateRule, RuleGroup):
            raise PolicyDataError("정책 root 규칙이 필요합니다")
        _validate_unique_nodes(self.root)


@dataclass(frozen=True, slots=True)
class PolicySet:
    schema_version: str
    dataset_version: str
    policies: tuple[Policy, ...]
    synthetic: bool = True
    test_only: bool = True
    allow_real_data: InitVar[bool] = dataclass_field(default=False, kw_only=True)

    def __post_init__(self, allow_real_data: bool) -> None:
        validate_schema_version(self.schema_version)
        require_text(self.dataset_version, "dataset_version", PolicyDataError)
        _validate_data_flags(self.synthetic, self.test_only, allow_real_data)
        if type(self.policies) is not tuple or not self.policies or any(type(p) is not Policy for p in self.policies):
            raise PolicyDataError("비어 있지 않은 Policy tuple이 필요합니다")
        if any(p.synthetic is not self.synthetic or p.test_only is not self.test_only for p in self.policies):
            raise PolicyDataError("데이터셋과 Policy의 synthetic/test_only가 일치해야 합니다")
        ids = [p.policy_id for p in self.policies]
        if len(ids) != len(set(ids)):
            raise PolicyDataError("중복 policy_id가 있습니다")
        nodes = tuple(n for p in self.policies for n in walk_nodes(p.root))
        rules = [n.rule_id for n in nodes]
        if len(rules) != len(set(rules)):
            raise PolicyDataError("데이터셋의 rule_id는 모두 유일해야 합니다")
        if self.schema_version == "m1.0" and any(type(node) is BirthDateRule for node in nodes):
            raise PolicyDataError("m1.0 데이터셋에는 BirthDateRule을 넣을 수 없습니다")
        if self.schema_version == "m1.0" and any(type(node) is ResidentRegistrationRule for node in nodes):
            raise PolicyDataError("m1.0 데이터셋에는 ResidentRegistrationRule을 넣을 수 없습니다")


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    as_of: date
    dataset_version: str
    engine_version: str = ENGINE_VERSION

    def __post_init__(self) -> None:
        if type(self.as_of) is not date:
            raise ContextValidationError("as_of: date 객체를 명시해야 합니다")
        require_text(self.dataset_version, "dataset_version", ContextValidationError)
        if self.engine_version != ENGINE_VERSION:
            raise ContextValidationError("실행 엔진과 engine_version이 다릅니다")


@dataclass(frozen=True, slots=True)
class ExpectedCondition:
    field: Field
    operator: Operator
    value: RuleValue
    fact_basis: FactBasis | None


@dataclass(frozen=True, slots=True)
class GroupCondition:
    operator: GroupOperator
    child_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_id: str
    status: Status
    reason_code: EvaluationReasonCode
    evaluated_value: Scalar | RegionSnapshot | date | None
    expected_condition: ExpectedCondition | GroupCondition | ResidentRegistrationCondition | BirthDateCondition
    missing_fields: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    details: EvaluationDetails | None = dataclass_field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.rule_id) is not str or not self.rule_id.strip():
            raise ResultValidationError("INVALID_RESULT_RULE_ID", "rule_id")
        if type(self.status) is not Status:
            raise ResultValidationError("INVALID_RESULT_STATUS", "status")
        _validate_result_reason(self.reason_code)
        birth_date_value = type(self.expected_condition) is BirthDateCondition and type(self.evaluated_value) is date
        if self.evaluated_value is not None and type(self.evaluated_value) not in (str, int, bool, RegionSnapshot) and not birth_date_value:
            raise ResultValidationError("INVALID_RESULT_VALUE", "evaluated_value")
        if type(self.expected_condition) not in (ExpectedCondition, GroupCondition, ResidentRegistrationCondition, BirthDateCondition):
            raise ResultValidationError("INVALID_RESULT_CONDITION", "expected_condition")
        if type(self.missing_fields) is not tuple or any(
                type(p) is not str or re.fullmatch(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*", p) is None
                for p in self.missing_fields):
            raise ResultValidationError("INVALID_MISSING_FIELDS", "missing_fields")
        if type(self.evidence_refs) is not tuple or any(type(p) is not str or not p.strip() for p in self.evidence_refs):
            raise ResultValidationError("INVALID_EVIDENCE_REFS", "evidence_refs")
        if self.details is not None and type(self.details) not in (ResidentRegistrationDetails, BirthDateDetails):
            raise ResultValidationError("INVALID_RESULT_DETAILS", "details")
        resident = type(self.expected_condition) is ResidentRegistrationCondition
        if type(self.expected_condition) is BirthDateCondition:
            if type(self.reason_code) is not BirthDateReasonCode:
                raise ResultValidationError("RESULT_REASON_CONDITION_MISMATCH", "reason_code")
            if type(self.details) is not BirthDateDetails:
                raise ResultValidationError("INVALID_RESULT_DETAILS", "details")
            expected_status = {
                BirthDateReasonCode.BIRTH_DATE_WITHIN_RANGE: Status.PASS,
                BirthDateReasonCode.BIRTH_DATE_BEFORE_RANGE: Status.FAIL,
                BirthDateReasonCode.BIRTH_DATE_AFTER_RANGE: Status.FAIL,
                BirthDateReasonCode.BIRTH_DATE_MISSING: Status.UNKNOWN,
            }[self.reason_code]
            if self.status is not expected_status:
                raise ResultValidationError("RESULT_REASON_STATUS_MISMATCH", "status")
            if self.status is Status.UNKNOWN:
                if self.evaluated_value is not None:
                    raise ResultValidationError("INVALID_RESULT_VALUE", "evaluated_value")
                if self.missing_fields != ("birth.birth_date",):
                    raise ResultValidationError("INVALID_MISSING_FIELDS", "missing_fields")
            else:
                if type(self.evaluated_value) is not date:
                    raise ResultValidationError("INVALID_RESULT_VALUE", "evaluated_value")
                if self.details.birth_source is None:
                    raise ResultValidationError("INVALID_BIRTH_SOURCE", "details.birth_source")
                if self.missing_fields:
                    raise ResultValidationError("INVALID_MISSING_FIELDS", "missing_fields")
            if not self.evidence_refs:
                raise ResultValidationError("INVALID_EVIDENCE_REFS", "evidence_refs")
            # 실제 날짜 비교와 before/within/after 선택은 후속 evaluator의 책임이다.
        elif resident:
            from .resolvers.resident_registration import ResidentRegistrationReasonCode

            if self.details is not None and type(self.details) is not ResidentRegistrationDetails:
                raise ResultValidationError("INVALID_RESULT_DETAILS", "details")
            if type(self.reason_code) is not ResidentRegistrationReasonCode:
                raise ResultValidationError("RESULT_REASON_CONDITION_MISMATCH", "reason_code")
            if self.evaluated_value is not None and type(self.evaluated_value) is not RegionSnapshot:
                raise ResultValidationError("INVALID_RESULT_VALUE", "evaluated_value")
            expected_status = {
                ResidentRegistrationReasonCode.RESIDENT_REGION_MATCH: Status.PASS,
                ResidentRegistrationReasonCode.RESIDENT_REGION_MISMATCH: Status.FAIL,
            }.get(self.reason_code, Status.UNKNOWN)
            if self.status is not expected_status:
                raise ResultValidationError("RESULT_REASON_STATUS_MISMATCH", "status")
            if self.status in (Status.PASS, Status.FAIL) and self.evaluated_value is None:
                raise ResultValidationError("INVALID_RESULT_VALUE", "evaluated_value")
            if self.details is not None:
                regions = {e.region for e in self.details.evidence if e.region is not None}
                if regions and regions != {self.evaluated_value}:
                    raise ResultValidationError("RESULT_EVIDENCE_VALUE_MISMATCH", "evaluated_value")
        elif self.details is not None or type(self.evaluated_value) in (RegionSnapshot, date) or type(self.reason_code) is not ReasonCode:
            raise ResultValidationError("RESULT_DETAIL_CONDITION_MISMATCH", "expected_condition")

    def to_dict(self) -> dict:
        return _jsonable(self)


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    policy_id: str
    overall_status: Status
    rule_results: tuple[RuleEvaluation, ...]
    missing_fields: tuple[str, ...]
    reason_codes: tuple[EvaluationReasonCode, ...]
    context: EvaluationContext
    rule_version: str

    def __post_init__(self) -> None:
        if type(self.reason_codes) is not tuple:
            raise ResultValidationError("INVALID_RESULT_REASON", "reason_codes")
        for reason in self.reason_codes:
            _validate_result_reason(reason)
        if type(self.rule_results) is not tuple or any(type(r) is not RuleEvaluation for r in self.rule_results):
            raise ResultValidationError("INVALID_RULE_RESULTS", "rule_results")

    @property
    def display_status(self) -> str:
        return {
            Status.PASS: "이용 가능성 높음",
            Status.FAIL: "현재 조건과 맞지 않음",
            Status.UNKNOWN: "추가 확인 필요",
        }[self.overall_status]

    def to_dict(self) -> dict:
        result = _jsonable(self)
        result["display_status"] = self.display_status
        return result


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is date:
        return value.isoformat()
    if is_dataclass(value):
        return {
            field.name: _jsonable(getattr(value, field.name)) for field in fields(value)
            if not (type(value) is RuleEvaluation and field.name == "details" and value.details is None)
        }
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    return value
