"""실제 Q3 자료의 resident+birth 조건 일부를 가상 사용자 사실로 검증한다."""

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from backend.policy_engine import (
    BirthDateRule, BirthDateReasonCode as BR, ContextValidationError, EvaluationContext,
    EvaluationFacts, PolicyReferenceContext, ResidentRegistrationRule, RuleGroup,
    Status, UserProfile, evaluate_policy_tree,
)
from backend.policy_engine.facts import (
    BirthFact, BirthSource, RegionRef, RegistrationSource, ResidentRegistrationFact,
    ResidentRegistrationValidationError,
)
from backend.policy_engine.policy_data import (
    EnvelopeValidationError, load_policy_envelope, parse_policy_envelope, validate_envelope_sources,
)
from backend.policy_engine.resolvers.resident_registration import ResidentRegistrationReasonCode as RR
from backend.policy_engine.sources import (
    SourceValidationError, load_source_registry, parse_evidence_ref, parse_source_registry,
)


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'data/releases/ansan-youth-2026-10-20-001'
DATA = ROOT / 'data/releases/ansan-youth-2026-10-20-002'
NAME = 'policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json'
RID = 'ANSAN_YBI_2026_RESIDENT_AT_APPLICATION'
BID = 'ANSAN_YBI_2026_Q3_BIRTH_RANGE'
GID = 'ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE'
DAY, ASOF = date(2026, 9, 15), date(2026, 10, 20)
LOW, MID, HIGH = date(2001, 7, 2), date(2001, 12, 15), date(2002, 7, 1)
ANSAN, SUWON = RegionRef('GYEONGGI', 'ANSAN'), RegionRef('GYEONGGI', 'SUWON')
SOURCE_IDS = ('ANSAN-2026-399-HWP', 'ANSAN-C0001545', 'ANSAN-B0238-1681390')
BREFS = tuple(s + '#eligibility-birth-date-2026-q3' for s in SOURCE_IDS)


def raw():
    return json.loads((DATA / NAME).read_text(encoding='utf-8'))


def loaded():
    envelope = load_policy_envelope(DATA / NAME)
    registry = load_source_registry(DATA / 'sources.json')
    validate_envelope_sources(envelope, registry)
    return envelope, registry


def resident(status=Status.PASS, day=DAY):
    return () if status is Status.UNKNOWN else (
        ResidentRegistrationFact(ANSAN if status is Status.PASS else SUWON,
                                 day, RegistrationSource.SELF_REPORTED),)


def run(birth=None, *, rstatus=Status.PASS, age=None, application=DAY, asof=ASOF, rfacts=None):
    envelope, _ = loaded()
    return evaluate_policy_tree(UserProfile(age=age), envelope.policy,
        EvaluationContext(asof, envelope.dataset_version),
        facts=EvaluationFacts(resident(rstatus) if rfacts is None else rfacts, birth=birth),
        reference_context=PolicyReferenceContext(envelope.policy_id, application))


def test_new_actual_sources_envelope_structure_versions_flags_and_coverage():
    envelope, registry = loaded()
    assert envelope.dataset_version == DATA.name
    assert envelope.policy_id == 'KR-GG-ANSAN-YOUTH-BASIC-INCOME'
    assert envelope.edition_id == '2026' and envelope.rule_version == 'r0002'
    assert envelope.schema_version == 'policy-data-1.0' and envelope.rule_schema_version == 'm1.1'
    assert envelope.verification_status.value == 'DRAFT'
    assert envelope.evaluation_scope.value == 'CONDITION_SLICE'
    assert envelope.synthetic is False and envelope.test_only is False
    assert envelope.effective_from is None and envelope.effective_to is None
    assert '3분기' in envelope.policy_name and '일부' in envelope.policy_name
    assert type(envelope.root) is RuleGroup and envelope.root.operator.value == 'ALL'
    assert envelope.root.rule_id == GID
    assert tuple(type(n) for n in envelope.root.children) == (ResidentRegistrationRule, BirthDateRule)
    assert envelope.coverage.included_rule_ids == (RID, BID)
    assert len(envelope.coverage.excluded_conditions) == 7
    assert all(any(word in text for text in envelope.coverage.excluded_conditions) for word in
               ['Q1', 'Q2', 'Q4', '연속 3년', '합산 10년', '국적', '귀화', '신청기간', '자동신청', '소급신청', '서류', '계산'])
    assert envelope.source_document_ids == SOURCE_IDS
    assert all(b.document_version == 'd0002' for b in envelope.source_bindings)
    assert len(registry.sources) == 3
    assert all(s.document_version == 'd0002' and len(s.locators) == 2 for s in registry.sources)
    birth = envelope.root.children[1]
    assert (birth.min_birth_date, birth.max_birth_date, birth.evidence_refs) == (LOW, HIGH, BREFS)
    old = load_policy_envelope(OLD / NAME)
    assert envelope.root.children[0] == old.root
    old_registry = load_source_registry(OLD / 'sources.json')
    for source in registry.sources:
        assert source.locators[0] == old_registry.get_source(source.source_document_id).locators[0]
        assert source.official_url == old_registry.get_source(source.source_document_id).official_url


@pytest.mark.parametrize(('birthday', 'status', 'reason'), [
    (LOW-timedelta(days=1), Status.FAIL, BR.BIRTH_DATE_BEFORE_RANGE),
    (LOW, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (MID, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (HIGH, Status.PASS, BR.BIRTH_DATE_WITHIN_RANGE),
    (HIGH+timedelta(days=1), Status.FAIL, BR.BIRTH_DATE_AFTER_RANGE),
])
def test_actual_implemented_slice_birth_boundaries(birthday, status, reason):
    result = run(BirthFact(birthday, BirthSource.SELF_REPORTED))
    assert result.overall_status is status
    group, resident_result, birth = result.rule_results
    assert group.status is status and resident_result.status is Status.PASS
    assert birth.status is status and birth.reason_code is reason
    assert birth.evaluated_value == birthday and birth.evidence_refs == BREFS


@pytest.mark.parametrize('source', [None, *BirthSource])
def test_birth_missing_preserves_provenance_and_returns_slice_unknown(source):
    result = run(None if source is None else BirthFact(None, source))
    birth = result.rule_results[2]
    assert result.overall_status is birth.status is Status.UNKNOWN
    assert birth.reason_code is BR.BIRTH_DATE_MISSING
    assert birth.details.birth_source is source
    assert result.missing_fields == ('birth.birth_date',)
    assert birth.evidence_refs == BREFS


@pytest.mark.parametrize('rs', list(Status))
@pytest.mark.parametrize('bs', list(Status))
def test_actual_resident_birth_all_nine_status_combinations(rs, bs):
    fact = {Status.PASS: BirthFact(MID, BirthSource.SELF_REPORTED),
            Status.FAIL: BirthFact(LOW-timedelta(days=1), BirthSource.SELF_REPORTED),
            Status.UNKNOWN: None}[bs]
    expected = Status.FAIL if Status.FAIL in (rs, bs) else (
        Status.PASS if rs is bs is Status.PASS else Status.UNKNOWN)
    result = run(fact, rstatus=rs)
    assert result.overall_status is expected
    assert tuple(r.status for r in result.rule_results[1:]) == (rs, bs)
    assert ('birth.birth_date' in result.missing_fields) == (bs is Status.UNKNOWN)
    assert ('resident_registration' in result.missing_fields) == (rs is Status.UNKNOWN)


@pytest.mark.parametrize('age', [None, 23, 24, 25])
def test_actual_birth_has_no_profile_age_dependency(age):
    assert run(BirthFact(MID, BirthSource.SELF_REPORTED), age=age).overall_status is Status.PASS
    assert run(age=age).overall_status is Status.UNKNOWN


@pytest.mark.parametrize('offset', [-1, 1])
def test_actual_resident_exact_date_is_not_relaxed_by_birth(offset):
    result = run(BirthFact(MID, BirthSource.SELF_REPORTED), rfacts=resident(day=DAY+timedelta(days=offset)))
    assert result.overall_status is Status.UNKNOWN
    assert result.rule_results[1].reason_code is RR.RESIDENT_REGISTRATION_DATE_UNPROVEN
    assert result.rule_results[2].status is Status.PASS


@pytest.mark.parametrize('application', [date(2026, 1, 10), date(2026, 11, 10)])
def test_explicit_q3_release_does_not_select_quarter_from_dates(application):
    result = run(BirthFact(LOW, BirthSource.SELF_REPORTED), application=application,
                 asof=date(2026, 12, 1), rfacts=resident(day=application))
    assert result.overall_status is Status.PASS
    assert result.rule_results[2].expected_condition.min_birth_date == LOW


@pytest.mark.parametrize('node_index', [0, 1])
def test_actual_leaf_evidence_traces_to_official_location(node_index):
    envelope, registry = loaded()
    result = run(BirthFact(MID, BirthSource.SELF_REPORTED))
    leaf = result.rule_results[node_index+1]
    assert leaf.evidence_refs == envelope.root.children[node_index].evidence_refs
    for ref in leaf.evidence_refs:
        source_id, locator = parse_evidence_ref(ref)
        document = registry.get_source(source_id)
        evidence = registry.resolve(ref)
        assert evidence.locator_id == locator and evidence.section
        assert envelope.policy_id in evidence.applicable_policy_ids
        assert document.official_url.startswith('https://www.ansan.go.kr/')
        assert document.document_version == 'd0002'
        assert evidence.verification_status.value == 'VERIFIED'
        assert evidence.status.value == 'ACTIVE'
        assert evidence.verified_at == envelope.last_verified_at == ASOF
        if node_index == 1:
            assert '3분기' in evidence.section or '3분기' in (evidence.table_position or '')


def test_broken_birth_locator_is_source_error_not_unknown():
    data = raw()
    data['policy']['root']['children'][1]['evidence_refs'][0] = SOURCE_IDS[0]+'#missing-birth'
    with pytest.raises(SourceValidationError) as error:
        validate_envelope_sources(parse_policy_envelope(data), loaded()[1])
    assert error.value.code == 'LOCATOR_NOT_FOUND'


@pytest.mark.parametrize('kind', ['version', 'coverage', 'binding', 'applies', 'lifecycle', 'date'])
def test_actual_metadata_and_reference_integrity_failures(kind):
    data = raw()
    sources = json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
    if kind == 'version':data['source_bindings'][0]['document_version']='d0001'
    if kind == 'coverage':data['coverage']['included_rule_ids']=[RID]
    if kind == 'binding':data['source_bindings'].pop()
    if kind == 'applies':sources['sources'][0]['locators'][1]['applicable_policy_ids']=['OTHER-POLICY']
    if kind == 'lifecycle':sources['sources'][0]['locators'][1]['status']='WITHDRAWN'
    if kind == 'date':data['last_verified_at']='2026-10-19'
    with pytest.raises((SourceValidationError, EnvelopeValidationError)):
        validate_envelope_sources(parse_policy_envelope(data), parse_source_registry(sources))


def test_actual_and_synthetic_registry_swap_is_rejected():
    envelope, _ = loaded()
    with pytest.raises(SourceValidationError) as error:
        validate_envelope_sources(envelope, load_source_registry(ROOT/'data/synthetic/sources.json'))
    assert error.value.code == 'SOURCE_NOT_FOUND'


def test_synthetic_birth_ref_in_actual_envelope_is_policy_evidence_mismatch():
    data = raw()
    data['policy']['root']['children'][1]['evidence_refs']=['SYNTH-SOURCE-001#eligibility-residence']
    data['source_bindings'].append({'source_document_id':'SYNTH-SOURCE-001','document_version':'d0001'})
    sources = json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
    sources['sources'] += json.loads((ROOT/'data/synthetic/sources.json').read_text(encoding='utf-8'))['sources']
    with pytest.raises(EnvelopeValidationError) as error:
        validate_envelope_sources(parse_policy_envelope(data), parse_source_registry(sources))
    assert error.value.code == 'POLICY_EVIDENCE_MISMATCH'


@pytest.mark.parametrize('flags', [(True, False), (False, True)])
def test_actual_mixed_flags_are_rejected(flags):
    data=raw()
    data['synthetic'],data['test_only']=flags
    with pytest.raises(ValueError):parse_policy_envelope(data)


@pytest.mark.parametrize('birthday', [MID, LOW-timedelta(days=1), None])
def test_actual_result_serialization_is_deterministic_and_preserves_leaf_details(birthday):
    fact = BirthFact(birthday, BirthSource.SELF_REPORTED)
    first,second=run(fact),run(fact)
    assert first == second
    snapshot=first.to_dict()
    assert snapshot == second.to_dict()
    assert json.dumps(snapshot,sort_keys=True,ensure_ascii=False)==json.dumps(second.to_dict(),sort_keys=True,ensure_ascii=False)
    assert [r['rule_id'] for r in snapshot['rule_results']]==[GID,RID,BID]
    birth=snapshot['rule_results'][2]
    assert birth['evaluated_value']==(birthday.isoformat() if birthday else None)
    assert birth['expected_condition']=={'min_birth_date':LOW.isoformat(),'max_birth_date':HIGH.isoformat()}
    assert birth['details']=={'birth_source':'SELF_REPORTED'}
    assert birth['evidence_refs']==list(BREFS)
    assert birth['missing_fields']==([] if birthday else ['birth.birth_date'])
    snapshot['rule_results'].clear()
    assert len(first.to_dict()['rule_results'])==3


def test_resident_context_and_conflict_errors_are_not_hidden_by_birth():
    envelope,_=loaded()
    with pytest.raises(ContextValidationError):
        evaluate_policy_tree(UserProfile(),envelope.policy,EvaluationContext(ASOF,DATA.name))
    with pytest.raises(ResidentRegistrationValidationError):
        run(BirthFact(MID,BirthSource.SELF_REPORTED),rfacts=resident()+resident(Status.FAIL))


def test_old_release_still_reproduces_resident_only_without_birth():
    envelope=load_policy_envelope(OLD/NAME)
    validate_envelope_sources(envelope,load_source_registry(OLD/'sources.json'))
    result=evaluate_policy_tree(UserProfile(),envelope.policy,EvaluationContext(ASOF,OLD.name),
        facts=EvaluationFacts(resident()),reference_context=PolicyReferenceContext(envelope.policy_id,DAY))
    assert envelope.rule_version=='r0001' and type(envelope.root) is ResidentRegistrationRule
    assert result.overall_status is Status.PASS and len(result.rule_results)==1


@pytest.mark.parametrize(('relative','sha'), [
    ('README.md','4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f'),
    ('sources.json','a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b'),
    (NAME,'9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025'),
])
def test_old_resident_release_bytes_remain_immutable(relative,sha):
    assert hashlib.sha256((OLD/relative).read_bytes()).hexdigest()==sha


@pytest.mark.parametrize(('name','sha'), [
    ("policies_m11_birth.json", "2ad1757b3c2f5897a1d74d0477a2c19492111c09f2f93fcd674abe83276ccf01"),
    ("policies_m11.json", "121287d4b4c7c9a12205318e2ad12e7fb6c2d5d8eddd8625a82c265c1248ef0f"),
    ("policies.json", "59ea3f0ea1033ab84e6ce506f4479019ed23e5de752c6c18d1c05b351ded73ef"),
    ("policy_envelope_m11.json", "ada139c90f41932eaad625a04bf7f9ac46ccc8f7633511807fb83b2fabfed2a5"),
    ("profile.json", "46aca31d8c0d5443d99fbc5451be8780f4fc8299fc78f88c24d28bd17ae3916f"),
    ("README.md", "8f17baa6482dc3962ed1e3ad582d671d0297fa9b30a927e7123359b374a0cd77"),
    ("SOURCES_README.md", "6e5c4d9830aea8854f3b957a0221e7cfe41ee972394934650988dbffdf30406b"),
    ("sources.json", "0c77e2604c5ead6d80dd9fa6d8a681543b784d7c7b32e3eef747e74c6927f84e"),
])
def test_existing_synthetic_fixture_bytes_remain_immutable(name,sha):
    assert hashlib.sha256((ROOT/'data/synthetic'/name).read_bytes()).hexdigest()==sha
