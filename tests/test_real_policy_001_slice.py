"""실제 공식 정책의 주민등록 leaf만 실행한다. 사용자 사실은 모두 가상이다."""

from copy import deepcopy
from dataclasses import fields, replace
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from backend.policy_engine import (
    EvaluationContext, EvaluationFacts, Policy, PolicyDataError, PolicyReferenceContext,
    PolicySet, ResidentRegistrationRule, Status, UserProfile, evaluate_policy_tree,
)
from backend.policy_engine.facts import (
    RegionRef, RegistrationSource, ResidentRegistrationFact, ResidentRegistrationValidationError,
)
from backend.policy_engine.loader import parse_policy_set
from backend.policy_engine.policy_data import (
    EnvelopeValidationError, EvaluationScope, PolicyVerificationStatus,
    load_policy_envelope, parse_policy_envelope, validate_envelope_sources,
)
from backend.policy_engine.resolvers.resident_registration import ResidentRegistrationReasonCode as RR
from backend.policy_engine.sources import (
    SourceValidationError, VerificationStatus, load_source_registry, parse_evidence_ref, parse_source_registry,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/releases/ansan-youth-2026-10-20-001"
POLICY_FILE = DATA / "policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json"
SOURCE_FILE = DATA / "sources.json"
POLICY_ID = "KR-GG-ANSAN-YOUTH-BASIC-INCOME"
RULE_ID = "ANSAN_YBI_2026_RESIDENT_AT_APPLICATION"
DAY = date(2026, 9, 15)
EVALUATION_DAY = date(2026, 10, 20)
ANSAN = RegionRef("GYEONGGI", "ANSAN")
SUWON = RegionRef("GYEONGGI", "SUWON")


def raw_policy():
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))


def raw_sources():
    return json.loads(SOURCE_FILE.read_text(encoding="utf-8"))


def fact(region=ANSAN, day=DAY):
    return ResidentRegistrationFact(region, day, RegistrationSource.SELF_REPORTED)


def loaded():
    envelope = load_policy_envelope(POLICY_FILE)
    registry = load_source_registry(SOURCE_FILE)
    validate_envelope_sources(envelope, registry)
    return envelope, registry


def run_leaf(facts=(), *, profile_region=None, application_day=DAY):
    envelope, registry = loaded()
    result = evaluate_policy_tree(
        UserProfile(region=profile_region), envelope.policy,
        EvaluationContext(EVALUATION_DAY, envelope.dataset_version),
        facts=EvaluationFacts(facts),
        reference_context=PolicyReferenceContext(envelope.policy_id, application_day),
    )
    assert len(result.rule_results) == 1
    leaf = result.rule_results[0]
    assert leaf.rule_id == RULE_ID
    assert leaf.evidence_refs == envelope.root.evidence_refs
    assert result.overall_status is leaf.status  # 단일 leaf 트리의 집계이며 전체 자격이 아니다.
    for ref in leaf.evidence_refs:
        source_id, locator = parse_evidence_ref(ref)
        assert registry.resolve(ref).locator_id == locator
        assert registry.get_source(source_id).official_url.startswith("https://www.ansan.go.kr/")
    return leaf


def test_actual_source_registry_and_envelope_strict_load_and_cross_validate():
    envelope, registry = loaded()
    assert envelope.policy_id == POLICY_ID
    assert envelope.edition_id == "2026" and envelope.rule_version == "r0001"
    assert type(envelope.root) is ResidentRegistrationRule
    assert envelope.root.required_region == ANSAN
    assert envelope.root.reference_date_source.value == "APPLICATION_DATE"
    assert envelope.synthetic is False and envelope.test_only is False
    assert envelope.policy.synthetic is False and envelope.policy.test_only is False
    assert len(registry.sources) == 3
    assert set(envelope.source_document_ids) == {source.source_document_id for source in registry.sources}
    assert all(source.document_version == "d0001" for source in registry.sources)
    notice = registry.get_source("ANSAN-2026-399-HWP")
    assert notice.notice_number == "안산시 공고 제2026-399호"
    assert notice.publication_date == date(2026, 2, 19)
    assert notice.content_sha256 == "b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106"
    assert registry.get_source("ANSAN-C0001545").publication_date is None
    assert registry.get_source("ANSAN-B0238-1681390").publication_date == date(2026, 8, 31)
    assert all(source.verified_at == EVALUATION_DAY for source in registry.sources)
    assert all(source.verification_status is VerificationStatus.VERIFIED for source in registry.sources)


@pytest.mark.parametrize(("facts", "region", "application_day", "status", "reason"), [
    ((fact(),), None, DAY, Status.PASS, RR.RESIDENT_REGION_MATCH),
    ((fact(SUWON),), None, DAY, Status.FAIL, RR.RESIDENT_REGION_MISMATCH),
    ((), None, DAY, Status.UNKNOWN, RR.RESIDENT_REGISTRATION_MISSING),
    ((), "ANSAN", DAY, Status.UNKNOWN, RR.RESIDENT_REGISTRATION_MISSING),
    ((fact(day=DAY - timedelta(days=1)),), None, DAY, Status.UNKNOWN, RR.RESIDENT_REGISTRATION_DATE_UNPROVEN),
    ((fact(day=EVALUATION_DAY + timedelta(days=1)),), None,
     EVALUATION_DAY + timedelta(days=1), Status.UNKNOWN, RR.RESIDENT_REFERENCE_DATE_IN_FUTURE),
], ids=["A-ansan-leaf-pass", "B-suwon-leaf-fail", "C-no-facts-unknown",
        "D-no-profile-fallback", "E-no-past-extrapolation", "G-future-unknown"])
def test_actual_resident_leaf_scenarios_and_evidence_trace(facts, region, application_day, status, reason):
    leaf = run_leaf(facts, profile_region=region, application_day=application_day)
    assert leaf.status is status and leaf.reason_code is reason
    assert leaf.details.reference_date == application_day
    if status in (Status.PASS, Status.FAIL):
        assert leaf.details.evidence[0].fact_as_of_date == DAY
        assert leaf.details.evidence[0].source is RegistrationSource.SELF_REPORTED


def test_F_actual_resident_leaf_conflicting_same_day_facts_are_data_error():
    with pytest.raises(ResidentRegistrationValidationError) as error:
        run_leaf((fact(), fact(SUWON)))
    assert error.value.code == "CONFLICTING_RESIDENT_REGISTRATION_FACTS"


def test_actual_resident_leaf_uses_existing_resolver_then_adapter(monkeypatch):
    from backend.policy_engine import routing

    calls = []
    resolver = routing.resolve_resident_registration
    adapter = routing.adapt_resident_registration_resolution

    def resolve(*args, **kwargs):
        calls.append("resolver")
        assert kwargs["reference_date"] == DAY
        assert kwargs["evaluation_date"] == EVALUATION_DAY
        return resolver(*args, **kwargs)

    def adapt(**kwargs):
        calls.append("adapter")
        assert kwargs["resolution"].status is Status.PASS
        return adapter(**kwargs)

    monkeypatch.setattr(routing, "resolve_resident_registration", resolve)
    monkeypatch.setattr(routing, "adapt_resident_registration_resolution", adapt)
    assert run_leaf((fact(),)).status is Status.PASS
    assert calls == ["resolver", "adapter"]


def test_actual_draft_condition_slice_does_not_claim_whole_policy_approval():
    envelope, _ = loaded()
    assert envelope.verification_status is PolicyVerificationStatus.DRAFT
    assert envelope.evaluation_scope is EvaluationScope.CONDITION_SLICE
    assert envelope.coverage.included_rule_ids == (RULE_ID,)
    assert len(envelope.coverage.excluded_conditions) == 6
    assert envelope.effective_from is None and envelope.effective_to is None
    assert envelope.last_verified_at == EVALUATION_DAY
    assert "allow_real_data" not in {field.name for field in fields(envelope.policy)}
    assert "allow_real_data" not in envelope.to_dict()["policy"]


@pytest.mark.parametrize("level", ["outer", "inner", "both"])
@pytest.mark.parametrize(("synthetic", "test_only"), [
    (True, False), (False, True), (1, False), (False, 0), (None, False), ("false", False),
])
def test_actual_envelope_rejects_invalid_or_mixed_flags(level, synthetic, test_only):
    data = raw_policy()
    targets = [data] if level == "outer" else [data["policy"]] if level == "inner" else [data, data["policy"]]
    for item in targets:
        item.update(synthetic=synthetic, test_only=test_only)
    with pytest.raises(PolicyDataError):
        parse_policy_envelope(data)


@pytest.mark.parametrize("outer_is_real", [True, False])
def test_actual_synthetic_outer_inner_mismatch_rejected(outer_is_real):
    data = raw_policy()
    target = data["policy"] if outer_is_real else data
    target.update(synthetic=True, test_only=True)
    with pytest.raises(EnvelopeValidationError, match="POLICY_FLAGS_MISMATCH"):
        parse_policy_envelope(data)


def test_real_policy_and_policy_set_require_explicit_opt_in_without_serialized_permission():
    envelope, _ = loaded()
    data = raw_policy()
    payload = dict(schema_version="m1.1", dataset_version=envelope.dataset_version,
                   synthetic=False, test_only=False, policies=[data["policy"]])
    with pytest.raises(PolicyDataError):
        parse_policy_set(payload)
    parsed = parse_policy_set(payload, allow_real_data=True)
    assert parsed.policies[0] == envelope.policy
    assert parsed.synthetic is False and parsed.test_only is False
    with pytest.raises(PolicyDataError):
        replace(envelope.policy)
    assert replace(envelope.policy, allow_real_data=True) == envelope.policy
    with pytest.raises(PolicyDataError):
        PolicySet("m1.1", envelope.dataset_version, (envelope.policy,))
    with pytest.raises(PolicyDataError):
        parse_policy_set(payload, allow_real_data=1)
    payload["policies"][0]["synthetic"] = True
    payload["policies"][0]["test_only"] = True
    with pytest.raises(PolicyDataError):
        parse_policy_set(payload, allow_real_data=True)


@pytest.mark.parametrize(("synthetic", "test_only"), [
    (True, True), (False, False), (True, False), (False, True), (1, True), (False, 0),
])
def test_explicit_domain_flag_pairs(synthetic, test_only):
    envelope, _ = loaded()
    kwargs = dict(policy_id=POLICY_ID, policy_name=envelope.policy_name, rule_version="r0001",
                  root=envelope.root, synthetic=synthetic, test_only=test_only, allow_real_data=True)
    if type(synthetic) is bool and type(test_only) is bool and synthetic is test_only:
        result = Policy(**kwargs)
        assert result.synthetic is synthetic and result.test_only is test_only
    else:
        with pytest.raises(PolicyDataError):
            Policy(**kwargs)


@pytest.mark.parametrize("actual_policy", [True, False])
def test_actual_and_synthetic_wrong_registry_is_rejected(actual_policy):
    actual, actual_sources = loaded()
    synthetic = load_policy_envelope(ROOT / "data/synthetic/policy_envelope_m11.json")
    synthetic_sources = load_source_registry(ROOT / "data/synthetic/sources.json")
    with pytest.raises(SourceValidationError, match="SOURCE_NOT_FOUND"):
        validate_envelope_sources(actual if actual_policy else synthetic,
                                  synthetic_sources if actual_policy else actual_sources)


@pytest.mark.parametrize("actual_policy", [True, False])
def test_rebinding_real_and_synthetic_evidence_still_rejects_wrong_policy_applicability(actual_policy):
    actual, actual_sources = loaded()
    synthetic = load_policy_envelope(ROOT / "data/synthetic/policy_envelope_m11.json")
    synthetic_sources = load_source_registry(ROOT / "data/synthetic/sources.json")
    target = actual if actual_policy else synthetic
    donor = synthetic if actual_policy else actual
    # 합성 root를 주민등록 leaf로 좁혀 참조/버전만 바꿔도 적용 정책 검증을 우회할 수 없음을 확인한다.
    root = donor.root.children[1] if actual_policy else donor.root
    new_policy = replace(target.policy, root=root, allow_real_data=not target.synthetic)
    rebound = replace(target, policy=new_policy, coverage=replace(target.coverage, included_rule_ids=(root.rule_id,)),
                      source_bindings=donor.source_bindings, last_verified_at=donor.last_verified_at)
    with pytest.raises(EnvelopeValidationError, match="POLICY_EVIDENCE_MISMATCH"):
        validate_envelope_sources(rebound, synthetic_sources if actual_policy else actual_sources)


@pytest.mark.parametrize(("change", "error"), [
    ("version", "SOURCE_VERSION_MISMATCH"), ("locator", "LOCATOR_NOT_FOUND"),
    ("lifecycle", "SOURCE_NOT_REFERENCEABLE"), ("policy", "POLICY_EVIDENCE_MISMATCH"),
])
def test_actual_source_cross_validation_rejects_broken_binding(change, error):
    envelope, _ = loaded()
    data = raw_sources()
    source = data["sources"][0]
    if change == "version":
        source["document_version"] = "d0002"
    elif change == "locator":
        source["locators"][0]["locator_id"] = "another-condition"
    elif change == "lifecycle":
        source["status"] = "WITHDRAWN"
    else:
        source["locators"][0]["applicable_policy_ids"] = ["SYNTH-POLICY-001"]
    with pytest.raises(PolicyDataError, match=error):
        validate_envelope_sources(envelope, parse_source_registry(data))


def test_actual_load_validate_and_evaluation_are_deterministic_and_do_not_mutate_inputs():
    data, sources = raw_policy(), raw_sources()
    before = deepcopy((data, sources))
    envelope, registry = parse_policy_envelope(data), parse_source_registry(sources)
    validate_envelope_sources(envelope, registry)
    first = run_leaf((fact(),)).to_dict()
    assert run_leaf((fact(),)).to_dict() == first
    assert (data, sources) == before
