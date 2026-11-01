"""검토 Entry가 고정한 동일 bytes에서 Coverage 입력과 Inventory 대응만 복원한다."""

import hashlib
import json

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .condition_binding import ConditionBinding
from .condition_inventory import ConditionInventory
from .coverage import EligibilityCoverage
from .coverage_fingerprint import fingerprint_condition_inventory
from .eligibility_coverage import ApplicabilityScope
from .manifest import ArtifactReference
from .required_condition import ConditionRequirement, RequiredCondition


_COVERAGE_KEYS = ("inventory", "bindings")
_INVENTORY_KEYS = ("policy_id", "scope", "inventory_version", "conditions", "completeness_review_ref")
_CONDITION_KEYS = ("condition_id", "meaning", "requirement", "evidence_refs")
_BINDING_KEYS = ("condition_id", "rule_root_id", "implementation_review_ref")


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _expected_ref(artifact: AcceptanceReviewArtifact, record: PolicyBenefitAcceptance) -> ArtifactReference:
    prefix = "HISTORICAL_COVERAGE_REVIEW_BINDING_MISMATCH"
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
    if type(entry.coverage_snapshot_ref) is not ArtifactReference:
        raise _error("INVALID_HISTORICAL_COVERAGE_EXPECTED_REF", "entry.coverage_snapshot_ref")
    return entry.coverage_snapshot_ref


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_HISTORICAL_COVERAGE_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_HISTORICAL_COVERAGE_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_HISTORICAL_COVERAGE_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_HISTORICAL_COVERAGE_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, keys: tuple[str, ...], field: str) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_HISTORICAL_COVERAGE_TYPE", field)
    for key in keys:
        if key not in value:
            raise _error("INVALID_HISTORICAL_COVERAGE_FIELDS", field, "missing " + key)
    if value.keys() - set(keys):
        raise _error("INVALID_HISTORICAL_COVERAGE_FIELDS", field, "extra")
    return value


def _string(value: object, field: str) -> None:
    if type(value) is not str:
        raise _error("INVALID_HISTORICAL_COVERAGE_TYPE", field)


def _array(value: object, field: str) -> list:
    if type(value) is not list:
        raise _error("INVALID_HISTORICAL_COVERAGE_TYPE", field)
    return value


def _schema(value: object) -> dict:
    root = _object(value, ("schema_version", "coverage"), "root")
    _string(root["schema_version"], "schema_version")
    if root["schema_version"] != "historical-eligibility-coverage-1.0":
        raise _error("INVALID_HISTORICAL_COVERAGE_SCHEMA", "schema_version")
    coverage = _object(root["coverage"], _COVERAGE_KEYS, "coverage")
    inventory = _object(coverage["inventory"], _INVENTORY_KEYS, "coverage.inventory")
    _string(inventory["policy_id"], "coverage.inventory.policy_id")
    scope = _object(inventory["scope"], ("edition_id", "quarter"), "coverage.inventory.scope")
    _string(scope["edition_id"], "coverage.inventory.scope.edition_id")
    if scope["quarter"] is not None and type(scope["quarter"]) is not int:
        raise _error("INVALID_HISTORICAL_COVERAGE_TYPE", "coverage.inventory.scope.quarter")
    _string(inventory["inventory_version"], "coverage.inventory.inventory_version")
    for index, row in enumerate(_array(inventory["conditions"], "coverage.inventory.conditions")):
        path = f"coverage.inventory.conditions[{index}]"
        row = _object(row, _CONDITION_KEYS, path)
        for key in ("condition_id", "meaning", "requirement"):
            _string(row[key], path + "." + key)
        for ref_index, ref in enumerate(_array(row["evidence_refs"], path + ".evidence_refs")):
            _string(ref, f"{path}.evidence_refs[{ref_index}]")
    if inventory["completeness_review_ref"] is not None:
        _string(inventory["completeness_review_ref"], "coverage.inventory.completeness_review_ref")
    for index, binding in enumerate(_array(coverage["bindings"], "coverage.bindings")):
        path = f"coverage.bindings[{index}]"
        binding = _object(binding, _BINDING_KEYS, path)
        for key in _BINDING_KEYS:
            _string(binding[key], path + "." + key)
    return root


def _construct(constructor, field: str, **kwargs):
    try:
        return constructor(**kwargs)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_COVERAGE_MODEL", field) from None


def _load_coverage(obj: dict) -> EligibilityCoverage:
    inventory_raw = obj["inventory"]
    scope = _construct(ApplicabilityScope, "coverage.inventory.scope", **inventory_raw["scope"])
    conditions = []
    for index, row in enumerate(inventory_raw["conditions"]):
        path = f"coverage.inventory.conditions[{index}]"
        try:
            requirement = ConditionRequirement(row["requirement"])
        except ValueError:
            raise _error("INVALID_HISTORICAL_COVERAGE_VALUE", path + ".requirement") from None
        conditions.append(_construct(
            RequiredCondition, path, condition_id=row["condition_id"], meaning=row["meaning"],
            requirement=requirement, evidence_refs=tuple(row["evidence_refs"]),
        ))
    inventory = _construct(
        ConditionInventory, "coverage.inventory", policy_id=inventory_raw["policy_id"], scope=scope,
        inventory_version=inventory_raw["inventory_version"], conditions=tuple(conditions),
        completeness_review_ref=inventory_raw["completeness_review_ref"],
    )
    bindings = tuple(_construct(ConditionBinding, f"coverage.bindings[{index}]", **binding)
                     for index, binding in enumerate(obj["bindings"]))
    return _construct(EligibilityCoverage, "coverage", inventory=inventory, bindings=bindings)


def _bind(coverage: EligibilityCoverage, fingerprint: str, record: PolicyBenefitAcceptance) -> None:
    inventory = coverage.inventory
    for field in ("policy_id", "scope"):
        if getattr(inventory, field) != getattr(record, field):
            raise _error("HISTORICAL_COVERAGE_IDENTITY_MISMATCH", "coverage.inventory." + field)
    if inventory.inventory_version != record.coverage_inventory_version:
        raise _error("HISTORICAL_COVERAGE_INVENTORY_VERSION_MISMATCH", "coverage.inventory.inventory_version")
    if fingerprint != record.coverage_inventory_fingerprint:
        raise _error("HISTORICAL_COVERAGE_INVENTORY_FINGERPRINT_MISMATCH", "coverage.inventory")


def load_historical_eligibility_coverage_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> EligibilityCoverage:
    """P0~P9 입력 복원·Inventory 대응만 검사한다. FULL/Review/Tree/현재 사용을 판정하지 않는다."""
    for field, value, expected_type in (
        ("raw_bytes", raw_bytes, bytes), ("artifact", artifact, AcceptanceReviewArtifact),
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
    ):
        if type(value) is not expected_type:
            raise _error("INVALID_HISTORICAL_COVERAGE_LOADER_INPUT", field)
    ref = _expected_ref(artifact, expected_acceptance)
    if hashlib.sha256(raw_bytes).hexdigest() != ref.sha256:
        raise _error("HISTORICAL_COVERAGE_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_HISTORICAL_COVERAGE_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_HISTORICAL_COVERAGE_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_HISTORICAL_COVERAGE_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_HISTORICAL_COVERAGE_BYTES", "raw_bytes")
    coverage = _load_coverage(payload["coverage"])
    try:
        fingerprint = fingerprint_condition_inventory(coverage.inventory)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_COVERAGE_FINGERPRINT", "coverage.inventory") from None
    _bind(coverage, fingerprint, expected_acceptance)
    return coverage
