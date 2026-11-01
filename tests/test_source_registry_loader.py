"""합성/test_only Source Registry JSON 경계와 기존 도메인 계약을 검증한다."""

from copy import deepcopy
from datetime import date, datetime
from enum import Enum
import json
from pathlib import Path

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.facts import RegistrationSource
from backend.policy_engine.sources import (
    SourceDocument, SourceEvidence, SourceRegistry, SourceStatus, SourceType,
    SourceValidationError, VerificationStatus, load_source_registry,
    parse_source_registry, validate_evidence_refs,
)


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "sources.json"
REF = "SYNTH-SOURCE-001#eligibility-residence"


def raw():
    # 기존 source serializer에 기대지 않는 최소 JSON 입력.
    return {
        "schema_version": "source-registry-1.0",
        "sources": [{
            "source_document_id": "SYNTH-SOURCE-001", "document_version": "d0001",
            "source_type": "OFFICIAL_NOTICE", "issuer": "SYNTHETIC_AUTHORITY_TEST_ONLY",
            "title": "Synthetic test_only notice", "official_url": "https://policy.example.invalid/1",
            "publication_date": "2024-02-29", "verified_at": "2026-01-10",
            "verification_status": "VERIFIED", "status": "ACTIVE",
            "locators": [{
                "locator_id": "eligibility-residence", "section": "합성 지역 조건",
                "meaning_summary": "합성 test_only 조건 위치", "applicable_policy_ids": ["SYNTH-POLICY-001"],
                "verified_at": "2026-01-10", "verification_status": "VERIFIED", "status": "ACTIVE",
            }],
        }],
    }


def expected():
    item = SourceEvidence(
        locator_id="eligibility-residence", section="합성 지역 조건", meaning_summary="합성 test_only 조건 위치",
        applicable_policy_ids=("SYNTH-POLICY-001",), verified_at=date(2026, 1, 10),
        verification_status=VerificationStatus.VERIFIED, status=SourceStatus.ACTIVE,
    )
    return SourceRegistry((SourceDocument(
        source_document_id="SYNTH-SOURCE-001", document_version="d0001", source_type=SourceType.OFFICIAL_NOTICE,
        issuer="SYNTHETIC_AUTHORITY_TEST_ONLY", title="Synthetic test_only notice",
        official_url="https://policy.example.invalid/1", publication_date=date(2024, 2, 29),
        verified_at=date(2026, 1, 10), verification_status=VerificationStatus.VERIFIED,
        status=SourceStatus.ACTIVE, locators=(item,),
    ),))


def save(tmp_path, text):
    path = tmp_path / "sources.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_minimal_json_reproduces_independent_hand_built_domain():
    assert parse_source_registry(raw()) == expected()
    loaded = parse_source_registry(raw())
    assert type(loaded) is SourceRegistry
    assert type(loaded.sources[0]) is SourceDocument
    assert type(loaded.resolve(REF)) is SourceEvidence
    assert loaded.get_source("SYNTH-SOURCE-001").publication_date == date(2024, 2, 29)
    assert loaded.get_source("SYNTH-SOURCE-001").source_type is SourceType.OFFICIAL_NOTICE


def test_fixture_contains_multiple_sources_locators_and_test_only_metadata():
    loaded = load_source_registry(FIXTURE)
    assert [doc.source_document_id for doc in loaded.sources] == ["SYNTH-SOURCE-001", "SYNTH-SOURCE-002"]
    assert [item.locator_id for item in loaded.sources[0].locators] == ["eligibility-residence", "application-period"]
    assert loaded.resolve(REF).section == "합성 조건 / 지역"
    assert loaded.resolve("SYNTH-SOURCE-002#eligibility-residence").verification_status is VerificationStatus.DRAFT
    for doc in loaded.sources:
        assert doc.issuer == "SYNTHETIC_AUTHORITY_TEST_ONLY"
        assert "Synthetic test_only" in doc.title
        assert ".example.invalid/" in doc.official_url
    refs = (REF, "SYNTH-SOURCE-001#application-period", "SYNTH-SOURCE-002#eligibility-residence")
    assert len(validate_evidence_refs(refs, loaded)) == 3


def test_load_parse_round_trip_order_and_input_snapshot(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["sources"].reverse()
    data["sources"][1]["locators"].reverse()
    before = deepcopy(data)
    loaded = parse_source_registry(data)
    assert data == before
    assert loaded == load_source_registry(save(tmp_path, json.dumps(data, ensure_ascii=False)))
    assert loaded == parse_source_registry(loaded.to_dict())
    assert loaded == parse_source_registry(data)
    assert loaded.sources[0].source_document_id == "SYNTH-SOURCE-002"
    assert loaded.sources[1].locators[0].locator_id == "application-period"
    data["sources"][1]["locators"].clear()
    data["sources"].clear()
    assert loaded.resolve(REF).locator_id == "eligibility-residence"


@pytest.mark.parametrize("value", [None, [], (), "source", 1, True])
def test_invalid_root_type(value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_OBJECT"):
        parse_source_registry(value)


@pytest.mark.parametrize("value", [None, "", "1.0", "source-registry-2.0", "source-registry-1.0 ", 1.0, True, [], {}])
def test_invalid_version_checked_before_source_shape(value):
    with pytest.raises(SourceValidationError) as caught:
        parse_source_registry({"schema_version": value, "sources": None})
    assert caught.value.code == "INVALID_SOURCE_SCHEMA_VERSION"
    assert caught.value.field == "schema_version"


def test_missing_version_not_inferred():
    data = raw()
    del data["schema_version"]
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_SCHEMA_VERSION"):
        parse_source_registry(data)


@pytest.mark.parametrize("key", ["synthetic", "test_only", "schemaVersion", "extra"])
def test_top_level_has_only_confirmed_keys(key):
    data = raw()
    data[key] = True
    with pytest.raises(SourceValidationError, match="UNKNOWN_SOURCE_FIELDS"):
        parse_source_registry(data)


def test_missing_sources_is_not_empty_registry():
    with pytest.raises(SourceValidationError, match="MISSING_SOURCE_FIELDS"):
        parse_source_registry({"schema_version": "source-registry-1.0"})


@pytest.mark.parametrize("value", [None, {}, "sources", 1, True, (), (raw()["sources"][0],)])
def test_sources_requires_json_list(value):
    data = raw()
    data["sources"] = value
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_ARRAY"):
        parse_source_registry(data)


def test_empty_sources_rejected_by_existing_registry_contract():
    data = raw()
    data["sources"] = []
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_COLLECTION"):
        parse_source_registry(data)


@pytest.mark.parametrize("level", ["document", "evidence"])
@pytest.mark.parametrize("value", [None, [], "object", 1, False])
def test_nested_models_require_objects(level, value):
    data = raw()
    if level == "document":
        data["sources"][0] = value
    else:
        data["sources"][0]["locators"][0] = value
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_OBJECT"):
        parse_source_registry(data)


@pytest.mark.parametrize("field", list(raw()["sources"][0]))
def test_each_required_document_field_must_be_present(field):
    data = raw()
    del data["sources"][0][field]
    with pytest.raises(SourceValidationError, match="MISSING_SOURCE_FIELDS"):
        parse_source_registry(data)


@pytest.mark.parametrize("field", list(raw()["sources"][0]["locators"][0]))
def test_each_required_evidence_field_must_be_present(field):
    data = raw()
    del data["sources"][0]["locators"][0][field]
    with pytest.raises(SourceValidationError, match="MISSING_SOURCE_FIELDS"):
        parse_source_registry(data)


@pytest.mark.parametrize("level", ["document", "evidence", "supersedes"])
@pytest.mark.parametrize("field", ["extra", "verifed_at", "source_documnt_id", "lifecycle_status"])
def test_all_nested_levels_reject_unknown_fields(level, field):
    data = raw()
    doc = data["sources"][0]
    obj = doc if level == "document" else doc["locators"][0]
    if level == "supersedes":
        obj = {"source_document_id": "SYNTH-SOURCE-OLD", "document_version": "d0001"}
        doc["supersedes"] = [obj]
    obj[field] = "ignored?"
    with pytest.raises(SourceValidationError, match="UNKNOWN_SOURCE_FIELDS"):
        parse_source_registry(data)


@pytest.mark.parametrize(("field", "value"), [
    ("source_document_id", ""), ("source_document_id", 123), ("source_document_id", True),
    ("document_version", 1), ("issuer", False), ("title", 123),
    ("official_url", "http://policy.example.invalid"), ("official_url", True),
    ("content_sha256", "A" * 64), ("notice_number", 1), ("attachment_url", "/file"),
])
def test_document_domain_errors_remain_data_errors(field, value):
    data = raw()
    data["sources"][0][field] = value
    with pytest.raises(SourceValidationError) as caught:
        parse_source_registry(data)
    assert isinstance(caught.value, PolicyDataError)


@pytest.mark.parametrize("field", ["publication_date", "verified_at", "effective_from", "effective_to"])
@pytest.mark.parametrize("value", ["2026-02-30", "2026-1-10", "20260110", "2026-W02-6", "2026-01-10T00:00:00", "2026-01-10T00:00:00+09:00", " 2026-01-10", "2026-01-10\n", True, 20260110, date(2026, 1, 10), datetime(2026, 1, 10)])
def test_document_dates_use_exact_iso_json_string_or_null(field, value):
    data = raw()
    data["sources"][0][field] = value
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_DATE"):
        parse_source_registry(data)


@pytest.mark.parametrize("value", ["2025-02-29", "2026-1-10", "2026-01-10T12:00:00Z", False, [], date(2026, 1, 10)])
def test_evidence_date_uses_same_strict_boundary(value):
    data = raw()
    data["sources"][0]["locators"][0]["verified_at"] = value
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_DATE"):
        parse_source_registry(data)


@pytest.mark.parametrize(("level", "field"), [("document", "source_type"), ("document", "status"), ("document", "verification_status"), ("evidence", "status"), ("evidence", "verification_status")])
@pytest.mark.parametrize("value", [None, "invalid", "active", " ACTIVE", 1, True, RegistrationSource.OFFICIAL_DATA, SourceStatus.ACTIVE])
def test_enum_boundary_accepts_only_canonical_json_strings(level, field, value):
    data = raw()
    obj = data["sources"][0]
    if level == "evidence":
        obj = obj["locators"][0]
    obj[field] = value
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_ENUM"):
        parse_source_registry(data)


@pytest.mark.parametrize("member", list(SourceType))
def test_canonical_source_type_strings(member):
    data = raw()
    data["sources"][0]["source_type"] = member.value
    assert parse_source_registry(data).sources[0].source_type is member


@pytest.mark.parametrize(("level", "field"), [("document", "locators"), ("document", "previous_urls"), ("document", "supersedes"), ("evidence", "applicable_policy_ids")])
@pytest.mark.parametrize("value", [None, {}, "array", (), True])
def test_array_boundary_does_not_coerce_other_iterables(level, field, value):
    data = raw()
    obj = data["sources"][0] if level == "document" else data["sources"][0]["locators"][0]
    obj[field] = value
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_ARRAY"):
        parse_source_registry(data)


@pytest.mark.parametrize(("field", "value"), [("locator_id", ""), ("locator_id", 1), ("locator_id", "거주 조건"), ("section", None), ("page", True), ("page", 0), ("table_position", 123), ("applicable_policy_ids", []), ("applicable_policy_ids", [RegistrationSource.SELF_REPORTED])])
def test_evidence_domain_errors_preserved(field, value):
    data = raw()
    data["sources"][0]["locators"][0][field] = value
    with pytest.raises(SourceValidationError):
        parse_source_registry(data)


def test_optional_fields_omitted_or_explicit_null_are_equivalent():
    data = raw()
    minimal = parse_source_registry(data)
    doc = data["sources"][0]
    for field in ("notice_number", "attachment_url", "effective_from", "effective_to", "content_sha256"):
        doc[field] = None
    doc["previous_urls"] = []
    doc["supersedes"] = []
    doc["locators"][0].update(page=None, table_position=None)
    assert parse_source_registry(data) == minimal


def test_all_optional_values_and_supersedes_pair_are_preserved():
    data = raw()
    doc = data["sources"][0]
    doc.update(notice_number="SYNTH-NOTICE-001", attachment_url="https://policy.example.invalid/file",
               previous_urls=["https://old.example.invalid/1"], effective_from="2025-01-01",
               effective_to="2025-12-31", content_sha256="a" * 64,
               supersedes=[{"source_document_id": "SYNTH-SOURCE-OLD", "document_version": "d0001"}])
    doc["locators"][0].update(page=3, table_position="합성 표 / 첫 행")
    loaded = parse_source_registry(data)
    result = loaded.sources[0]
    assert result.supersedes == (("SYNTH-SOURCE-OLD", "d0001"),)
    assert result.effective_from == date(2025, 1, 1)
    assert result.previous_urls == ("https://old.example.invalid/1",)
    assert loaded.to_dict() == data


@pytest.mark.parametrize("level", ["source", "locator"])
@pytest.mark.parametrize("identical", [True, False])
def test_duplicate_array_identifiers_rejected_even_for_identical_definitions(level, identical):
    data = raw()
    array = data["sources"] if level == "source" else data["sources"][0]["locators"]
    duplicate = deepcopy(array[0])
    if not identical:
        duplicate["title" if level == "source" else "section"] = "Other synthetic definition"
    array.append(duplicate)
    code = "DUPLICATE_SOURCE_ID" if level == "source" else "DUPLICATE_SOURCE_LOCATOR"
    with pytest.raises(SourceValidationError, match=code):
        parse_source_registry(data)


@pytest.mark.parametrize("level", ["source", "locator"])
@pytest.mark.parametrize("status", [SourceStatus.SUPERSEDED, SourceStatus.WITHDRAWN])
def test_loader_preserves_lifecycle_and_registry_alone_rejects_reference(level, status):
    data = raw()
    obj = data["sources"][0] if level == "source" else data["sources"][0]["locators"][0]
    obj["status"] = status.value
    loaded = parse_source_registry(data)
    assert loaded.has_evidence(REF)
    with pytest.raises(SourceValidationError, match="NOT_REFERENCEABLE"):
        loaded.resolve(REF)


@pytest.mark.parametrize("status", list(VerificationStatus))
def test_no_freshness_enforcement_or_verification_state_rewriting(status):
    data = raw()
    for obj in (data["sources"][0], data["sources"][0]["locators"][0]):
        obj.update(verified_at="2000-01-01", verification_status=status.value)
    loaded = parse_source_registry(data)
    assert loaded.resolve(REF).verification_status is status
    assert loaded.sources[0].verified_at == date(2000, 1, 1)


def test_null_unknown_dates_preserved_in_draft():
    data = raw()
    data["sources"][0]["publication_date"] = None
    for obj in (data["sources"][0], data["sources"][0]["locators"][0]):
        obj.update(verified_at=None, verification_status="DRAFT")
    loaded = parse_source_registry(data)
    assert loaded.sources[0].publication_date is None
    assert loaded.resolve(REF).verified_at is None


@pytest.mark.parametrize(("ref", "code"), [("SYNTH-SOURCE-999#eligibility-residence", "SOURCE_NOT_FOUND"), ("SYNTH-SOURCE-001#missing", "LOCATOR_NOT_FOUND")])
def test_loaded_registry_uses_existing_broken_ref_errors(ref, code):
    with pytest.raises(SourceValidationError, match=code):
        parse_source_registry(raw()).resolve(ref)


def test_invalid_later_source_never_returns_partial_registry():
    data = raw()
    broken = deepcopy(data["sources"][0])
    broken["source_document_id"] = "SYNTH-SOURCE-002"
    broken["locators"][0]["status"] = "INVALID"
    data["sources"].append(broken)
    with pytest.raises(SourceValidationError):
        parse_source_registry(data)


@pytest.mark.parametrize("text", ["", " ", "{", '{"schema_version":', '{"schema_version":"source-registry-1.0",}', "NaN", "Infinity", "-Infinity", '{"schema_version":"source-registry-1.0","sources":NaN}', "\ufeff{}"])
def test_malformed_nonstandard_or_bom_json_is_rejected(tmp_path, text):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_JSON"):
        load_source_registry(save(tmp_path, text))


@pytest.mark.parametrize("level", ["top", "source", "evidence", "supersedes"])
def test_duplicate_json_object_keys_are_detected_at_every_level(tmp_path, level):
    data = raw()
    data["sources"][0]["supersedes"] = [{"source_document_id": "SYNTH-SOURCE-OLD", "document_version": "d0001"}]
    text = json.dumps(data)
    key = {"top": "schema_version", "source": "source_document_id", "evidence": "locator_id", "supersedes": "document_version"}[level]
    if level == "supersedes":
        target = '"document_version": "d0001"'
        pos = text.rfind(target)
        text = text[:pos] + text[pos:].replace(target, target + ', ' + target, 1)
    else:
        target = f'"{key}": '
        pos = text.index(target)
        text = text[:pos] + f'"{key}": null, ' + text[pos:]
    with pytest.raises(SourceValidationError, match="DUPLICATE_SOURCE_JSON_KEY"):
        load_source_registry(save(tmp_path, text))


def test_missing_file_is_distinct_from_invalid_json(tmp_path):
    with pytest.raises(SourceValidationError) as caught:
        load_source_registry(tmp_path / "absent.json")
    assert caught.value.code == "SOURCE_FILE_ERROR"
    assert isinstance(caught.value.__cause__, FileNotFoundError)


def test_invalid_utf8_has_distinct_error_and_no_encoding_detection(tmp_path):
    path = tmp_path / "sources.json"
    path.write_bytes("합성".encode("cp949"))
    with pytest.raises(SourceValidationError) as caught:
        load_source_registry(path)
    assert caught.value.code == "INVALID_SOURCE_ENCODING"


@pytest.mark.parametrize("root", [[], None, "object", 123, False])
def test_wrong_file_root_is_data_error_after_json_decoding(tmp_path, root):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_OBJECT"):
        load_source_registry(save(tmp_path, json.dumps(root)))


def test_pure_parser_has_no_io_and_loader_has_no_network(monkeypatch, tmp_path):
    import builtins
    import socket
    import urllib.request

    path = save(tmp_path, json.dumps(raw(), ensure_ascii=False))

    def unexpected(*args, **kwargs):
        pytest.fail("허용되지 않은 I/O를 호출했습니다")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    assert load_source_registry(path) == expected()
    monkeypatch.setattr(builtins, "open", unexpected)
    monkeypatch.setattr(Path, "open", unexpected)
    assert parse_source_registry(raw()) == expected()
