"""동일 raw bytes의 무결성·구조·외부 record 대응만 확인하는 순수 loader."""

from dataclasses import replace
from datetime import date
import hashlib
import json
import re

from ..errors import PolicyDataError
from .benefit_acceptance import BenefitAcceptanceStatus, PolicyBenefitAcceptance
from .benefit_acceptance_review_artifact import (
    AcceptanceReviewArtifact, AcceptanceReviewEntry, BenefitReviewClaim, ClaimEvidenceMapping,
    ReviewSourceOriginal,
)
from .eligibility_coverage import ApplicabilityScope
from .envelope import SourceBinding
from .manifest import ArtifactReference


_RAW_ACCEPTANCE_KEYS = (
    "acceptance_ref", "acceptance_version", "status", "policy_id", "scope", "benefit_id",
    "coverage_inventory_version", "coverage_inventory_fingerprint", "coverage_rule_version",
    "coverage_policy_tree_fingerprint", "coverage_dataset_version", "coverage_source_registry_fingerprint",
    "coverage_implementation_fingerprint", "benefit_version", "benefit_fingerprint",
    "benefit_dataset_version", "benefit_source_registry_fingerprint", "reviewed_at", "valid_until",
    "revokes_acceptance_ref",
)
_REFERENCE_KEYS = (
    "accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
    "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref",
)
_ENTRY_KEYS = (
    "acceptance", *_REFERENCE_KEYS, "claim_evidence", "source_bindings", "source_documents",
    "prepared_by", "reviewed_by", "review_note", "manual_scenario_ids",
)


def _error(prefix: str, field: str, reason: str = "계약을 확인하세요") -> PolicyDataError:
    return PolicyDataError(f"{prefix}: {field}: {reason}")


def _expected_ref(records: tuple[PolicyBenefitAcceptance, ...]) -> str:
    for index, record in enumerate(records):
        value = record.review_artifact_ref
        if type(value) is not str or re.fullmatch(r"acceptance-review:sha256:[0-9a-f]{64}", value) is None:
            raise _error("INVALID_REVIEW_ARTIFACT_EXPECTED_REF",
                         f"expected_acceptances[{index}].review_artifact_ref")
    common = records[0].review_artifact_ref
    if any(record.review_artifact_ref != common for record in records):
        raise _error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", "expected_acceptances", "refs differ")
    if len({record.acceptance_ref for record in records}) != len(records):
        raise _error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", "expected_acceptances", "duplicate ref")
    revisions = {(record.policy_id, record.scope, record.benefit_id, record.acceptance_version) for record in records}
    if len(revisions) != len(records):
        raise _error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", "expected_acceptances", "duplicate revision")
    return common


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _error("DUPLICATE_REVIEW_ARTIFACT_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_number(token: str) -> None:
    raise _error("INVALID_REVIEW_ARTIFACT_NUMBER", "json")


def _integer(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise _error("INVALID_REVIEW_ARTIFACT_NUMBER", "json") from None


def _unicode_scalars(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise _error("INVALID_REVIEW_ARTIFACT_UNICODE", "json")
        elif type(item) is dict:
            for key, child in item.items():
                pending.extend((key, child))
        elif type(item) is list:
            pending.extend(item)


def _object(value: object, keys: tuple[str, ...], field: str) -> dict:
    if type(value) is not dict:
        raise _error("INVALID_REVIEW_ARTIFACT_TYPE", field)
    for key in keys:
        if key not in value:
            raise _error("INVALID_REVIEW_ARTIFACT_FIELDS", field, "missing " + key)
    if value.keys() - set(keys):
        raise _error("INVALID_REVIEW_ARTIFACT_FIELDS", field, "extra")
    return value


def _string(value: object, field: str) -> None:
    if type(value) is not str:
        raise _error("INVALID_REVIEW_ARTIFACT_TYPE", field)


def _array(value: object, field: str) -> list:
    if type(value) is not list:
        raise _error("INVALID_REVIEW_ARTIFACT_TYPE", field)
    return value


def _check_reference(value: object, field: str) -> None:
    obj = _object(value, ("path", "sha256"), field)
    for key in ("path", "sha256"):
        _string(obj[key], field + "." + key)


def _check_binding(value: object, field: str) -> None:
    obj = _object(value, ("source_document_id", "document_version"), field)
    for key in ("source_document_id", "document_version"):
        _string(obj[key], field + "." + key)


def _check_acceptance(value: object, field: str) -> None:
    obj = _object(value, _RAW_ACCEPTANCE_KEYS, field)
    for key in _RAW_ACCEPTANCE_KEYS:
        path = field + "." + key
        if key == "scope":
            scope = _object(obj[key], ("edition_id", "quarter"), path)
            _string(scope["edition_id"], path + ".edition_id")
            if scope["quarter"] is not None and type(scope["quarter"]) is not int:
                raise _error("INVALID_REVIEW_ARTIFACT_TYPE", path + ".quarter")
        elif key != "revokes_acceptance_ref" or obj[key] is not None:
            _string(obj[key], path)


def _check_entry(value: object, field: str) -> None:
    obj = _object(value, _ENTRY_KEYS, field)
    _check_acceptance(obj["acceptance"], field + ".acceptance")
    for key in _REFERENCE_KEYS:
        if obj[key] is not None:
            _check_reference(obj[key], field + "." + key)
    for index, row in enumerate(_array(obj["claim_evidence"], field + ".claim_evidence")):
        path = f"{field}.claim_evidence[{index}]"
        row = _object(row, ("claim", "evidence_refs"), path)
        _string(row["claim"], path + ".claim")
        for ref_index, ref in enumerate(_array(row["evidence_refs"], path + ".evidence_refs")):
            _string(ref, f"{path}.evidence_refs[{ref_index}]")
    for index, binding in enumerate(_array(obj["source_bindings"], field + ".source_bindings")):
        _check_binding(binding, f"{field}.source_bindings[{index}]")
    for index, original in enumerate(_array(obj["source_documents"], field + ".source_documents")):
        path = f"{field}.source_documents[{index}]"
        original = _object(original, ("binding", "artifact"), path)
        _check_binding(original["binding"], path + ".binding")
        _check_reference(original["artifact"], path + ".artifact")
    for key in ("prepared_by", "reviewed_by", "review_note"):
        _string(obj[key], field + "." + key)
    for index, scenario in enumerate(_array(obj["manual_scenario_ids"], field + ".manual_scenario_ids")):
        _string(scenario, f"{field}.manual_scenario_ids[{index}]")


def _schema(value: object) -> dict:
    obj = _object(value, ("schema_version", "entries"), "root")
    _string(obj["schema_version"], "schema_version")
    if obj["schema_version"] != "benefit-acceptance-review-1.0":
        raise _error("INVALID_REVIEW_ARTIFACT_SCHEMA", "schema_version")
    for index, entry in enumerate(_array(obj["entries"], "entries")):
        _check_entry(entry, f"entries[{index}]")
    return obj


def _construct(constructor, field: str, *args, **kwargs):
    try:
        return constructor(*args, **kwargs)
    except PolicyDataError:
        raise _error("INVALID_REVIEW_ARTIFACT_MODEL", field) from None


def _enum(value: str, enum_type, field: str):
    try:
        return enum_type(value)
    except ValueError:
        raise _error("INVALID_REVIEW_ARTIFACT_VALUE", field) from None


def _date(value: str, field: str) -> date:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is not None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise _error("INVALID_REVIEW_ARTIFACT_VALUE", field)


def _load_acceptance(obj: dict, ref: str, field: str) -> PolicyBenefitAcceptance:
    status = _enum(obj["status"], BenefitAcceptanceStatus, field + ".status")
    scope = _construct(ApplicabilityScope, field + ".scope", **obj["scope"])
    reviewed_at = _date(obj["reviewed_at"], field + ".reviewed_at")
    valid_until = _date(obj["valid_until"], field + ".valid_until")
    values = {key: obj[key] for key in _RAW_ACCEPTANCE_KEYS}
    values.update(status=status, scope=scope, reviewed_at=reviewed_at, valid_until=valid_until,
                  review_artifact_ref=ref)
    return _construct(PolicyBenefitAcceptance, field, **values)


def _load_reference(obj: dict | None, field: str) -> ArtifactReference | None:
    return None if obj is None else _construct(ArtifactReference, field, **obj)


def _load_entry(obj: dict, ref: str, field: str) -> AcceptanceReviewEntry:
    acceptance = _load_acceptance(obj["acceptance"], ref, field + ".acceptance")
    references = {key: _load_reference(obj[key], field + "." + key) for key in _REFERENCE_KEYS}
    claims = []
    for index, row in enumerate(obj["claim_evidence"]):
        path = f"{field}.claim_evidence[{index}]"
        claim = _enum(row["claim"], BenefitReviewClaim, path + ".claim")
        claims.append(_construct(ClaimEvidenceMapping, path, claim=claim, evidence_refs=tuple(row["evidence_refs"])))
    bindings = tuple(_construct(SourceBinding, f"{field}.source_bindings[{index}]", **binding)
                     for index, binding in enumerate(obj["source_bindings"]))
    originals = []
    for index, original in enumerate(obj["source_documents"]):
        path = f"{field}.source_documents[{index}]"
        binding = _construct(SourceBinding, path + ".binding", **original["binding"])
        artifact = _load_reference(original["artifact"], path + ".artifact")
        originals.append(_construct(ReviewSourceOriginal, path, binding=binding, artifact=artifact))
    return _construct(
        AcceptanceReviewEntry, field, acceptance=acceptance, **references, claim_evidence=tuple(claims),
        source_bindings=bindings, source_documents=tuple(originals), prepared_by=obj["prepared_by"],
        reviewed_by=obj["reviewed_by"], review_note=obj["review_note"],
        manual_scenario_ids=tuple(obj["manual_scenario_ids"]),
    )


def _bind_originals(candidate: AcceptanceReviewArtifact,
                    expected: tuple[PolicyBenefitAcceptance, ...]) -> AcceptanceReviewArtifact:
    originals = {record.acceptance_ref: record for record in expected}
    present = set()
    prefix = "REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH"
    for index, entry in enumerate(candidate.entries):
        ref = entry.acceptance.acceptance_ref
        if ref not in originals:
            raise _error(prefix, f"entries[{index}].acceptance.acceptance_ref", "unlisted")
        present.add(ref)
    for record in expected:
        if record.acceptance_ref not in present:
            raise _error(prefix, "entries", "missing")
    for index, entry in enumerate(candidate.entries):
        original = originals[entry.acceptance.acceptance_ref]
        for key in _RAW_ACCEPTANCE_KEYS:
            if getattr(entry.acceptance, key) != getattr(original, key):
                raise _error(prefix, f"entries[{index}].acceptance.{key}")
    entries = tuple(_construct(replace, f"entries[{index}]", entry,
                               acceptance=originals[entry.acceptance.acceptance_ref])
                    for index, entry in enumerate(candidate.entries))
    return _construct(AcceptanceReviewArtifact, "root", review_artifact_ref=candidate.review_artifact_ref,
                      entries=entries)


def load_acceptance_review_artifact_bytes(
    *,
    raw_bytes: bytes,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
) -> AcceptanceReviewArtifact:
    """P0~P9 strict 복원. 파일/원문·현재 usability를 조회하거나 승인하지 않는다."""
    if type(raw_bytes) is not bytes:
        raise _error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", "raw_bytes")
    if type(expected_acceptances) is not tuple or not expected_acceptances:
        raise _error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", "expected_acceptances")
    if any(type(record) is not PolicyBenefitAcceptance for record in expected_acceptances):
        raise _error("INVALID_REVIEW_ARTIFACT_LOADER_INPUT", "expected_acceptances")
    ref = _expected_ref(expected_acceptances)
    if hashlib.sha256(raw_bytes).hexdigest() != ref.rsplit(":", 1)[1]:
        raise _error("REVIEW_ARTIFACT_BYTES_MISMATCH", "raw_bytes")
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise _error("INVALID_REVIEW_ARTIFACT_ENCODING", "raw_bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _error("INVALID_REVIEW_ARTIFACT_ENCODING", "raw_bytes") from None
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_invalid_number,
                          parse_float=_invalid_number, parse_int=_integer)
    except (json.JSONDecodeError, RecursionError):
        raise _error("INVALID_REVIEW_ARTIFACT_JSON", "json") from None
    _unicode_scalars(data)
    payload = _schema(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                           allow_nan=False).encode("utf-8", errors="strict")
    if raw_bytes != canonical:
        raise _error("NONCANONICAL_REVIEW_ARTIFACT_BYTES", "raw_bytes")
    entries = tuple(_load_entry(entry, ref, f"entries[{index}]") for index, entry in enumerate(payload["entries"]))
    candidate = _construct(AcceptanceReviewArtifact, "root", review_artifact_ref=ref, entries=entries)
    return _bind_originals(candidate, expected_acceptances)
