"""합성/test_only 정책 근거만 사용한다. 실제 기관·정책·공식 URL은 넣지 않는다."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.facts import RegistrationSource, ResidentRegistrationFact, RegionRef
from backend.policy_engine.sources import (
    SourceDocument, SourceEvidence, SourceRegistry, SourceStatus, SourceType,
    SourceValidationError, VerificationStatus, parse_evidence_ref, validate_evidence_refs,
)


# 도메인 계약에 없는 production flag를 새 필드로 추가하지 않는다.
# 이 모듈의 빌더 전체가 명시적으로 합성 테스트 전용이다.
SYNTHETIC = True
TEST_ONLY = True
DAY = date(2026, 1, 10)
REF = "SYNTH-SOURCE-001#eligibility-residence"


def evidence(**changes):
    values = dict(
        locator_id="eligibility-residence", section="Synthetic section / residence",
        meaning_summary="Synthetic residence requirement", applicable_policy_ids=("SYNTH-POLICY-001",),
        verified_at=DAY, verification_status=VerificationStatus.VERIFIED, status=SourceStatus.ACTIVE,
    )
    return SourceEvidence(**(values | changes))


def document(**changes):
    values = dict(
        source_document_id="SYNTH-SOURCE-001", document_version="d0001",
        source_type=SourceType.OFFICIAL_NOTICE, issuer="SYNTHETIC_AUTHORITY",
        title="Synthetic Policy Notice", official_url="https://policy.example.invalid/notice/1",
        publication_date=date(2026, 1, 1), verified_at=DAY,
        verification_status=VerificationStatus.VERIFIED, status=SourceStatus.ACTIVE,
        locators=(evidence(),),
    )
    return SourceDocument(**(values | changes))


def registry():
    return SourceRegistry((document(),))


def test_normal_models_lookup_and_repeat_resolution():
    item = evidence(page=2, table_position="row 1 / condition")
    doc = document(locators=(item,))
    sources = SourceRegistry((doc,))
    assert sources.get_source("SYNTH-SOURCE-001") is doc
    assert sources.has_source("SYNTH-SOURCE-001")
    assert sources.has_evidence(REF)
    assert sources.resolve(REF) is item
    assert sources.resolve(REF) == sources.resolve(REF)
    assert parse_evidence_ref(REF) == ("SYNTH-SOURCE-001", "eligibility-residence")
    assert sources == SourceRegistry((document(locators=(evidence(page=2, table_position="row 1 / condition"),)),))


def test_multiple_documents_locators_and_ordered_batch():
    extra = evidence(locator_id="application-period")
    other = document(source_document_id="SYNTH-SOURCE-002", locators=(extra,))
    sources = SourceRegistry((document(locators=(evidence(), extra)), other))
    refs = ("SYNTH-SOURCE-002#application-period", REF, "SYNTH-SOURCE-001#application-period")
    assert validate_evidence_refs(refs, sources) == (extra, evidence(), extra)
    assert sources.get_source("SYNTH-SOURCE-002") == other
    assert not sources.has_source("SYNTH-SOURCE-999")
    assert not sources.has_evidence("SYNTH-SOURCE-999#eligibility-residence")
    assert not sources.has_evidence("SYNTH-SOURCE-001#missing")


@pytest.mark.parametrize("value", [None, "", " ", 1, True, [], {}, "source", "SYNTH_SOURCE", " SYNTH-SOURCE", "SYNTH-SOURCE ", "https://example.invalid", "SYNTH--SOURCE"])
def test_invalid_source_identifiers(value):
    with pytest.raises(SourceValidationError) as caught:
        document(source_document_id=value)
    assert caught.value.code == "INVALID_SOURCE_IDENTIFIER"
    assert isinstance(caught.value, (PolicyDataError, EngineValidationError))


@pytest.mark.parametrize("value", [None, "", " ", 1, True, [], {}, "Eligibility", "eligibility_residence", "거주조건", "eligibility--residence", "eligibility-residence "])
def test_invalid_locator_identifiers(value):
    with pytest.raises(SourceValidationError) as caught:
        evidence(locator_id=value)
    assert caught.value.code == "INVALID_SOURCE_LOCATOR"


@pytest.mark.parametrize("ref", [None, "", " ", 1, True, [], {}, (), "SYNTH-SOURCE-001", "#eligibility-residence", "SYNTH-SOURCE-001#", "SYNTH-SOURCE-001#x#y", "##", "SYNTH-SOURCE-001 #eligibility-residence", "SYNTH-SOURCE-001#eligibility-residence ", "synth-source-001#eligibility-residence", "SYNTH-SOURCE-001#거주조건"])
def test_malformed_reference_is_error_for_all_reference_apis(ref):
    sources = registry()
    for operation in (parse_evidence_ref, sources.resolve, sources.has_evidence):
        with pytest.raises(SourceValidationError):
            operation(ref)


@pytest.mark.parametrize(("ref", "code"), [
    ("SYNTH-SOURCE-999#eligibility-residence", "SOURCE_NOT_FOUND"),
    ("SYNTH-SOURCE-001#missing", "LOCATOR_NOT_FOUND"),
])
def test_broken_references_rejected_without_partial_results(ref, code):
    with pytest.raises(SourceValidationError) as caught:
        validate_evidence_refs((REF, ref), registry())
    assert caught.value.code == code
    assert ref not in str(caught.value)


@pytest.mark.parametrize("changed", [False, True])
def test_duplicate_source_id_is_error_even_for_identical_definitions(changed):
    doc = document()
    duplicate = replace(doc, title="Another synthetic title") if changed else doc
    with pytest.raises(SourceValidationError, match="DUPLICATE_SOURCE_ID"):
        SourceRegistry((doc, duplicate))


@pytest.mark.parametrize("changed", [False, True])
def test_duplicate_locator_is_error_even_for_identical_definitions(changed):
    item = evidence()
    duplicate = replace(item, meaning_summary="Other synthetic meaning") if changed else item
    with pytest.raises(SourceValidationError, match="DUPLICATE_SOURCE_LOCATOR"):
        document(locators=(item, duplicate))


def test_same_locator_id_in_different_documents_is_allowed():
    sources = SourceRegistry((document(), document(source_document_id="SYNTH-SOURCE-002")))
    assert sources.resolve(REF) == sources.resolve("SYNTH-SOURCE-002#eligibility-residence")


@pytest.mark.parametrize("value", [None, (), [], {}, "sources", (None,), (evidence(),)])
def test_invalid_registry_collection(value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_COLLECTION"):
        SourceRegistry(value)


@pytest.mark.parametrize("value", [None, (), [], {}, "locators", (None,), ("locator",)])
def test_invalid_document_locator_collection(value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_EVIDENCE"):
        document(locators=value)


@pytest.mark.parametrize("refs", [None, (), [], {}, "SYNTH-SOURCE-001#eligibility-residence", (REF, REF)])
def test_invalid_reference_collection_and_duplicate_references(refs):
    with pytest.raises(SourceValidationError):
        validate_evidence_refs(refs, registry())


def test_batch_requires_registry_type():
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_REGISTRY"):
        validate_evidence_refs((REF,), (document(),))


@pytest.mark.parametrize("status", [SourceStatus.SUPERSEDED, SourceStatus.WITHDRAWN])
@pytest.mark.parametrize("target", ["document", "locator"])
def test_nonreferenceable_lifecycle_preserved_but_resolution_rejected(status, target):
    doc = document(status=status) if target == "document" else document(locators=(evidence(status=status),))
    sources = SourceRegistry((doc,))
    assert sources.has_source(doc.source_document_id)
    assert sources.has_evidence(REF)  # 존재와 참조 허용은 별도 계약이다.
    assert sources.get_source(doc.source_document_id) is doc
    code = "SOURCE_NOT_REFERENCEABLE" if target == "document" else "EVIDENCE_NOT_REFERENCEABLE"
    with pytest.raises(SourceValidationError, match=code):
        sources.resolve(REF)


@pytest.mark.parametrize("status", list(VerificationStatus))
def test_verification_and_ancient_dates_do_not_trigger_freshness(status):
    old = date(2000, 1, 1)
    item = evidence(verified_at=old, verification_status=status)
    sources = SourceRegistry((document(verified_at=old, verification_status=status, locators=(item,)),))
    assert sources.resolve(REF) is item
    assert sources.get_source("SYNTH-SOURCE-001").verification_status is status


def test_no_clock_based_future_date_enforcement_or_effective_period_filter():
    future = date(2099, 1, 1)
    doc = document(verified_at=future, locators=(evidence(verified_at=future),),
                   effective_from=date(2001, 1, 1), effective_to=date(2001, 2, 1))
    assert SourceRegistry((doc,)).resolve(REF) == evidence(verified_at=future)


@pytest.mark.parametrize("field", ["publication_date", "verified_at", "effective_from", "effective_to"])
@pytest.mark.parametrize("value", ["2026-01-10", 0, True, datetime(2026, 1, 10), datetime(2026, 1, 10, tzinfo=timezone.utc)])
def test_document_dates_require_exact_date_type(field, value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_DATE"):
        document(**{field: value})


@pytest.mark.parametrize("value", ["2026-01-10", 0, False, datetime(2026, 1, 10)])
def test_evidence_date_requires_exact_date_type(value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_DATE"):
        evidence(verified_at=value)


def test_unknown_dates_remain_none_in_draft_models():
    item = evidence(verified_at=None, verification_status=VerificationStatus.DRAFT)
    doc = document(publication_date=None, verified_at=None,
                   verification_status=VerificationStatus.DRAFT, locators=(item,))
    assert doc.to_dict()["publication_date"] is None
    assert doc.to_dict()["verified_at"] is None
    assert SourceRegistry((doc,)).resolve(REF) is item


@pytest.mark.parametrize("target", ["document", "locator"])
def test_verified_metadata_requires_confirmation_date(target):
    with pytest.raises(SourceValidationError, match="VERIFIED_DATE_REQUIRED"):
        document(verified_at=None) if target == "document" else evidence(verified_at=None)


@pytest.mark.parametrize("parent_date", [None, date(2026, 1, 9)])
def test_locator_confirmation_must_be_covered_by_document_confirmation(parent_date):
    with pytest.raises(SourceValidationError, match="EVIDENCE_DATE_MISMATCH"):
        document(verified_at=parent_date, verification_status=VerificationStatus.DRAFT)


def test_effective_period_order_and_equal_boundary():
    assert document(effective_from=DAY, effective_to=DAY).effective_to == DAY
    with pytest.raises(SourceValidationError, match="INVALID_EFFECTIVE_PERIOD"):
        document(effective_from=DAY, effective_to=date(2026, 1, 9))


@pytest.mark.parametrize("field", ["source_type", "status", "verification_status"])
@pytest.mark.parametrize("value", [None, "ACTIVE", 0, True, RegistrationSource.OFFICIAL_DATA])
def test_document_enums_do_not_accept_raw_strings_or_user_source(field, value):
    with pytest.raises(SourceValidationError):
        document(**{field: value})


@pytest.mark.parametrize("field", ["status", "verification_status"])
@pytest.mark.parametrize("value", [None, "ACTIVE", 0, True, RegistrationSource.SELF_REPORTED])
def test_evidence_enums_are_exact_types(field, value):
    with pytest.raises(SourceValidationError):
        evidence(**{field: value})


@pytest.mark.parametrize("member", list(SourceType))
def test_all_confirmed_source_types(member):
    assert document(source_type=member).source_type is member


@pytest.mark.parametrize("value", [None, "", "d0000", "d001", "d00001", "d-0001", "d1.0", "D0001", 1, True])
def test_invalid_document_versions(value):
    with pytest.raises(SourceValidationError, match="INVALID_DOCUMENT_VERSION"):
        document(document_version=value)


@pytest.mark.parametrize("value", ["d0001", "d9999", "d10000"])
def test_canonical_document_versions(value):
    assert document(document_version=value).document_version == value


@pytest.mark.parametrize("field", ["official_url", "attachment_url"])
@pytest.mark.parametrize("value", ["", " ", "http://policy.example.invalid", "/notice", "https://", "https:///notice", "https://user:secret@policy.example.invalid", "https://policy.example.invalid:bad", " https://policy.example.invalid", "https://policy.example.invalid/with space", "https://policy.example.invalid/\n", 0, True, {}, "https://[bad"])
def test_urls_have_minimal_strict_https_structure_without_network(field, value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_URL"):
        document(**{field: value})


@pytest.mark.parametrize("field", ["issuer", "title", "notice_number"])
@pytest.mark.parametrize("value", ["", " ", 1, False, [], RegistrationSource.OFFICIAL_DATA])
def test_invalid_document_text(field, value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_TEXT"):
        document(**{field: value})


@pytest.mark.parametrize("field", ["section", "meaning_summary", "table_position"])
@pytest.mark.parametrize("value", ["", " ", 1, True, [], RegistrationSource.MANUALLY_VERIFIED])
def test_invalid_evidence_text(field, value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_TEXT"):
        evidence(**{field: value})


@pytest.mark.parametrize("value", [0, -1, True, "1", 1.5])
def test_page_is_positive_exact_integer(value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_PAGE"):
        evidence(page=value)


@pytest.mark.parametrize("value", [None, [], (), ("bad_id",), ("SYNTH-POLICY-001", "SYNTH-POLICY-001"), (RegistrationSource.SELF_REPORTED,)])
def test_applicable_policy_identifiers_are_strict_nonempty_unique_tuple(value):
    with pytest.raises(SourceValidationError):
        evidence(applicable_policy_ids=value)


@pytest.mark.parametrize("member", list(RegistrationSource))
def test_user_provenance_is_not_converted_to_source_id_or_source_model(member):
    with pytest.raises(SourceValidationError):
        document(source_document_id=member)
    with pytest.raises(SourceValidationError):
        parse_evidence_ref(f"{member.value}#eligibility-residence")
    with pytest.raises(SourceValidationError):
        SourceRegistry((member,))
    assert not registry().has_source(member.value.replace("_", "-"))


def test_registry_does_not_mutate_user_evidence_or_existing_rule_refs():
    from backend.policy_engine.specialized_rules import ResidentRegistrationRule
    from backend.policy_engine.result_types import ReferenceDateSource

    fact = ResidentRegistrationFact(RegionRef("GYEONGGI", "ANSAN"), DAY, RegistrationSource.SELF_REPORTED)
    rule = ResidentRegistrationRule("SYNTH-RULE-001", RegionRef("GYEONGGI", "ANSAN"),
                                    ReferenceDateSource.APPLICATION_DATE, (REF,))
    before = fact.to_dict()
    validate_evidence_refs(rule.evidence_refs, registry())
    assert fact.to_dict() == before
    assert fact.source is RegistrationSource.SELF_REPORTED
    assert rule.evidence_refs == (REF,)
    assert type(rule.evidence_refs[0]) is str


def test_models_are_deeply_immutable_and_input_list_is_not_retained():
    locators = [evidence()]
    doc = document(locators=tuple(locators))
    documents = [doc]
    sources = SourceRegistry(tuple(documents))
    locators.clear()
    documents.clear()
    assert sources.resolve(REF) == evidence()
    for obj, field, new in [(doc, "title", "changed"), (evidence(), "section", "changed"),
                            (sources, "sources", ())]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, new)
    with pytest.raises(AttributeError):
        sources.sources.append(document())
    with pytest.raises(AttributeError):
        doc.locators.append(evidence())
    assert hash(sources) == hash(SourceRegistry((document(),)))


def test_explicit_serialization_copies_all_mutable_output_and_preserves_types():
    doc = document(
        notice_number="SYNTH-NOTICE-001", attachment_url="https://policy.example.invalid/file/1",
        previous_urls=("https://old.example.invalid/notice/1",),
        supersedes=(("SYNTH-SOURCE-OLD", "d0001"),), content_sha256="a" * 64,
    )
    sources = SourceRegistry((doc,))
    result = sources.to_dict()
    encoded = json.loads(json.dumps(result))
    assert encoded == result
    assert result["sources"][0]["verified_at"] == "2026-01-10"
    assert result["sources"][0]["source_type"] == "OFFICIAL_NOTICE"
    assert result["sources"][0]["supersedes"] == [{"source_document_id": "SYNTH-SOURCE-OLD", "document_version": "d0001"}]
    result["sources"][0]["locators"][0]["applicable_policy_ids"].clear()
    result["sources"][0]["previous_urls"].clear()
    result["sources"][0]["supersedes"][0]["document_version"] = "d9999"
    result["sources"].clear()
    assert sources.get_source("SYNTH-SOURCE-001") == doc
    assert sources.resolve(REF).applicable_policy_ids == ("SYNTH-POLICY-001",)


@pytest.mark.parametrize("value", [None, [], (("SYNTH-SOURCE-OLD",),), (["SYNTH-SOURCE-OLD", "d0001"],), (("SYNTH-SOURCE-001", "d0001"),), (("SYNTH-SOURCE-OLD", "d0001"), ("SYNTH-SOURCE-OLD", "d0001"))])
def test_invalid_supersedes_structure_duplicates_and_self_reference(value):
    with pytest.raises(SourceValidationError):
        document(supersedes=value)


def test_registry_rejects_local_supersedes_cycle_but_preserves_historical_binding():
    first = document(supersedes=(("SYNTH-SOURCE-002", "d0001"),))
    second = document(source_document_id="SYNTH-SOURCE-002", supersedes=(("SYNTH-SOURCE-001", "d0001"),))
    with pytest.raises(SourceValidationError, match="CYCLIC_SUPERSEDES"):
        SourceRegistry((first, second))
    historical = document(document_version="d0002", supersedes=(("SYNTH-SOURCE-001", "d0001"),))
    assert SourceRegistry((historical,)).get_source("SYNTH-SOURCE-001").supersedes == (("SYNTH-SOURCE-001", "d0001"),)


def test_acyclic_supersedes_chain_is_not_mistaken_for_cycle():
    old = document(source_document_id="SYNTH-SOURCE-003", status=SourceStatus.SUPERSEDED)
    middle = document(source_document_id="SYNTH-SOURCE-002", supersedes=((old.source_document_id, "d0001"),))
    new = document(supersedes=((middle.source_document_id, "d0001"), (old.source_document_id, "d0001")))
    assert SourceRegistry((new, middle, old)).resolve(REF) == evidence()


@pytest.mark.parametrize("value", [[], ("http://old.example.invalid",), ("https://old.example.invalid", "https://old.example.invalid")])
def test_previous_urls_are_strict_unique_tuple(value):
    with pytest.raises(SourceValidationError):
        document(previous_urls=value)


@pytest.mark.parametrize("value", ["", "a" * 63, "A" * 64, "g" * 64, 0, True])
def test_hash_is_optional_but_strict_when_present(value):
    with pytest.raises(SourceValidationError, match="INVALID_SOURCE_HASH"):
        document(content_sha256=value)


def test_no_io_is_performed_during_model_construction_or_resolution(monkeypatch):
    import builtins
    import socket
    import urllib.request

    def unexpected(*args, **kwargs):
        pytest.fail("정책 근거 도메인에서 I/O를 호출했습니다")

    monkeypatch.setattr(builtins, "open", unexpected)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    sources = registry()
    assert validate_evidence_refs((REF,), sources) == (evidence(),)
    assert json.dumps(sources.to_dict())
