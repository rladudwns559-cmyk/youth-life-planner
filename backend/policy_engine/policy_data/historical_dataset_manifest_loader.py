"""선택 Entry의 동일 HM1 bytes에서 Manifest와 직접 binding만 복원한다."""

from datetime import datetime, timedelta
import hashlib
import json
import re

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact, AcceptanceReviewEntry
from .envelope import SourceBinding
from .manifest import (
    ArtifactReference, DatasetManifest, PolicyEditionReference, SourceRegistryReference,
)


_MANIFEST_KEYS = (
    "schema_version", "dataset_id", "dataset_version", "created_at", "freshness_max_age_days",
    "engine_version", "engine_artifact_sha256", "policy_versions", "source_registry",
    "source_versions", "review_manifest",
)
_POLICY_KEYS = (
    "policy_id", "edition_id", "rule_version", "artifact", "fingerprint", "schema_version",
    "rule_schema_version",
)
_REGISTRY_KEYS = ("artifact", "fingerprint", "schema_version")
_ARTIFACT_KEYS = ("path", "sha256")
_SOURCE_KEYS = ("source_document_id", "document_version")


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _selected_entry(artifact: AcceptanceReviewArtifact, record: PolicyBenefitAcceptance) -> AcceptanceReviewEntry:
    prefix = "HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH"
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
    if type(entry.dataset_manifest_ref) is not ArtifactReference:
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_EXPECTED_REF", "entry.dataset_manifest_ref")
    return entry


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_HISTORICAL_DATASET_MANIFEST_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, keys: tuple[str, ...], field: str) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", field)
    for key in keys:
        if key not in value:
            raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_FIELDS", field, "missing " + key)
    if value.keys() - set(keys):
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_FIELDS", field, "extra")
    return value


def _string(value: object, field: str) -> None:
    if type(value) is not str:
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", field)


def _literal(value: object, expected: str, field: str) -> None:
    _string(value, field)
    if value != expected:
        raise _error("UNSUPPORTED_HISTORICAL_DATASET_MANIFEST_SCHEMA", field)


def _reference_schema(value: object, keys: tuple[str, ...], field: str) -> None:
    obj = _object(value, keys, field)
    for key in keys:
        if key == "artifact":
            _reference_schema(obj[key], _ARTIFACT_KEYS, field + ".artifact")
        else:
            _string(obj[key], field + "." + key)


def _schema(value: object) -> dict:
    obj = _object(value, ("schema_version", "manifest"), "root")
    _literal(obj["schema_version"], "historical-dataset-manifest-1.0", "schema_version")
    manifest = _object(obj["manifest"], _MANIFEST_KEYS, "manifest")
    _literal(manifest["schema_version"], "dataset-manifest-1.0", "manifest.schema_version")
    for key in _MANIFEST_KEYS:
        field = "manifest." + key
        item = manifest[key]
        if key == "freshness_max_age_days":
            if type(item) is not int:
                raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", field)
        elif key in ("policy_versions", "source_versions"):
            if type(item) is not list:
                raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_TYPE", field)
            keys = _POLICY_KEYS if key == "policy_versions" else _SOURCE_KEYS
            for index, row in enumerate(item):
                _reference_schema(row, keys, f"{field}[{index}]")
        elif key == "source_registry":
            _reference_schema(item, _REGISTRY_KEYS, field)
        elif key == "review_manifest":
            if item is not None:
                _reference_schema(item, _ARTIFACT_KEYS, field)
        else:
            _string(item, field)
    return obj


def _timestamp(value: str) -> datetime:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{6})?\+00:00", value):
        try:
            result = datetime.fromisoformat(value)
            if result.utcoffset() == timedelta(0) and result.isoformat() == value:
                return result
        except (ValueError, OverflowError):
            pass
    raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_TIMESTAMP", "manifest.created_at")


def _construct(constructor, field: str, **kwargs):
    try:
        return constructor(**kwargs)
    except PolicyDataError as exc:
        child = getattr(exc, "field", None)
        reason = getattr(exc, "code", type(exc).__name__)
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_MODEL",
                     field + "." + child if child else field, reason) from None


def _load_manifest(obj: dict) -> DatasetManifest:
    created_at = _timestamp(obj["created_at"])
    policies = []
    for index, row in enumerate(obj["policy_versions"]):
        field = f"manifest.policy_versions[{index}]"
        artifact = _construct(ArtifactReference, field + ".artifact", **row["artifact"])
        values = {key: row[key] for key in _POLICY_KEYS if key != "artifact"}
        policies.append(_construct(PolicyEditionReference, field, artifact=artifact, **values))
    registry_raw = obj["source_registry"]
    registry_artifact = _construct(ArtifactReference, "manifest.source_registry.artifact", **registry_raw["artifact"])
    registry = _construct(SourceRegistryReference, "manifest.source_registry", artifact=registry_artifact,
                          fingerprint=registry_raw["fingerprint"], schema_version=registry_raw["schema_version"])
    sources = tuple(_construct(SourceBinding, f"manifest.source_versions[{index}]", **row)
                    for index, row in enumerate(obj["source_versions"]))
    review = obj["review_manifest"]
    if review is not None:
        review = _construct(ArtifactReference, "manifest.review_manifest", **review)
    values = {key: obj[key] for key in _MANIFEST_KEYS if key not in (
        "created_at", "policy_versions", "source_registry", "source_versions", "review_manifest",
    )}
    return _construct(DatasetManifest, "manifest", created_at=created_at, policy_versions=tuple(policies),
                      source_registry=registry, source_versions=sources, review_manifest=review, **values)


def _bind(manifest: DatasetManifest, record: PolicyBenefitAcceptance, entry: AcceptanceReviewEntry) -> None:
    for field in ("coverage_dataset_version", "benefit_dataset_version"):
        if manifest.dataset_version != getattr(record, field):
            raise _error("HISTORICAL_DATASET_MANIFEST_DATASET_MISMATCH", "manifest.dataset_version", field)
    policies = tuple(ref for ref in manifest.policy_versions if ref.policy_id == record.policy_id)
    if len(policies) != 1:
        raise _error("HISTORICAL_DATASET_MANIFEST_POLICY_MEMBERSHIP_MISMATCH", "manifest.policy_versions")
    selected = policies[0]
    if selected.edition_id != record.scope.edition_id:
        raise _error("HISTORICAL_DATASET_MANIFEST_EDITION_MISMATCH", "manifest.policy_versions.edition_id")
    if selected.rule_version != record.coverage_rule_version:
        raise _error("HISTORICAL_DATASET_MANIFEST_RULE_VERSION_MISMATCH", "manifest.policy_versions.rule_version")
    for field in ("coverage_source_registry_fingerprint", "benefit_source_registry_fingerprint"):
        if manifest.source_registry.fingerprint != getattr(record, field):
            raise _error("HISTORICAL_DATASET_MANIFEST_REGISTRY_FINGERPRINT_MISMATCH",
                         "manifest.source_registry.fingerprint", field)
    if selected.artifact != entry.policy_envelope_ref:
        raise _error("HISTORICAL_DATASET_MANIFEST_POLICY_REFERENCE_MISMATCH", "manifest.policy_versions.artifact")
    if manifest.source_registry.artifact != entry.source_registry_ref:
        raise _error("HISTORICAL_DATASET_MANIFEST_REGISTRY_REFERENCE_MISMATCH", "manifest.source_registry.artifact")


def load_historical_dataset_manifest_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> DatasetManifest:
    """P0~P9: HM1 복원·선택 선언만 검사한다. 전체 release/Registry/ZIP/사용 승인은 별도다."""
    for field, value, expected_type in (
        ("raw_bytes", raw_bytes, bytes), ("artifact", artifact, AcceptanceReviewArtifact),
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
    ):
        if type(value) is not expected_type:
            raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_LOADER_INPUT", field)
    entry = _selected_entry(artifact, expected_acceptance)
    if hashlib.sha256(raw_bytes).hexdigest() != entry.dataset_manifest_ref.sha256:
        raise _error("HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_HISTORICAL_DATASET_MANIFEST_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_HISTORICAL_DATASET_MANIFEST_BYTES", "raw_bytes")
    manifest = _load_manifest(payload["manifest"])
    _bind(manifest, expected_acceptance, entry)
    return manifest
