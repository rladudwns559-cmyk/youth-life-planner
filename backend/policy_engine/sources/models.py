"""공식 정책 근거의 불변 값 모델. I/O·현재 시각·정책 판정에 의존하지 않는다."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from urllib.parse import urlsplit

from ..errors import PolicyDataError


class SourceValidationError(PolicyDataError):
    """원문 값 대신 안정적인 code/field만 제공하는 정책 근거 데이터 오류."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field} 정책 근거 계약을 확인하세요")


class SourceType(str, Enum):
    OFFICIAL_NOTICE = "OFFICIAL_NOTICE"
    OFFICIAL_POLICY_PAGE = "OFFICIAL_POLICY_PAGE"
    OFFICIAL_QUARTER_GUIDE = "OFFICIAL_QUARTER_GUIDE"


class SourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class VerificationStatus(str, Enum):
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    STALE = "STALE"


def _identifier(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", value) is None:
        raise SourceValidationError("INVALID_SOURCE_IDENTIFIER", field)


def _locator(value: object) -> None:
    if type(value) is not str or re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", value) is None:
        raise SourceValidationError("INVALID_SOURCE_LOCATOR", "locator_id")


def _version(value: object) -> None:
    if (type(value) is not str
            or re.fullmatch(r"d(?:[0-9]{4}|[1-9][0-9]{4,})", value) is None
            or value == "d0000"):
        raise SourceValidationError("INVALID_DOCUMENT_VERSION", "document_version")


def _text(value: object, field: str) -> None:
    if type(value) is not str or not value.strip():
        raise SourceValidationError("INVALID_SOURCE_TEXT", field)


def _date(value: object, field: str) -> None:
    if value is not None and type(value) is not date:
        raise SourceValidationError("INVALID_SOURCE_DATE", field)


def _url(value: object, field: str) -> None:
    if (type(value) is not str or not value.startswith("https://")
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)):
        raise SourceValidationError("INVALID_SOURCE_URL", field)
    try:
        parts = urlsplit(value)
        valid = bool(parts.hostname) and parts.username is None and parts.password is None
        port = parts.port
        valid = valid and (port is None or 0 < port <= 65535)
    except ValueError:
        valid = False
    if not valid:
        raise SourceValidationError("INVALID_SOURCE_URL", field)


def _verification(status: object, verified_at: date | None) -> None:
    if type(status) is not VerificationStatus:
        raise SourceValidationError("INVALID_VERIFICATION_STATUS", "verification_status")
    if status is VerificationStatus.VERIFIED and verified_at is None:
        raise SourceValidationError("VERIFIED_DATE_REQUIRED", "verified_at")


def parse_evidence_ref(ref: str) -> tuple[str, str]:
    """canonical 문자열을 분해한다. 별칭·공백·대소문자를 보정하지 않는다."""
    if type(ref) is not str or ref.count("#") != 1:
        raise SourceValidationError("INVALID_EVIDENCE_REF", "evidence_ref")
    source_id, locator_id = ref.split("#")
    _identifier(source_id, "source_document_id")
    _locator(locator_id)
    return source_id, locator_id


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceEvidence:
    """문서 내부의 의미 위치. 소속 문서는 SourceDocument.locators로 결정한다."""

    locator_id: str
    section: str
    meaning_summary: str
    applicable_policy_ids: tuple[str, ...]
    verified_at: date | None
    verification_status: VerificationStatus
    status: SourceStatus
    page: int | None = None
    table_position: str | None = None

    def __post_init__(self) -> None:
        _locator(self.locator_id)
        _text(self.section, "section")
        _text(self.meaning_summary, "meaning_summary")
        if self.page is not None and (type(self.page) is not int or self.page < 1):
            raise SourceValidationError("INVALID_SOURCE_PAGE", "page")
        if self.table_position is not None:
            _text(self.table_position, "table_position")
        if type(self.applicable_policy_ids) is not tuple or not self.applicable_policy_ids:
            raise SourceValidationError("INVALID_POLICY_IDS", "applicable_policy_ids")
        for policy_id in self.applicable_policy_ids:
            _identifier(policy_id, "applicable_policy_ids")
        if len(set(self.applicable_policy_ids)) != len(self.applicable_policy_ids):
            raise SourceValidationError("DUPLICATE_POLICY_ID", "applicable_policy_ids")
        _date(self.verified_at, "verified_at")
        _verification(self.verification_status, self.verified_at)
        if type(self.status) is not SourceStatus:
            raise SourceValidationError("INVALID_SOURCE_STATUS", "status")

    def to_dict(self) -> dict:
        return {
            "locator_id": self.locator_id, "section": self.section,
            "page": self.page, "table_position": self.table_position,
            "meaning_summary": self.meaning_summary,
            "applicable_policy_ids": list(self.applicable_policy_ids),
            "verified_at": self.verified_at.isoformat() if self.verified_at is not None else None,
            "verification_status": self.verification_status.value, "status": self.status.value,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceDocument:
    source_document_id: str
    document_version: str
    source_type: SourceType
    issuer: str
    title: str
    official_url: str
    publication_date: date | None
    verified_at: date | None
    verification_status: VerificationStatus
    status: SourceStatus
    locators: tuple[SourceEvidence, ...]
    notice_number: str | None = None
    attachment_url: str | None = None
    previous_urls: tuple[str, ...] = ()
    effective_from: date | None = None
    effective_to: date | None = None
    supersedes: tuple[tuple[str, str], ...] = ()
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.source_document_id, "source_document_id")
        _version(self.document_version)
        if type(self.source_type) is not SourceType:
            raise SourceValidationError("INVALID_SOURCE_TYPE", "source_type")
        _text(self.issuer, "issuer")
        _text(self.title, "title")
        if self.notice_number is not None:
            _text(self.notice_number, "notice_number")
        _url(self.official_url, "official_url")
        if self.attachment_url is not None:
            _url(self.attachment_url, "attachment_url")
        if type(self.previous_urls) is not tuple:
            raise SourceValidationError("INVALID_PREVIOUS_URLS", "previous_urls")
        for url in self.previous_urls:
            _url(url, "previous_urls")
        if len(set(self.previous_urls)) != len(self.previous_urls):
            raise SourceValidationError("DUPLICATE_PREVIOUS_URL", "previous_urls")
        for field in ("publication_date", "verified_at", "effective_from", "effective_to"):
            _date(getattr(self, field), field)
        if (self.effective_from is not None and self.effective_to is not None
                and self.effective_from > self.effective_to):
            raise SourceValidationError("INVALID_EFFECTIVE_PERIOD", "effective_to")
        _verification(self.verification_status, self.verified_at)
        if type(self.status) is not SourceStatus:
            raise SourceValidationError("INVALID_SOURCE_STATUS", "status")
        if (type(self.locators) is not tuple or not self.locators
                or any(type(item) is not SourceEvidence for item in self.locators)):
            raise SourceValidationError("INVALID_SOURCE_EVIDENCE", "locators")
        ids = tuple(item.locator_id for item in self.locators)
        if len(set(ids)) != len(ids):
            raise SourceValidationError("DUPLICATE_SOURCE_LOCATOR", "locators")
        for item in self.locators:
            if item.verified_at is not None and (
                    self.verified_at is None or item.verified_at > self.verified_at):
                raise SourceValidationError("EVIDENCE_DATE_MISMATCH", "locators.verified_at")
        if type(self.supersedes) is not tuple:
            raise SourceValidationError("INVALID_SUPERSEDES", "supersedes")
        for item in self.supersedes:
            if type(item) is not tuple or len(item) != 2:
                raise SourceValidationError("INVALID_SUPERSEDES", "supersedes")
            _identifier(item[0], "supersedes.source_document_id")
            _version(item[1])
            if item == (self.source_document_id, self.document_version):
                raise SourceValidationError("SELF_SUPERSEDES", "supersedes")
        if len(set(self.supersedes)) != len(self.supersedes):
            raise SourceValidationError("DUPLICATE_SUPERSEDES", "supersedes")
        if self.content_sha256 is not None and (
                type(self.content_sha256) is not str
                or re.fullmatch(r"[0-9a-f]{64}", self.content_sha256) is None):
            raise SourceValidationError("INVALID_SOURCE_HASH", "content_sha256")

    def to_dict(self) -> dict:
        def iso(value: date | None) -> str | None:
            return value.isoformat() if value is not None else None

        return {
            "source_document_id": self.source_document_id, "document_version": self.document_version,
            "source_type": self.source_type.value, "issuer": self.issuer, "title": self.title,
            "notice_number": self.notice_number, "official_url": self.official_url,
            "attachment_url": self.attachment_url, "previous_urls": list(self.previous_urls),
            "publication_date": iso(self.publication_date), "effective_from": iso(self.effective_from),
            "effective_to": iso(self.effective_to), "verified_at": iso(self.verified_at),
            "verification_status": self.verification_status.value, "status": self.status.value,
            "supersedes": [{"source_document_id": item[0], "document_version": item[1]}
                           for item in self.supersedes],
            "content_sha256": self.content_sha256,
            "locators": [item.to_dict() for item in self.locators],
        }
