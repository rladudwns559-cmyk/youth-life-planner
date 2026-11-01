"""M2.53 합성 source ZIP의 verify-only. 정책 계산·배포 승인·영속 증명서는 제공하지 않는다."""

import argparse
from contextlib import contextmanager, redirect_stdout
import hashlib
import importlib
import io
import json
import keyword
import os
from pathlib import Path
import platform
import re
import stat
import sys
import types
import zipfile
import zipimport


class _Failure(Exception):
    def __init__(self, prefix, field):
        self.prefix = prefix
        self.field = field
        super().__init__(prefix + ": " + field)


def _fail(prefix, field):
    raise _Failure(prefix, field)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("INVALID_ARTIFACT_INPUT", "cli")


def _path_key(value):
    return os.path.normcase(os.path.normpath(os.fspath(value)))


def _absolute(value, field, *, exists=True):
    path = Path(value)
    if not path.is_absolute() or str(value) != str(value).strip():
        _fail("INVALID_ARTIFACT_INPUT", field)
    if exists and not path.exists():
        _fail("ARTIFACT_NOT_AVAILABLE", field)
    # zipimport와 보호 handle이 다른 link target을 선택하지 않도록 한다.
    for part in (path, *path.parents):
        if part.exists() and part.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            _fail("INVALID_ARTIFACT_INPUT", field)
    return path.resolve()


def _backend_modules():
    return {name: module for name, module in sys.modules.items()
            if name == "backend" or name.startswith("backend.")}


def _check_flags():
    if os.name != "nt" or sys.platform != "win32":
        _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "platform")
    for name in ("isolated", "ignore_environment", "no_user_site", "no_site",
                 "dont_write_bytecode", "safe_path", "utf8_mode", "hash_randomization"):
        if getattr(sys.flags, name) != 1:
            _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "flags")
    if sys.flags.optimize != 0 or sys.get_int_max_str_digits() != 4300:
        _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "flags")


@contextmanager
def _protected_zip(path):
    """같은 파일의 일반 쓰기/delete 공유를 거부하며 reader는 허용한다."""
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    drive_type = kernel.GetDriveTypeW
    drive_type.argtypes = (wintypes.LPCWSTR,)
    drive_type.restype = wintypes.UINT
    if drive_type(path.anchor) != 3:
        _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "filesystem")
    handle = create(str(path), 0x80000000, 0x1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        _fail("ARTIFACT_LOCK_UNAVAILABLE", "bundle")
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close(handle)
        raise
    try:
        stream = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with stream:
        yield stream


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _fail("INVALID_CODE_BUNDLE", "runtime.json")
        value[key] = item
    return value


def _invalid_constant(value):
    _fail("INVALID_CODE_BUNDLE", "runtime.json")


def _runtime_profile(raw):
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError):
        _fail("INVALID_CODE_BUNDLE", "runtime.json")
    fields = {"bundle_format", "python_implementation", "python_version", "sys_platform",
              "machine", "runtime_dependencies"}
    if type(value) is not dict or set(value) != fields:
        _fail("INVALID_CODE_BUNDLE", "runtime.json")
    if value["bundle_format"] != "python-code-bundle-1.0":
        _fail("INVALID_CODE_BUNDLE", "bundle_format")
    for name in ("python_implementation", "sys_platform", "machine"):
        if type(value[name]) is not str or not value[name].strip():
            _fail("INVALID_CODE_BUNDLE", name)
    version = value["python_version"]
    if (type(version) is not list or len(version) != 3
            or any(type(item) is not int or item < 0 for item in version)):
        _fail("INVALID_CODE_BUNDLE", "python_version")
    if type(value["runtime_dependencies"]) is not list or value["runtime_dependencies"]:
        _fail("INVALID_CODE_BUNDLE", "runtime_dependencies")
    return value


def _source_inventory(raw):
    """원본 ZIP 내용만 읽는다. bootstrap/backend source를 실행하거나 추출하지 않는다."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if names != sorted(names) or len(set(name.casefold() for name in names)) != len(names):
                _fail("INVALID_CODE_BUNDLE", "entries")
            if archive.comment or not {"bootstrap.py", "runtime.json", "backend/__init__.py"} <= set(names):
                _fail("INVALID_CODE_BUNDLE", "required_entries")
            modules = {}
            for item in infos:
                name = item.filename
                parts = name.split("/")
                mode = item.external_attr >> 16
                if (name != item.orig_filename or any(part in ("", ".", "..") for part in parts)
                        or "\\" in name or ":" in name
                        or any(ord(char) < 32 or ord(char) == 127 for char in name)
                        or item.is_dir() or item.external_attr & 0x10
                        or (stat.S_IFMT(mode) and not stat.S_ISREG(mode))
                        or item.compress_type != zipfile.ZIP_STORED or item.flag_bits & 1
                        or item.extra or item.comment or item.date_time != (1980, 1, 1, 0, 0, 0)):
                    _fail("INVALID_CODE_BUNDLE", "entries")
                if name in ("bootstrap.py", "runtime.json"):
                    continue
                if parts[0] != "backend" or len(parts) < 2 or not name.endswith(".py"):
                    _fail("INVALID_CODE_BUNDLE", "source_paths")
                is_package = parts[-1] == "__init__.py"
                components = parts[:-1] if is_package else parts[:-1] + [parts[-1][:-3]]
                if any(not part.isidentifier() or keyword.iskeyword(part) for part in components):
                    _fail("INVALID_CODE_BUNDLE", "source_paths")
                module = ".".join(components)
                if module in modules:
                    _fail("INVALID_CODE_BUNDLE", "module_inventory")
                modules[module] = (name, is_package)
            for module in sorted(modules):
                parts = module.split(".")
                for i in range(1, len(parts)):
                    if modules.get(".".join(parts[:i]), (None, False))[1] is not True:
                        _fail("INVALID_CODE_BUNDLE", "package_inventory")
            if archive.read("bootstrap.py") != Path(__file__).read_bytes():
                _fail("INVALID_CODE_BUNDLE", "bootstrap.py")
            profile = _runtime_profile(archive.read("runtime.json"))
            # 모든 source entry의 CRC/read 실패도 import 전에 확인한다.
            for name in names:
                archive.read(name)
            return modules, profile
    except _Failure:
        raise
    except (OSError, ValueError, RuntimeError, EOFError, zipfile.BadZipFile, NotImplementedError):
        _fail("INVALID_CODE_BUNDLE", "zip")


def _environment(profile, executable, base):
    expected = (("python_implementation", platform.python_implementation()),
                ("python_version", list(sys.version_info[:3])), ("sys_platform", sys.platform),
                ("machine", platform.machine()))
    for field, observed in expected:
        if profile[field] != observed:
            _fail("ARTIFACT_ENVIRONMENT_MISMATCH", field)
    if _path_key(executable) != _path_key(Path(sys.executable).resolve()):
        _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "python_executable")
    if _path_key(base) != _path_key(Path(sys.base_prefix).resolve()):
        _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "python_base")
    major, minor, _ = profile["python_version"]
    paths = [str(base / f"python{major}{minor}.zip"), str(base / "DLLs"),
             str(base / "Lib"), str(base)]
    if tuple(map(_path_key, sys.path)) != tuple(map(_path_key, paths)):
        _fail("ARTIFACT_ENVIRONMENT_MISMATCH", "sys.path")
    return paths


def _check_loaded(inventory, bundle, *, complete=False):
    loaded = _backend_modules()
    if not set(loaded) <= set(inventory) or (complete and set(loaded) != set(inventory)):
        _fail("ARTIFACT_IMPORT_MISMATCH", "module_inventory")
    for name in sorted(loaded):
        module = loaded[name]
        entry, is_package = inventory[name]
        origin = str(bundle) + os.sep + entry.replace("/", os.sep)
        spec = getattr(module, "__spec__", None)
        loader = getattr(spec, "loader", None)
        if (type(module) is not types.ModuleType or spec is None or spec.name != name
                or type(loader) is not zipimport.zipimporter
                or getattr(module, "__loader__", None) is not loader
                or _path_key(loader.archive) != _path_key(bundle)):
            _fail("ARTIFACT_IMPORT_MISMATCH", "loader")
        prefix = "/".join(name.split(".")[:-1])
        prefix = prefix + "/" if prefix else ""
        if loader.prefix.replace("\\", "/") != prefix:
            _fail("ARTIFACT_IMPORT_MISMATCH", "loader_prefix")
        if (any(type(value) is not str or _path_key(value) != _path_key(origin)
                for value in (getattr(module, "__file__", None), spec.origin, loader.get_filename(name)))
                or loader.is_package(name) is not is_package):
            _fail("ARTIFACT_IMPORT_MISMATCH", "origin")
        expected_package = name if is_package else name.rpartition(".")[0]
        if getattr(module, "__package__", None) != expected_package:
            _fail("ARTIFACT_IMPORT_MISMATCH", "package")
        if is_package:
            expected_path = _path_key(os.path.dirname(origin))
            for paths in (getattr(module, "__path__", None), spec.submodule_search_locations):
                if type(paths) is not list or len(paths) != 1 or _path_key(paths[0]) != expected_path:
                    _fail("ARTIFACT_IMPORT_MISMATCH", "package_path")
        elif hasattr(module, "__path__") or spec.submodule_search_locations is not None:
            _fail("ARTIFACT_IMPORT_MISMATCH", "package_path")
        for value in vars(module).values():
            if type(value) is types.FunctionType and value.__module__ == name:
                if _path_key(value.__code__.co_filename) != _path_key(origin):
                    _fail("ARTIFACT_IMPORT_MISMATCH", "function_origin")
    return loaded


def _import_inventory(inventory, bundle, stdlib_paths):
    paths = [str(bundle), *stdlib_paths]
    sys.path[:] = paths
    meta_path, hooks = tuple(sys.meta_path), tuple(sys.path_hooks)
    originals = {}
    for name in sorted(inventory):
        try:
            with redirect_stdout(sys.stderr):
                importlib.import_module(name)
            if sys.path != paths or tuple(sys.meta_path) != meta_path or tuple(sys.path_hooks) != hooks:
                _fail("ARTIFACT_IMPORT_MISMATCH", "import_state")
            current = _check_loaded(inventory, bundle)
            if any(current.get(key) is not value for key, value in originals.items()):
                _fail("ARTIFACT_IMPORT_MISMATCH", "module_replaced")
            originals.update(current)
        except _Failure:
            raise
        except BaseException:
            _fail("ARTIFACT_IMPORT_MISMATCH", "import")
    _check_loaded(inventory, bundle, complete=True)
    return tuple(sorted(inventory))


def _verify(args):
    _check_flags()
    if _backend_modules():
        _fail("ARTIFACT_IMPORT_MISMATCH", "preloaded_backend")
    if re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256) is None:
        _fail("INVALID_ARTIFACT_INPUT", "expected_sha256")
    bundle = _absolute(args.bundle, "bundle")
    executable = _absolute(args.python_executable, "python_executable")
    base = _absolute(args.python_base, "python_base")
    if not bundle.is_file() or not executable.is_file() or not base.is_dir():
        _fail("INVALID_ARTIFACT_INPUT", "paths")
    with _protected_zip(bundle) as protected:
        raw = protected.read()
        if hashlib.sha256(raw).hexdigest() != args.expected_sha256:
            _fail("ARTIFACT_HASH_MISMATCH", "bundle")
        inventory, profile = _source_inventory(raw)
        paths = _environment(profile, executable, base)
        checked = _import_inventory(inventory, bundle, paths)
        protected.seek(0)
        if (hashlib.sha256(protected.read()).hexdigest() != args.expected_sha256
                or not os.path.samestat(os.fstat(protected.fileno()), bundle.stat())):
            _fail("ARTIFACT_CHANGED_DURING_STARTUP", "bundle")
        _check_flags()
        _check_loaded(inventory, bundle, complete=True)
        # 성공 출력까지 handle을 유지한다. 종료 뒤 결과 재사용을 보장하지 않는다.
        print(json.dumps({"mode": "verify-only", "scope": "synthetic-code-import-only",
                          "expected_module_count": len(inventory), "checked_module_count": len(checked),
                          "checked_modules": list(checked)}, sort_keys=True, separators=(",", ":")), flush=True)


def main(argv=None):
    parser = _Parser(description="합성 ZIP verify-only", allow_abbrev=False)
    parser.add_argument("--verify-only", action="store_true", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--python-base", required=True)
    try:
        args = parser.parse_args(argv)
        _verify(args)
    except _Failure as exc:
        print(f"{exc.prefix}: {exc.field}", file=sys.stderr, flush=True)
        return 2
    except Exception:
        print("INVALID_ARTIFACT_INPUT: startup", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
