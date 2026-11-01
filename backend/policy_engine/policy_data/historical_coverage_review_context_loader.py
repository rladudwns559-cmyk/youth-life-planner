"""선택 Entry의 동일 bytes에서 과거 검토 기록과 Context baseline만 복원한다."""

from datetime import date
import hashlib
import json
import re

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .coverage_review import InventoryCompletenessReview
from .coverage_review_context import CoverageReviewContext
from .eligibility_coverage import ApplicabilityScope
from .implementation_review import ImplementationBindingReview
from .manifest import ArtifactReference


_CONTEXT_KEYS = (
    "policy_id", "scope", "dataset_version", "source_registry_fingerprint", "implementation_fingerprint",
    "inventory_reviews", "implementation_reviews",
)
_INVENTORY_KEYS = (
    "review_ref", "policy_id", "scope", "inventory_version", "inventory_fingerprint", "dataset_version",
    "source_registry_fingerprint", "reviewed_at", "review_artifact_ref",
)
_IMPLEMENTATION_KEYS = (
    "review_ref", "policy_id", "scope", "condition_id", "rule_root_id", "inventory_version",
    "inventory_fingerprint", "rule_version", "policy_tree_fingerprint", "subtree_fingerprint",
    "dataset_version", "source_registry_fingerprint", "implementation_fingerprint", "reviewed_at",
    "review_artifact_ref",
)


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _expected_ref(artifact: AcceptanceReviewArtifact, record: PolicyBenefitAcceptance) -> ArtifactReference:
    prefix = "HISTORICAL_COVERAGE_REVIEW_CONTEXT_REVIEW_BINDING_MISMATCH"
    if record.status is not BenefitAcceptanceStatus.ACCEPTED:
        raise _error(prefix, "expected_acceptance.status")
    if artifact.review_artifact_ref != record.review_artifact_ref:
        raise _error(prefix, "artifact.review_artifact_ref")
    entries = tuple(entry for entry in artifact.entries
                    if entry.acceptance.acceptance_ref == record.acceptance_ref)
    if len(entries) != 1:
        raise _error(prefix, "artifact.entries")
    entry = entries[0]
    if entry.acceptance is not record:
        raise _error(prefix, "entry.acceptance")
    if type(entry.coverage_reviews_ref) is not ArtifactReference:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_EXPECTED_REF", "entry.coverage_reviews_ref")
    return entry.coverage_reviews_ref


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, keys: tuple[str, ...], field: str) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE", field)
    for key in keys:
        if key not in value:
            raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", field, "missing " + key)
    if value.keys() - set(keys):
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS", field, "extra")
    return value


def _string(value: object, field: str) -> None:
    if type(value) is not str:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE", field)


def _scope_schema(value: object, field: str) -> None:
    obj = _object(value, ("edition_id", "quarter"), field)
    _string(obj["edition_id"], field + ".edition_id")
    if obj["quarter"] is not None and type(obj["quarter"]) is not int:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE", field + ".quarter")


def _review_schema(value: object, keys: tuple[str, ...], field: str) -> None:
    if type(value) is not list:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE", field)
    for index, row in enumerate(value):
        path = f"{field}[{index}]"
        row = _object(row, keys, path)
        for key in keys:
            if key == "scope":
                _scope_schema(row[key], path + ".scope")
            else:
                _string(row[key], path + "." + key)


def _schema(value: object) -> dict:
    obj = _object(value, ("schema_version", "review_context"), "root")
    _string(obj["schema_version"], "schema_version")
    if obj["schema_version"] != "historical-coverage-review-context-1.0":
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCHEMA", "schema_version")
    context = _object(obj["review_context"], _CONTEXT_KEYS, "review_context")
    for key in _CONTEXT_KEYS:
        path = "review_context." + key
        if key == "scope":
            _scope_schema(context[key], path)
        elif key == "inventory_reviews":
            _review_schema(context[key], _INVENTORY_KEYS, path)
        elif key == "implementation_reviews":
            _review_schema(context[key], _IMPLEMENTATION_KEYS, path)
        else:
            _string(context[key], path)
    return obj


def _construct(constructor, field: str, **kwargs):
    try:
        return constructor(**kwargs)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL", field) from None


def _review_date(value: str, field: str) -> date:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATE", field)


def _load_context(obj: dict) -> CoverageReviewContext:
    scope = _construct(ApplicabilityScope, "review_context.scope", **obj["scope"])
    collections = []
    for name, keys, constructor in (
        ("inventory_reviews", _INVENTORY_KEYS, InventoryCompletenessReview),
        ("implementation_reviews", _IMPLEMENTATION_KEYS, ImplementationBindingReview),
    ):
        records = []
        for index, row in enumerate(obj[name]):
            path = f"review_context.{name}[{index}]"
            record_scope = _construct(ApplicabilityScope, path + ".scope", **row["scope"])
            reviewed_at = _review_date(row["reviewed_at"], path + ".reviewed_at")
            values = {key: row[key] for key in keys if key not in ("scope", "reviewed_at")}
            records.append(_construct(constructor, path, scope=record_scope, reviewed_at=reviewed_at, **values))
        collections.append(tuple(records))
    return _construct(
        CoverageReviewContext, "review_context", policy_id=obj["policy_id"], scope=scope,
        dataset_version=obj["dataset_version"], source_registry_fingerprint=obj["source_registry_fingerprint"],
        implementation_fingerprint=obj["implementation_fingerprint"], inventory_reviews=collections[0],
        implementation_reviews=collections[1],
    )


def _bind(context: CoverageReviewContext, record: PolicyBenefitAcceptance) -> None:
    for field, expected_field, prefix in (
        ("policy_id", "policy_id", "HISTORICAL_COVERAGE_REVIEW_CONTEXT_IDENTITY_MISMATCH"),
        ("scope", "scope", "HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCOPE_MISMATCH"),
        ("dataset_version", "coverage_dataset_version", "HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATASET_MISMATCH"),
        ("source_registry_fingerprint", "coverage_source_registry_fingerprint",
         "HISTORICAL_COVERAGE_REVIEW_CONTEXT_REGISTRY_FINGERPRINT_MISMATCH"),
        ("implementation_fingerprint", "coverage_implementation_fingerprint",
         "HISTORICAL_COVERAGE_REVIEW_CONTEXT_IMPLEMENTATION_FINGERPRINT_MISMATCH"),
    ):
        if getattr(context, field) != getattr(record, expected_field):
            raise _error(prefix, "review_context." + field)


def load_historical_coverage_review_context_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> CoverageReviewContext:
    """P0~P8의 원본·Context baseline만 검사한다. Review/FULL/현재 사용을 판정하지 않는다."""
    for field, value, expected_type in (
        ("raw_bytes", raw_bytes, bytes), ("artifact", artifact, AcceptanceReviewArtifact),
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
    ):
        if type(value) is not expected_type:
            raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_INPUT", field)
    ref = _expected_ref(artifact, expected_acceptance)
    if hashlib.sha256(raw_bytes).hexdigest() != ref.sha256:
        raise _error("HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES", "raw_bytes")
    context = _load_context(payload["review_context"])
    _bind(context, expected_acceptance)
    return context
