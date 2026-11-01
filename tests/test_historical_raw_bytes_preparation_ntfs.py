"""실제 Windows/NTFS 시험. 합성 원본은 pytest 임시 보관소에만 쓴다."""

import ctypes
from ctypes import wintypes
import json
import os
import struct
import subprocess
import sys

import pytest

import test_historical_six_artifact_integration as synthetic
import test_historical_same_call_orchestrator as authored
import test_historical_raw_bytes_preparation as support
from backend.policy_engine.policy_data import historical_raw_bytes_preparation as domain
from backend.policy_engine.policy_data import historical_windows_file_io as windows


pytestmark = pytest.mark.skipif(not windows._supported_windows(), reason='실제 Windows 10/11 x64가 필요합니다')


def write_archive(tmp_path, inputs=None, omit=()):
    if inputs is None:
        inputs = authored.inputs_from(synthetic.definitions())
    root = tmp_path / 'archive'
    root.mkdir()
    files = support.original_files(inputs)
    for relative, raw in files.items():
        if relative in omit:
            continue
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return inputs, root, files


def run(inputs, root):
    return domain._prepare_and_validate_historical_artifacts(**support.arguments(inputs, str(root)))


def test_actual_ntfs_full_pipeline_metadata_and_same_bytes(tmp_path, monkeypatch):
    inputs, root, files = write_archive(tmp_path)
    captured = []
    real = domain._orchestrate_historical_artifact_validation
    def observe(**kwargs):
        captured.append(kwargs)
        return real(**kwargs)
    monkeypatch.setattr(domain, '_orchestrate_historical_artifact_validation', observe)
    result, raw7 = run(inputs, root)
    assert len(captured) == 1 and raw7 == tuple(files.values())
    assert result[0].entries[0].acceptance is inputs['expected_acceptance']
    assert all(captured[0][name] is raw for name, raw in zip(authored.ARGUMENTS[2:], raw7))
    assert ctypes.sizeof(wintypes.DWORD) == 4 and ctypes.sizeof(wintypes.FILETIME) == 8
    assert ctypes.sizeof(windows._HandleInfo) == 52
    api = windows._Win32()
    handle = api.open(str(root / next(iter(files))), False)
    try:
        first = api.basic(handle, 'review')
        filesystem, serial, path = api.location(handle, 'review')
        assert filesystem == 'NTFS' and serial == first[3] and first[4] > 0 and first[6] == 1
        assert path.startswith('\\\\?\\Volume{')
        assert api.basic(handle, 'review') == first
    finally:
        api.close(handle)


def test_actual_competing_process_write_rename_delete_are_denied_while_reading(tmp_path, monkeypatch):
    inputs, root, files = write_archive(tmp_path)
    target = str(root / next(iter(files)))
    actual = []
    child_code = r'''
import ctypes, json, os, sys
from pathlib import Path
from ctypes import wintypes
p=sys.argv[1]
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
k.CreateFileW.restype=wintypes.HANDLE
k.CloseHandle.argtypes=(wintypes.HANDLE,)
k.CloseHandle.restype=wintypes.BOOL
r={}
archive=Path(p).parent.parent.resolve()
directory=Path(p).parent.resolve()
renamed=Path(str(directory)+'.moved').resolve()
assert directory.is_relative_to(archive) and renamed.is_relative_to(archive)
assert directory!=archive and renamed!=archive
h=k.CreateFileW(p,0x40000000,7,None,3,0,None)
if h==ctypes.c_void_p(-1).value:r['write_open']=ctypes.get_last_error()
else:r['write_open']=0;k.CloseHandle(h)
for name,fn in [('rename',lambda:os.rename(p,p+'.moved')),('delete',lambda:os.unlink(p)),
                ('directory_rename',lambda:os.rename(os.path.dirname(p),os.path.dirname(p)+'.moved'))]:
    try:fn();r[name]=0
    except OSError as e:r[name]=e.winerror
print(json.dumps(r))
'''
    real_read = windows._Win32.read_into
    def barrier(api, handle, buffer, offset, count):
        if not actual:
            child = subprocess.run([sys.executable, '-B', '-c', child_code, target],
                                   capture_output=True, text=True, timeout=15)
            assert child.returncode == 0, child.stderr
            actual.append(json.loads(child.stdout))
        return real_read(api, handle, buffer, offset, count)
    monkeypatch.setattr(windows._Win32, 'read_into', barrier)
    _, raw7 = run(inputs, root)
    assert len(actual) == 1
    assert {name: actual[0][name] for name in ('write_open', 'rename', 'delete')} == {
        'write_open': 32, 'rename': 32, 'delete': 32}
    assert actual[0]['directory_rename'] in (5, 32)
    assert raw7 == tuple(files.values())
    api = windows._Win32()
    handle = api.CreateFileW(target, 0x40000000, 7, None, 3, 0, None)
    assert handle != ctypes.c_void_p(-1).value
    api.close(handle)
    directory, renamed = root / 'acceptance-reviews', root / 'released-reviews'
    assert directory.resolve().is_relative_to(root.resolve()) and renamed.resolve().is_relative_to(root.resolve())
    directory.rename(renamed)
    renamed.rename(directory)


@pytest.mark.parametrize('access', (0x40000000, 0x10000))
def test_actual_existing_write_or_delete_handle_causes_sharing_failure(tmp_path, access):
    inputs, root, files = write_archive(tmp_path)
    api = windows._Win32()
    handle = api.CreateFileW(str(root / next(iter(files))), access, 7, None, 3, 0, None)
    assert handle != ctypes.c_void_p(-1).value
    try:
        with pytest.raises(OSError) as caught: run(inputs, root)
        assert caught.value.winerror == 32
    finally:
        api.close(handle)
    assert run(inputs, root)[1] == tuple(files.values())


def make_junction(link, target):
    """새 임시 빈 폴더에 NTFS mount-point reparse 데이터를 쓴다."""
    link.mkdir()
    api = windows._Win32()
    handle = api.CreateFileW(str(link), 0x40000000, 7, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    ioctl = kernel.DeviceIoControl
    ioctl.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                      wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID)
    ioctl.restype = wintypes.BOOL
    substitute = ('\\??\\' + str(target)).encode('utf-16-le')
    printable = str(target).encode('utf-16-le')
    payload = substitute + b'\0\0' + printable + b'\0\0'
    raw = struct.pack('<IHHHHHH', 0xA0000003, 8 + len(payload), 0,
                      0, len(substitute), len(substitute) + 2, len(printable)) + payload
    buffer = ctypes.create_string_buffer(raw)
    count = wintypes.DWORD()
    try:
        if not ioctl(handle, 0x900A4, buffer, len(raw), None, 0, ctypes.byref(count), None):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        api.close(handle)


def test_actual_junction_as_trusted_root_is_rejected(tmp_path):
    inputs, root, _ = write_archive(tmp_path)
    link = tmp_path / 'root-link'
    make_junction(link, root)
    try:
        support.error(lambda: run(inputs, link), windows._FILE)
    finally:
        os.rmdir(link)


def test_actual_nested_junction_is_rejected_without_reading_outside_root(tmp_path):
    inputs = authored.inputs_from(synthetic.definitions(), edit_review=lambda body:
        body['entries'][0]['accepted_terms_ref'].update(path='linked/benefit.json'))
    inputs, root, _ = write_archive(tmp_path, inputs, omit=('linked/benefit.json',))
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'benefit.json').write_bytes(inputs['benefit_raw_bytes'])
    link = root / 'linked'
    make_junction(link, outside)
    try:
        support.error(lambda: run(inputs, root), windows._FILE)
    finally:
        os.rmdir(link)


def test_actual_file_symlink_rejected(tmp_path):
    inputs = authored.inputs_from(synthetic.definitions())
    review_path = next(iter(support.original_files(inputs)))
    inputs, root, _ = write_archive(tmp_path, inputs, omit=(review_path,))
    outside = tmp_path / 'original-review.json'
    outside.write_bytes(inputs['review_artifact_raw_bytes'])
    link = root / review_path
    link.parent.mkdir(parents=True, exist_ok=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateSymbolicLinkW
    create.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
    create.restype = ctypes.c_ubyte
    if not create(str(link), str(outside), 2):
        code = ctypes.get_last_error()
        if code == 1314:
            pytest.skip('파일 symlink 생성 권한/Developer Mode가 없어 실제 사례 미실행')
        raise ctypes.WinError(code)
    try:
        support.error(lambda: run(inputs, root), windows._FILE)
    finally:
        link.unlink()


def test_actual_hard_link_count_is_rejected(tmp_path):
    inputs, root, files = write_archive(tmp_path)
    target = root / next(iter(files))
    alias = tmp_path / 'outside-hardlink.json'
    os.link(target, alias)
    try:
        assert os.stat(target).st_nlink == 2
        support.error(lambda: run(inputs, root), windows._FILE)
    finally:
        alias.unlink()
    assert run(inputs, root)[1] == tuple(files.values())


@pytest.mark.parametrize('size', (65537, 4_194_304, 4_194_305))
def test_actual_bounded_read_limits_and_cleanup(tmp_path, size):
    root = tmp_path / 'archive'
    root.mkdir()
    target = root / 'payload.bin'
    target.write_bytes(b'x' * size)
    session = windows._FileSession()
    anchor, parts = windows._root_parts(str(root))
    try:
        session.open_root(anchor, parts)
        if size > 4_194_304:
            support.error(lambda: session.read(('payload.bin',), 'benefit'), windows._LIMIT)
        else:
            assert session.read(('payload.bin',), 'benefit') == b'x' * size
    finally:
        session.close(False)
    target.unlink()


def test_actual_domain_failure_closes_all_handles(tmp_path):
    inputs, root, files = write_archive(tmp_path)
    target = root / list(files)[3]
    target.write_bytes(target.read_bytes() + b' ')
    support.error(lambda: run(inputs, root), 'HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH')
    for path in (root / relative for relative in files):
        path.unlink()


def test_actual_repeated_success_and_failure_no_handle_growth(tmp_path):
    inputs, root, files = write_archive(tmp_path)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.argtypes = ()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetProcessHandleCount.restype = wintypes.BOOL
    def count():
        value = wintypes.DWORD()
        assert kernel.GetProcessHandleCount(kernel.GetCurrentProcess(), ctypes.byref(value))
        return value.value
    run(inputs, root)
    before = count()
    target = root / list(files)[-1]
    original = target.read_bytes()
    for _ in range(20):
        assert run(inputs, root)[1] == tuple(files.values())
        target.write_bytes(original + b' ')
        support.error(lambda: run(inputs, root), 'HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH')
        target.write_bytes(original)
    assert count() == before


def test_actual_aggregate_exact_limit_then_overflow(tmp_path):
    root = tmp_path / 'archive'
    root.mkdir()
    for index in range(4):
        (root / f'{index}.bin').write_bytes(b'x' * 4_194_304)
    (root / 'extra.bin').write_bytes(b'x')
    session = windows._FileSession()
    anchor, parts = windows._root_parts(str(root))
    try:
        session.open_root(anchor, parts)
        for index in range(4):
            assert len(session.read((f'{index}.bin',), 'benefit')) == 4_194_304
        assert session.total == 16_777_216
        support.error(lambda: session.read(('extra.bin',), 'registry'), windows._LIMIT)
    finally:
        session.close(False)


def test_actual_case_alias_root_is_rejected(tmp_path):
    inputs, root, _ = write_archive(tmp_path)
    alias = root.with_name('ARCHIVE')
    assert alias.is_dir()
    support.error(lambda: run(inputs, alias), windows._PATH)


def test_actual_empty_file_is_rejected(tmp_path):
    inputs, root, files = write_archive(tmp_path)
    (root / next(iter(files))).write_bytes(b'')
    support.error(lambda: run(inputs, root), windows._FILE)


def test_actual_write_attributes_not_locked_but_changed_metadata_is_rejected(tmp_path, monkeypatch):
    inputs, root, files = write_archive(tmp_path)
    target = str(root / next(iter(files)))
    changed = []
    real_read = windows._Win32.read_into
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    set_time = kernel.SetFileTime
    set_time.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
                        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME))
    set_time.restype = wintypes.BOOL
    def alter(api, handle, buffer, offset, count):
        if not changed:
            metadata = api.CreateFileW(target, 0x100, 7, None, 3, 0, None)
            assert metadata != ctypes.c_void_p(-1).value
            try:
                old = api.basic(handle, 'review')[2]
                new = old + 10_000_000
                value = wintypes.FILETIME(new & 0xffffffff, new >> 32)
                assert set_time(metadata, None, None, ctypes.byref(value))
                changed.append(True)
            finally:
                api.close(metadata)
        return real_read(api, handle, buffer, offset, count)
    monkeypatch.setattr(windows._Win32, 'read_into', alter)
    support.error(lambda: run(inputs, root), windows._CHANGED)
    assert changed == [True]
