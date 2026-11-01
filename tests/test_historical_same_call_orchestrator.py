"""M2.75: 실제 raw7 복원 경로와, 별도의 단위 spy/오류 전파 경계를 검증한다.

파일 취득·production ZIP·공식 원문/현재 사용 판정을 실행한 시험은 아니다.
"""

import ast
import builtins
from copy import deepcopy
from dataclasses import fields, FrozenInstanceError, replace
import inspect
import io
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import time
from typing import get_type_hints

import pytest

import test_historical_six_artifact_integration as synthetic
import test_historical_cross_artifact_validator as cross
from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, BenefitAcceptanceStatus, BenefitSnapshot, CoverageReviewContext,
    DatasetManifest, EligibilityCoverage, PolicyBenefitAcceptance, PolicyEnvelope,
)
from backend.policy_engine.policy_data import historical_artifact_orchestration as domain
from backend.policy_engine.sources import SourceRegistry


RAW_ARGUMENTS = dict(zip(synthetic.LOADERS, (
    'benefit_raw_bytes', 'coverage_raw_bytes', 'policy_envelope_raw_bytes',
    'coverage_reviews_raw_bytes', 'dataset_manifest_raw_bytes', 'source_registry_raw_bytes',
)))
ARGUMENTS = ('expected_acceptance', 'expected_acceptances', 'review_artifact_raw_bytes', *RAW_ARGUMENTS.values())
REVIEW = 'load_acceptance_review_artifact_bytes'
SELECT = '_selected_entry'
LOADER_NAMES = tuple(loader.__name__ for loader in synthetic.LOADERS.values())
CROSS = '_validate_historical_artifact_relationships'
STEPS = (REVIEW, SELECT, *LOADER_NAMES, CROSS)
DOMAIN_ARGUMENTS = ('benefit_snapshot', 'eligibility_coverage', 'policy_envelope',
                    'coverage_review_context', 'dataset_manifest', 'source_registry')
INPUT_PREFIX = 'INVALID_HISTORICAL_ORCHESTRATION_INPUT'
BINDING_PREFIX = 'HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH'


def inputs_from(*specs, selected=0, edit_review=None):
    """독립 합성 저작만 재사용한다. 반환 객체를 운영 입력으로 공급하지 않는다."""
    _, originals, raw_sets, review_raw = synthetic.prepare(*specs)
    kwargs = {'expected_acceptance': originals[selected], 'expected_acceptances': originals,
              'review_artifact_raw_bytes': review_raw,
              **{RAW_ARGUMENTS[name]: raw for name, raw in raw_sets[selected].items()}}
    if edit_review is not None:
        body = json.loads(review_raw)
        edit_review(body)
        kwargs = authored_review_bytes(kwargs, synthetic.canonical(body))
    return kwargs


def authored_review_bytes(kwargs, raw):
    """시험 저작에서 raw를 고정한 뒤 최종 expected 원본을 만든다. 소비 보정이 아니다."""
    selected = next(i for i, record in enumerate(kwargs['expected_acceptances'])
                    if record is kwargs['expected_acceptance'])
    root = 'acceptance-review:sha256:' + synthetic.sha(raw)
    originals = tuple(replace(record, review_artifact_ref=root) for record in kwargs['expected_acceptances'])
    return {**kwargs, 'expected_acceptance': originals[selected], 'expected_acceptances': originals,
            'review_artifact_raw_bytes': raw}


def authored_artifact_bytes(kwargs, name, raw):
    """matching SHA로 strict/domain 실패까지 도달시키는 합성 자료 저작이다."""
    body = json.loads(kwargs['review_artifact_raw_bytes'])
    entry = next(row for row in body['entries']
                 if row['acceptance']['acceptance_ref'] == kwargs['expected_acceptance'].acceptance_ref)
    entry[synthetic.REF_FIELDS[name]]['sha256'] = synthetic.sha(raw)
    values = {**kwargs, RAW_ARGUMENTS[name]: raw}
    if name == 'registry':
        # Registry 단계 전 Manifest의 path+SHA 직접 결합을 먼저 통과해야 한다.
        manifest = json.loads(values['dataset_manifest_raw_bytes'])
        manifest['manifest']['source_registry']['artifact'] = dict(entry['source_registry_ref'])
        manifest_raw = synthetic.canonical(manifest)
        values['dataset_manifest_raw_bytes'] = manifest_raw
        entry['dataset_manifest_ref']['sha256'] = synthetic.sha(manifest_raw)
    return authored_review_bytes(values, synthetic.canonical(body))


@pytest.fixture
def inputs():
    return inputs_from(synthetic.definitions())


def run(kwargs):
    return domain._orchestrate_historical_artifact_validation(**kwargs)


def observe(monkeypatch):
    """실제 함수의 순서·원본 인자·반환/발생 예외를 기록한다. 정상 반환은 대체하지 않는다."""
    calls, returned, raised = [], [], []
    for name in STEPS:
        real = getattr(domain, name)
        def observed(*args, _name=name, _real=real, **kwargs):
            calls.append((_name, args, kwargs))
            try:
                result = _real(*args, **kwargs)
            except Exception as exc:
                raised.append((_name, exc))
                raise
            returned.append((_name, result))
            return result
        monkeypatch.setattr(domain, name, observed)
    return calls, returned, raised


def assert_error(kwargs, prefix, field=None):
    with pytest.raises(PolicyDataError) as caught:
        run(kwargs)
    if field is None:
        assert str(caught.value).startswith(prefix + ':'), str(caught.value)
    else:
        assert str(caught.value) == f'{prefix}: {field}: 계약을 확인하세요'
    return caught.value


def assert_stop(calls, failed_step):
    assert [name for name, _, _ in calls] == list(STEPS[:STEPS.index(failed_step) + 1])


def test_hso01_02_56_exact_private_api_and_return_annotation():
    function = domain._orchestrate_historical_artifact_validation
    signature = inspect.signature(function)
    assert tuple(signature.parameters) == ARGUMENTS
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in signature.parameters.values())
    hints = get_type_hints(function)
    assert hints == {
        'expected_acceptance': PolicyBenefitAcceptance,
        'expected_acceptances': tuple[PolicyBenefitAcceptance, ...],
        **{name: bytes for name in ARGUMENTS[2:]},
        'return': tuple[AcceptanceReviewArtifact, tuple[
            BenefitSnapshot, EligibilityCoverage, PolicyEnvelope, CoverageReviewContext,
            DatasetManifest, SourceRegistry]],
    }
    assert not hasattr(policy_data, function.__name__)


def test_hso01_02_real_integration_original_arguments_results_and_full_order(inputs, monkeypatch):
    calls, returned, raised = observe(monkeypatch)
    result = run(inputs)
    assert type(result) is tuple and len(result) == 2
    artifact, objects = result
    assert type(objects) is tuple and len(objects) == 6
    assert tuple(type(value) for value in objects) == synthetic.TYPES
    assert [name for name, _, _ in calls] == list(STEPS)
    assert not raised
    outcomes = dict(returned)
    assert artifact is outcomes[REVIEW]
    assert calls[0][1] == ()
    assert calls[0][2]['raw_bytes'] is inputs['review_artifact_raw_bytes']
    assert calls[0][2]['expected_acceptances'] is inputs['expected_acceptances']
    assert calls[1][1][0] is artifact and calls[1][1][1] is inputs['expected_acceptance']
    assert outcomes[SELECT] is artifact.entries[0]
    assert artifact.entries[0].acceptance is inputs['expected_acceptance']
    for (name, argument), loader_name, value in zip(RAW_ARGUMENTS.items(), LOADER_NAMES, objects):
        call = next(row for row in calls if row[0] == loader_name)
        assert call[1] == () and tuple(call[2]) == ('raw_bytes', 'artifact', 'expected_acceptance')
        assert call[2]['raw_bytes'] is inputs[argument]
        assert call[2]['artifact'] is artifact and call[2]['expected_acceptance'] is inputs['expected_acceptance']
        assert value is outcomes[loader_name]
        assert synthetic.sha(inputs[argument]) == synthetic.SYNTHETIC_RAW_SHA256[name]
    cross_call = calls[-1][2]
    assert cross_call['artifact'] is artifact and cross_call['expected_acceptance'] is inputs['expected_acceptance']
    assert all(cross_call[name] is value for name, value in zip(DOMAIN_ARGUMENTS, objects))
    assert outcomes[CROSS] is None


def test_separate_unit_spies_fix_call_boundary_without_claiming_raw_validation(inputs, monkeypatch):
    # 정상 실제 로더 통합 시험과 구별되는 단위 연결 시험이다.
    artifact = synthetic.load_acceptance_review_artifact_bytes(
        raw_bytes=inputs['review_artifact_raw_bytes'], expected_acceptances=inputs['expected_acceptances'])
    raw_set = {name: inputs[arg] for name, arg in RAW_ARGUMENTS.items()}
    objects = tuple(synthetic.restore(artifact, inputs['expected_acceptance'], raw_set).values())
    values = (artifact, artifact.entries[0], *objects, None)
    calls = []
    for name, value in zip(STEPS, values):
        def spy(*args, _name=name, _value=value, **kwargs):
            calls.append((_name, args, kwargs))
            return _value
        monkeypatch.setattr(domain, name, spy)
    returned = run(inputs)
    assert [name for name, _, _ in calls] == list(STEPS)
    assert returned[0] is artifact and all(left is right for left, right in zip(returned[1], objects))
    for row, value in zip(calls[2:8], objects):
        assert row[2]['artifact'] is artifact and row[2]['expected_acceptance'] is inputs['expected_acceptance']
    assert all(calls[-1][2][name] is value for name, value in zip(DOMAIN_ARGUMENTS, objects))


@pytest.mark.parametrize('selected', (0, 1))
@pytest.mark.parametrize('reverse', (False, True))
def test_hso05_06_explicit_revision_and_whole_expected_tuple(selected, reverse, monkeypatch):
    kwargs = inputs_from(synthetic.definitions(), synthetic.definitions(2), selected=selected)
    originals = kwargs['expected_acceptances']
    if reverse:
        kwargs['expected_acceptances'] = originals[::-1]
    calls, _, _ = observe(monkeypatch)
    artifact, values = run(kwargs)
    assert calls[0][2]['expected_acceptances'] is kwargs['expected_acceptances']
    assert len(calls[0][2]['expected_acceptances']) == 2
    assert artifact.entries[selected].acceptance is originals[selected]
    assert all(entry.acceptance is original for entry, original in zip(artifact.entries, originals))
    assert values[0].dataset_version == f'SYNTH-D{selected + 1}'
    assert values[4].dataset_version == values[0].dataset_version
    assert_stop(calls, CROSS)


def test_hso03_04_44_56_one_hundred_calls_reexecute_and_preserve_inputs(inputs, monkeypatch):
    calls, returned, _ = observe(monkeypatch)
    original = inputs['expected_acceptance']
    records = inputs['expected_acceptances']
    raw_before = tuple((name, inputs[name], synthetic.sha(inputs[name])) for name in ARGUMENTS[2:])
    record_before = tuple(record.to_dict() for record in records)
    first = run(inputs)
    snapshot = first[0].to_dict(), tuple(obj.to_dict() for obj in first[1])
    previous = first
    for _ in range(100):
        current = run(inputs)
        assert current == first
        assert current[0] is not previous[0]
        assert all(left is not right for left, right in zip(current[1], previous[1]))
        assert current[0].entries[0].acceptance is original
        diagnostic = current[0].to_dict()
        diagnostic['entries'][0]['acceptance']['scope'].clear()
        assert current[0].to_dict() == snapshot[0]
        assert tuple(obj.to_dict() for obj in current[1]) == snapshot[1]
        previous = current
    assert [name for name, _, _ in calls] == list(STEPS) * 101
    assert inputs['expected_acceptance'] is original and inputs['expected_acceptances'] is records
    assert tuple(record.to_dict() for record in records) == record_before
    assert all(inputs[name] is raw and synthetic.sha(raw) == digest for name, raw, digest in raw_before)
    with pytest.raises(FrozenInstanceError):
        first[0].review_artifact_ref = 'changed'
    with pytest.raises(TypeError):
        first[1][0] = None
    assert first[0].to_dict() == snapshot[0]
    assert sum(name == CROSS for name, _ in returned) == 101


def test_hso44_second_valid_different_bytes_use_second_revision(monkeypatch):
    first_inputs = inputs_from(synthetic.definitions())
    second_inputs = inputs_from(synthetic.definitions(2))
    calls, _, _ = observe(monkeypatch)
    first, second = run(first_inputs), run(second_inputs)
    assert [name for name, _, _ in calls] == list(STEPS) * 2
    assert first[0] is not second[0]
    assert first[1][0].dataset_version == 'SYNTH-D1' and second[1][0].dataset_version == 'SYNTH-D2'
    assert first[1][0].amount_krw == 100000 and second[1][0].amount_krw == 200000
    assert all(left is not right for left, right in zip(first[1], second[1]))
    assert second[0].entries[0].acceptance is second_inputs['expected_acceptance']


@pytest.mark.parametrize('missing', ARGUMENTS)
def test_hso22_missing_argument_is_native_typeerror_before_body(inputs, monkeypatch, missing):
    calls, _, _ = observe(monkeypatch)
    del inputs[missing]
    with pytest.raises(TypeError):
        run(inputs)
    assert not calls


@pytest.mark.parametrize('option', ('artifact', 'preloaded_objects', 'previous_result', 'skip_validation',
    'trust_preloaded_objects', 'allow_partial', 'ignore_mismatch', 'force_verified', 'force_usable',
    'use_latest', 'fallback_revision', 'expected_sha256', 'loader'))
def test_hso22_43_57_no_bypass_options(inputs, monkeypatch, option):
    calls, _, _ = observe(monkeypatch)
    with pytest.raises(TypeError):
        run({**inputs, option: None})
    assert not calls


def test_no_positional_arguments(inputs, monkeypatch):
    calls, _, _ = observe(monkeypatch)
    with pytest.raises(TypeError):
        domain._orchestrate_historical_artifact_validation(*inputs.values())
    assert not calls


@pytest.mark.parametrize('kind', ('none', 'dict', 'string', 'bool', 'subclass'))
def test_hso09_wrong_exact_acceptance_type(inputs, monkeypatch, kind):
    class Child(PolicyBenefitAcceptance):
        pass
    child = Child(**{field.name: getattr(inputs['expected_acceptance'], field.name)
                     for field in fields(PolicyBenefitAcceptance)})
    bad = {'none': None, 'dict': {}, 'string': 'ACCEPTED', 'bool': True, 'subclass': child}[kind]
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, 'expected_acceptance': bad}, INPUT_PREFIX, 'expected_acceptance')
    assert not calls


@pytest.mark.parametrize('kind', ('none', 'list', 'empty', 'dict_record', 'subclass_tuple', 'subclass_record'))
def test_hso11_expected_tuple_uses_original_review_loader_contract(inputs, monkeypatch, kind):
    class Records(tuple):
        pass
    class Child(PolicyBenefitAcceptance):
        pass
    child = Child(**{field.name: getattr(inputs['expected_acceptance'], field.name)
                     for field in fields(PolicyBenefitAcceptance)})
    bad = {'none': None, 'list': list(inputs['expected_acceptances']), 'empty': (), 'dict_record': ({},),
           'subclass_tuple': Records(inputs['expected_acceptances']), 'subclass_record': (child,)}[kind]
    calls, _, _ = observe(monkeypatch)
    exc = assert_error({**inputs, 'expected_acceptances': bad}, 'INVALID_REVIEW_ARTIFACT_LOADER_INPUT')
    assert_stop(calls, REVIEW)
    assert 'expected_acceptances' in str(exc)


@pytest.mark.parametrize('kind', ('none', 'str', 'bytearray', 'memoryview', 'subclass', 'domain'))
def test_hso10_review_requires_exact_bytes(inputs, monkeypatch, kind):
    class Raw(bytes):
        pass
    raw = inputs['review_artifact_raw_bytes']
    bad = {'none': None, 'str': raw.decode(), 'bytearray': bytearray(raw), 'memoryview': memoryview(raw),
           'subclass': Raw(raw), 'domain': inputs['expected_acceptance']}[kind]
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, 'review_artifact_raw_bytes': bad}, 'INVALID_REVIEW_ARTIFACT_LOADER_INPUT')
    assert_stop(calls, REVIEW)


@pytest.mark.parametrize('argument', tuple(RAW_ARGUMENTS.values()))
@pytest.mark.parametrize('kind', ('none', 'str', 'bytearray', 'memoryview', 'subclass', 'domain'))
def test_hso21_42_all_six_raw_roles_exact_bytes_before_any_historical_loader(inputs, monkeypatch, argument, kind):
    class Raw(bytes):
        pass
    raw = inputs[argument]
    bad = {'none': None, 'str': raw.decode(), 'bytearray': bytearray(raw), 'memoryview': memoryview(raw),
           'subclass': Raw(raw), 'domain': inputs['expected_acceptance']}[kind]
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, argument: bad}, INPUT_PREFIX, argument)
    assert_stop(calls, SELECT)


@pytest.mark.parametrize('kind', ('opaque', 'different_refs', 'duplicate_ref', 'duplicate_revision'))
def test_hso12_13_expected_refs_relationships_precede_sha(monkeypatch, kind):
    inputs = inputs_from(synthetic.definitions(), synthetic.definitions(2))
    a, b = inputs['expected_acceptances']
    if kind == 'opaque':
        records = (replace(a, review_artifact_ref='opaque'), b)
        prefix = 'INVALID_REVIEW_ARTIFACT_EXPECTED_REF'
    else:
        prefix = 'INVALID_REVIEW_ARTIFACT_LOADER_INPUT'
        if kind == 'different_refs': records = (a, replace(b, review_artifact_ref='acceptance-review:sha256:' + 'a' * 64))
        elif kind == 'duplicate_ref': records = (a, a)
        else: records = (a, replace(a, acceptance_ref='SYNTH-OTHER'))
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, 'expected_acceptances': records, 'review_artifact_raw_bytes': b'wrong'}, prefix)
    assert_stop(calls, REVIEW)


def test_hso14_review_sha_keeps_independent_expected(inputs, monkeypatch):
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, 'review_artifact_raw_bytes': inputs['review_artifact_raw_bytes'] + b' '},
                 'REVIEW_ARTIFACT_BYTES_MISMATCH')
    assert_stop(calls, REVIEW)


@pytest.mark.parametrize('kind,prefix', (
    ('json', 'INVALID_REVIEW_ARTIFACT_JSON'), ('duplicate', 'DUPLICATE_REVIEW_ARTIFACT_JSON_KEY'),
    ('noncanonical', 'NONCANONICAL_REVIEW_ARTIFACT_BYTES'), ('missing', 'INVALID_REVIEW_ARTIFACT_FIELDS'),
))
def test_hso15_review_strict_errors_with_independently_authored_matching_root(inputs, monkeypatch, kind, prefix):
    raw = {'json': b'{', 'duplicate': b'{"entries":[],"entries":[]}',
           'noncanonical': inputs['review_artifact_raw_bytes'] + b'\n', 'missing': b'{}'}[kind]
    kwargs = authored_review_bytes(inputs, raw)
    calls, _, _ = observe(monkeypatch)
    assert_error(kwargs, prefix)
    assert_stop(calls, REVIEW)


@pytest.mark.parametrize('kind', ('unlisted', 'missing', 'different_value'))
def test_hso16_entire_expected_collection_is_checked(inputs, monkeypatch, kind):
    body = json.loads(inputs['review_artifact_raw_bytes'])
    if kind == 'unlisted': body['entries'][0]['acceptance']['acceptance_ref'] = 'SYNTH-UNLISTED'
    elif kind == 'different_value': body['entries'][0]['acceptance']['benefit_version'] = 'b9999'
    kwargs = authored_review_bytes(inputs, synthetic.canonical(body))
    if kind == 'missing':
        a = kwargs['expected_acceptance']
        kwargs['expected_acceptances'] = (a, replace(a, acceptance_ref='SYNTH-MISSING', acceptance_version='a9999'))
    calls, _, _ = observe(monkeypatch)
    assert_error(kwargs, 'REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH')
    assert_stop(calls, REVIEW)


def test_hso16_unselected_later_entry_is_checked_before_selected_raw_six(monkeypatch):
    kwargs = inputs_from(synthetic.definitions(), synthetic.definitions(2), selected=0,
        edit_review=lambda body: body['entries'][1]['acceptance'].update(benefit_version='b9999'))
    calls, _, _ = observe(monkeypatch)
    exc = assert_error(kwargs, 'REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH')
    assert 'entries[1].acceptance.benefit_version' in str(exc)
    assert_stop(calls, REVIEW)


@pytest.mark.parametrize('kind,field', (
    ('clone', 'entry.acceptance'), ('absent', 'artifact.entries'),
    ('revision', 'artifact.entries'), ('root', 'artifact.review_artifact_ref'),
))
def test_hso17_18_explicit_selected_original_binding(inputs, monkeypatch, kind, field):
    a = inputs['expected_acceptance']
    changed = {'clone': {}, 'absent': {'acceptance_ref': 'SYNTH-ABSENT'},
               'revision': {'acceptance_ref': 'SYNTH-ACCEPT-2', 'acceptance_version': 'a0002'},
               'root': {'review_artifact_ref': 'acceptance-review:sha256:' + 'b' * 64}}[kind]
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, 'expected_acceptance': replace(a, **changed)}, BINDING_PREFIX, field)
    assert_stop(calls, SELECT)


def revoked_inputs(inputs):
    body = json.loads(inputs['review_artifact_raw_bytes'])
    entry = body['entries'][0]
    entry['acceptance'].update(status='REVOKED', revokes_acceptance_ref='SYNTH-OLDER')
    for name in (*synthetic.REF_FIELDS.values(), 'implementation_artifact_ref'):
        entry[name] = None
    for name in ('claim_evidence', 'source_bindings', 'source_documents'):
        entry[name] = []
    kwargs = authored_review_bytes(inputs, synthetic.canonical(body))
    a = replace(kwargs['expected_acceptance'], status=BenefitAcceptanceStatus.REVOKED,
                revokes_acceptance_ref='SYNTH-OLDER')
    return {**kwargs, 'expected_acceptance': a, 'expected_acceptances': (a,)}


def test_hso19_revoked_record_restores_review_but_cannot_fallback_raw_six(inputs, monkeypatch):
    kwargs = revoked_inputs(inputs)
    calls, returned, _ = observe(monkeypatch)
    assert_error(kwargs, BINDING_PREFIX, 'expected_acceptance.status')
    assert_stop(calls, SELECT)
    assert dict(returned)[REVIEW].entries[0].dataset_manifest_ref is None


def test_hso20_expired_accepted_is_restored_without_current_use_claim():
    spec = synthetic.definitions()
    spec['values']['valid_until'] = spec['values']['reviewed_at']
    kwargs = inputs_from(spec)
    artifact, values = run(kwargs)
    assert artifact.entries[0].acceptance is kwargs['expected_acceptance']
    assert artifact.entries[0].acceptance.status is BenefitAcceptanceStatus.ACCEPTED
    assert values[2].verification_status.value == 'DRAFT'
    assert values[2].evaluation_scope.value == 'CONDITION_SLICE'


@pytest.mark.parametrize('name', tuple(RAW_ARGUMENTS))
@pytest.mark.parametrize('kind', ('changed', 'empty', 'other_entry'))
def test_hso23_to29_33_each_role_sha_and_revision_no_fallback(monkeypatch, name, kind):
    kwargs = inputs_from(synthetic.definitions(), synthetic.definitions(2))
    if kind == 'changed': raw = kwargs[RAW_ARGUMENTS[name]] + b' '
    elif kind == 'empty': raw = b''
    else:
        other = inputs_from(synthetic.definitions(), synthetic.definitions(2), selected=1)
        raw = other[RAW_ARGUMENTS[name]]
    calls, _, raised = observe(monkeypatch)
    exc = assert_error({**kwargs, RAW_ARGUMENTS[name]: raw}, synthetic.BYTE_ERRORS[name])
    failed = synthetic.LOADERS[name].__name__
    assert_stop(calls, failed)
    assert raised[-1][1] is exc


@pytest.mark.parametrize('name', tuple(RAW_ARGUMENTS))
def test_hso30_each_role_invalid_json_with_independent_matching_expected_sha(inputs, monkeypatch, name):
    kwargs = authored_artifact_bytes(inputs, name, b'{')
    errors = {
        'benefit': 'INVALID_HISTORICAL_BENEFIT_JSON', 'coverage': 'INVALID_HISTORICAL_COVERAGE_JSON',
        'envelope': 'INVALID_HISTORICAL_POLICY_ENVELOPE_JSON', 'reviews': 'INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON',
        'manifest': 'INVALID_HISTORICAL_DATASET_MANIFEST_JSON', 'registry': 'INVALID_HISTORICAL_SOURCE_REGISTRY_JSON',
    }
    calls, _, _ = observe(monkeypatch)
    assert_error(kwargs, errors[name])
    assert_stop(calls, synthetic.LOADERS[name].__name__)


@pytest.mark.parametrize('name,prefix', (
    ('benefit', 'HISTORICAL_BENEFIT_FINGERPRINT_MISMATCH'),
    ('coverage', 'HISTORICAL_COVERAGE_INVENTORY_FINGERPRINT_MISMATCH'),
    ('envelope', 'HISTORICAL_POLICY_ENVELOPE_TREE_FINGERPRINT_MISMATCH'),
    ('reviews', 'HISTORICAL_COVERAGE_REVIEW_CONTEXT_IMPLEMENTATION_FINGERPRINT_MISMATCH'),
    ('manifest', 'HISTORICAL_DATASET_MANIFEST_POLICY_MEMBERSHIP_MISMATCH'),
    ('registry', 'HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH'),
))
def test_hso31_32_each_role_domain_binding_failure(inputs, monkeypatch, name, prefix):
    body = json.loads(inputs[RAW_ARGUMENTS[name]])
    if name == 'benefit': body['snapshot']['amount_krw'] += 1
    elif name == 'coverage': body['coverage']['inventory']['conditions'][0]['meaning'] = '합성 의미 변경'
    elif name == 'envelope': body['policy']['root']['children'][0]['value'] = 20
    elif name == 'reviews': body['review_context']['implementation_fingerprint'] = synthetic.sha(b'other implementation')
    elif name == 'manifest': body['manifest']['policy_versions'][0]['policy_id'] = 'SYNTH-OTHER'
    else: body['sources'][0]['title'] = '합성 제목 변경'
    kwargs = authored_artifact_bytes(inputs, name, synthetic.canonical(body))
    calls, _, raised = observe(monkeypatch)
    exc = assert_error(kwargs, prefix)
    assert_stop(calls, synthetic.LOADERS[name].__name__)
    assert raised[-1][1] is exc


@pytest.mark.parametrize('scenario,kind,prefix,field', cross.CROSS_CASES,
                         ids=[row[0] for row in cross.CROSS_CASES])
def test_hso34_to40_real_six_success_then_real_cross_failure(monkeypatch, scenario, kind, prefix, field):
    kwargs = inputs_from(cross.negative_spec(kind))
    calls, returned, raised = observe(monkeypatch)
    exc = assert_error(kwargs, prefix, field)
    assert_stop(calls, CROSS)
    assert [name for name, _ in returned] == list(STEPS[:-1])
    assert raised == [(CROSS, exc)]


@pytest.mark.parametrize('target', ('policy', 'registry'))
@pytest.mark.parametrize('field', ('path', 'sha256'))
def test_hso41_manifest_reference_mismatch_fails_loader_not_later_cross(monkeypatch, target, field):
    spec = synthetic.definitions()
    body = spec['bodies']['manifest']['manifest']
    artifact = body['policy_versions'][0]['artifact'] if target == 'policy' else body['source_registry']['artifact']
    artifact[field] = 'synthetic/wrong-original.json' if field == 'path' else synthetic.sha(b'other original')
    kwargs = inputs_from(spec)
    calls, _, _ = observe(monkeypatch)
    prefix = 'HISTORICAL_DATASET_MANIFEST_' + ('POLICY_REFERENCE' if target == 'policy' else 'REGISTRY_REFERENCE') + '_MISMATCH'
    assert_error(kwargs, prefix)
    assert_stop(calls, 'load_historical_dataset_manifest_bytes')


@pytest.mark.parametrize('step', STEPS)
@pytest.mark.parametrize('error_type', (PolicyDataError, RuntimeError))
def test_hso45_46_47_55_sentinel_exception_is_original_and_no_later_call(inputs, monkeypatch, step, error_type):
    sentinel = error_type('sentinel original exception')
    def fail(*args, **kwargs):
        raise sentinel
    monkeypatch.setattr(domain, step, fail)
    calls, returned, raised = observe(monkeypatch)
    with pytest.raises(error_type) as caught:
        run(inputs)
    assert caught.value is sentinel
    assert_stop(calls, step)
    assert [name for name, _ in returned] == list(STEPS[:STEPS.index(step)])
    assert raised == [(step, sentinel)]


@pytest.mark.parametrize('kind,prefix,field,last', (
    ('a_and_review', INPUT_PREFIX, 'expected_acceptance', None),
    ('review_and_raw', 'INVALID_REVIEW_ARTIFACT_LOADER_INPUT', None, REVIEW),
    ('clone_and_raw', BINDING_PREFIX, 'entry.acceptance', SELECT),
    ('sha_and_type', INPUT_PREFIX, 'source_registry_raw_bytes', SELECT),
    ('multiple_types', INPUT_PREFIX, 'benefit_raw_bytes', SELECT),
    ('multiple_sha', 'HISTORICAL_BENEFIT_BYTES_MISMATCH', None, LOADER_NAMES[0]),
))
def test_hso48_to52_global_first_error_precedence(inputs, monkeypatch, kind, prefix, field, last):
    kwargs = dict(inputs)
    if kind == 'a_and_review': kwargs.update(expected_acceptance=None, review_artifact_raw_bytes=None)
    elif kind == 'review_and_raw': kwargs.update(review_artifact_raw_bytes=None, source_registry_raw_bytes=None)
    elif kind == 'clone_and_raw': kwargs.update(expected_acceptance=replace(inputs['expected_acceptance']), source_registry_raw_bytes=None)
    elif kind == 'sha_and_type': kwargs.update(benefit_raw_bytes=b'wrong', source_registry_raw_bytes=None)
    elif kind == 'multiple_types': kwargs.update(benefit_raw_bytes=None, source_registry_raw_bytes=None)
    else: kwargs.update(benefit_raw_bytes=b'wrong', coverage_raw_bytes=b'wrong', source_registry_raw_bytes=b'wrong')
    calls, _, _ = observe(monkeypatch)
    assert_error(kwargs, prefix, field)
    if last is None: assert not calls
    else: assert_stop(calls, last)


def test_hso53_cross_internal_order_is_preserved(monkeypatch):
    spec = cross.negative_spec('source_version')
    spec['bodies']['manifest']['manifest']['policy_versions'][0]['fingerprint'] = synthetic.sha(b'wrong envelope')
    kwargs = inputs_from(spec)
    calls, returned, _ = observe(monkeypatch)
    assert_error(kwargs, 'HISTORICAL_ARTIFACT_POLICY_MISMATCH', 'selected_policy.fingerprint')
    assert_stop(calls, CROSS)
    assert len(returned) == 8


@pytest.mark.parametrize('kind', ('missing', 'stale', 'partial'))
def test_hso08_normal_historical_states_are_not_promoted_or_rejected(monkeypatch, kind):
    spec = synthetic.definitions()
    body = spec['bodies']['coverage']['coverage']
    if kind == 'partial': body['bindings'].pop(0)
    else:
        body['inventory']['completeness_review_ref'] = None if kind == 'missing' else 'INV-OLD'
        body['bindings'][0]['implementation_review_ref'] = 'IMPL-OLD'
    kwargs = inputs_from(spec)
    calls, _, _ = observe(monkeypatch)
    artifact, values = run(kwargs)
    assert artifact.entries[0].acceptance is kwargs['expected_acceptance']
    assert_stop(calls, CROSS)
    assert not any(hasattr(values[1], attribute) for attribute in ('status', 'usable', 'verified'))
    assert values[2].evaluation_scope.value == 'CONDITION_SLICE'


def test_hso54_normal_stale_does_not_hide_later_independent_error(monkeypatch):
    spec = synthetic.definitions()
    spec['bodies']['coverage']['coverage']['inventory']['completeness_review_ref'] = None
    cross.current_review(spec)['subtree_fingerprint'] = synthetic.sha(b'wrong subtree')
    kwargs = inputs_from(spec)
    calls, returned, _ = observe(monkeypatch)
    assert_error(kwargs, 'SUBTREE_FINGERPRINT_CONFLICT')
    assert_stop(calls, CROSS)
    assert len(returned) == 8


@pytest.mark.parametrize('kind', ('review', 'benefit', 'registry', 'cross'))
def test_hso03_error_one_hundred_repetitions_are_deterministic(inputs, monkeypatch, kind):
    kwargs = dict(inputs)
    if kind == 'review': kwargs['review_artifact_raw_bytes'] += b' '
    elif kind == 'benefit': kwargs['benefit_raw_bytes'] += b' '
    elif kind == 'registry': kwargs['source_registry_raw_bytes'] += b' '
    else: kwargs = inputs_from(cross.negative_spec('source_version'))
    before = tuple(record.to_dict() for record in kwargs['expected_acceptances'])
    original_raws = tuple(kwargs[name] for name in ARGUMENTS[2:])
    calls, _, raised = observe(monkeypatch)
    failed = {'review': REVIEW, 'benefit': LOADER_NAMES[0], 'registry': LOADER_NAMES[5], 'cross': CROSS}[kind]
    expected_calls = list(STEPS[:STEPS.index(failed) + 1])
    messages = []
    for _ in range(100):
        with pytest.raises(PolicyDataError) as caught:
            run(kwargs)
        messages.append(str(caught.value))
    assert len(set(messages)) == 1
    assert [name for name, _, _ in calls] == expected_calls * 100
    assert len(raised) == 100 and all(name == failed for name, _ in raised)
    assert tuple(record.to_dict() for record in kwargs['expected_acceptances']) == before
    assert all(kwargs[name] is raw for name, raw in zip(ARGUMENTS[2:], original_raws))


@pytest.mark.parametrize('kind', ('domain', 'previous_tuple'))
def test_hso42_43_previous_domain_results_cannot_replace_raw(inputs, monkeypatch, kind):
    previous = run(inputs)
    invalid = previous[1][0] if kind == 'domain' else previous
    calls, _, _ = observe(monkeypatch)
    assert_error({**inputs, 'benefit_raw_bytes': invalid}, INPUT_PREFIX, 'benefit_raw_bytes')
    assert_stop(calls, SELECT)


@pytest.mark.parametrize('kind', ('engine_version', 'engine_sha', 'missing_locator', 'source_status', 'superseded'))
def test_hso07_60_62_external_checks_are_not_claimed_by_tuple(kind):
    spec = synthetic.definitions()
    if kind == 'engine_version': spec['bodies']['manifest']['manifest']['engine_version'] = 'historical-other-engine'
    elif kind == 'engine_sha': spec['bodies']['manifest']['manifest']['engine_artifact_sha256'] = synthetic.sha(b'other engine')
    elif kind in ('source_status', 'superseded'):
        status = 'WITHDRAWN' if kind == 'source_status' else 'SUPERSEDED'
        cross.rewrite_registry(spec, lambda body: body['sources'][0].update(status=status))
    else:
        benefit = replace(spec['authored']['benefit'], benefit_evidence_refs=('SYNTH-A#missing', 'SYNTH-B#benefit'))
        spec['authored']['benefit'] = benefit
        spec['bodies']['benefit']['snapshot'] = benefit.to_dict()
        spec['values']['benefit_fingerprint'] = synthetic.fingerprint_benefit_snapshot(benefit)
    artifact, values = run(inputs_from(spec))
    assert type(artifact) is AcceptanceReviewArtifact and len(values) == 6
    # 성공해도 실제 실행 ZIP/locator/현재 Source 사용요건을 검사했다는 뜻이 아니다.


def test_hso61_selected_envelope_is_not_whole_manifest_release():
    spec = synthetic.definitions()
    body = spec['bodies']['manifest']['manifest']
    other = deepcopy(body['policy_versions'][0])
    other['policy_id'] = 'SYNTH-OTHER'
    other['artifact']['path'] = 'synthetic/unprovided-other-policy.json'
    body['policy_versions'].insert(0, other)
    _, values = run(inputs_from(spec))
    assert len(values[4].policy_versions) == 2
    assert values[4].policy_versions[1].policy_id == values[2].policy_id


def test_hso63_pure_path_uses_no_external_io_environment_clock_random_or_other_evaluator(inputs, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('same-call 순수 경계 밖의 I/O/평가를 실행했습니다')
    with monkeypatch.context() as patch:
        for obj, name in ((builtins, 'open'), (io, 'open'), (Path, 'open'), (Path, 'read_bytes'),
                          (os, 'getenv'), (socket, 'create_connection'), (subprocess, 'run'),
                          (time, 'time'), (random, 'random'), (random, 'randint'),
                          (SourceRegistry, 'resolve')):
            patch.setattr(obj, name, forbidden)
        patch.setattr(policy_data, 'evaluate_eligibility_coverage', forbidden)
        result = run(inputs)
    assert type(result[0]) is AcceptanceReviewArtifact


def test_hso64_minimal_module_has_one_private_function_and_no_extra_algorithms_or_state():
    source = inspect.getsource(domain)
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert [node.name for node in functions] == ['_orchestrate_historical_artifact_validation']
    assert not any(isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Try, ast.Yield, ast.YieldFrom))
                   for node in ast.walk(tree))
    assert len([node for node in ast.walk(functions[0]) if isinstance(node, ast.Return)]) == 1
    assert not any(isinstance(value, (dict, list, set)) for name, value in vars(domain).items()
                   if not name.startswith('__'))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports == {
        'errors', 'sources', 'benefit_acceptance', 'benefit_acceptance_review_artifact',
        'benefit_acceptance_review_artifact_loader', 'benefit_snapshot', 'coverage',
        'coverage_review_context', 'envelope', 'historical_benefit_snapshot_loader',
        'historical_coverage_review_context_loader', 'historical_cross_artifact_validator',
        'historical_dataset_manifest_loader', 'historical_eligibility_coverage_loader',
        'historical_policy_envelope_loader', 'historical_source_registry_loader', 'manifest',
    }
    assert not any(isinstance(node, ast.Import) for node in ast.walk(tree))
    assert set(__import__('re').findall(r'INVALID_HISTORICAL_ORCHESTRATION_INPUT', source)) == {INPUT_PREFIX}
    assert 'hashlib' not in source and 'json.loads' not in source
