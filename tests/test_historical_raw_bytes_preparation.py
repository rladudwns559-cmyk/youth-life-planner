"""M2.77 합성 OS 시험. 실제 Windows 공유/경쟁 증거는 별도 NTFS 시험에 둔다."""

import ast
from dataclasses import fields, replace
import inspect
import json
from pathlib import Path
from typing import get_type_hints

import pytest

import test_historical_six_artifact_integration as synthetic
import test_historical_cross_artifact_validator as cross
import test_historical_same_call_orchestrator as authored
from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import historical_raw_bytes_preparation as domain
from backend.policy_engine.policy_data import historical_windows_file_io as windows


VOLUME = '\\\\?\\Volume{12345678-1234-1234-1234-123456789abc}\\'
ROOT = 'C:\\Root'
ROLES = ('review', *authored.RAW_ARGUMENTS)
ARGUMENTS = ('expected_acceptance', 'expected_acceptances', 'trusted_root')


def original_files(inputs):
    body = json.loads(inputs['review_artifact_raw_bytes'])
    entry = next(row for row in body['entries']
                 if row['acceptance']['acceptance_ref'] == inputs['expected_acceptance'].acceptance_ref)
    result = {'acceptance-reviews/' + inputs['expected_acceptance'].review_artifact_ref.rsplit(':', 1)[1] + '.json':
              inputs['review_artifact_raw_bytes']}
    result.update({entry[synthetic.REF_FIELDS[name]]['path']: inputs[arg]
                   for name, arg in authored.RAW_ARGUMENTS.items()})
    return result


def arguments(inputs, root=ROOT):
    return {'expected_acceptance': inputs['expected_acceptance'],
            'expected_acceptances': inputs['expected_acceptances'], 'trusted_root': root}


class FakeWin32:
    """OS 반환을 명시 저작한다. 실제 잠금 보호를 증명하는 fake가 아니다."""

    def __init__(self, files, root=ROOT):
        self.root = self.canonical(root)
        self.files = {self.root + '\\' + path.replace('/', '\\'): raw for path, raw in files.items()}
        self.directories = {VOLUME}
        for path in (self.root, *self.files):
            tail = path[len(VOLUME):].split('\\')
            end = len(tail) if path == self.root else len(tail) - 1
            self.directories.update(VOLUME + '\\'.join(tail[:i]) for i in range(1, end + 1))
        self.events, self.opened, self.closed = [], [], []
        self.handles, self.positions, self.ids = {}, {}, {}
        self.basic_changes, self.final_changes = {}, {}
        self.fs = 'NTFS'
        self.drive = 3
        self.short = None
        self.fail = None

    @staticmethod
    def canonical(path):
        return VOLUME + path[3:] if path.startswith('C:\\') else path

    def event(self, operation, key):
        self.events.append((operation, key))
        if self.fail is not None:
            self.fail(operation, key)

    def drive_type(self, anchor):
        self.event('drive', anchor)
        return self.drive

    def open(self, path, directory):
        path = self.canonical(path)
        self.event('open_directory' if directory else 'open_file', path)
        if path not in self.directories and path not in self.files:
            raise FileNotFoundError(2, 'synthetic missing file')
        handle = len(self.opened) + 1
        self.handles[handle] = path
        self.positions[handle] = 0
        self.opened.append(handle)
        return handle

    def basic(self, handle, role):
        path = self.handles[handle]
        self.event('basic', path)
        identifier = self.ids.setdefault(path, len(self.ids) + 1)
        basic = (16 if path in self.directories else 32, 100, 200, 7, identifier,
                 len(self.files[path]) if path in self.files else 0, 1)
        changes = self.basic_changes.get(path, {})
        if callable(changes):
            changes = changes(basic)
        return tuple(changes.get(i, value) for i, value in enumerate(basic))

    def location(self, handle, role):
        path = self.handles[handle]
        self.event('location', path)
        return self.fs, 7, self.final_changes.get(path, path)

    def read_into(self, handle, buffer, offset, count):
        path = self.handles[handle]
        self.event('read', (path, count))
        count = min(count, self.short) if self.short is not None else count
        start = self.positions[handle]
        raw = self.files[path][start:start + count]
        buffer[offset:offset + len(raw)] = raw
        self.positions[handle] += len(raw)
        return len(raw)

    def close(self, handle):
        self.closed.append(handle)
        self.event('close', handle)


def setup_fake(monkeypatch, inputs=None, files=None):
    if inputs is None:
        inputs = authored.inputs_from(synthetic.definitions())
    fake = FakeWin32(original_files(inputs) if files is None else files)
    monkeypatch.setattr(domain, '_supported_windows', lambda: True)
    monkeypatch.setattr(windows, '_Win32', lambda: fake)
    return inputs, fake


def run(inputs):
    return domain._prepare_and_validate_historical_artifacts(**arguments(inputs))


def error(call, prefix, field=None):
    with pytest.raises(PolicyDataError) as caught:
        call()
    if field is None:
        assert str(caught.value).startswith(prefix + ':'), str(caught.value)
    else:
        assert str(caught.value) == f'{prefix}: {field}: 계약을 확인하세요'
    return caught.value


def assert_closed(fake):
    assert fake.closed == fake.opened[::-1]


def file_opens(fake):
    return [value for op, value in fake.events if op == 'open_file']


def test_exact_api_and_annotations_no_export():
    function = domain._prepare_and_validate_historical_artifacts
    signature = inspect.signature(function)
    assert tuple(signature.parameters) == ARGUMENTS
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in signature.parameters.values())
    hints = get_type_hints(function)
    assert hints['expected_acceptance'] is synthetic.PolicyBenefitAcceptance
    assert hints['expected_acceptances'] == tuple[synthetic.PolicyBenefitAcceptance, ...]
    assert hints['trusted_root'] is str
    assert hints['return'] == tuple[tuple[synthetic.AcceptanceReviewArtifact, tuple[
        synthetic.BenefitSnapshot, synthetic.EligibilityCoverage, synthetic.PolicyEnvelope,
        synthetic.CoverageReviewContext, synthetic.DatasetManifest, synthetic.SourceRegistry]],
        tuple[bytes, bytes, bytes, bytes, bytes, bytes, bytes]]
    assert not hasattr(policy_data, function.__name__)


def test_hbp01_to16_real_domain_loaders_with_synthetic_os(monkeypatch):
    inputs, fake = setup_fake(monkeypatch)
    calls, result_objects = [], []
    real_review, real_c = domain.load_acceptance_review_artifact_bytes, domain._orchestrate_historical_artifact_validation
    def review(**kwargs):
        calls.append(('review', kwargs))
        value = real_review(**kwargs)
        result_objects.append(value)
        return value
    def orchestrate(**kwargs):
        calls.append(('orchestrator', kwargs))
        value = real_c(**kwargs)
        result_objects.append(value)
        assert not fake.closed and len(file_opens(fake)) == 7
        return value
    monkeypatch.setattr(domain, 'load_acceptance_review_artifact_bytes', review)
    monkeypatch.setattr(domain, '_orchestrate_historical_artifact_validation', orchestrate)
    result, raws = run(inputs)
    assert type(raws) is tuple and len(raws) == 7 and all(type(raw) is bytes for raw in raws)
    assert raws == tuple(original_files(inputs).values())
    assert result is result_objects[1]
    assert result[0] is not result_objects[0]
    assert result[0].entries[0].acceptance is inputs['expected_acceptance']
    assert [row[0] for row in calls] == ['review', 'orchestrator']
    assert all(row[1]['expected_acceptances'] is inputs['expected_acceptances'] for row in calls)
    assert calls[0][1]['raw_bytes'] is raws[0]
    assert calls[1][1]['expected_acceptance'] is inputs['expected_acceptance']
    assert all(calls[1][1][name] is raw for name, raw in zip(authored.ARGUMENTS[2:], raws))
    assert file_opens(fake) == [fake.root + '\\' + key.replace('/', '\\') for key in original_files(inputs)]
    assert_closed(fake)


@pytest.mark.parametrize('selected', (0, 1))
def test_multiple_entry_revision_uses_whole_expected_and_explicit_old_or_new(monkeypatch, selected):
    inputs = authored.inputs_from(synthetic.definitions(), synthetic.definitions(2), selected=selected)
    _, fake = setup_fake(monkeypatch, inputs)
    result, raws = run(inputs)
    assert len(result[0].entries) == 2
    assert result[0].entries[selected].acceptance is inputs['expected_acceptance']
    assert result[1][0].dataset_version == f'SYNTH-D{selected + 1}'
    assert raws == tuple(original_files(inputs).values())
    assert_closed(fake)


@pytest.mark.parametrize('name', ARGUMENTS)
def test_missing_keyword_before_body(name):
    values = dict.fromkeys(ARGUMENTS)
    del values[name]
    with pytest.raises(TypeError):
        domain._prepare_and_validate_historical_artifacts(**values)


@pytest.mark.parametrize('name', ('skip', 'reader', 'use_latest', 'review_locator', 'expected_sha256', 'allow_partial'))
def test_no_bypass_options(name):
    with pytest.raises(TypeError):
        domain._prepare_and_validate_historical_artifacts(expected_acceptance=None, expected_acceptances=(),
            trusted_root=ROOT, **{name: True})


@pytest.mark.parametrize('field,bad', (
    ('expected_acceptance', None), ('expected_acceptance', {}),
    ('expected_acceptances', []), ('expected_acceptances', ()), ('expected_acceptances', ({},)),
    ('trusted_root', None), ('trusted_root', Path('C:/Root')),
))
def test_q0_exact_inputs_no_file_operations(monkeypatch, field, bad):
    inputs, fake = setup_fake(monkeypatch)
    values = {**arguments(inputs), field: bad}
    error(lambda: domain._prepare_and_validate_historical_artifacts(**values), windows._INPUT, field)
    assert not fake.events


@pytest.mark.parametrize('kind', ('clone', 'opaque', 'unsupported'))
def test_q0_precedence_and_original_expected_helper(monkeypatch, kind):
    inputs, fake = setup_fake(monkeypatch)
    values = arguments(inputs)
    prefix = windows._INPUT
    if kind == 'clone': values['expected_acceptance'] = replace(inputs['expected_acceptance'])
    elif kind == 'opaque':
        a = replace(inputs['expected_acceptance'], review_artifact_ref='opaque')
        values.update(expected_acceptance=a, expected_acceptances=(a,))
        prefix = 'INVALID_REVIEW_ARTIFACT_EXPECTED_REF'
    else:
        monkeypatch.setattr(domain, '_supported_windows', lambda: False)
        prefix = windows._ENV
    error(lambda: domain._prepare_and_validate_historical_artifacts(**values), prefix)
    assert not fake.events


@pytest.mark.parametrize('path', ('', '.', '..', '../a', 'a/../b', '/a', 'C:/x', 'C:x',
    '//server/a', '\\\\server\\a', '\\\\?\\C:\\a', '\\\\.\\pipe\\a', 'a:b', 'a//b', 'a\\b',
    'a.', 'a ', 'CON', 'con.txt', 'NUL.tar.gz', 'COM1', 'LPT9.txt', 'COM¹.txt', 'LPT²', 'CLOCK$',
    'CONIN$', 'CONOUT$', 'a\x00', 'a\x7f', 'a*', 'a?', 'a|b', 'a<b', '\ud800'))
def test_hbp18_to25_path_components_reject_before_open(path):
    error(lambda: windows._relative_parts(path, 'benefit'), windows._PATH)


@pytest.mark.parametrize('path', ('정책/원본.json', 'a b/자료.JSON', 'a/.hidden', 'a/é.json', 'a/é.json', 'a/%2e%2e.json'))
def test_legal_unicode_spaces_are_preserved_without_decoding_or_normalization(path):
    assert windows._relative_parts(path, 'benefit') == tuple(path.split('/'))


@pytest.mark.parametrize('root', ('C:\\', 'C:Root', 'Root', 'C:/Root', '\\\\server\\root',
    '\\\\?\\C:\\Root', 'C:\\Root\\', ' C:\\Root', 'C:\\Root ', 'C:\\a\\..\\Root'))
def test_root_profile_rejects(root):
    error(lambda: windows._root_parts(root), windows._PATH)


@pytest.mark.parametrize('path', ('x' * 256, '/'.join(['a'] * 17), '/'.join(['a' * 200] * 6)))
def test_component_depth_utf16_limits(path):
    error(lambda: windows._relative_parts(path, 'benefit'), windows._LIMIT)


@pytest.mark.parametrize('kind', ('reparse_root', 'reparse_directory', 'reparse_file', 'directory_file',
    'hardlink', 'outside_path', 'case_alias', 'short_alias', 'other_volume', 'not_ntfs', 'remote_drive'))
def test_handle_target_rejections_and_cleanup(monkeypatch, kind):
    inputs, fake = setup_fake(monkeypatch)
    review = next(iter(fake.files))
    if kind == 'reparse_root': fake.basic_changes[fake.root] = {0: 16 | 0x400}
    elif kind == 'reparse_directory': fake.basic_changes[review.rsplit('\\', 1)[0]] = {0: 16 | 0x400}
    elif kind == 'reparse_file': fake.basic_changes[review] = {0: 32 | 0x400}
    elif kind == 'directory_file': fake.basic_changes[review] = {0: 16}
    elif kind == 'hardlink': fake.basic_changes[review] = {6: 2}
    elif kind == 'outside_path': fake.final_changes[review] = VOLUME + 'RootSibling\\x.json'
    elif kind == 'case_alias': fake.final_changes[review] = review.replace('Root', 'root')
    elif kind == 'short_alias': fake.final_changes[review] = review.replace('Root', 'ROOT~1')
    elif kind == 'other_volume': fake.final_changes[review] = review.replace('12345678', '87654321')
    elif kind == 'not_ntfs': fake.fs = 'ReFS'
    else: fake.drive = 4
    expected = windows._ENV if kind in ('not_ntfs', 'remote_drive') else windows._FILE if kind.startswith('reparse') or kind in ('directory_file', 'hardlink') else windows._PATH
    error(lambda: run(inputs), expected)
    assert not any(op == 'read' for op, _ in fake.events)
    assert_closed(fake)


def test_every_historical_path_is_checked_before_any_six_file_open(monkeypatch):
    inputs = authored.inputs_from(synthetic.definitions(), edit_review=lambda body:
        body['entries'][0]['source_registry_ref'].update(path='synthetic/CON.txt'))
    _, fake = setup_fake(monkeypatch, inputs)
    error(lambda: run(inputs), windows._PATH)
    assert len(file_opens(fake)) == 1
    assert_closed(fake)


@pytest.mark.parametrize('name', tuple(authored.RAW_ARGUMENTS))
def test_sha_failure_each_role_after_all_reads_and_domain_error_original(monkeypatch, name):
    inputs, fake = setup_fake(monkeypatch)
    target = list(fake.files)[list(authored.RAW_ARGUMENTS).index(name) + 1]
    fake.files[target] += b' '
    caught = []
    real = domain._orchestrate_historical_artifact_validation
    def observe(**kwargs):
        try: return real(**kwargs)
        except PolicyDataError as exc:
            caught.append(exc)
            raise
    monkeypatch.setattr(domain, '_orchestrate_historical_artifact_validation', observe)
    exc = error(lambda: run(inputs), synthetic.BYTE_ERRORS[name])
    assert caught == [exc] and caught[0] is exc
    assert len(file_opens(fake)) == 7
    assert_closed(fake)


@pytest.mark.parametrize('kind', ('sha', 'strict', 'revoked'))
def test_review_failure_cannot_open_untrusted_six_paths(monkeypatch, kind):
    inputs = authored.inputs_from(synthetic.definitions())
    if kind == 'strict': inputs = authored.authored_review_bytes(inputs, b'{')
    elif kind == 'revoked': inputs = authored.revoked_inputs(inputs)
    files = None
    if kind in ('strict', 'revoked'):
        files = {'acceptance-reviews/' + inputs['expected_acceptance'].review_artifact_ref.rsplit(':', 1)[1] + '.json':
                 inputs['review_artifact_raw_bytes']}
    _, fake = setup_fake(monkeypatch, inputs, files=files)
    if kind == 'sha': fake.files[next(iter(fake.files))] += b' '
    prefix = {'sha': 'REVIEW_ARTIFACT_BYTES_MISMATCH', 'strict': 'INVALID_REVIEW_ARTIFACT_JSON',
              'revoked': 'HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH'}[kind]
    error(lambda: run(inputs), prefix)
    assert len(file_opens(fake)) == 1
    assert_closed(fake)


@pytest.mark.parametrize('scenario,kind,prefix,field', cross.CROSS_CASES, ids=[row[0] for row in cross.CROSS_CASES])
def test_real_six_loaders_then_cross_failure_propagates(monkeypatch, scenario, kind, prefix, field):
    inputs = authored.inputs_from(cross.negative_spec(kind))
    _, fake = setup_fake(monkeypatch, inputs)
    error(lambda: run(inputs), prefix)
    assert len(file_opens(fake)) == 7
    assert_closed(fake)


@pytest.mark.parametrize('index', range(7))
def test_missing_file_first_failure_no_later_open(monkeypatch, index):
    inputs, fake = setup_fake(monkeypatch)
    del fake.files[list(fake.files)[index]]
    with pytest.raises(FileNotFoundError): run(inputs)
    assert len(file_opens(fake)) == index + 1
    assert_closed(fake)


def session_for(monkeypatch, files):
    _, fake = setup_fake(monkeypatch, files=files)
    session = windows._FileSession()
    session.open_root('C:\\', ('Root',))
    return session, fake


@pytest.mark.parametrize('size', (1, 65535, 65536, 65537, 4_194_304))
def test_io_exact_boundary_chunk_counts(monkeypatch, size):
    session, fake = session_for(monkeypatch, {'payload.bin': b'x' * size})
    try:
        assert session.read(('payload.bin',), 'benefit') == b'x' * size
    finally:
        session.close(False)
    counts = [value[1] for op, value in fake.events if op == 'read']
    assert all(0 < count <= 65536 for count in counts)
    assert counts[-1] == 1
    assert sum(counts[:-1]) == size
    assert_closed(fake)


def test_total_exact_limit_then_one_byte_over(monkeypatch):
    session, fake = session_for(monkeypatch, {f'{i}.bin': b'x' * 4_194_304 for i in range(4)} | {'extra.bin': b'x'})
    try:
        for i in range(4): assert len(session.read((f'{i}.bin',), 'benefit')) == 4_194_304
        assert session.total == 16_777_216
        error(lambda: session.read(('extra.bin',), 'registry'), windows._LIMIT)
    finally: session.close(False)
    assert_closed(fake)


@pytest.mark.parametrize('size,prefix', ((0, windows._FILE), (4_194_305, windows._LIMIT), (2**40, windows._LIMIT)))
def test_size_from_handle_before_allocation_or_read(monkeypatch, size, prefix):
    session, fake = session_for(monkeypatch, {'payload.bin': b'x'})
    fake.basic_changes[fake.root + '\\payload.bin'] = {5: size}
    try: error(lambda: session.read(('payload.bin',), 'benefit'), prefix)
    finally: session.close(False)
    assert not any(op == 'read' for op, _ in fake.events)
    assert_closed(fake)


def test_short_reads_continue_same_handle(monkeypatch):
    inputs, fake = setup_fake(monkeypatch)
    fake.short = 17
    result, raws = run(inputs)
    assert raws == tuple(original_files(inputs).values())
    assert result[0].entries[0].acceptance is inputs['expected_acceptance']
    assert_closed(fake)


@pytest.mark.parametrize('kind', ('early_eof', 'growth', 'identity', 'last_write', 'attributes', 'location'))
def test_changes_reject_and_cleanup(monkeypatch, kind):
    inputs, fake = setup_fake(monkeypatch)
    target = next(iter(fake.files))
    if kind == 'early_eof': fake.basic_changes[target] = {5: len(fake.files[target]) + 1}
    elif kind == 'growth': fake.basic_changes[target] = {5: len(fake.files[target]) - 1}
    else:
        key = {'identity': 4, 'last_write': 2, 'attributes': 0}.get(kind)
        def change(op, value):
            if op == 'read' and value[0] == target:
                if kind == 'location': fake.final_changes[target] = VOLUME + 'Root\\changed.json'
                else: fake.basic_changes[target] = {key: 999}
        fake.fail = change
    error(lambda: run(inputs), windows._CHANGED)
    assert_closed(fake)


@pytest.mark.parametrize('operation', ('open_file', 'basic', 'location', 'read'))
def test_original_os_or_programming_error_and_cleanup(monkeypatch, operation):
    inputs, fake = setup_fake(monkeypatch)
    sentinel = OSError(5, 'synthetic denied')
    def fail(op, value):
        if op == operation: raise sentinel
    fake.fail = fail
    with pytest.raises(OSError) as caught: run(inputs)
    assert caught.value is sentinel
    assert_closed(fake)


@pytest.mark.parametrize('primary', (False, True))
def test_close_failure_never_returns_partial_or_masks_primary(monkeypatch, primary):
    inputs, fake = setup_fake(monkeypatch)
    close_error, data_error = OSError(6, 'synthetic close'), PolicyDataError('synthetic domain')
    def fail(op, value):
        if op == 'close': raise close_error
    fake.fail = fail
    if primary:
        def bad(**kwargs): raise data_error
        monkeypatch.setattr(domain, '_orchestrate_historical_artifact_validation', bad)
    with pytest.raises((PolicyDataError, OSError)) as caught: run(inputs)
    assert caught.value is (data_error if primary else close_error)
    assert_closed(fake)


def test_missing_late_file_precedes_earlier_sha_mismatch(monkeypatch):
    inputs, fake = setup_fake(monkeypatch)
    fake.files[list(fake.files)[1]] += b' '
    del fake.files[list(fake.files)[-1]]
    with pytest.raises(FileNotFoundError): run(inputs)
    assert_closed(fake)


def test_one_hundred_fixed_os_states_reexecute_without_mutating_expected(monkeypatch):
    inputs, fake = setup_fake(monkeypatch)
    before = tuple(a.to_dict() for a in inputs['expected_acceptances'])
    first = run(inputs)
    for _ in range(100):
        current = run(inputs)
        assert current == first and current[0] is not first[0]
        assert current[0][0].entries[0].acceptance is inputs['expected_acceptance']
    assert len(file_opens(fake)) == 7 * 101
    assert sorted(fake.closed) == fake.opened
    assert tuple(a.to_dict() for a in inputs['expected_acceptances']) == before


def test_no_new_hash_parser_domain_models_or_io_fallback():
    tree = ast.parse(inspect.getsource(domain))
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert functions == ['_prepare_and_validate_historical_artifacts']
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    source = inspect.getsource(domain) + inspect.getsource(windows)
    assert 'hashlib' not in source and 'json.loads' not in source
    assert 'read_bytes(' not in source and 'Path.resolve' not in source
    assert not hasattr(policy_data, '_prepare_and_validate_historical_artifacts')


@pytest.mark.parametrize('kind', ('same_path', 'same_id'))
def test_two_roles_cannot_alias_one_file(monkeypatch, kind):
    session, fake = session_for(monkeypatch, {'a.bin': b'a', 'b.bin': b'b'})
    try:
        session.read(('a.bin',), 'benefit')
        if kind == 'same_id':
            first = session.files[0][3]
            fake.basic_changes[fake.root + '\\b.bin'] = {4: first[4]}
        error(lambda: session.read(('a.bin' if kind == 'same_path' else 'b.bin',), 'coverage'), windows._FILE)
    finally:
        session.close(False)
    assert_closed(fake)


def test_directory_handle_budget_has_no_fallback(monkeypatch):
    session, fake = session_for(monkeypatch, {'payload.bin': b'x'})
    monkeypatch.setattr(windows, '_DIRECTORY_CAP', len(session.directories))
    before = len(fake.opened)
    try:
        error(lambda: session._directory((*session.root, 'extra'), 'benefit'), windows._LIMIT)
    finally:
        session.close(False)
    assert len(fake.opened) == before
    assert_closed(fake)


def test_handle_ownership_allocation_failure_preserves_primary_and_closes_new_handle(monkeypatch):
    _, fake = setup_fake(monkeypatch)
    session = windows._FileSession()
    primary = MemoryError('synthetic ownership allocation')
    class FailingList(list):
        def append(self, value):
            raise primary
    session.handles = FailingList()
    with pytest.raises(MemoryError) as caught:
        session.open_root('C:\\', ('Root',))
    assert caught.value is primary
    assert_closed(fake)


@pytest.mark.parametrize('phase', ('before_c', 'after_c'))
def test_q5_q7_rechecks_block_return_on_late_change(monkeypatch, phase):
    inputs, fake = setup_fake(monkeypatch)
    target = next(iter(fake.files))
    real_check, real_c = windows._FileSession.recheck_all, domain._orchestrate_historical_artifact_validation
    calls = []
    def recheck(session):
        if phase == 'before_c': fake.basic_changes[target] = {2: 999}
        return real_check(session)
    def orchestrate(**kwargs):
        calls.append(kwargs)
        value = real_c(**kwargs)
        if phase == 'after_c': fake.basic_changes[target] = {2: 999}
        return value
    monkeypatch.setattr(windows._FileSession, 'recheck_all', recheck)
    monkeypatch.setattr(domain, '_orchestrate_historical_artifact_validation', orchestrate)
    error(lambda: run(inputs), windows._CHANGED)
    assert len(calls) == (0 if phase == 'before_c' else 1)
    assert_closed(fake)


def test_original_c_runtime_error_is_not_wrapped(monkeypatch):
    inputs, fake = setup_fake(monkeypatch)
    primary = RuntimeError('synthetic C programming error')
    def fail(**kwargs): raise primary
    monkeypatch.setattr(domain, '_orchestrate_historical_artifact_validation', fail)
    with pytest.raises(RuntimeError) as caught: run(inputs)
    assert caught.value is primary
    assert len(file_opens(fake)) == 7
    assert_closed(fake)


def test_missing_file_identity_is_rejected_before_content_read(monkeypatch):
    inputs, fake = setup_fake(monkeypatch)
    fake.basic_changes[next(iter(fake.files))] = {4: 0}
    error(lambda: run(inputs), windows._FILE)
    assert not any(op == 'read' for op, _ in fake.events)
    assert_closed(fake)
