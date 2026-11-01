"""배포 선택 목록의 불변 값과 메모리 내용 지문. 파일·환경·시각을 조회하지 않는다."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from ..errors import PolicyDataError
from ..models import _jsonable
from ..sources import SourceRegistry
from .envelope import PolicyEnvelope, SourceBinding, _identifier, _version


class ManifestValidationError(PolicyDataError):
    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field} dataset 계약을 확인하세요")


def _text(value: object, field: str) -> None:
    if type(value) is not str or not value.strip():
        raise ManifestValidationError("INVALID_MANIFEST_TEXT", field)


def _hash(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ManifestValidationError("INVALID_MANIFEST_HASH", field)


def _digest(value: dict) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ManifestValidationError("INVALID_FINGERPRINT_CONTENT", "fingerprint") from exc
    return hashlib.sha256(encoded).hexdigest()


def fingerprint_policy_envelope(envelope: PolicyEnvelope) -> str:
    if type(envelope) is not PolicyEnvelope:
        raise ManifestValidationError("INVALID_MANIFEST_ENVELOPE", "envelope")
    value = envelope.to_dict()
    value["source_bindings"].sort(key=lambda item: item["source_document_id"])
    value["coverage"]["included_rule_ids"].sort()
    return _digest(value)


def fingerprint_source_registry(registry: SourceRegistry) -> str:
    if type(registry) is not SourceRegistry:
        raise ManifestValidationError("INVALID_MANIFEST_REGISTRY", "registry")
    value = registry.to_dict()
    value["sources"].sort(key=lambda item: item["source_document_id"])
    for source in value["sources"]:
        source["locators"].sort(key=lambda item: item["locator_id"])
        source["supersedes"].sort(key=lambda item: (item["source_document_id"], item["document_version"]))
        for evidence in source["locators"]:
            evidence["applicable_policy_ids"].sort()
    return _digest(value)


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        if (type(self.path) is not str or not self.path or self.path != self.path.strip()
                or "\\" in self.path or ":" in self.path
                or any(part in ("", ".", "..") for part in self.path.split("/"))
                or any(ord(char) < 32 or ord(char) == 127 for char in self.path)):
            raise ManifestValidationError("INVALID_ARTIFACT_PATH", "path")
        _hash(self.sha256, "sha256")


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyEditionReference:
    policy_id: str
    edition_id: str
    rule_version: str
    artifact: ArtifactReference
    fingerprint: str
    schema_version: str = "policy-data-1.0"
    rule_schema_version: str = "m1.1"

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "policy_id")
        _version(self.rule_version, "r", "rule_version")
        if type(self.edition_id) is not str or re.fullmatch(r"[0-9]{4}", self.edition_id) is None:
            raise ManifestValidationError("INVALID_MANIFEST_EDITION", "edition_id")
        if type(self.artifact) is not ArtifactReference:
            raise ManifestValidationError("INVALID_ARTIFACT_REFERENCE", "artifact")
        _hash(self.fingerprint, "fingerprint")
        if type(self.schema_version) is not str or self.schema_version != "policy-data-1.0":
            raise ManifestValidationError("UNSUPPORTED_POLICY_REFERENCE_SCHEMA", "schema_version")
        if type(self.rule_schema_version) is not str or self.rule_schema_version != "m1.1":
            raise ManifestValidationError("UNSUPPORTED_RULE_REFERENCE_SCHEMA", "rule_schema_version")


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceRegistryReference:
    artifact: ArtifactReference
    fingerprint: str
    schema_version: str = "source-registry-1.0"

    def __post_init__(self) -> None:
        if type(self.artifact) is not ArtifactReference:
            raise ManifestValidationError("INVALID_ARTIFACT_REFERENCE", "artifact")
        _hash(self.fingerprint, "fingerprint")
        if type(self.schema_version) is not str or self.schema_version != "source-registry-1.0":
            raise ManifestValidationError("UNSUPPORTED_REGISTRY_REFERENCE_SCHEMA", "schema_version")


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetManifest:
    schema_version: str
    dataset_id: str
    dataset_version: str
    created_at: datetime
    freshness_max_age_days: int
    engine_version: str
    engine_artifact_sha256: str
    policy_versions: tuple[PolicyEditionReference, ...]
    source_registry: SourceRegistryReference
    source_versions: tuple[SourceBinding, ...]
    review_manifest: ArtifactReference | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != "dataset-manifest-1.0":
            raise ManifestValidationError("UNSUPPORTED_MANIFEST_SCHEMA", "schema_version")
        for field in ("dataset_id", "dataset_version", "engine_version"):
            _text(getattr(self, field), field)
        if type(self.created_at) is not datetime or self.created_at.utcoffset() is None:
            raise ManifestValidationError("INVALID_MANIFEST_TIMESTAMP", "created_at")
        if type(self.freshness_max_age_days) is not int or self.freshness_max_age_days < 1:
            raise ManifestValidationError("INVALID_FRESHNESS_METADATA", "freshness_max_age_days")
        _hash(self.engine_artifact_sha256, "engine_artifact_sha256")
        if (type(self.policy_versions) is not tuple or not self.policy_versions
                or any(type(item) is not PolicyEditionReference for item in self.policy_versions)):
            raise ManifestValidationError("INVALID_POLICY_REFERENCES", "policy_versions")
        policy_ids = tuple(item.policy_id for item in self.policy_versions)
        if len(set(policy_ids)) != len(policy_ids):
            raise ManifestValidationError("DUPLICATE_MANIFEST_POLICY", "policy_versions")
        if type(self.source_registry) is not SourceRegistryReference:
            raise ManifestValidationError("INVALID_REGISTRY_REFERENCE", "source_registry")
        if (type(self.source_versions) is not tuple or not self.source_versions
                or any(type(item) is not SourceBinding for item in self.source_versions)):
            raise ManifestValidationError("INVALID_SOURCE_REFERENCES", "source_versions")
        source_ids = tuple(item.source_document_id for item in self.source_versions)
        if len(set(source_ids)) != len(source_ids):
            raise ManifestValidationError("DUPLICATE_MANIFEST_SOURCE", "source_versions")
        if self.review_manifest is not None and type(self.review_manifest) is not ArtifactReference:
            raise ManifestValidationError("INVALID_ARTIFACT_REFERENCE", "review_manifest")
        paths = [item.artifact.path for item in self.policy_versions] + [self.source_registry.artifact.path]
        if self.review_manifest is not None:
            paths.append(self.review_manifest.path)
        if len(paths) != len(set(paths)):
            raise ManifestValidationError("DUPLICATE_ARTIFACT_PATH", "path")

    def to_dict(self) -> dict:
        value = _jsonable(self)
        value["created_at"] = self.created_at.astimezone(timezone.utc).isoformat()
        return value

    def fingerprint(self) -> str:
        value = self.to_dict()
        value["policy_versions"].sort(key=lambda item: item["policy_id"])
        value["source_versions"].sort(key=lambda item: item["source_document_id"])
        return _digest(value)
