"""신뢰된 Windows NTFS 보관소용 제한 I/O. 발급 권한/악성 호스트는 인증하지 않는다."""

import ctypes
from ctypes import wintypes
import os
import platform
import re
import sys

from ..errors import PolicyDataError


_INPUT = 'INVALID_HISTORICAL_RAW_PREPARATION_INPUT'
_ENV = 'HISTORICAL_RAW_PREPARATION_UNSUPPORTED_ENVIRONMENT'
_PATH = 'HISTORICAL_RAW_PREPARATION_PATH_REJECTED'
_FILE = 'HISTORICAL_RAW_PREPARATION_FILE_REJECTED'
_LIMIT = 'HISTORICAL_RAW_PREPARATION_LIMIT_EXCEEDED'
_CHANGED = 'HISTORICAL_RAW_PREPARATION_FILE_CHANGED'
_FILE_CAP = 4_194_304
_TOTAL_CAP = 16_777_216
_CHUNK = 65_536
_DIRECTORY_CAP = 128
_DIRECTORY = 0x10
_REPARSE = 0x400


def _reject(prefix, field):
    raise PolicyDataError(f'{prefix}: {field}: 계약을 확인하세요')


def _supported_windows():
    if (os.name != 'nt' or sys.platform != 'win32' or ctypes.sizeof(ctypes.c_void_p) != 8
            or platform.machine() != 'AMD64'):
        return False
    version = sys.getwindowsversion()
    return version.major == 10 and version.build >= 10240 and version.product_type == 1


def _components(path, separator, role):
    if any(0xD800 <= ord(c) <= 0xDFFF for c in path):
        _reject(_PATH, role + '.path')
    if len(path.encode('utf-16-le')) // 2 > 1024:
        _reject(_LIMIT, role + '.path_length')
    parts = tuple(path.split(separator))
    if len(parts) > 16:
        _reject(_LIMIT, role + '.depth')
    for part in parts:
        if not part or part in ('.', '..') or part[-1] in '. ':
            _reject(_PATH, role + '.path')
        if len(part.encode('utf-16-le')) // 2 > 255:
            _reject(_LIMIT, role + '.component_length')
        if any(ord(c) < 32 or ord(c) == 127 or c in '<>:"/\\|?*' for c in part):
            _reject(_PATH, role + '.path')
        stem = part.split('.', 1)[0].upper()
        if (stem in ('CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$', 'CLOCK$')
                or re.fullmatch(r'(?:COM|LPT)[1-9¹²³]', stem)):
            _reject(_PATH, role + '.path')
    return parts


def _root_parts(root):
    if (not re.match(r'^[A-Za-z]:\\', root) or root != root.strip()
            or '/' in root or len(root) <= 3):
        _reject(_PATH, 'root.path')
    if len(root.encode('utf-16-le', errors='surrogatepass')) // 2 > 1024:
        _reject(_LIMIT, 'root.path_length')
    return root[:3], _components(root[3:], '\\', 'root')


def _relative_parts(path, role):
    return _components(path, '/', role)


def _canonical_parts(path, role):
    match = re.fullmatch(
        r'(\\\\\?\\Volume\{[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\}\\)(.*)', path)
    if match is None:
        _reject(_PATH, role + '.final_path')
    tail = match.group(2)
    return (match.group(1), *(tail.split('\\') if tail else ()))


class _HandleInfo(ctypes.Structure):
    _fields_ = [('attributes', wintypes.DWORD), ('creation', wintypes.FILETIME),
                ('access', wintypes.FILETIME), ('write', wintypes.FILETIME),
                ('serial', wintypes.DWORD), ('size_high', wintypes.DWORD),
                ('size_low', wintypes.DWORD), ('links', wintypes.DWORD),
                ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD)]


class _Win32:
    """파일 취득에 필요한 Win32 호출만 묶는다. 도메인 검증은 기존 함수에 둔다."""

    def __init__(self):
        try:
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            signatures = (
                ('CreateFileW', (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                 wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE), wintypes.HANDLE),
                ('CloseHandle', (wintypes.HANDLE,), wintypes.BOOL),
                ('GetDriveTypeW', (wintypes.LPCWSTR,), wintypes.UINT),
                ('GetFileType', (wintypes.HANDLE,), wintypes.DWORD),
                ('GetFileInformationByHandle', (wintypes.HANDLE, ctypes.POINTER(_HandleInfo)), wintypes.BOOL),
                ('GetVolumeInformationByHandleW', (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD), wintypes.BOOL),
                ('GetFinalPathNameByHandleW', (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD), wintypes.DWORD),
                ('ReadFile', (wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                              ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID), wintypes.BOOL),
            )
            for name, args, result in signatures:
                function = getattr(kernel, name)
                function.argtypes, function.restype = args, result
                setattr(self, name, function)
        except (AttributeError, OSError):
            _reject(_ENV, 'platform.api')

    def open(self, path, directory):
        handle = self.CreateFileW(path, 0x80 if directory else 0x80000000,
                                  0x1, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def basic(self, handle, role):
        ctypes.set_last_error(0)
        kind = self.GetFileType(handle)
        if kind == 0 and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        if kind != 1:
            _reject(_FILE, role + '.kind')
        info = _HandleInfo()
        if not self.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        return (info.attributes, (info.creation.dwHighDateTime << 32) | info.creation.dwLowDateTime,
                (info.write.dwHighDateTime << 32) | info.write.dwLowDateTime, info.serial,
                (info.index_high << 32) | info.index_low, (info.size_high << 32) | info.size_low, info.links)

    def location(self, handle, role):
        filesystem = ctypes.create_unicode_buffer(32)
        serial = wintypes.DWORD()
        if not self.GetVolumeInformationByHandleW(handle, None, 0, ctypes.byref(serial), None, None, filesystem, 32):
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_unicode_buffer(4096)
        length = self.GetFinalPathNameByHandleW(handle, buffer, 4096, 1)
        if not length:
            raise ctypes.WinError(ctypes.get_last_error())
        if length >= 4096:
            _reject(_LIMIT, role + '.final_path_length')
        return filesystem.value, serial.value, buffer.value

    def read_into(self, handle, buffer, offset, count):
        target = (ctypes.c_ubyte * count).from_buffer(buffer, offset)
        actual = wintypes.DWORD()
        if not self.ReadFile(handle, target, count, ctypes.byref(actual), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return actual.value

    def close(self, handle):
        if not self.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def drive_type(self, anchor):
        return self.GetDriveTypeW(anchor)


class _FileSession:
    """한 호출의 OS 자원만 소유한다. 도메인 결과나 전역 cache를 저장하지 않는다."""

    def __init__(self):
        self.api = _Win32()
        self.handles = []
        self.directories = {}
        self.files = []
        self.total = 0
        self.serial = None
        self.volume = None
        self.root = None

    def _state(self, handle, directory, role, initial):
        basic = self.api.basic(handle, role)
        if initial and (bool(basic[0] & _DIRECTORY) != directory or basic[0] & _REPARSE):
            _reject(_FILE, role + '.attributes')
        filesystem, serial, final_path = self.api.location(handle, role)
        canonical = _canonical_parts(final_path, role)
        if initial:
            if filesystem != 'NTFS':
                _reject(_ENV, role + '.filesystem')
            if basic[4] == 0:
                _reject(_FILE, role + '.identity')
            if serial != basic[3] or (self.serial is not None and serial != self.serial):
                _reject(_PATH, role + '.volume')
            if self.volume is not None and canonical[0] != self.volume:
                _reject(_PATH, role + '.volume')
        if directory:
            return (basic[0] & (_DIRECTORY | _REPARSE), basic[3], basic[4], canonical, filesystem, serial)
        return (*basic, canonical, filesystem, serial)

    def _open(self, path, directory, expected, role):
        handle = self.api.open(path, directory)
        try:
            self.handles.append(handle)
        except BaseException:
            # 소유권 목록 할당 실패도 방금 확보한 handle을 유실하지 않게 한다.
            try:
                self.api.close(handle)
            except BaseException:
                pass
            raise
        state = self._state(handle, directory, role, True)
        canonical = state[3] if directory else state[7]
        if expected is None:
            if len(canonical) != 1:
                _reject(_PATH, 'root.drive_alias')
        elif canonical != expected:
            _reject(_PATH, role + '.final_path')
        return handle, directory, role, state

    @staticmethod
    def _join(parts):
        return parts[0] + '\\'.join(parts[1:])

    def _directory(self, parts, role):
        if parts not in self.directories:
            if len(self.directories) >= _DIRECTORY_CAP:
                _reject(_LIMIT, role + '.directory_handles')
            self.directories[parts] = self._open(self._join(parts), True, parts, role)
        return self.directories[parts]

    def open_root(self, anchor, parts):
        if self.api.drive_type(anchor) != 3:
            _reject(_ENV, 'root.drive')
        record = self._open(anchor, True, None, 'root')
        state = record[3]
        self.serial, self.volume = state[1], state[3][0]
        canonical = state[3]
        self.directories[canonical] = record
        for part in parts:
            canonical = (*canonical, part)
            self._directory(canonical, 'root')
        self.root = canonical

    def recheck(self, record):
        handle, directory, role, state = record
        if self._state(handle, directory, role, False) != state:
            _reject(_CHANGED, role + '.identity')

    def read(self, parts, role):
        canonical = self.root
        for part in parts[:-1]:
            canonical = (*canonical, part)
            self._directory(canonical, role)
        expected = (*canonical, parts[-1])
        if len(self.files) >= 7:
            _reject(_LIMIT, role + '.file_handles')
        if any(record[3][7] == expected for record in self.files):
            _reject(_FILE, role + '.alias')
        record = self._open(self._join(expected), False, expected, role)
        self.files.append(record)
        handle, _, _, state = record
        if state[6] != 1:
            _reject(_FILE, role + '.links')
        if any(other[3][3:5] == state[3:5] for other in self.files[:-1]):
            _reject(_FILE, role + '.alias')
        size = state[5]
        if size == 0:
            _reject(_FILE, role + '.empty')
        if size > _FILE_CAP or self.total + size > _TOTAL_CAP:
            _reject(_LIMIT, role + '.size')
        buffer = bytearray(size)
        offset = 0
        while offset < size:
            count = min(_CHUNK, size - offset)
            actual = self.api.read_into(handle, buffer, offset, count)
            if not 0 < actual <= count:
                _reject(_CHANGED, role + '.read_length')
            offset += actual
        if self.api.read_into(handle, bytearray(1), 0, 1) != 0:
            _reject(_CHANGED, role + '.eof')
        self.recheck(record)
        raw = bytes(buffer)
        self.total += size
        return raw

    def recheck_all(self):
        # 파일은 Review→원본6 순서, directory는 확보 순서로 확인한다.
        for record in self.files:
            self.recheck(record)
        for record in self.directories.values():
            self.recheck(record)

    def close(self, preserve_error):
        first = None
        while self.handles:
            handle = self.handles.pop()
            try:
                self.api.close(handle)
            except BaseException as exc:
                if first is None:
                    first = exc
        if first is not None and not preserve_error:
            raise first
