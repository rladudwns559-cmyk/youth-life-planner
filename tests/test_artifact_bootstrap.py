"""M2.53: tmp의 합성 ZIP과 실제 새 subprocess만 사용한다. 실제 backend 배포물은 만들지 않는다."""

import hashlib
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
import platform
import queue
import stat
import subprocess
import sys
import threading
from types import SimpleNamespace
import zipfile

import pytest


BOOTSTRAP = Path(__file__).resolve().parents[1] / "tools/artifacts/bootstrap.py"
SOURCE = BOOTSTRAP.read_bytes()
FLAGS = ["-I", "-S", "-B", "-X", "utf8"]
EXPECTED_MODULES = ("backend", "backend.alpha", "backend.nested", "backend.nested.beta", "backend.z_last")
BASE_SOURCES = {
    "backend/__init__.py": "# synthetic/test-only package\n",
    "backend/alpha.py": "from .nested.beta import LABEL\nVALUE = LABEL\n",
    "backend/nested/__init__.py": "from . import beta\n",
    "backend/nested/beta.py": "LABEL = 'synthetic-test-only'\n",
    "backend/z_last.py": "def forbidden_evaluator():\n    raise AssertionError('must never be called')\n",
}
NATIVE = pytest.mark.skipif(sys.platform != "win32", reason="실제 Windows 공유 모드/subprocess 전용")
CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


@pytest.fixture
def bootstrap_module():
    spec = importlib.util.spec_from_file_location("synthetic_bootstrap_under_test", BOOTSTRAP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bundle_factory(tmp_path):
    counter = 0

    def make(*, sources=None, profile_changes=None, raw_profile=None, omit=(), extra=(),
             bootstrap=SOURCE, raw_zip=None, reverse=False, compression=zipfile.ZIP_STORED):
        nonlocal counter
        counter += 1
        root = tmp_path / f"synthetic-test-only-{counter}"
        root.mkdir()
        path = root / "synthetic-code-bundle.zip"
        profile = {"bundle_format": "python-code-bundle-1.0", "python_implementation": "CPython",
                   "python_version": list(sys.version_info[:3]), "sys_platform": "win32",
                   "machine": platform.machine(), "runtime_dependencies": []}
        profile.update(profile_changes or {})
        entries = {**BASE_SOURCES, **(sources or {}), "bootstrap.py": bootstrap,
                   "runtime.json": raw_profile if raw_profile is not None else
                   json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")}
        for name in omit:
            entries.pop(name)
        pairs = list(entries.items()) + list(extra)
        pairs.sort(key=lambda item: item[0], reverse=reverse)
        if raw_zip is None:
            with zipfile.ZipFile(path, "w") as archive:
                for name, data in pairs:
                    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    info.compress_type = compression
                    with pytest.warns(UserWarning, match="Duplicate name") if name in archive.namelist() else nullcontext():
                        archive.writestr(info, data.encode("utf-8") if type(data) is str else data)
        else:
            path.write_bytes(raw_zip)
        # 변형 전에 최초 fixture bytes에서 독립적으로 확보한 기대값이다.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return SimpleNamespace(root=root, path=path, digest=digest, profile=profile)

    return make


def _arguments(bundle, *, digest=None, executable=None, base=None):
    return ["--verify-only", "--bundle", str(bundle.path), "--expected-sha256",
            bundle.digest if digest is None else digest, "--python-executable",
            str(executable if executable is not None else Path(sys.executable).resolve()),
            "--python-base", str(base if base is not None else Path(sys.base_prefix).resolve())]


def _run(bundle, *, flags=FLAGS, args=None, env=None, wrapper=None):
    arguments = _arguments(bundle) if args is None else args
    if wrapper is None:
        command = [sys.executable, *flags, str(BOOTSTRAP), *arguments]
    else:
        script = bundle.root / "test-only-wrapper.py"
        script.write_text(wrapper + "\nimport runpy,sys\nsys.argv = " + repr([str(BOOTSTRAP), *arguments])
                          + "\nrunpy.run_path(" + repr(str(BOOTSTRAP)) + ",run_name='__main__')\n", encoding="utf-8")
        command = [sys.executable, *flags, str(script)]
    return subprocess.run(command, cwd=bundle.root, env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", timeout=15,
                          creationflags=CREATION_FLAGS)


def _failure(result, prefix, field=None):
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert result.stdout == ""
    line = result.stderr.splitlines()[-1]
    assert line.startswith(prefix + ": "), result.stderr
    if field is not None:
        assert line == f"{prefix}: {field}"
    assert "Traceback" not in result.stderr


def _success(result, modules=EXPECTED_MODULES):
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value == {"mode": "verify-only", "scope": "synthetic-code-import-only",
                     "expected_module_count": len(modules), "checked_module_count": len(modules),
                     "checked_modules": list(modules)}
    return value


def _marker_code(path):
    return f"from pathlib import Path\nPath({str(path)!r}).write_text('IMPORTED',encoding='utf-8')\n"


def test_inventory_reads_bytes_without_importing_backend(bootstrap_module, bundle_factory, tmp_path):
    marker = tmp_path / "not-imported"
    bundle = bundle_factory(sources={"backend/__init__.py": _marker_code(marker)})
    modules, profile = bootstrap_module._source_inventory(bundle.path.read_bytes())
    assert tuple(sorted(modules)) == EXPECTED_MODULES
    assert profile == bundle.profile
    assert not marker.exists()


@pytest.mark.parametrize("raw", [b"{}", b"[]", b"null", b"{broken", b"\xff", b'\xef\xbb\xbf{}',
                                b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_profile_structural_errors_without_platform_io(bootstrap_module, raw):
    with pytest.raises(bootstrap_module._Failure, match="INVALID_CODE_BUNDLE"):
        bootstrap_module._runtime_profile(raw)


def test_no_backend_import_or_domain_evaluator_dependency():
    import ast
    tree = ast.parse(SOURCE)
    names = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    names += [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name == "backend" or name.startswith("backend.") for name in names)


def test_non_windows_never_reports_native_success(bundle_factory):
    bundle = bundle_factory()
    result = _run(bundle, wrapper="import sys\nsys.platform='linux'\n")
    _failure(result, "ARTIFACT_ENVIRONMENT_MISMATCH", "platform")


@NATIVE
class TestWindowsVerifyOnly:
    def test_normal_nested_and_indirect_imports_without_calling_evaluator(self, bundle_factory):
        _success(_run(bundle_factory()))

    def test_explicit_marker_runs_only_after_hash_gate(self, bundle_factory, tmp_path):
        marker = tmp_path / "import-marker"
        bundle = bundle_factory(sources={"backend/__init__.py": _marker_code(marker)})
        _failure(_run(bundle, args=_arguments(bundle, digest="0" * 64)), "ARTIFACT_HASH_MISMATCH")
        assert not marker.exists()
        _success(_run(bundle))
        assert marker.read_text(encoding="utf-8") == "IMPORTED"

    def test_repeated_new_processes_have_same_complete_decision(self, bundle_factory):
        bundle = bundle_factory()
        assert _success(_run(bundle)) == _success(_run(bundle))

    def test_inventory_size_is_not_production_file_count(self, bundle_factory):
        bundle = bundle_factory(omit=("backend/alpha.py", "backend/nested/__init__.py", "backend/nested/beta.py"))
        _success(_run(bundle), ("backend", "backend.z_last"))

    @pytest.mark.parametrize("digest", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64,
                                       " " + "a" * 64, "0x" + "a" * 64])
    def test_invalid_expected_hash_is_not_normalized(self, bundle_factory, digest):
        bundle = bundle_factory()
        _failure(_run(bundle, args=_arguments(bundle, digest=digest)), "INVALID_ARTIFACT_INPUT", "expected_sha256")

    @pytest.mark.parametrize("same_size", [False, True])
    def test_changed_zip_keeps_original_expectation_and_prevents_import(self, bundle_factory, tmp_path, same_size):
        marker = tmp_path / "hash-marker"
        bundle = bundle_factory(sources={"backend/__init__.py": _marker_code(marker)})
        original = bundle.path.read_bytes()
        changed = original.replace(b"synthetic-test-only", b"synthetic-test-ONLY", 1) if same_size else original + b"changed"
        assert changed != original
        if same_size:
            assert len(changed) == len(original)
        bundle.path.write_bytes(changed)
        _failure(_run(bundle), "ARTIFACT_HASH_MISMATCH", "bundle")
        assert not marker.exists()

    def test_hash_gate_precedes_structure_failure(self, bundle_factory):
        bundle = bundle_factory()
        bundle.path.write_bytes(b"not a zip")
        _failure(_run(bundle), "ARTIFACT_HASH_MISMATCH")

    def test_corrupt_zip_with_correct_expected_bytes_is_format_error(self, bundle_factory):
        _failure(_run(bundle_factory(raw_zip=b"not a zip")), "INVALID_CODE_BUNDLE", "zip")

    def test_missing_artifact_is_unavailable_not_a_hash_or_domain_result(self, bundle_factory):
        bundle = bundle_factory()
        bundle.path.unlink()
        _failure(_run(bundle), "ARTIFACT_NOT_AVAILABLE", "bundle")

    @pytest.mark.parametrize("missing", ["bootstrap.py", "runtime.json", "backend/__init__.py",
                                        "backend/nested/__init__.py"])
    def test_missing_required_entry_or_package_is_rejected(self, bundle_factory, missing):
        _failure(_run(bundle_factory(omit=(missing,))), "INVALID_CODE_BUNDLE")

    def test_missing_indirectly_required_source_is_import_failure(self, bundle_factory):
        _failure(_run(bundle_factory(omit=("backend/nested/beta.py",))), "ARTIFACT_IMPORT_MISMATCH", "import")

    @pytest.mark.parametrize("extra", [("backend/alpha.py", "# duplicate"), ("backend/Alpha.py", "# case"),
                                      ("../outside.py", "# outside"), ("/outside.py", "# outside"),
                                      ("C:/outside.py", "# drive"), ("backend\\other.py", "# backslash"),
                                      ("backend//other.py", "# empty"), ("backend/./other.py", "# dot"),
                                      ("backend/cache.pyc", b"cache"), ("backend/native.pyd", b"native"),
                                      ("backend/nested.zip", b"nested"), ("backend/resource.txt", b"resource"),
                                      ("other/__init__.py", "# outside namespace"),
                                      ("backend/alpha/__init__.py", "# module-package collision")])
    def test_invalid_source_entries_block_all_imports(self, bundle_factory, tmp_path, extra):
        marker = tmp_path / "structure-marker"
        bundle = bundle_factory(extra=(extra,), sources={"backend/__init__.py": _marker_code(marker)})
        _failure(_run(bundle), "INVALID_CODE_BUNDLE")
        assert not marker.exists()

    def test_unsorted_entries_are_not_rewritten(self, bundle_factory):
        _failure(_run(bundle_factory(reverse=True)), "INVALID_CODE_BUNDLE", "entries")

    def test_compressed_zip_is_not_source_bundle_format(self, bundle_factory):
        _failure(_run(bundle_factory(compression=zipfile.ZIP_DEFLATED)), "INVALID_CODE_BUNDLE", "entries")

    def test_symlink_entry_is_not_regular_source(self, bundle_factory):
        bundle = bundle_factory()
        with zipfile.ZipFile(bundle.path) as old:
            entries = [(item, old.read(item)) for item in old.infolist()]
        with zipfile.ZipFile(bundle.path, "w") as new:
            for info, raw in entries:
                if info.filename == "backend/alpha.py":
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                new.writestr(info, raw)
        bundle.digest = hashlib.sha256(bundle.path.read_bytes()).hexdigest()
        _failure(_run(bundle), "INVALID_CODE_BUNDLE", "entries")

    @pytest.mark.parametrize("change", ["dos_directory", "timestamp"])
    def test_noncanonical_source_metadata_is_rejected(self, bundle_factory, change):
        bundle = bundle_factory()
        with zipfile.ZipFile(bundle.path) as archive:
            entries = [(info, archive.read(info)) for info in archive.infolist()]
        with zipfile.ZipFile(bundle.path, "w") as archive:
            for info, raw in entries:
                if info.filename == "backend/alpha.py":
                    if change == "dos_directory":
                        info.external_attr |= 0x10
                    else:
                        info.date_time = (2026, 10, 22, 0, 0, 0)
                archive.writestr(info, raw)
        bundle.digest = hashlib.sha256(bundle.path.read_bytes()).hexdigest()
        _failure(_run(bundle), "INVALID_CODE_BUNDLE", "entries")

    def test_foreign_bootstrap_bytes_are_not_executed(self, bundle_factory, tmp_path):
        marker = tmp_path / "zip-bootstrap-marker"
        bundle = bundle_factory(bootstrap=_marker_code(marker).encode())
        _failure(_run(bundle), "INVALID_CODE_BUNDLE", "bootstrap.py")
        assert not marker.exists()

    @pytest.mark.parametrize("profile", [{"extra": True}, {"bundle_format": "other"},
                                         {"python_version": [True, 12, 14]}, {"python_version": [3, 12]},
                                         {"runtime_dependencies": ["pytest"]}, {"runtime_dependencies": {}},
                                         {"machine": ""}])
    def test_profile_structure_is_strict(self, bundle_factory, profile):
        _failure(_run(bundle_factory(profile_changes=profile)), "INVALID_CODE_BUNDLE")

    @pytest.mark.parametrize("field,value", [("python_implementation", "PyPy"), ("python_version", [0, 0, 0]),
                                            ("sys_platform", "linux"), ("machine", "wrong-architecture")])
    def test_expected_environment_is_not_replaced_with_observed_values(self, bundle_factory, tmp_path, field, value):
        marker = tmp_path / "environment-marker"
        bundle = bundle_factory(profile_changes={field: value}, sources={"backend/__init__.py": _marker_code(marker)})
        _failure(_run(bundle), "ARTIFACT_ENVIRONMENT_MISMATCH", field)
        assert not marker.exists()

    @pytest.mark.parametrize("flags", [["-S", "-B", "-X", "utf8"], ["-I", "-B", "-X", "utf8"],
                                      ["-I", "-S", "-X", "utf8"], ["-I", "-S", "-B", "-X", "utf8=0"],
                                      [*FLAGS, "-O"], [*FLAGS, "-X", "int_max_str_digits=0"]])
    def test_actual_flags_are_checked(self, bundle_factory, flags):
        _failure(_run(bundle_factory(), flags=flags), "ARTIFACT_ENVIRONMENT_MISMATCH", "flags")

    @pytest.mark.parametrize("field", ["python_executable", "python_base"])
    def test_explicit_interpreter_and_base_are_checked(self, bundle_factory, field):
        bundle = bundle_factory()
        args = _arguments(bundle, executable=bundle.path) if field == "python_executable" else _arguments(bundle, base=bundle.root)
        _failure(_run(bundle, args=args), "ARTIFACT_ENVIRONMENT_MISMATCH", field)

    def test_cwd_and_pythonpath_backend_are_not_used(self, bundle_factory, tmp_path):
        bundle = bundle_factory()
        fake = bundle.root / "backend"
        fake.mkdir()
        marker = tmp_path / "ambient-backend-marker"
        (fake / "__init__.py").write_text(_marker_code(marker) + "raise RuntimeError('ambient backend')\n", encoding="utf-8")
        environment = dict(os.environ, PYTHONPATH=str(bundle.root), PYTHONHOME="test-only-invalid-home")
        _success(_run(bundle, env=environment))
        assert not marker.exists()

    @pytest.mark.parametrize("kind", ["directory", "zip"])
    def test_unapproved_import_path_is_rejected_in_new_process(self, bundle_factory, kind):
        bundle = bundle_factory()
        foreign = bundle_factory()
        path = foreign.root if kind == "directory" else foreign.path
        _failure(_run(bundle, wrapper=f"import sys\nsys.path.append({str(path)!r})\n"),
                 "ARTIFACT_ENVIRONMENT_MISMATCH", "sys.path")

    def test_external_backend_already_loaded_is_not_removed_or_reloaded(self, bundle_factory):
        bundle = bundle_factory()
        fake = bundle.root / "preloaded" / "backend"
        fake.mkdir(parents=True)
        (fake / "__init__.py").write_text("# external test-only backend\n", encoding="utf-8")
        wrapper = f"import sys\nsys.path.insert(0,{str(fake.parent)!r})\nimport backend\nsys.path.pop(0)\n"
        _failure(_run(bundle, wrapper=wrapper), "ARTIFACT_IMPORT_MISMATCH", "preloaded_backend")

    def test_similarly_named_namespace_is_not_backend(self, bundle_factory):
        bundle = bundle_factory()
        wrapper = "import sys,types\nsys.modules['backendish']=types.ModuleType('backendish')\n"
        _success(_run(bundle, wrapper=wrapper))

    @pytest.mark.parametrize("source", ["raise RuntimeError('private raw payload')\n", "raise SystemExit(0)\n",
                                       "raise ImportError('late source failure')\n"])
    def test_late_import_failure_is_whole_failure_and_diagnostic_is_sanitized(self, bundle_factory, tmp_path, source):
        marker = tmp_path / "early-import"
        bundle = bundle_factory(sources={"backend/__init__.py": _marker_code(marker), "backend/z_last.py": source})
        result = _run(bundle)
        _failure(result, "ARTIFACT_IMPORT_MISMATCH", "import")
        assert marker.exists()
        assert "private raw payload" not in result.stderr
        with bundle.path.open("r+b"):
            pass  # 실패 종료 뒤에도 보호 handle이 남지 않는다.

    @pytest.mark.parametrize("source,field", [
        ("__path__.append('test-only-foreign-path')\n", "package_path"),
        ("__spec__.submodule_search_locations=[]\n", "package_path"),
        ("__loader__=None\n", "loader"),
        ("__spec__.origin='test-only-foreign-origin'\n", "origin"),
        ("import sys,types\nsys.modules['backend.unexpected']=types.ModuleType('backend.unexpected')\n", "module_inventory"),
    ])
    def test_package_inventory_and_origin_metadata_are_checked(self, bundle_factory, source, field):
        _failure(_run(bundle_factory(sources={"backend/__init__.py": source})), "ARTIFACT_IMPORT_MISMATCH", field)

    @pytest.mark.parametrize("source,field", [
        ("import sys\nsys.path.append('foreign')\n", "import_state"),
        ("import sys\nsys.meta_path.append(object())\n", "import_state"),
        ("import sys\nsys.path_hooks.append(lambda x: None)\n", "import_state"),
        ("exec(compile('def injected(): pass','<foreign-code>','exec'),globals())\n", "function_origin"),
    ])
    def test_late_module_cannot_change_import_state_or_function_origin(self, bundle_factory, source, field):
        _failure(_run(bundle_factory(sources={"backend/z_last.py": source})), "ARTIFACT_IMPORT_MISMATCH", field)

    def test_other_zip_with_common_path_prefix_is_not_same_archive(self, bundle_factory):
        bundle = bundle_factory()
        foreign_path = Path(str(bundle.path) + ".other.zip")
        with zipfile.ZipFile(foreign_path, "w") as archive:
            archive.writestr("backend/z_last.py", "# foreign synthetic code\n")
        source = ("import importlib.util,sys,zipimport\n"
                  f"loader=zipimport.zipimporter({str(foreign_path)!r}+'/backend')\n"
                  "spec=loader.find_spec('backend.z_last')\n"
                  "foreign=importlib.util.module_from_spec(spec)\n"
                  "sys.modules['backend.z_last']=foreign\nloader.exec_module(foreign)\n")
        with zipfile.ZipFile(bundle.path) as archive:
            entries = [(info, archive.read(info)) for info in archive.infolist()]
        with zipfile.ZipFile(bundle.path, "w") as archive:
            for info, raw in entries:
                archive.writestr(info, source.encode("utf-8") if info.filename == "backend/alpha.py" else raw)
        # 이 합성 fixture의 첫 실행 전에 완성한 기대값이며 mismatch 테스트의 갱신이 아니다.
        bundle.digest = hashlib.sha256(bundle.path.read_bytes()).hexdigest()
        _failure(_run(bundle), "ARTIFACT_IMPORT_MISMATCH", "loader")

    @pytest.mark.parametrize("extra", [["--implementation-bundle", "other.zip"], ["--manifest", "real.json"],
                                      ["--verified", "true"], ["--allow-stale"], ["--skip-validation"]])
    def test_unimplemented_or_bypass_options_are_rejected(self, bundle_factory, extra):
        bundle = bundle_factory()
        _failure(_run(bundle, args=[*_arguments(bundle), *extra]), "INVALID_ARTIFACT_INPUT", "cli")

    def test_missing_required_cli_arguments(self, bundle_factory):
        bundle = bundle_factory()
        _failure(_run(bundle, args=[]), "INVALID_ARTIFACT_INPUT", "cli")


def _paused_bundle(bundle_factory):
    source = ("import sys\nprint('TEST_ONLY_HANDLE_HELD',file=sys.stderr,flush=True)\n"
              "if sys.stdin.readline() != 'CONTINUE\\n':\n    raise RuntimeError('test-only synchronization ended')\n")
    return bundle_factory(sources={"backend/z_last.py": source})


def _start_paused(bundle, *, holder=False):
    if holder:
        script = ("import sys\nf=open(sys.argv[1],'r+b')\n"
                  "print('TEST_ONLY_HANDLE_HELD',file=sys.stderr,flush=True)\n"
                  "sys.stdin.readline()\nf.close()\n")
        command = [sys.executable, *FLAGS, "-c", script, str(bundle.path)]
    else:
        command = [sys.executable, *FLAGS, str(BOOTSTRAP), *_arguments(bundle)]
    process = subprocess.Popen(command, cwd=bundle.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=CREATION_FLAGS)
    lines = queue.Queue()

    def read_until_ready():
        for line in process.stderr:
            lines.put(line)
            if line.rstrip() == "TEST_ONLY_HANDLE_HELD":
                return
        lines.put(None)

    reader = threading.Thread(target=read_until_ready, daemon=True)
    reader.start()
    try:
        line = lines.get(timeout=10)
        assert line == "TEST_ONLY_HANDLE_HELD\n", line
        reader.join(timeout=5)
        assert not reader.is_alive()
        return process
    except BaseException:
        _stop(process)
        reader.join(timeout=5)
        raise


def _stop(process):
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=10)


def _mutate(bundle, operation):
    destination = bundle.root / "renamed.zip"
    replacement = bundle.root / "replacement.zip"
    replacement.write_bytes(b"test-only-replacement")
    script = (
        "from pathlib import Path\nimport os,sys\np=Path(sys.argv[1]); op=sys.argv[2]\n"
        "try:\n"
        " if op == 'write':\n  with p.open('r+b') as f: f.write(b'X')\n"
        " elif op == 'overwrite': p.write_bytes(b'X')\n"
        " elif op == 'delete': p.unlink()\n"
        " elif op == 'rename': p.rename(sys.argv[3])\n"
        " elif op == 'replace': os.replace(sys.argv[4],p)\n"
        "except OSError as exc:\n print('DENIED',exc.errno,getattr(exc,'winerror',None));sys.exit(3)\n"
        "print('CHANGED')\n"
    )
    return subprocess.run([sys.executable, *FLAGS, "-c", script, str(bundle.path), operation,
                           str(destination), str(replacement)], capture_output=True, text=True, encoding="utf-8",
                          timeout=10, creationflags=CREATION_FLAGS)


@NATIVE
class TestWindowsHandleLifetime:
    @pytest.mark.parametrize("operation", ["write", "overwrite", "delete", "rename", "replace"])
    def test_real_other_process_mutation_is_denied_until_worker_exits(self, bundle_factory, operation):
        bundle = _paused_bundle(bundle_factory)
        # 사전 쓰기 접근과 같은 대상의 종료 후 변경 성공을 함께 확인한다.
        with bundle.path.open("r+b"):
            pass
        process = _start_paused(bundle)
        try:
            denied = _mutate(bundle, operation)
            assert denied.returncode == 3, (denied.stdout, denied.stderr)
            # CRT open은 errno만, MoveFileEx 기반 replace는 ACCESS_DENIED를 반환할 수 있다.
            assert denied.stdout.strip() in ("DENIED 13 None", "DENIED 13 32", "DENIED 13 5")
            # 동기화 신호는 최종 성공이 아니다. 전체 import 완료 뒤 stdout을 확인한다.
            out, err = process.communicate("CONTINUE\n", timeout=10)
            _success(SimpleNamespace(returncode=process.returncode, stdout=out, stderr=err))
        finally:
            _stop(process)
        changed = _mutate(bundle, operation)
        assert changed.returncode == 0, (changed.stdout, changed.stderr)
        assert changed.stdout.strip() == "CHANGED"

    def test_existing_writer_blocks_protection_and_failure_cleans_up(self, bundle_factory):
        bundle = bundle_factory()
        writer = _start_paused(bundle, holder=True)
        try:
            _failure(_run(bundle), "ARTIFACT_LOCK_UNAVAILABLE", "bundle")
            writer.communicate("CONTINUE\n", timeout=10)
        finally:
            _stop(writer)
        _success(_run(bundle))

    @pytest.mark.parametrize("end", ["kill", "timeout", "import_failure"])
    def test_termination_timeout_and_failure_release_native_handle(self, bundle_factory, end):
        bundle = _paused_bundle(bundle_factory)
        process = _start_paused(bundle)
        try:
            if end == "import_failure":
                out, err = process.communicate("FAIL\n", timeout=10)
                _failure(SimpleNamespace(returncode=process.returncode, stdout=out, stderr=err), "ARTIFACT_IMPORT_MISMATCH")
            elif end == "timeout":
                with pytest.raises(subprocess.TimeoutExpired):
                    process.wait(timeout=0.05)
            else:
                process.kill()
        finally:
            _stop(process)
        changed = _mutate(bundle, "write")
        assert changed.returncode == 0, (changed.stdout, changed.stderr)

    def test_native_createfile_writer_reports_sharing_violation(self, bundle_factory):
        bundle = _paused_bundle(bundle_factory)
        script = (
            "import ctypes,sys\nfrom ctypes import wintypes\n"
            "k=ctypes.WinDLL('kernel32',use_last_error=True)\n"
            "f=k.CreateFileW;f.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,"
            "wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE);f.restype=wintypes.HANDLE\n"
            "c=k.CloseHandle;c.argtypes=(wintypes.HANDLE,);c.restype=wintypes.BOOL\n"
            "h=f(sys.argv[1],0x40000000,7,None,3,0x80,None)\n"
            "if h==ctypes.c_void_p(-1).value:\n print(ctypes.get_last_error());sys.exit(3)\n"
            "c(h)\nprint('OPENED')\n"
        )

        def attempt():
            return subprocess.run([sys.executable, *FLAGS, "-c", script, str(bundle.path)],
                                  capture_output=True, text=True, encoding="utf-8", timeout=10,
                                  creationflags=CREATION_FLAGS)

        assert attempt().stdout.strip() == "OPENED"
        process = _start_paused(bundle)
        try:
            denied = attempt()
            assert denied.returncode == 3 and denied.stdout.strip() == "32"
            out, err = process.communicate("CONTINUE\n", timeout=10)
            _success(SimpleNamespace(returncode=process.returncode, stdout=out, stderr=err))
        finally:
            _stop(process)
        assert attempt().stdout.strip() == "OPENED"
