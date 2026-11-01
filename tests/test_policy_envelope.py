"""합성/test_only Policy·근거로 edition 모델을 검증한다. 실제 정책 자료는 없다."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timezone
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
from backend.policy_engine.policy_data import (
    EnvelopeValidationError, EvaluationScope, PolicyCategory, PolicyCoverage, PolicyEnvelope,
    PolicyLifecycleStatus, PolicyVerificationStatus, SourceBinding, validate_envelope_sources,
)
from backend.policy_engine.result_types import ReferenceDateSource
from backend.policy_engine.sources import (
    SourceDocument, SourceEvidence, SourceRegistry, SourceStatus, SourceType,
    SourceValidationError, VerificationStatus, load_source_registry,
)
from backend.policy_engine.specialized_rules import ResidentRegistrationRule


DAY = date(2026, 1, 10)
REF = "SYNTH-SOURCE-001#eligibility-residence"
ATOM_REF = "SYNTH-SOURCE-001#application-period"
REGION = RegionRef("SEOUL", "JONGNO")


def policy(**changes):
    root = RuleGroup("SYNTH-ROOT", GroupOperator.ALL, (
        PolicyRule("SYNTH-ATOM", Field.AGE, Operator.GTE, 19, evidence_refs=(ATOM_REF,)),
        ResidentRegistrationRule("SYNTH-RESIDENT", REGION, ReferenceDateSource.APPLICATION_DATE, (REF,)),
    ))
    values = dict(policy_id="SYNTH-POLICY-001", policy_name="합성 test_only 정책",
                  rule_version="r0001", root=root, synthetic=True, test_only=True)
    return Policy(**(values | changes))


def envelope(**changes):
    values = dict(
        schema_version="policy-data-1.0", rule_schema_version="m1.1", policy=policy(),
        edition_id="2026", jurisdiction=REGION, category=PolicyCategory.YOUTH_SUPPORT,
        dataset_version="synthetic-edition-001", evaluation_scope=EvaluationScope.CONDITION_SLICE,
        coverage=PolicyCoverage(("SYNTH-ATOM", "SYNTH-RESIDENT"), ("합성 미구현 조건",)),
        source_bindings=(SourceBinding("SYNTH-SOURCE-001", "d0001"),),
        verification_status=PolicyVerificationStatus.DRAFT, last_verified_at=DAY,
        lifecycle_status=PolicyLifecycleStatus.ACTIVE,
    )
    return PolicyEnvelope(**(values | changes))


def evidence(locator_id="eligibility-residence", **changes):
    values = dict(locator_id=locator_id, section="합성 test_only 위치", meaning_summary="합성 조건의 근거",
                  applicable_policy_ids=("SYNTH-POLICY-001",), verified_at=DAY,
                  verification_status=VerificationStatus.VERIFIED, status=SourceStatus.ACTIVE)
    return SourceEvidence(**(values | changes))


def document(**changes):
    values = dict(source_document_id="SYNTH-SOURCE-001", document_version="d0001",
                  source_type=SourceType.OFFICIAL_NOTICE, issuer="SYNTHETIC_AUTHORITY_TEST_ONLY",
                  title="Synthetic test_only notice", official_url="https://policy.example.invalid/synthetic/1",
                  publication_date=None, verified_at=DAY, verification_status=VerificationStatus.VERIFIED,
                  status=SourceStatus.ACTIVE, locators=(evidence(), evidence("application-period")))
    return SourceDocument(**(values | changes))


def registry(**changes):
    return SourceRegistry((document(**changes),))


def test_valid_envelope_wraps_identical_policy_without_duplicate_metadata():
    original = policy()
    item = envelope(policy=original)
    assert item.policy is original
    assert item.root is original.root
    assert item.policy_id == original.policy_id
    assert item.policy_name == original.policy_name
    assert item.rule_version == original.rule_version
    assert item.synthetic is True and item.test_only is True
    assert item.source_document_ids == ("SYNTH-SOURCE-001",)
    assert validate_envelope_sources(item, registry()) is None
    names = {field.name for field in fields(item)}
    assert not names.intersection({"policy_id", "policy_name", "rule_version", "root", "synthetic", "test_only", "source_document_ids"})


@pytest.mark.parametrize("key", ["policy_id", "rule_version", "synthetic", "test_only", "source_document_ids"])
def test_duplicate_identity_metadata_cannot_be_supplied_or_mismatched(key):
    with pytest.raises(TypeError):
        envelope(**{key: "MISMATCH"})


def test_policy_identity_survives_edition_and_display_name_changes():
    first = envelope()
    next_year = replace(first, edition_id="2027", policy=replace(first.policy, policy_name="합성 변경 명칭", rule_version="r0002"))
    assert first.policy_id == next_year.policy_id
    assert first.edition_id != next_year.edition_id
    assert first.rule_version != next_year.rule_version


@pytest.mark.parametrize("value", [None, "", " ", 1, True, "SYNTH_POLICY_001", "synth-policy-001", " SYNTH-POLICY-001"])
def test_canonical_policy_id_contract_does_not_change_legacy_policy(value):
    with pytest.raises(PolicyDataError):
        envelope(policy=policy(policy_id=value))


@pytest.mark.parametrize("value", [None, "", " ", 2026, True, "2026 ", "26", "２０２６", "SYNTH-POLICY-001-EDITION-A"])
def test_edition_is_exact_four_digit_year_string(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_EDITION_ID"):
        envelope(edition_id=value)


@pytest.mark.parametrize(("field", "value"), [
    ("schema_version", None), ("schema_version", 1.0), ("schema_version", "m1.1"),
    ("schema_version", "policy-data-2.0"), ("schema_version", "policy-data-1.0 "),
    ("rule_schema_version", "m1.0"), ("rule_schema_version", None), ("rule_schema_version", True),
])
def test_supported_versions_are_explicit_without_fallback(field, value):
    with pytest.raises(EnvelopeValidationError):
        envelope(**{field: value})


@pytest.mark.parametrize("value", [None, "", "v1", "r0000", "r001", "r00001", "R0001", "r0001 ", 1, True])
def test_rule_version_naming_contract(value):
    with pytest.raises(PolicyDataError):
        envelope(policy=policy(rule_version=value))


@pytest.mark.parametrize("value", ["r0001", "r9999", "r10000"])
def test_valid_rule_versions_remain_on_policy(value):
    assert envelope(policy=policy(rule_version=value)).rule_version == value


@pytest.mark.parametrize("value", [None, "", " ", 1, True, []])
def test_dataset_version_is_retained_as_required_by_m19(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_DATASET_VERSION"):
        envelope(dataset_version=value)


@pytest.mark.parametrize("value", [None, "policy", {}, (), 1])
def test_envelope_requires_existing_policy_type(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_POLICY"):
        envelope(policy=value)


@pytest.mark.parametrize("value", [None, "SEOUL/JONGNO", {}, ("SEOUL", "JONGNO")])
def test_jurisdiction_requires_existing_complete_region_value(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_JURISDICTION"):
        envelope(jurisdiction=value)


@pytest.mark.parametrize(("field", "value"), [
    ("category", None), ("category", "YOUTH_SUPPORT"), ("evaluation_scope", "CONDITION_SLICE"),
    ("evaluation_scope", "FULL_POLICY"), ("verification_status", "DRAFT"),
    ("verification_status", VerificationStatus.VERIFIED),
    ("lifecycle_status", "ACTIVE"), ("lifecycle_status", SourceStatus.ACTIVE),
])
def test_enums_are_exact_and_policy_source_status_types_are_separate(field, value):
    with pytest.raises(EnvelopeValidationError):
        envelope(**{field: value})


@pytest.mark.parametrize("status", list(PolicyVerificationStatus))
def test_all_policy_verification_states_are_domain_valid_without_acceptance(status):
    item = envelope(verification_status=status)
    assert item.verification_status is status
    assert validate_envelope_sources(item, registry()) is None


def test_draft_or_stale_may_have_unknown_confirmation_but_verified_requires_date():
    for status in (PolicyVerificationStatus.DRAFT, PolicyVerificationStatus.STALE):
        assert envelope(verification_status=status, last_verified_at=None).last_verified_at is None
    with pytest.raises(EnvelopeValidationError, match="VERIFIED_DATE_REQUIRED"):
        envelope(verification_status=PolicyVerificationStatus.VERIFIED, last_verified_at=None)


@pytest.mark.parametrize("field", ["last_verified_at", "effective_from", "effective_to"])
@pytest.mark.parametrize("value", ["2026-01-10", 20260110, False, datetime(2026, 1, 10), datetime(2026, 1, 10, tzinfo=timezone.utc)])
def test_exact_date_types_no_datetime_truncation(field, value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_DATE"):
        envelope(**{field: value})


@pytest.mark.parametrize(("start", "end"), [(None, None), (DAY, None), (None, DAY), (DAY, DAY), (date(2025, 1, 1), DAY)])
def test_optional_effective_period_and_equal_boundaries(start, end):
    item = envelope(effective_from=start, effective_to=end)
    assert (item.effective_from, item.effective_to) == (start, end)
    assert validate_envelope_sources(item, registry()) is None


def test_reversed_effective_period_is_data_error():
    with pytest.raises(EnvelopeValidationError, match="INVALID_EFFECTIVE_PERIOD"):
        envelope(effective_from=DAY, effective_to=date(2025, 1, 1))


@pytest.mark.parametrize(("synthetic", "test_only"), [(True, False), (False, True), (False, False), (1, True), (True, 1), (None, True)])
def test_legacy_policy_rejects_non_test_only_combinations_before_wrapping(synthetic, test_only):
    with pytest.raises(PolicyDataError):
        envelope(policy=policy(synthetic=synthetic, test_only=test_only))


@pytest.mark.parametrize("values", [None, (), [], ("SYNTH-SOURCE-001",), ({"source_document_id": "SYNTH-SOURCE-001"},)])
def test_source_bindings_require_nonempty_immutable_typed_tuple(values):
    with pytest.raises(EnvelopeValidationError, match="INVALID_SOURCE_BINDINGS"):
        envelope(source_bindings=values)


@pytest.mark.parametrize("value", [None, "", " ", 1, True, "SYNTH_SOURCE_001", "source"])
def test_source_binding_id_contract(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_ID"):
        SourceBinding(value, "d0001")


@pytest.mark.parametrize("value", [None, "", 1, "d0000", "d001", "d00001", "r0001"])
def test_source_binding_document_version_contract(value):
    with pytest.raises(EnvelopeValidationError, match="INVALID_ENVELOPE_VERSION"):
        SourceBinding("SYNTH-SOURCE-001", value)


@pytest.mark.parametrize("version", ["d0001", "d0002"])
def test_duplicate_source_ids_rejected_even_with_different_versions(version):
    with pytest.raises(EnvelopeValidationError, match="DUPLICATE_SOURCE_BINDING"):
        envelope(source_bindings=(SourceBinding("SYNTH-SOURCE-001", "d0001"), SourceBinding("SYNTH-SOURCE-001", version)))


@pytest.mark.parametrize("bindings", [
    (SourceBinding("SYNTH-SOURCE-002", "d0001"),),
    (SourceBinding("SYNTH-SOURCE-001", "d0001"), SourceBinding("SYNTH-SOURCE-002", "d0001")),
])
def test_source_binding_set_must_equal_all_leaf_source_ids(bindings):
    with pytest.raises(EnvelopeValidationError, match="SOURCE_BINDING_COVERAGE_MISMATCH"):
        envelope(source_bindings=bindings)


@pytest.mark.parametrize(("field", "value"), [
    ("included_rule_ids", None), ("included_rule_ids", ()), ("included_rule_ids", []),
    ("included_rule_ids", ("",)), ("included_rule_ids", (True,)),
    ("excluded_conditions", None), ("excluded_conditions", ()), ("excluded_conditions", ["condition"]),
    ("excluded_conditions", (" ",)), ("excluded_conditions", (False,)),
])
def test_coverage_requires_explicit_immutable_nonempty_values(field, value):
    args = dict(included_rule_ids=("SYNTH-ATOM", "SYNTH-RESIDENT"), excluded_conditions=("합성 미구현 조건",))
    args[field] = value
    with pytest.raises(EnvelopeValidationError, match="INVALID_POLICY_COVERAGE"):
        PolicyCoverage(**args)


def test_duplicate_coverage_ids_rejected():
    with pytest.raises(EnvelopeValidationError, match="DUPLICATE_COVERAGE_RULE"):
        PolicyCoverage(("SYNTH-ATOM", "SYNTH-ATOM"), ("합성 제외 조건",))


@pytest.mark.parametrize("ids", [("SYNTH-ATOM",), ("SYNTH-ATOM", "SYNTH-RESIDENT", "SYNTH-ROOT"), ("UNKNOWN",)])
def test_coverage_must_match_leaves_not_groups(ids):
    with pytest.raises(EnvelopeValidationError, match="COVERAGE_RULE_MISMATCH"):
        envelope(coverage=PolicyCoverage(ids, ("합성 제외 조건",)))


def test_coverage_can_be_listed_in_different_order_without_changing_tree():
    item = envelope(coverage=PolicyCoverage(("SYNTH-RESIDENT", "SYNTH-ATOM"), ("합성 제외 조건",)))
    assert [child.rule_id for child in item.root.children] == ["SYNTH-ATOM", "SYNTH-RESIDENT"]


def test_existing_policy_keeps_responsibility_for_duplicate_rule_ids():
    atom = PolicyRule("DUP", Field.AGE, Operator.GTE, 19, evidence_refs=(REF,))
    with pytest.raises(PolicyDataError):
        policy(root=RuleGroup("ROOT", GroupOperator.ALL, (atom, atom)))


@pytest.mark.parametrize("ref", ["legacy:synthetic-ref", "#locator", "SYNTH-SOURCE-001#bad#ref"])
def test_envelope_ref_syntax_is_stricter_than_unchanged_legacy_policy(ref):
    atom = PolicyRule("SYNTH-ATOM", Field.AGE, Operator.GTE, 19, evidence_refs=(ref,))
    original = policy(root=atom)
    with pytest.raises(SourceValidationError):
        envelope(policy=original, coverage=PolicyCoverage((atom.rule_id,), ("합성 제외 조건",)))
    assert original.root.evidence_refs == (ref,)


def test_duplicate_refs_within_leaf_rejected_but_shared_between_leaves_allowed():
    atom = PolicyRule("SYNTH-ATOM", Field.AGE, Operator.GTE, 19, evidence_refs=(REF, REF))
    with pytest.raises(EnvelopeValidationError, match="DUPLICATE_LEAF_EVIDENCE"):
        envelope(policy=policy(root=atom), coverage=PolicyCoverage((atom.rule_id,), ("합성 제외 조건",)))
    original = policy()
    atom = replace(original.root.children[0], evidence_refs=(REF,))
    shared = envelope(policy=replace(original, root=replace(original.root, children=(atom, original.root.children[1]))))
    assert validate_envelope_sources(shared, registry()) is None


@pytest.mark.parametrize(("item", "sources", "code"), [
    (None, registry(), "INVALID_ENVELOPE"), (envelope(), None, "INVALID_ENVELOPE_REGISTRY"),
])
def test_cross_validator_requires_explicit_typed_arguments(item, sources, code):
    with pytest.raises(EnvelopeValidationError, match=code):
        validate_envelope_sources(item, sources)


def test_missing_source_and_locator_use_existing_registry_errors():
    with pytest.raises(SourceValidationError, match="SOURCE_NOT_FOUND"):
        validate_envelope_sources(envelope(), registry(source_document_id="SYNTH-SOURCE-999"))
    with pytest.raises(SourceValidationError, match="LOCATOR_NOT_FOUND"):
        validate_envelope_sources(envelope(), registry(locators=(evidence(),)))


def test_source_version_is_pinned_not_automatically_updated():
    with pytest.raises(EnvelopeValidationError, match="SOURCE_VERSION_MISMATCH"):
        validate_envelope_sources(envelope(), registry(document_version="d0002"))


def test_multiple_sources_are_pinned_and_minimum_date_uses_all_referenced_locators():
    older = date(2026, 1, 1)
    original = policy()
    atom = replace(original.root.children[0], evidence_refs=("SYNTH-SOURCE-002#eligibility-residence",))
    wrapped = envelope(
        policy=replace(original, root=replace(original.root, children=(atom, original.root.children[1]))),
        source_bindings=(SourceBinding("SYNTH-SOURCE-002", "d0002"), SourceBinding("SYNTH-SOURCE-001", "d0001")),
        last_verified_at=older,
    )
    sources = SourceRegistry((document(), document(source_document_id="SYNTH-SOURCE-002",
                             document_version="d0002", verified_at=older,
                             locators=(evidence(verified_at=older),))))
    assert validate_envelope_sources(wrapped, sources) is None
    assert wrapped.source_document_ids == ("SYNTH-SOURCE-002", "SYNTH-SOURCE-001")


def test_single_leaf_and_not_tree_use_leaf_coverage_and_existing_tree_validation():
    leaf = policy().root.children[0]
    coverage = PolicyCoverage((leaf.rule_id,), ("합성 미구현 조건",))
    assert envelope(policy=policy(root=leaf), coverage=coverage).root is leaf
    tree = RuleGroup("SYNTH-NOT", GroupOperator.NOT, (leaf,))
    wrapped = envelope(policy=policy(root=tree), coverage=coverage)
    assert validate_envelope_sources(wrapped, registry()) is None


def test_other_policy_evidence_is_rejected_even_when_ref_resolves():
    items = (evidence(applicable_policy_ids=("SYNTH-POLICY-OTHER",)), evidence("application-period"))
    sources = registry(locators=items)
    assert sources.resolve(REF) == items[0]
    with pytest.raises(EnvelopeValidationError, match="POLICY_EVIDENCE_MISMATCH"):
        validate_envelope_sources(envelope(), sources)


@pytest.mark.parametrize("target", ["source", "locator"])
@pytest.mark.parametrize("status", [SourceStatus.SUPERSEDED, SourceStatus.WITHDRAWN])
def test_lifecycle_reference_rejection_delegated_to_registry(target, status):
    sources = registry(status=status) if target == "source" else registry(locators=(evidence(status=status), evidence("application-period")))
    with pytest.raises(SourceValidationError, match="NOT_REFERENCEABLE"):
        validate_envelope_sources(envelope(), sources)


def test_last_verified_at_is_oldest_used_locator_not_newest_document_date():
    older = date(2026, 1, 1)
    sources = registry(locators=(evidence(verified_at=older), evidence("application-period")))
    assert validate_envelope_sources(envelope(last_verified_at=older), sources) is None
    with pytest.raises(EnvelopeValidationError, match="LAST_VERIFIED_DATE_MISMATCH"):
        validate_envelope_sources(envelope(), sources)


def test_unknown_locator_date_propagates_to_unknown_policy_confirmation():
    sources = registry(locators=(evidence(verified_at=None, verification_status=VerificationStatus.DRAFT), evidence("application-period")))
    assert validate_envelope_sources(envelope(last_verified_at=None), sources) is None
    with pytest.raises(EnvelopeValidationError, match="LAST_VERIFIED_DATE_MISMATCH"):
        validate_envelope_sources(envelope(), sources)


def test_extra_unused_registry_documents_and_locators_do_not_change_derived_date():
    sources = SourceRegistry((document(locators=(evidence(), evidence("application-period"),
                                               evidence("unused", verified_at=None, verification_status=VerificationStatus.DRAFT))),
                              document(source_document_id="SYNTH-SOURCE-OTHER", verification_status=VerificationStatus.STALE)))
    assert validate_envelope_sources(envelope(), sources) is None


@pytest.mark.parametrize("day", [date(2000, 1, 1), date(2099, 1, 1)])
@pytest.mark.parametrize("status", list(PolicyVerificationStatus))
def test_no_clock_freshness_or_operational_status_changes(day, status):
    items = (evidence(verified_at=day, verification_status=VerificationStatus.STALE),
             evidence("application-period", verified_at=day))
    sources = registry(verified_at=day, verification_status=VerificationStatus.STALE, locators=items)
    item = envelope(last_verified_at=day, verification_status=status, lifecycle_status=PolicyLifecycleStatus.ENDED)
    assert validate_envelope_sources(item, sources) is None
    assert item.verification_status is status
    assert sources.sources[0].verification_status is VerificationStatus.STALE


def test_deep_immutability_equality_repr_and_serialization_snapshot():
    bindings = [SourceBinding("SYNTH-SOURCE-001", "d0001")]
    item = envelope(source_bindings=tuple(bindings))
    bindings.clear()
    assert item == envelope()
    assert hash(item) == hash(envelope())
    assert repr(item) == repr(envelope())
    for obj, name, value in [(item, "edition_id", "2027"), (item.policy, "policy_id", "OTHER"),
                              (item.coverage, "included_rule_ids", ()), (item.source_bindings[0], "document_version", "d0002")]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, name, value)
    with pytest.raises(AttributeError):
        item.source_bindings.append(SourceBinding("OTHER", "d0001"))
    result = item.to_dict()
    assert json.loads(json.dumps(result)) == result
    assert result["last_verified_at"] == "2026-01-10"
    assert result["policy"]["synthetic"] is True
    result["policy"]["root"]["children"].clear()
    result["source_bindings"].clear()
    result["coverage"]["included_rule_ids"].clear()
    assert item == envelope()


def test_loaded_synthetic_registry_integration_and_no_input_changes():
    sources = load_source_registry(Path(__file__).resolve().parents[1] / "data/synthetic/sources.json")
    item = envelope()
    before = (item.to_dict(), sources.to_dict())
    assert validate_envelope_sources(item, sources) is None
    assert before == (item.to_dict(), sources.to_dict())


@pytest.mark.parametrize(("age", "fact_region"), [(24, REGION), (18, REGION), (24, RegionRef("GYEONGGI", "SUWON")), (24, None)])
def test_wrapped_policy_evaluates_identically_without_envelope_semantic_changes(age, fact_region):
    original = policy()
    item = envelope(policy=original)
    context = EvaluationContext(DAY, item.dataset_version)
    facts = EvaluationFacts(()) if fact_region is None else EvaluationFacts((ResidentRegistrationFact(fact_region, DAY, RegistrationSource.SELF_REPORTED),))
    reference = PolicyReferenceContext(original.policy_id, DAY)
    before = evaluate_policy_tree(UserProfile(age=age), original, context, facts=facts, reference_context=reference)
    after = evaluate_policy_tree(UserProfile(age=age), item.policy, context, facts=facts, reference_context=reference)
    assert after == before
    assert after.to_dict() == before.to_dict()
    assert item.policy is original


def test_constructor_and_cross_validator_are_pure_without_global_registry(monkeypatch):
    import builtins
    import socket
    import urllib.request

    def unexpected(*args, **kwargs):
        pytest.fail("edition 도메인에서 I/O를 호출했습니다")

    monkeypatch.setattr(builtins, "open", unexpected)
    monkeypatch.setattr(Path, "open", unexpected)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected)
    item = envelope()
    assert validate_envelope_sources(item, registry()) is None
