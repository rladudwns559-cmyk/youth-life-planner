"""합성/test_only edition JSON → 기존 parser → 근거 검증 → 엔진 통합."""

from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path

import pytest

from backend.policy_engine import (
    EvaluationContext, Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, UserProfile,
    evaluate_policy_tree,
)
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.evaluation_inputs import EvaluationFacts, PolicyReferenceContext
from backend.policy_engine.facts import RegionRef, RegistrationSource, ResidentRegistrationFact
from backend.policy_engine.loader import parse_policy_set
from backend.policy_engine.policy_data import (
    EnvelopeValidationError, EvaluationScope, PolicyCategory, PolicyCoverage, PolicyEnvelope,
    PolicyLifecycleStatus, PolicyVerificationStatus, SourceBinding,
    load_policy_envelope, parse_policy_envelope, validate_envelope_sources,
)
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.sources import (
    SourceValidationError, VerificationStatus, load_source_registry, parse_source_registry,
)
from backend.policy_engine.specialized_rules import ResidentRegistrationRule


DATA = Path(__file__).resolve().parents[1] / "data/synthetic"
FIXTURE = DATA / "policy_envelope_m11.json"
DAY = date(2026, 1, 10)
REGION = RegionRef("SEOUL", "JONGNO")


def raw():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def source_raw():
    return json.loads((DATA / "sources.json").read_text(encoding="utf-8"))


def hand_built():
    root = RuleGroup("SYNTH-ROOT", GroupOperator.ALL, (
        PolicyRule("SYNTH-ATOM", Field.AGE, Operator.GTE, 19,
                   evidence_refs=("SYNTH-SOURCE-001#application-period",)),
        ResidentRegistrationRule("SYNTH-RESIDENT", REGION, ReferenceDateSource.APPLICATION_DATE,
                                 ("SYNTH-SOURCE-001#eligibility-residence",)),
    ))
    return PolicyEnvelope(
        schema_version="policy-data-1.0", rule_schema_version="m1.1",
        policy=Policy("SYNTH-POLICY-001", "합성 test_only 정책", "r0001", root, True, True),
        edition_id="2026", jurisdiction=REGION, category=PolicyCategory.YOUTH_SUPPORT,
        dataset_version="synthetic-edition-001", evaluation_scope=EvaluationScope.CONDITION_SLICE,
        coverage=PolicyCoverage(("SYNTH-ATOM", "SYNTH-RESIDENT"), ("합성 미구현 조건",)),
        source_bindings=(SourceBinding("SYNTH-SOURCE-001", "d0001"),),
        verification_status=PolicyVerificationStatus.DRAFT, last_verified_at=DAY,
        lifecycle_status=PolicyLifecycleStatus.ACTIVE,
        effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
    )


def save(tmp_path, text):
    path = tmp_path / "envelope.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_loaded_and_hand_built_envelopes_are_identical_and_synthetic():
    loaded = load_policy_envelope(FIXTURE)
    assert loaded == hand_built() == parse_policy_envelope(raw())
    assert loaded.to_dict() == hand_built().to_dict()
    assert loaded.policy_id == "SYNTH-POLICY-001"
    assert loaded.rule_version == "r0001"
    assert loaded.source_document_ids == ("SYNTH-SOURCE-001",)
    assert loaded.synthetic is True and loaded.test_only is True
    assert loaded.verification_status is PolicyVerificationStatus.DRAFT
    assert loaded.effective_from == date(2026, 1, 1)


def test_existing_public_m11_parser_is_called_once_without_tree_reimplementation(monkeypatch):
    import backend.policy_engine.policy_data.loader as target

    calls = []
    original = target.parse_policy_set

    def track(data):
        calls.append(deepcopy(data))
        return original(data)

    monkeypatch.setattr(target, "parse_policy_set", track)
    result = target.parse_policy_envelope(raw())
    assert len(calls) == 1
    assert calls[0]["schema_version"] == "m1.1"
    assert calls[0]["policies"] == [raw()["policy"]]
    assert result.policy == parse_policy_set(calls[0]).policies[0]


def test_source_loader_registry_and_envelope_validation_are_separate():
    item = load_policy_envelope(FIXTURE)
    sources = load_source_registry(DATA / "sources.json")
    before = (item.to_dict(), sources.to_dict())
    assert validate_envelope_sources(item, sources) is None
    assert before == (item.to_dict(), sources.to_dict())


@pytest.mark.parametrize(("age", "region", "application_date", "status"), [
    (24, REGION, DAY, "PASS"), (18, REGION, DAY, "FAIL"),
    (24, RegionRef("GYEONGGI", "SUWON"), DAY, "FAIL"),
    (24, None, DAY, "UNKNOWN"), (24, REGION, None, "UNKNOWN"),
])
def test_end_to_end_loaded_vs_hand_built_and_existing_m11_parser_results(age, region, application_date, status):
    item = load_policy_envelope(FIXTURE)
    validate_envelope_sources(item, load_source_registry(DATA / "sources.json"))
    data = raw()
    legacy_loaded = parse_policy_set({
        "schema_version": "m1.1", "dataset_version": data["dataset_version"],
        "synthetic": True, "test_only": True, "policies": [data["policy"]],
    }).policies[0]
    facts = EvaluationFacts(()) if region is None else EvaluationFacts((ResidentRegistrationFact(region, DAY, RegistrationSource.SELF_REPORTED),))
    context = EvaluationContext(DAY, item.dataset_version)
    reference = PolicyReferenceContext(item.policy_id, application_date)
    results = [evaluate_policy_tree(UserProfile(age=age), candidate, context, facts=facts, reference_context=reference)
               for candidate in (item.policy, hand_built().policy, legacy_loaded)]
    assert results[0] == results[1] == results[2]
    assert results[0].to_dict() == results[1].to_dict() == results[2].to_dict()
    assert results[0].overall_status.value == status


@pytest.mark.parametrize("level", ["jurisdiction", "coverage", "binding"])
@pytest.mark.parametrize("value", [None, [], "object", True])
def test_nested_metadata_requires_json_objects(level, value):
    data = raw()
    if level == "binding":
        data["source_bindings"][0] = value
    else:
        data[level] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_OBJECT"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("field", ["included_rule_ids", "excluded_conditions"])
@pytest.mark.parametrize("value", [None, (), "array", {}])
def test_coverage_array_conversion_is_explicit_and_strict(field, value):
    data = raw()
    data["coverage"][field] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_ARRAY"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("region", [{"sido": "SEOUL"}, {"sido": "SEOUL", "sigungu": None}, {"sido": "서울", "sigungu": "종로"}])
def test_invalid_jurisdiction_uses_data_error_without_alias_correction(region):
    data = raw()
    data["jurisdiction"] = region
    with pytest.raises(PolicyDataError):
        parse_policy_envelope(data)


def test_deterministic_parsing_preserves_input_order_and_creates_immutable_snapshot():
    data = raw()
    data["policy"]["root"]["children"].reverse()
    before = deepcopy(data)
    result = parse_policy_envelope(data)
    assert data == before
    assert result == parse_policy_envelope(data)
    assert result.policy.root.children[0].rule_id == "SYNTH-RESIDENT"
    data["policy"]["root"]["children"].clear()
    data["source_bindings"].clear()
    assert len(result.policy.root.children) == 2
    assert result.source_document_ids == ("SYNTH-SOURCE-001",)


@pytest.mark.parametrize("value", [None, [], (), "object", 1, True])
def test_wrong_root_type(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_OBJECT"):
        parse_policy_envelope(value)


@pytest.mark.parametrize("field", ["schema_version", "rule_schema_version"])
@pytest.mark.parametrize("value", [None, "", 1, 1.0, False, [], "m1.0", "policy-data-2.0", " m1.1"])
def test_version_type_support_and_priority_over_payload(field, value):
    data = raw()
    data[field] = value
    data["policy"] = None
    with pytest.raises(EnvelopeValidationError) as caught:
        parse_policy_envelope(data)
    assert caught.value.field == field


@pytest.mark.parametrize("field", ["schema_version", "rule_schema_version"])
def test_missing_versions_not_inferred(field):
    data = raw()
    del data[field]
    with pytest.raises(EnvelopeValidationError) as caught:
        parse_policy_envelope(data)
    assert caught.value.field == field


@pytest.mark.parametrize("field", [key for key in raw() if key not in ("schema_version", "rule_schema_version", "effective_from", "effective_to")])
def test_every_required_outer_field_is_mandatory(field):
    data = raw()
    del data[field]
    with pytest.raises(EnvelopeValidationError, match="MISSING_ENVELOPE_FIELDS"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("field", ["last_verifed_at", "extra", "source_document_ids", "root", "rule_version", "policy_name"])
def test_no_unknown_or_duplicate_property_metadata_fields(field):
    data = raw()
    data[field] = None
    with pytest.raises(EnvelopeValidationError, match="UNKNOWN_ENVELOPE_FIELDS"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("level", ["jurisdiction", "coverage", "binding"])
def test_nested_metadata_extra_fields_rejected(level):
    data = raw()
    obj = data["source_bindings"][0] if level == "binding" else data[level]
    obj["extra"] = "never ignored"
    with pytest.raises(EnvelopeValidationError, match="UNKNOWN_ENVELOPE_FIELDS"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("value", [None, 123, True, [], {}])
def test_outer_policy_id_requires_exact_string(value):
    data = raw()
    data["policy_id"] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_ID"):
        parse_policy_envelope(data)


def test_outer_and_inner_policy_ids_must_match_without_overwrite():
    data = raw()
    data["policy_id"] = "SYNTH-POLICY-OTHER"
    before = deepcopy(data)
    with pytest.raises(EnvelopeValidationError, match="POLICY_ID_MISMATCH"):
        parse_policy_envelope(data)
    assert data == before


@pytest.mark.parametrize("value", ["", " ", "2026-Q1", "26", "２０２６", 2026, True, None])
def test_edition_granularity_remains_four_digit_year(value):
    data = raw()
    data["edition_id"] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_EDITION_ID"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("value", [None, "", "r0000", "r001", "r00001", "v1", 1])
def test_rule_version_validation_stays_in_existing_models(value):
    data = raw()
    data["policy"]["rule_version"] = value
    with pytest.raises(PolicyDataError):
        parse_policy_envelope(data)


@pytest.mark.parametrize("field", ["last_verified_at", "effective_from", "effective_to"])
@pytest.mark.parametrize("value", ["2026-02-30", "2026/01/01", "26-01-01", "20260101", "2026-W01-1", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00+09:00", 1767225600, True, date(2026, 1, 1), datetime(2026, 1, 1)])
def test_dates_have_only_strict_iso_boundary_conversion(field, value):
    data = raw()
    data[field] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_DATE"):
        parse_policy_envelope(data)


def test_optional_effective_dates_and_null_unknown_dates():
    data = raw()
    del data["effective_from"]
    del data["effective_to"]
    data["last_verified_at"] = None
    item = parse_policy_envelope(data)
    assert item.effective_from is None and item.effective_to is None
    assert item.last_verified_at is None


def test_effective_period_reverse_is_not_application_window_logic():
    data = raw()
    data.update(effective_from="2026-12-31", effective_to="2026-01-01")
    with pytest.raises(EnvelopeValidationError, match="INVALID_EFFECTIVE_PERIOD"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("field", ["category", "verification_status", "lifecycle_status", "evaluation_scope"])
@pytest.mark.parametrize("value", [None, "unknown", "draft", " ACTIVE", 1, True, VerificationStatus.DRAFT])
def test_enum_canonical_json_strings_only(field, value):
    data = raw()
    data[field] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_ENUM"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("status", ["DRAFT", "VERIFIED", "STALE"])
def test_verification_state_is_preserved_with_ancient_date_no_freshness(status):
    data = raw()
    data.update(verification_status=status, last_verified_at="2000-01-01", lifecycle_status="ENDED")
    item = parse_policy_envelope(data)
    assert item.verification_status.value == status
    assert item.last_verified_at == date(2000, 1, 1)
    assert item.lifecycle_status.value == "ENDED"


@pytest.mark.parametrize("field", ["synthetic", "test_only"])
@pytest.mark.parametrize("value", [None, 1, 0, "true", [], {}])
def test_outer_flags_are_exact_booleans(field, value):
    data = raw()
    data[field] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_FLAGS"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("field", ["synthetic", "test_only"])
def test_outer_false_and_inner_true_is_explicit_mismatch(field):
    data = raw()
    data[field] = False
    with pytest.raises(EnvelopeValidationError, match="POLICY_FLAGS_MISMATCH"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("flags", [(False, False), (False, True), (True, False), (1, True)])
def test_inner_non_synthetic_or_non_test_only_policy_remains_rejected(flags):
    data = raw()
    data["policy"]["synthetic"], data["policy"]["test_only"] = flags
    with pytest.raises(PolicyDataError):
        parse_policy_envelope(data)


@pytest.mark.parametrize("value", [None, [], "policy", 1, {}])
def test_malformed_embedded_policy_is_not_returned_as_partial_envelope(value):
    data = raw()
    data["policy"] = value
    with pytest.raises(PolicyDataError):
        parse_policy_envelope(data)


@pytest.mark.parametrize("change", ["missing-rule-type", "unknown-kind", "extra-policy-field", "extra-leaf-field", "m10-payload", "duplicate-rule-id", "empty-group"])
def test_embedded_policy_uses_existing_strict_m11_contract(change):
    data = raw()
    payload = data["policy"]
    children = payload["root"]["children"]
    if change == "missing-rule-type":
        del children[0]["rule_type"]
    elif change == "unknown-kind":
        children[0]["kind"] = "unknown"
    elif change == "extra-policy-field":
        payload["schema_version"] = "m1.0"
    elif change == "extra-leaf-field":
        children[0]["extra"] = "bad"
    elif change == "m10-payload":
        del children[0]["rule_type"]
        payload["root"] = children[0]
    elif change == "duplicate-rule-id":
        children[1]["rule_id"] = children[0]["rule_id"]
    else:
        payload["root"]["children"] = []
    with pytest.raises(PolicyDataError):
        parse_policy_envelope(data)


@pytest.mark.parametrize("value", [None, (), {}, "SYNTH-SOURCE-001"])
def test_source_bindings_require_explicit_json_array(value):
    data = raw()
    data["source_bindings"] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_ARRAY"):
        parse_policy_envelope(data)


def test_duplicate_source_id_and_evidence_outside_binding_fail_domain_validation():
    data = raw()
    data["source_bindings"].append(deepcopy(data["source_bindings"][0]))
    with pytest.raises(EnvelopeValidationError, match="DUPLICATE_SOURCE_BINDING"):
        parse_policy_envelope(data)
    data = raw()
    data["policy"]["root"]["children"][1]["evidence_refs"] = ["SYNTH-SOURCE-OTHER#eligibility-residence"]
    with pytest.raises(EnvelopeValidationError, match="SOURCE_BINDING_COVERAGE_MISMATCH"):
        parse_policy_envelope(data)


@pytest.mark.parametrize("case", ["missing-source", "missing-locator", "superseded", "withdrawn", "version-mismatch"])
def test_broken_registry_references_fail_only_explicit_cross_validation(case):
    data = source_raw()
    source = data["sources"][0]
    if case == "missing-source":
        source["source_document_id"] = "SYNTH-SOURCE-OTHER"
    elif case == "missing-locator":
        source["locators"] = source["locators"][:1]
    elif case in ("superseded", "withdrawn"):
        source["status"] = case.upper()
    else:
        source["document_version"] = "d0002"
    item = load_policy_envelope(FIXTURE)
    sources = parse_source_registry(data)
    with pytest.raises(PolicyDataError):
        validate_envelope_sources(item, sources)


@pytest.mark.parametrize("level", ["top", "policy", "region", "coverage", "binding", "group", "leaf"])
def test_duplicate_json_keys_detected_with_shared_source_hook(tmp_path, level):
    data = raw()
    target = {
        "top": data, "policy": data["policy"], "region": data["jurisdiction"], "coverage": data["coverage"],
        "binding": data["source_bindings"][0], "group": data["policy"]["root"],
        "leaf": data["policy"]["root"]["children"][0],
    }[level]
    target["DUPLICATE_TEST_KEY"] = 1
    text = json.dumps(data).replace('"DUPLICATE_TEST_KEY": 1', '"DUPLICATE_TEST_KEY": 1, "DUPLICATE_TEST_KEY": 2')
    with pytest.raises(EnvelopeValidationError, match="DUPLICATE_ENVELOPE_JSON_KEY"):
        load_policy_envelope(save(tmp_path, text))


@pytest.mark.parametrize("text", ["", "{", '{"schema_version":', '{"schema_version":"policy-data-1.0",}', "NaN", "Infinity", "-Infinity", "\ufeff{}"])
def test_malformed_nonstandard_bom_json_rejected(tmp_path, text):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_JSON"):
        load_policy_envelope(save(tmp_path, text))


def test_utf8_file_api_and_encoding_failure_are_distinct(tmp_path):
    path = save(tmp_path, json.dumps(raw(), ensure_ascii=False))
    assert load_policy_envelope(str(path)) == hand_built()
    path.write_bytes("합성".encode("cp949"))
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_ENCODING"):
        load_policy_envelope(path)


def test_missing_file_preserves_filesystem_cause(tmp_path):
    with pytest.raises(EnvelopeValidationError) as caught:
        load_policy_envelope(tmp_path / "absent.json")
    assert caught.value.code == "ENVELOPE_FILE_ERROR"
    assert isinstance(caught.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize("value", [None, [], "object", 1, False])
def test_json_file_wrong_root_type(tmp_path, value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_OBJECT"):
        load_policy_envelope(save(tmp_path, json.dumps(value)))


def test_invalid_metadata_does_not_return_just_embedded_policy():
    data = raw()
    data["coverage"]["included_rule_ids"] = ["MISSING-LEAF"]
    with pytest.raises(EnvelopeValidationError, match="COVERAGE_RULE_MISMATCH"):
        parse_policy_envelope(data)


def test_constructor_domain_snapshot_is_not_treated_as_input_schema():
    with pytest.raises(EnvelopeValidationError, match="MISSING_ENVELOPE_FIELDS"):
        parse_policy_envelope(hand_built().to_dict())


def test_pure_parser_has_no_file_or_network_access_and_needs_no_global_registry(monkeypatch):
    import builtins
    import socket
    import urllib.request

    data = raw()

    def unexpected(*args, **kwargs):
        pytest.fail("JSON 메모리 parser에서 I/O를 호출했습니다")

    monkeypatch.setattr(builtins, "open", unexpected)
    monkeypatch.setattr(Path, "open", unexpected)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    assert parse_policy_envelope(data) == hand_built()
