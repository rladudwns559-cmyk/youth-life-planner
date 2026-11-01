"""정책 JSON 로딩. 기본 경로는 합성 전용이며 전체 검증 성공 시에만 반환한다."""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .errors import EngineValidationError, PolicyDataError, ProfileValidationError
from .models import FactBasis, Field, GroupOperator, Operator, Policy, PolicyFact, PolicyRule, PolicySet, RuleGroup, RuleNode, UserProfile, validate_schema_version
from .facts import RegionRef
from .result_types import ReferenceDateSource
from .specialized_rules import BirthDateRule, ResidentRegistrationRule


def _object(data: Any, required: set[str], optional: set[str] | None = None) -> dict:
    if type(data) is not dict:
        raise EngineValidationError("JSON object가 필요합니다")
    if required - data.keys():
        raise EngineValidationError("필수 JSON 키가 누락됐습니다: " + ", ".join(sorted(required - data.keys())))
    if data.keys() - required - (optional or set()):
        raise EngineValidationError("정의되지 않은 JSON 키가 있습니다")
    return data


def _array(data: Any) -> list:
    if type(data) is not list:
        raise EngineValidationError("JSON array가 필요합니다")
    return data


def _basis(data: Any) -> FactBasis | None:
    if data is None:
        return None
    return FactBasis(**_object(data, {"basis", "subject", "period", "reference_year", "unit"}))


def _atomic(obj: dict) -> PolicyRule:
    """두 버전에서 동일한 원자 파싱/도메인 검증을 사용한다."""
    operator = Operator(obj["operator"])
    value = tuple(_array(obj["value"])) if operator is Operator.IN else obj["value"]
    return PolicyRule(
        rule_id=obj["rule_id"], field=Field(obj["field"]), operator=operator, value=value,
        fact_basis=_basis(obj.get("fact_basis")), evidence_refs=tuple(_array(obj["evidence_refs"])),
    )


def _required_birth_date(value: object, field: str) -> date:
    """정확한 ASCII 날짜 문자열만 변환한다. 범위 검증은 Rule 생성자 책임이다."""
    if type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise PolicyDataError(f"{field}: 정확한 YYYY-MM-DD 날짜 문자열이 필요합니다")


def _node(data: Any, schema_version: str) -> RuleNode:
    if type(data) is not dict:
        raise PolicyDataError("규칙은 JSON object여야 합니다")
    if data.get("kind") == "rule":
        atomic_keys = {"kind", "rule_id", "field", "operator", "value", "evidence_refs"}
        if schema_version == "m1.0":
            return _atomic(_object(data, atomic_keys, {"fact_basis"}))
        rule_type = data.get("rule_type")
        if type(rule_type) is not str:
            raise PolicyDataError("rule_type: m1.1 leaf에는 명시적인 문자열이 필요합니다")
        if rule_type == "atomic":
            return _atomic(_object(data, atomic_keys | {"rule_type"}, {"fact_basis"}))
        if rule_type == "resident_registration":
            obj = _object(data, {"kind", "rule_type", "rule_id", "required_region", "reference_date_source", "evidence_refs"})
            region = _object(obj["required_region"], {"sido", "sigungu"})
            return ResidentRegistrationRule(
                rule_id=obj["rule_id"], required_region=RegionRef(region["sido"], region["sigungu"]),
                reference_date_source=ReferenceDateSource(obj["reference_date_source"]),
                evidence_refs=tuple(_array(obj["evidence_refs"])),
            )
        if rule_type == "birth_date":
            obj = _object(data, {"kind", "rule_type", "rule_id", "min_birth_date", "max_birth_date", "evidence_refs"})
            return BirthDateRule(
                rule_id=obj["rule_id"],
                min_birth_date=_required_birth_date(obj["min_birth_date"], "min_birth_date"),
                max_birth_date=_required_birth_date(obj["max_birth_date"], "max_birth_date"),
                evidence_refs=tuple(_array(obj["evidence_refs"])),
            )
        raise PolicyDataError("지원하지 않는 m1.1 rule_type입니다")
    if data.get("kind") == "group":
        obj = _object(data, {"kind", "rule_id", "operator", "children"})
        return RuleGroup(obj["rule_id"], GroupOperator(obj["operator"]), tuple(_node(c, schema_version) for c in _array(obj["children"])))
    raise PolicyDataError("규칙 kind는 rule 또는 group이어야 합니다")


def parse_policy_set(data: Any, *, allow_real_data: bool = False) -> PolicySet:
    try:
        if type(data) is not dict:
            raise PolicyDataError("정책 데이터셋은 JSON object여야 합니다")
        if "schema_version" not in data:
            raise PolicyDataError("schema_version: 필수 버전이 누락됐습니다")
        schema_version = validate_schema_version(data["schema_version"])
        obj = _object(data, {"schema_version", "dataset_version", "synthetic", "test_only", "policies"})
        policies = []
        for item in _array(obj["policies"]):
            item = _object(item, {"policy_id", "policy_name", "rule_version", "synthetic", "test_only", "root"})
            policies.append(Policy(
                policy_id=item["policy_id"], policy_name=item["policy_name"], rule_version=item["rule_version"],
                root=_node(item["root"], schema_version), synthetic=item["synthetic"], test_only=item["test_only"],
                allow_real_data=allow_real_data,
            ))
        return PolicySet(obj["schema_version"], obj["dataset_version"], tuple(policies), obj["synthetic"], obj["test_only"],
                         allow_real_data=allow_real_data)
    except (ValueError, TypeError, RecursionError) as exc:
        # 입력값 전체를 예외 메시지에 복사하지 않는다.
        if isinstance(exc, PolicyDataError):
            raise
        raise PolicyDataError("정책 데이터의 구조·필드·연산자·타입을 확인하세요") from exc


def parse_profile(data: Any) -> UserProfile:
    try:
        obj = _object(data, set(), {"age", "region", "student_status", "employment_status", "monthly_income", "policy_facts"})
        facts = []
        for fact in _array(obj.get("policy_facts", [])):
            fact = _object(fact, {"field", "value"}, {"fact_basis"})
            facts.append(PolicyFact(Field(fact["field"]), fact["value"], _basis(fact.get("fact_basis"))))
        values = {key: value for key, value in obj.items() if key != "policy_facts"}
        return UserProfile(**values, policy_facts=tuple(facts))
    except (ValueError, TypeError) as exc:
        if isinstance(exc, ProfileValidationError):
            raise
        raise ProfileValidationError("프로필의 구조·필드·타입을 확인하세요") from exc


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise EngineValidationError("중복 JSON 키가 있습니다")
        result[key] = value
    return result


def _read(path: str | Path, error: type[EngineValidationError]) -> Any:
    try:
        with Path(path).open(encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=_unique_keys)
    except (OSError, ValueError, RecursionError) as exc:
        raise error("JSON 파일을 읽을 수 없거나 형식이 잘못됐습니다") from exc


def load_policy_set(path: str | Path) -> PolicySet:
    return parse_policy_set(_read(path, PolicyDataError))


def load_profile(path: str | Path) -> UserProfile:
    return parse_profile(_read(path, ProfileValidationError))
