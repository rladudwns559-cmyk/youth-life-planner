"""선택 Entry의 동일 HSR1 bytes와 실제 Registry 지문만 검증한다. 사용 승인은 별도다."""

import hashlib
import json

from ..errors import PolicyDataError
from ..sources import SourceRegistry, parse_source_registry
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .manifest import ArtifactReference, fingerprint_source_registry


_DOCUMENT_REQUIRED = (
    "source_document_id", "document_version", "source_type", "issuer", "title", "official_url",
    "publication_date", "verified_at", "verification_status", "status", "locators",
)
_DOCUMENT_OPTIONAL = (
    "notice_number", "attachment_url", "previous_urls", "effective_from", "effective_to", "supersedes",
    "content_sha256",
)
_EVIDENCE_REQUIRED = (
    "locator_id", "section", "meaning_summary", "applicable_policy_ids", "verified_at",
    "verification_status", "status",
)
_EVIDENCE_OPTIONAL = ("page", "table_position")
_DOCUMENT_NULLABLE = (
    "publication_date", "verified_at", "notice_number", "attachment_url", "effective_from", "effective_to",
    "content_sha256",
)


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _expected_ref(artifact: AcceptanceReviewArtifact, record: PolicyBenefitAcceptance) -> ArtifactReference:
    prefix = "HISTORICAL_SOURCE_REGISTRY_REVIEW_BINDING_MISMATCH"
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
    if type(entry.source_registry_ref) is not ArtifactReference:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_EXPECTED_REF", "entry.source_registry_ref")
    return entry.source_registry_ref


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_HISTORICAL_SOURCE_REGISTRY_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, required: tuple[str, ...], optional: tuple[str, ...], field: str) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", field)
    for key in required:
        if key not in value:
            raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_FIELDS", field, "missing " + key)
    if value.keys() - set(required) - set(optional):
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_FIELDS", field, "extra")
    return value


def _string(value: object, field: str) -> None:
    if type(value) is not str:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", field)


def _array(value: object, field: str) -> list:
    if type(value) is not list:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", field)
    return value


def _string_array(value: object, field: str) -> None:
    for index, item in enumerate(_array(value, field)):
        _string(item, f"{field}[{index}]")


def _evidence_schema(value: object, field: str) -> None:
    obj = _object(value, _EVIDENCE_REQUIRED, _EVIDENCE_OPTIONAL, field)
    for key in _EVIDENCE_REQUIRED + _EVIDENCE_OPTIONAL:
        if key not in obj:
            continue
        path = field + "." + key
        item = obj[key]
        if key == "applicable_policy_ids":
            _string_array(item, path)
        elif key == "page":
            if item is not None and type(item) is not int:
                raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE", path)
        elif key in ("verified_at", "table_position") and item is None:
            continue
        else:
            _string(item, path)


def _document_schema(value: object, field: str) -> None:
    obj = _object(value, _DOCUMENT_REQUIRED, _DOCUMENT_OPTIONAL, field)
    for key in _DOCUMENT_REQUIRED + _DOCUMENT_OPTIONAL:
        if key not in obj:
            continue
        path = field + "." + key
        item = obj[key]
        if key == "locators":
            for index, row in enumerate(_array(item, path)):
                _evidence_schema(row, f"{path}[{index}]")
        elif key == "previous_urls":
            _string_array(item, path)
        elif key == "supersedes":
            for index, row in enumerate(_array(item, path)):
                row_path = f"{path}[{index}]"
                row = _object(row, ("source_document_id", "document_version"), (), row_path)
                for name in ("source_document_id", "document_version"):
                    _string(row[name], row_path + "." + name)
        elif key in _DOCUMENT_NULLABLE and item is None:
            continue
        else:
            _string(item, path)


def _schema(value: object) -> dict:
    obj = _object(value, ("schema_version", "sources"), (), "root")
    _string(obj["schema_version"], "schema_version")
    if obj["schema_version"] != "source-registry-1.0":
        raise _error("UNSUPPORTED_HISTORICAL_SOURCE_REGISTRY_SCHEMA", "schema_version")
    for index, row in enumerate(_array(obj["sources"], "sources")):
        _document_schema(row, f"sources[{index}]")
    return obj


def load_historical_source_registry_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> SourceRegistry:
    """P0~P9: raw integrity/복원/domain fp만 확인한다. Source Gate·전체 release는 실행하지 않는다."""
    for field, value, expected_type in (
        ("raw_bytes", raw_bytes, bytes), ("artifact", artifact, AcceptanceReviewArtifact),
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
    ):
        if type(value) is not expected_type:
            raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_LOADER_INPUT", field)
    ref = _expected_ref(artifact, expected_acceptance)
    if hashlib.sha256(raw_bytes).hexdigest() != ref.sha256:
        raise _error("HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_HISTORICAL_SOURCE_REGISTRY_BYTES", "raw_bytes")
    try:
        registry = parse_source_registry(payload)
    except PolicyDataError as exc:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL", getattr(exc, "field", "registry"),
                     getattr(exc, "code", type(exc).__name__)) from None
    try:
        fingerprint = fingerprint_source_registry(registry)
    except PolicyDataError as exc:
        raise _error("INVALID_HISTORICAL_SOURCE_REGISTRY_FINGERPRINT", getattr(exc, "field", "fingerprint"),
                     getattr(exc, "code", type(exc).__name__)) from None
    for field in ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"):
        if fingerprint != getattr(expected_acceptance, field):
            raise _error("HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH", "expected_acceptance." + field)
    return registry
