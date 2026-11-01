"""선택한 검토 Entry의 동일 bytes에서 과거 Envelope와 전체 Rule Tree를 복원한다."""

import hashlib
import json

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import AcceptanceReviewArtifact
from .coverage_fingerprint import fingerprint_policy_tree
from .envelope import PolicyEnvelope
from .loader import parse_policy_envelope
from .manifest import ArtifactReference


_ROOT_KEYS = (
    "schema_version", "rule_schema_version", "policy_id", "policy", "edition_id", "jurisdiction",
    "category", "dataset_version", "evaluation_scope", "coverage", "source_bindings",
    "verification_status", "last_verified_at", "lifecycle_status", "synthetic", "test_only",
)
_POLICY_KEYS = ("policy_id", "policy_name", "rule_version", "synthetic", "test_only", "root")
_GROUP_KEYS = ("kind", "rule_id", "operator", "children")
_ATOMIC_KEYS = ("kind", "rule_type", "rule_id", "field", "operator", "value", "evidence_refs")
_RESIDENT_KEYS = ("kind", "rule_type", "rule_id", "required_region", "reference_date_source", "evidence_refs")
_BIRTH_KEYS = ("kind", "rule_type", "rule_id", "min_birth_date", "max_birth_date", "evidence_refs")
_BASIS_KEYS = ("basis", "subject", "period", "reference_year", "unit")


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _expected_ref(artifact: AcceptanceReviewArtifact, record: PolicyBenefitAcceptance) -> ArtifactReference:
    prefix = "HISTORICAL_POLICY_ENVELOPE_REVIEW_BINDING_MISMATCH"
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
    if type(entry.policy_envelope_ref) is not ArtifactReference:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_EXPECTED_REF", "entry.policy_envelope_ref")
    return entry.policy_envelope_ref


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_HISTORICAL_POLICY_ENVELOPE_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, keys: tuple[str, ...], field: str, optional: tuple[str, ...] = ()) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", field)
    for key in keys:
        if key not in value:
            raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", field, "missing " + key)
    if value.keys() - set(keys) - set(optional):
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", field, "extra")
    return value


def _type(value: object, expected: type, field: str) -> None:
    if type(value) is not expected:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", field)


def _array(value: object, field: str) -> list:
    _type(value, list, field)
    return value


def _strings(value: object, field: str) -> None:
    for index, item in enumerate(_array(value, field)):
        _type(item, str, f"{field}[{index}]")


def _region(value: object, field: str) -> None:
    obj = _object(value, ("sido", "sigungu"), field)
    for key in ("sido", "sigungu"):
        _type(obj[key], str, field + "." + key)


def _tree_schema(value: object, field: str) -> None:
    """raw shape만 왼쪽부터 검사한다. 모델 생성·Enum/연산 의미 검사는 기존 parser 책임이다."""
    pending = [(value, field)]
    while pending:
        node, path = pending.pop()
        _type(node, dict, path)
        if "kind" not in node:
            raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", path, "missing kind")
        _type(node["kind"], str, path + ".kind")
        kind = node["kind"]
        if kind not in ("group", "rule"):
            raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_NODE", path + ".kind")
        rule_type = None
        if kind == "rule":
            if "rule_type" not in node:
                raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS", path, "missing rule_type")
            _type(node["rule_type"], str, path + ".rule_type")
            rule_type = node["rule_type"]
            if rule_type not in ("atomic", "resident_registration", "birth_date"):
                raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_NODE", path + ".rule_type")
        if kind == "group":
            _object(node, _GROUP_KEYS, path)
        elif rule_type == "atomic":
            _object(node, _ATOMIC_KEYS, path, ("fact_basis",))
        elif rule_type == "resident_registration":
            _object(node, _RESIDENT_KEYS, path)
        else:
            _object(node, _BIRTH_KEYS, path)
        _type(node["rule_id"], str, path + ".rule_id")
        if kind == "group":
            _type(node["operator"], str, path + ".operator")
            children = _array(node["children"], path + ".children")
            pending.extend((child, f"{path}.children[{index}]")
                           for index, child in reversed(tuple(enumerate(children))))
            continue
        if rule_type == "atomic":
            for key in ("field", "operator"):
                _type(node[key], str, path + "." + key)
            value = node["value"]
            if type(value) is list:
                for index, item in enumerate(value):
                    if type(item) not in (str, int, bool):
                        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", f"{path}.value[{index}]")
            elif type(value) not in (str, int, bool):
                raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE", path + ".value")
        elif rule_type == "resident_registration":
            _region(node["required_region"], path + ".required_region")
            _type(node["reference_date_source"], str, path + ".reference_date_source")
        else:
            for key in ("min_birth_date", "max_birth_date"):
                _type(node[key], str, path + "." + key)
        _strings(node["evidence_refs"], path + ".evidence_refs")
        if rule_type == "atomic" and node.get("fact_basis") is not None:
            basis_path = path + ".fact_basis"
            basis = _object(node["fact_basis"], _BASIS_KEYS, basis_path)
            for key in _BASIS_KEYS:
                _type(basis[key], int if key == "reference_year" else str, basis_path + "." + key)


def _schema(value: object) -> dict:
    obj = _object(value, _ROOT_KEYS, "root", ("effective_from", "effective_to"))
    for key, literal in (("schema_version", "policy-data-1.0"), ("rule_schema_version", "m1.1")):
        _type(obj[key], str, key)
        if obj[key] != literal:
            raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_SCHEMA", key)
    _type(obj["policy_id"], str, "policy_id")
    policy = _object(obj["policy"], _POLICY_KEYS, "policy")
    for key in ("policy_id", "policy_name", "rule_version"):
        _type(policy[key], str, "policy." + key)
    for key in ("synthetic", "test_only"):
        _type(policy[key], bool, "policy." + key)
    _tree_schema(policy["root"], "policy.root")
    _type(obj["edition_id"], str, "edition_id")
    _region(obj["jurisdiction"], "jurisdiction")
    for key in ("category", "dataset_version", "evaluation_scope"):
        _type(obj[key], str, key)
    coverage = _object(obj["coverage"], ("included_rule_ids", "excluded_conditions"), "coverage")
    for key in ("included_rule_ids", "excluded_conditions"):
        _strings(coverage[key], "coverage." + key)
    for index, binding in enumerate(_array(obj["source_bindings"], "source_bindings")):
        path = f"source_bindings[{index}]"
        binding = _object(binding, ("source_document_id", "document_version"), path)
        for key in ("source_document_id", "document_version"):
            _type(binding[key], str, path + "." + key)
    _type(obj["verification_status"], str, "verification_status")
    if obj["last_verified_at"] is not None:
        _type(obj["last_verified_at"], str, "last_verified_at")
    _type(obj["lifecycle_status"], str, "lifecycle_status")
    for key in ("synthetic", "test_only"):
        _type(obj[key], bool, key)
    for key in ("effective_from", "effective_to"):
        if key in obj and obj[key] is not None:
            _type(obj[key], str, key)
    return obj


def _bind(envelope: PolicyEnvelope, fingerprint: str, record: PolicyBenefitAcceptance) -> None:
    for actual, expected, prefix, field in (
        (envelope.policy_id, record.policy_id, "HISTORICAL_POLICY_ENVELOPE_IDENTITY_MISMATCH", "policy_id"),
        (envelope.edition_id, record.scope.edition_id, "HISTORICAL_POLICY_ENVELOPE_EDITION_MISMATCH", "edition_id"),
        (envelope.rule_version, record.coverage_rule_version,
         "HISTORICAL_POLICY_ENVELOPE_RULE_VERSION_MISMATCH", "policy.rule_version"),
        (fingerprint, record.coverage_policy_tree_fingerprint,
         "HISTORICAL_POLICY_ENVELOPE_TREE_FINGERPRINT_MISMATCH", "policy"),
        (envelope.dataset_version, record.coverage_dataset_version,
         "HISTORICAL_POLICY_ENVELOPE_DATASET_MISMATCH", "dataset_version"),
    ):
        if actual != expected:
            raise _error(prefix, field)


def load_historical_policy_envelope_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> PolicyEnvelope:
    """P0~P9의 원본·Tree binding만 검사한다. FULL/quarter/검토·현재 사용을 판정하지 않는다."""
    for field, value, expected_type in (
        ("raw_bytes", raw_bytes, bytes), ("artifact", artifact, AcceptanceReviewArtifact),
        ("expected_acceptance", expected_acceptance, PolicyBenefitAcceptance),
    ):
        if type(value) is not expected_type:
            raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_LOADER_INPUT", field)
    ref = _expected_ref(artifact, expected_acceptance)
    if hashlib.sha256(raw_bytes).hexdigest() != ref.sha256:
        raise _error("HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_HISTORICAL_POLICY_ENVELOPE_BYTES", "raw_bytes")
    try:
        envelope = parse_policy_envelope(payload)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL", "root") from None
    try:
        fingerprint = fingerprint_policy_tree(envelope.policy)
    except PolicyDataError:
        raise _error("INVALID_HISTORICAL_POLICY_ENVELOPE_FINGERPRINT", "policy") from None
    _bind(envelope, fingerprint, expected_acceptance)
    return envelope
