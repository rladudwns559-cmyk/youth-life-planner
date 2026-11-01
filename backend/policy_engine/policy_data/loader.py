"""edition JSON 경계. 규칙은 기존 m1.1 parser, 근거는 별도 validator 책임이다."""

import json
from pathlib import Path

from ..facts import RegionRef, ResidentRegistrationValidationError
from ..loader import parse_policy_set
from ..sources import SourceValidationError
from ..sources.loader import _array, _date, _enum, _invalid_constant, _object, _unique_keys
from .envelope import (
    EnvelopeValidationError, EvaluationScope, PolicyCategory, PolicyCoverage,
    PolicyEnvelope, PolicyLifecycleStatus, PolicyVerificationStatus, SourceBinding,
)


def _metadata(data: object) -> tuple[dict, dict]:
    """기존 JSON 경계 helper를 재사용한다. Source 모델·parser를 호출하지 않는다."""
    try:
        obj = _object(data, {
            "schema_version", "rule_schema_version", "policy_id", "policy", "edition_id",
            "jurisdiction", "category", "dataset_version", "evaluation_scope", "coverage",
            "source_bindings", "verification_status", "last_verified_at", "lifecycle_status",
            "synthetic", "test_only",
        }, {"effective_from", "effective_to"}, "envelope")
        region = _object(obj["jurisdiction"], {"sido", "sigungu"}, set(), "jurisdiction")
        coverage = _object(obj["coverage"], {"included_rule_ids", "excluded_conditions"}, set(), "coverage")
        bindings = []
        for raw in _array(obj["source_bindings"], "source_bindings"):
            raw = _object(raw, {"source_document_id", "document_version"}, set(), "source_bindings")
            bindings.append(SourceBinding(raw["source_document_id"], raw["document_version"]))
        values = dict(
            schema_version=obj["schema_version"], rule_schema_version=obj["rule_schema_version"],
            edition_id=obj["edition_id"], jurisdiction=RegionRef(region["sido"], region["sigungu"]),
            category=_enum(obj["category"], PolicyCategory, "category"), dataset_version=obj["dataset_version"],
            evaluation_scope=_enum(obj["evaluation_scope"], EvaluationScope, "evaluation_scope"),
            coverage=PolicyCoverage(
                tuple(_array(coverage["included_rule_ids"], "coverage.included_rule_ids")),
                tuple(_array(coverage["excluded_conditions"], "coverage.excluded_conditions")),
            ),
            source_bindings=tuple(bindings),
            verification_status=_enum(obj["verification_status"], PolicyVerificationStatus, "verification_status"),
            last_verified_at=_date(obj["last_verified_at"], "last_verified_at"),
            lifecycle_status=_enum(obj["lifecycle_status"], PolicyLifecycleStatus, "lifecycle_status"),
            effective_from=_date(obj.get("effective_from"), "effective_from"),
            effective_to=_date(obj.get("effective_to"), "effective_to"),
        )
    except SourceValidationError as exc:
        # 공통 JSON helper 오류만 이 경계의 code로 변환한다.
        raise EnvelopeValidationError(exc.code.replace("SOURCE", "ENVELOPE"), exc.field) from exc
    except ResidentRegistrationValidationError as exc:
        raise EnvelopeValidationError("INVALID_JURISDICTION", "jurisdiction") from exc
    return obj, values


def parse_policy_envelope(data: object) -> PolicyEnvelope:
    """registry 없이 구조만 파싱한다. 근거 존재 확인은 기존 별도 API 책임이다."""
    if type(data) is not dict:
        raise EnvelopeValidationError("INVALID_ENVELOPE_OBJECT", "envelope")
    if type(data.get("schema_version")) is not str or data["schema_version"] != "policy-data-1.0":
        raise EnvelopeValidationError("UNSUPPORTED_ENVELOPE_SCHEMA", "schema_version")
    if type(data.get("rule_schema_version")) is not str or data["rule_schema_version"] != "m1.1":
        raise EnvelopeValidationError("UNSUPPORTED_RULE_SCHEMA", "rule_schema_version")
    obj, values = _metadata(data)
    if type(obj["policy_id"]) is not str:
        raise EnvelopeValidationError("INVALID_ENVELOPE_ID", "policy_id")
    if type(obj["synthetic"]) is not bool or type(obj["test_only"]) is not bool:
        raise EnvelopeValidationError("INVALID_ENVELOPE_FLAGS", "synthetic/test_only")
    inner = obj["policy"]
    if type(inner) is dict and all(type(inner.get(key)) is bool for key in ("synthetic", "test_only")):
        if any(obj[key] is not inner[key] for key in ("synthetic", "test_only")):
            raise EnvelopeValidationError("POLICY_FLAGS_MISMATCH", "synthetic/test_only")
    # 단일 Policy용 adapter. rule/atomic/group 파싱을 복제하지 않는다.
    payload = {
        "schema_version": obj["rule_schema_version"], "dataset_version": obj["dataset_version"],
        "synthetic": obj["synthetic"], "test_only": obj["test_only"], "policies": [obj["policy"]],
    }
    # 실제 flags를 그대로 전달한다. 합성 기본 경로의 허용 범위는 넓히지 않는다.
    if obj["synthetic"] is False and obj["test_only"] is False:
        parsed = parse_policy_set(payload, allow_real_data=True)
    else:
        parsed = parse_policy_set(payload)
    policy = parsed.policies[0]
    if obj["policy_id"] != policy.policy_id:
        raise EnvelopeValidationError("POLICY_ID_MISMATCH", "policy_id")
    if obj["synthetic"] is not policy.synthetic or obj["test_only"] is not policy.test_only:
        raise EnvelopeValidationError("POLICY_FLAGS_MISMATCH", "synthetic/test_only")
    return PolicyEnvelope(policy=policy, **values)


def load_policy_envelope(path: str | Path) -> PolicyEnvelope:
    """UTF-8 JSON 읽기 경계. 외부 URL이나 registry를 참조하지 않는다."""
    try:
        with Path(path).open(encoding="utf-8") as stream:
            data = json.load(stream, object_pairs_hook=_unique_keys, parse_constant=_invalid_constant)
    except SourceValidationError as exc:
        raise EnvelopeValidationError(exc.code.replace("SOURCE", "ENVELOPE"), exc.field) from exc
    except OSError as exc:
        raise EnvelopeValidationError("ENVELOPE_FILE_ERROR", "path") from exc
    except UnicodeError as exc:
        raise EnvelopeValidationError("INVALID_ENVELOPE_ENCODING", "file") from exc
    except (ValueError, RecursionError) as exc:
        raise EnvelopeValidationError("INVALID_ENVELOPE_JSON", "json") from exc
    return parse_policy_envelope(data)
