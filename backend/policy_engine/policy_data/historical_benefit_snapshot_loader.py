"""검토 Entry가 고정한 동일 bytes에서 과거 혜택을 복원·대조하는 순수 loader."""

import hashlib
import json

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .benefit_fingerprint import fingerprint_benefit_snapshot
from .benefit_snapshot import (
    BenefitAmountType, BenefitMedium, BenefitPaymentCadence, BenefitRestriction, BenefitSnapshot,
)
from .eligibility_coverage import ApplicabilityScope
from .envelope import SourceBinding
from .manifest import ArtifactReference


_SNAPSHOT_KEYS = (
    "policy_id", "scope", "benefit_id", "benefit_version", "amount_type", "amount_krw",
    "amount_description", "payment_cadence", "benefit_medium", "restriction", "restriction_details",
    "applicable_months", "benefit_evidence_refs", "source_bindings", "dataset_version",
    "source_registry_fingerprint",
)


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _expected_ref(artifact: AcceptanceReviewArtifact, record: PolicyBenefitAcceptance) -> ArtifactReference:
    prefix = "HISTORICAL_BENEFIT_REVIEW_BINDING_MISMATCH"
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
    if type(entry.accepted_terms_ref) is not ArtifactReference:
        raise _error("INVALID_HISTORICAL_BENEFIT_EXPECTED_REF", "entry.accepted_terms_ref")
    return entry.accepted_terms_ref


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_HISTORICAL_BENEFIT_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_HISTORICAL_BENEFIT_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_HISTORICAL_BENEFIT_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_HISTORICAL_BENEFIT_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, keys: tuple[str, ...], field: str) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_HISTORICAL_BENEFIT_TYPE", field)
    for key in keys:
        if key not in value:
            raise _error("INVALID_HISTORICAL_BENEFIT_FIELDS", field, "missing " + key)
    if value.keys() - set(keys):
        raise _error("INVALID_HISTORICAL_BENEFIT_FIELDS", field, "extra")
    return value


def _string(value: object, field: str) -> None:
    if type(value) is not str:
        raise _error("INVALID_HISTORICAL_BENEFIT_TYPE", field)


def _array(value: object, field: str) -> list:
    if type(value) is not list:
        raise _error("INVALID_HISTORICAL_BENEFIT_TYPE", field)
    return value


def _schema(value: object) -> dict:
    root = _object(value, ("schema_version", "snapshot"), "root")
    _string(root["schema_version"], "schema_version")
    if root["schema_version"] != "historical-benefit-snapshot-1.0":
        raise _error("INVALID_HISTORICAL_BENEFIT_SCHEMA", "schema_version")
    obj = _object(root["snapshot"], _SNAPSHOT_KEYS, "snapshot")
    for key in _SNAPSHOT_KEYS:
        field = "snapshot." + key
        item = obj[key]
        if key == "scope":
            scope = _object(item, ("edition_id", "quarter"), field)
            _string(scope["edition_id"], field + ".edition_id")
            if scope["quarter"] is not None and type(scope["quarter"]) is not int:
                raise _error("INVALID_HISTORICAL_BENEFIT_TYPE", field + ".quarter")
        elif key == "amount_krw":
            if item is not None and type(item) is not int:
                raise _error("INVALID_HISTORICAL_BENEFIT_TYPE", field)
        elif key in ("amount_description", "restriction_details"):
            if item is not None:
                _string(item, field)
        elif key in ("applicable_months", "benefit_evidence_refs"):
            if key != "applicable_months" or item is not None:
                for index, text in enumerate(_array(item, field)):
                    _string(text, f"{field}[{index}]")
        elif key == "source_bindings":
            for index, binding in enumerate(_array(item, field)):
                path = f"{field}[{index}]"
                binding = _object(binding, ("source_document_id", "document_version"), path)
                for name in ("source_document_id", "document_version"):
                    _string(binding[name], path + "." + name)
        else:
            _string(item, field)
    return root


def _construct(constructor, field: str, **kwargs):
    try:
        return constructor(**kwargs)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_BENEFIT_MODEL", field) from None


def _enum(value: str, enum_type, field: str):
    try:
        return enum_type(value)
    except ValueError:
        raise _error("INVALID_HISTORICAL_BENEFIT_VALUE", field) from None


def _load_snapshot(obj: dict) -> BenefitSnapshot:
    scope = _construct(ApplicabilityScope, "snapshot.scope", **obj["scope"])
    amount_type = _enum(obj["amount_type"], BenefitAmountType, "snapshot.amount_type")
    cadence = _enum(obj["payment_cadence"], BenefitPaymentCadence, "snapshot.payment_cadence")
    medium = _enum(obj["benefit_medium"], BenefitMedium, "snapshot.benefit_medium")
    restriction = _enum(obj["restriction"], BenefitRestriction, "snapshot.restriction")
    bindings = tuple(_construct(SourceBinding, f"snapshot.source_bindings[{index}]", **binding)
                     for index, binding in enumerate(obj["source_bindings"]))
    values = {key: obj[key] for key in _SNAPSHOT_KEYS}
    values.update(
        scope=scope, amount_type=amount_type, payment_cadence=cadence, benefit_medium=medium,
        restriction=restriction, source_bindings=bindings,
        applicable_months=None if obj["applicable_months"] is None else tuple(obj["applicable_months"]),
        benefit_evidence_refs=tuple(obj["benefit_evidence_refs"]),
    )
    return _construct(BenefitSnapshot, "snapshot", **values)


def _bind(snapshot: BenefitSnapshot, fingerprint: str, record: PolicyBenefitAcceptance) -> None:
    for field in ("policy_id", "scope", "benefit_id", "benefit_version"):
        if getattr(snapshot, field) != getattr(record, field):
            raise _error("HISTORICAL_BENEFIT_IDENTITY_MISMATCH", "snapshot." + field)
    if fingerprint != record.benefit_fingerprint:
        raise _error("HISTORICAL_BENEFIT_FINGERPRINT_MISMATCH", "snapshot")
    if snapshot.dataset_version != record.benefit_dataset_version:
        raise _error("HISTORICAL_BENEFIT_DATASET_MISMATCH", "snapshot.dataset_version")
    if snapshot.source_registry_fingerprint != record.benefit_source_registry_fingerprint:
        raise _error("HISTORICAL_BENEFIT_REGISTRY_MISMATCH", "snapshot.source_registry_fingerprint")


def load_historical_benefit_snapshot_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> BenefitSnapshot:
    """P0~P8: 원본 bytes 대응만 확인한다. 실제 검토·현재 사용·지급을 승인하지 않는다."""
    for field, value, expected_type in (
        ("raw_bytes", raw_bytes, bytes), ("artifact", artifact, AcceptanceReviewArtifact),
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
    ):
        if type(value) is not expected_type:
            raise _error("INVALID_HISTORICAL_BENEFIT_LOADER_INPUT", field)
    ref = _expected_ref(artifact, expected_acceptance)
    if hashlib.sha256(raw_bytes).hexdigest() != ref.sha256:
        raise _error("HISTORICAL_BENEFIT_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_HISTORICAL_BENEFIT_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_HISTORICAL_BENEFIT_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_HISTORICAL_BENEFIT_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_HISTORICAL_BENEFIT_BYTES", "raw_bytes")
    snapshot = _load_snapshot(payload["snapshot"])
    try:
        fingerprint = fingerprint_benefit_snapshot(snapshot)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_BENEFIT_FINGERPRINT", "snapshot") from None
    _bind(snapshot, fingerprint, expected_acceptance)
    return snapshot
