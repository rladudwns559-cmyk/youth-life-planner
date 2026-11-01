"""버전이 명시된 정책 근거 JSON 경계. 정책 rule loader와 독립적이다."""

from datetime import date
from enum import Enum
import json
from pathlib import Path
import re

from .models import (
    SourceDocument, SourceEvidence, SourceStatus, SourceType,
    SourceValidationError, VerificationStatus,
)
from .registry import SourceRegistry


def _object(value: object, required: set[str], optional: set[str], field: str) -> dict:
    if type(value) is not dict:
        raise SourceValidationError("INVALID_SOURCE_OBJECT", field)
    if required - value.keys():
        raise SourceValidationError("MISSING_SOURCE_FIELDS", field)
    if value.keys() - required - optional:
        raise SourceValidationError("UNKNOWN_SOURCE_FIELDS", field)
    return value


def _array(value: object, field: str) -> list:
    if type(value) is not list:
        raise SourceValidationError("INVALID_SOURCE_ARRAY", field)
    return value


def _date(value: object, field: str) -> date | None:
    if value is None:
        return None
    if type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise SourceValidationError("INVALID_SOURCE_DATE", field)


def _enum(value: object, enum_type: type[Enum], field: str) -> Enum:
    if type(value) is str:
        try:
            return enum_type(value)
        except ValueError:
            pass
    raise SourceValidationError("INVALID_SOURCE_ENUM", field)


def _evidence(value: object) -> SourceEvidence:
    obj = _object(value, {
        "locator_id", "section", "meaning_summary", "applicable_policy_ids",
        "verified_at", "verification_status", "status",
    }, {"page", "table_position"}, "locators")
    return SourceEvidence(
        locator_id=obj["locator_id"], section=obj["section"], meaning_summary=obj["meaning_summary"],
        applicable_policy_ids=tuple(_array(obj["applicable_policy_ids"], "applicable_policy_ids")),
        verified_at=_date(obj["verified_at"], "locators.verified_at"),
        verification_status=_enum(obj["verification_status"], VerificationStatus, "locators.verification_status"),
        status=_enum(obj["status"], SourceStatus, "locators.status"),
        page=obj.get("page"), table_position=obj.get("table_position"),
    )


def _document(value: object) -> SourceDocument:
    obj = _object(value, {
        "source_document_id", "document_version", "source_type", "issuer", "title", "official_url",
        "publication_date", "verified_at", "verification_status", "status", "locators",
    }, {
        "notice_number", "attachment_url", "previous_urls", "effective_from", "effective_to",
        "supersedes", "content_sha256",
    }, "sources")
    supersedes = []
    for previous in _array(obj.get("supersedes", []), "supersedes"):
        previous = _object(previous, {"source_document_id", "document_version"}, set(), "supersedes")
        supersedes.append((previous["source_document_id"], previous["document_version"]))
    return SourceDocument(
        source_document_id=obj["source_document_id"], document_version=obj["document_version"],
        source_type=_enum(obj["source_type"], SourceType, "source_type"),
        issuer=obj["issuer"], title=obj["title"], official_url=obj["official_url"],
        publication_date=_date(obj["publication_date"], "publication_date"),
        verified_at=_date(obj["verified_at"], "verified_at"),
        verification_status=_enum(obj["verification_status"], VerificationStatus, "verification_status"),
        status=_enum(obj["status"], SourceStatus, "status"),
        locators=tuple(_evidence(item) for item in _array(obj["locators"], "locators")),
        notice_number=obj.get("notice_number"), attachment_url=obj.get("attachment_url"),
        previous_urls=tuple(_array(obj.get("previous_urls", []), "previous_urls")),
        effective_from=_date(obj.get("effective_from"), "effective_from"),
        effective_to=_date(obj.get("effective_to"), "effective_to"),
        supersedes=tuple(supersedes), content_sha256=obj.get("content_sha256"),
    )


def parse_source_registry(data: object) -> SourceRegistry:
    """JSON 호환 값의 구조를 검증한 뒤 전체 registry만 반환한다."""
    if type(data) is not dict:
        raise SourceValidationError("INVALID_SOURCE_OBJECT", "registry")
    if type(data.get("schema_version")) is not str or data["schema_version"] != "source-registry-1.0":
        raise SourceValidationError("INVALID_SOURCE_SCHEMA_VERSION", "schema_version")
    obj = _object(data, {"schema_version", "sources"}, set(), "registry")
    return SourceRegistry(tuple(_document(item) for item in _array(obj["sources"], "sources")))


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceValidationError("DUPLICATE_SOURCE_JSON_KEY", "json")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise SourceValidationError("INVALID_SOURCE_JSON", "json")


def load_source_registry(path: str | Path) -> SourceRegistry:
    """UTF-8 파일 읽기 경계. BOM·문자 인코딩 추정·네트워크 요청 없음."""
    try:
        with Path(path).open(encoding="utf-8") as stream:
            data = json.load(stream, object_pairs_hook=_unique_keys, parse_constant=_invalid_constant)
    except SourceValidationError:
        raise
    except OSError as exc:
        raise SourceValidationError("SOURCE_FILE_ERROR", "path") from exc
    except UnicodeError as exc:
        raise SourceValidationError("INVALID_SOURCE_ENCODING", "file") from exc
    except (ValueError, RecursionError) as exc:
        raise SourceValidationError("INVALID_SOURCE_JSON", "json") from exc
    return parse_source_registry(data)
