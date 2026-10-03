"""Measure real disposable site bindings rather than trusting equal versions."""

import hashlib
import importlib.abc
import importlib.util
import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def state_scope():
    with pytest.MonkeyPatch.context() as scope:
        yield scope


@pytest.fixture
def probe():
    path = Path(__file__).resolve().parents[2] / "scripts/deploy/preflight_probe.py"
    spec = importlib.util.spec_from_file_location("tested_preflight_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def snapshot(tmp_path, state_scope, probe):
    project, installed, binary = (tmp_path / name for name in ("app", "site", "bin"))
    installed.mkdir()
    binary.mkdir()
    roots = [{"id": "site", "kind": "python-site", "path": str(installed)},
             {"id": "bin", "kind": "python-bin", "path": str(binary)}]
    rows = []
    for name in sorted(probe.APP_DISTRIBUTIONS):
        module = name.replace("-", "_")
        info = installed / (module + "-1.0.dist-info")
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n")
        (info / "entry_points.txt").write_text(f"[console_scripts]\n{name} = {module}._cli:main\n")
        mode = "wheel" if name == "scitex-storage" else "editable"
        if mode == "wheel":
            package = installed / module
            pointer = {"root": "site", "path": module}
        else:
            source = project / ".apps" / name
            package = source / "src" / module
            roots.append({"id": name, "kind": "app-source", "path": str(source)})
            pointer = {"root": name, "path": "src/" + module}
            (installed / (module + ".pth")).write_text(str(source / "src") + "\n")
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("VERSION = '1.0'\n")
        (package / "_cli.py").write_text("def main():\n    raise RuntimeError('must never execute CLI')\n")
        wrapper = binary / name
        wrapper.write_text(f"#!{sys.executable}\nfrom {module}._cli import main\nmain()\n")
        paths = [info / "METADATA", info / "entry_points.txt", wrapper]
        if mode == "wheel":
            paths.extend([package / "__init__.py", package / "_cli.py"])
        (info / "RECORD").write_text("".join(os.path.relpath(path, installed) + ",,\n" for path in paths))
        rows.append({"name": name, "version": "1.0", "mode": mode, "package": pointer,
                     "metadata": {"root": "site", "path": info.name},
                     "console_scripts": [{"root": "bin", "path": name}]})
        for cached in list(sys.modules):
            if cached == module or cached.startswith(module + "."):
                state_scope.delitem(sys.modules, cached)
    # Let Python's real .pth reader establish the five editable bindings. The
    # preflight itself must neither synthesize nor prepend those paths.
    state_scope.setattr(sys, "path", [path for path in sys.path
                                      if path.startswith(sys.base_prefix + "/lib/python") and
                                      "site-packages" not in path and "dist-packages" not in path])
    site.addsitedir(str(installed))
    _inventory_fixture_roots(roots)
    yield {"schema": "scitex.apps.immutable-boot/v1", "profile": "reviewed-v3",
           "roots": roots, "distributions": rows, "absent": []}
    for cached in list(sys.modules):
        if any(cached == name.replace("-", "_") or cached.startswith(name.replace("-", "_") + ".")
               for name in probe.APP_DISTRIBUTIONS):
            sys.modules.pop(cached, None)


def _inventory_fixture_roots(roots):
    for root in roots:
        path = Path(root["path"])
        root["members"] = [{"path": str(file.relative_to(path)), "type": "file",
                            "size": file.stat().st_size,
                            "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
                           for file in path.rglob("*") if file.is_file()]


def test_real_site_retains_five_editables_and_storage_wheel(snapshot, probe):
    # Arrange: five genuine .pth source bindings and a sixth installed package.
    expected = {name: "wheel" if name == "scitex-storage" else "editable"
                for name in probe.APP_DISTRIBUTIONS}
    # Act: measure real imports, metadata and wrappers without calling a CLI.
    actual = probe._active_bindings(snapshot)
    # Assert: each incumbent remains bound to its declared mode and exact owner.
    assert {name: row["mode"] for name, row in actual.items() if row["verified"]} == expected


@pytest.mark.parametrize("drift", ["clone", "duplicate-metadata", "foreign-console", "wrong-call", "wrong-interpreter", "missing-callable"])
def test_equal_storage_version_does_not_mask_origin_or_console_drift(snapshot, probe, tmp_path, drift):
    # Arrange: retain 1.0 while corrupting one independent active binding.
    _storage_drift(snapshot, tmp_path, drift)
    # Act: ask the actual resolver, not a version mock.
    actual = probe._active_bindings(snapshot)["scitex-storage"]["verified"]
    # Assert: same-version binding drift refuses.
    assert actual is False


def _storage_drift(snapshot, tmp_path, drift):
    installed = Path(snapshot["roots"][0]["path"])
    binary = Path(snapshot["roots"][1]["path"])
    if drift == "clone":
        clone = tmp_path / "stale-storage/src/scitex_storage"
        clone.mkdir(parents=True)
        (clone / "__init__.py").write_text("VERSION = '1.0'\n")
        sys.path.insert(0, str(clone.parent))
    elif drift == "duplicate-metadata":
        shutil.copytree(installed / "scitex_storage-1.0.dist-info", installed / "scitex_storage-stale.dist-info")
    elif drift == "foreign-console":
        record = installed / "scitex_writer-1.0.dist-info/RECORD"
        record.write_text(record.read_text() + os.path.relpath(binary / "scitex-storage", installed) + ",,\n")
    elif drift == "wrong-call":
        (binary / "scitex-storage").write_text(f"#!{sys.executable}\nfrom scitex_storage._cli import main\nprint('echo')\n")
    elif drift == "missing-callable":
        (installed / "scitex_storage/_cli.py").write_text("main = None\n")
        _inventory_fixture_roots(snapshot["roots"])
    else:
        (binary / "scitex-storage").write_text("#!/wrong/python\nfrom scitex_storage._cli import main\nmain()\n")


def test_dynamic_foreign_finder_cannot_replace_verified_storage(snapshot, probe, tmp_path, state_scope):
    # Arrange: an unrecognized synthetic finder, without a stale path on sys.path.
    foreign = tmp_path / "foreign/scitex_storage/__init__.py"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("VERSION = '1.0'\n")

    class ForeignFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "scitex_storage":
                return importlib.util.spec_from_file_location(fullname, foreign)
            return None

    state_scope.setattr(sys, "meta_path", [ForeignFinder(), *sys.meta_path])
    # Act: perform the genuine import through this finder.
    actual = probe._active_bindings(snapshot)["scitex-storage"]["verified"]
    # Assert: dynamic import ownership must agree with the pinned wheel.
    assert actual is False


def _pinned(snapshot, tmp_path, state_scope):
    path = tmp_path / "public.json"
    data = json.dumps(snapshot).encode()
    path.write_bytes(data)
    state_scope.setenv("SCITEX_APPS_BOOT_MODE", "immutable")
    state_scope.setenv("SCITEX_APPS_BOOT_MANIFEST", str(path))
    state_scope.setenv("SCITEX_APPS_BOOT_MANIFEST_SHA256", hashlib.sha256(data).hexdigest())
    state_scope.setenv("SCITEX_APPS_BOOT_PROFILE", "reviewed-v3")
    return path


@pytest.mark.parametrize("drift", ["digest", "profile", "storage-editable", "writer-wheel", "missing-sibling", "duplicate-sibling"])
def test_snapshot_rechecks_pin_and_retained_mode_contract(snapshot, probe, tmp_path, state_scope, drift):
    # Arrange: the external verifier success cannot bypass the post-verification CAS.
    path = _pinned(snapshot, tmp_path, state_scope)
    _authority_drift(path, state_scope, drift)
    state_scope.setattr(probe.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0))
    # Act: re-read the exact immutable authority after the verifier boundary.
    actual, _manifest = probe._boot_snapshot(tmp_path)
    # Assert: no unchecked mode, omitted producer or changed pin is admitted.
    assert actual["verified"] is False


def _authority_drift(path, state_scope, drift):
    if drift == "digest":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        changed = json.loads(path.read_bytes())
        if drift == "profile":
            changed["profile"] = "another-profile"
        elif drift == "missing-sibling":
            changed["distributions"].pop()
        elif drift == "duplicate-sibling":
            changed["distributions"].append(changed["distributions"][0])
        else:
            name, mode = ("scitex-storage", "editable") if drift == "storage-editable" else ("scitex-writer", "wheel")
            next(row for row in changed["distributions"] if row["name"] == name)["mode"] = mode
        data = json.dumps(changed).encode()
        path.write_bytes(data)
        state_scope.setenv("SCITEX_APPS_BOOT_MANIFEST_SHA256", hashlib.sha256(data).hexdigest())


def test_failed_authority_never_prepends_or_imports(tmp_path, probe, state_scope, capsys):
    # Arrange: missing target authority and a module that would visibly execute.
    (tmp_path / "untrusted.py").write_text("raise RuntimeError('must not import')\n")
    state_scope.setenv("SCITEX_APPS_BOOT_MODE", "immutable")
    state_scope.delenv("SCITEX_APPS_BOOT_MANIFEST", raising=False)
    state_scope.setattr(probe.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 2))
    before = list(sys.path)
    # Act: invoke the real report path with a legacy clone request and import.
    probe._run({"extra_syspath": [str(tmp_path)], "import_probes": [{"module": "untrusted"}]})
    report = json.loads(capsys.readouterr().out.split(probe.REPORT_BEGIN)[1].split(probe.REPORT_END)[0])
    # Assert: refusal precedes path injection and all imports.
    assert sys.path == before and report["imports"] == [] and report["boot"]["verified"] is False


def test_immutable_report_never_prepends_even_valid_editable_sources(snapshot, probe, state_scope, capsys):
    # Arrange: genuine site bindings already provide every producer.
    state_scope.setattr(probe, "_boot_snapshot", lambda: ({"mode": "immutable", "verified": True}, snapshot))
    before = list(sys.path)
    # Act: use the actual report path with a stale requested clone.
    probe._run({"extra_syspath": ["/app/.apps/scitex-storage/src"]})
    report = json.loads(capsys.readouterr().out.split(probe.REPORT_BEGIN)[1].split(probe.REPORT_END)[0])
    # Assert: active site ownership succeeds without any synthetic clone overlay.
    assert sys.path == before and report["overlay"] == {} and report["boot"]["verified"] is True


@pytest.fixture
def driver(state_scope):
    path = Path(__file__).resolve().parents[2] / "scripts/deploy/preflight_sibling_floors.py"
    state_scope.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("tested_preflight_driver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("report", [
    {}, {"boot": {"mode": "other"}},
    {"boot": {"mode": "immutable", "verified": False}},
    {"boot": {"mode": "immutable", "verified": True}, "bindings": {}},
])
def test_driver_refuses_missing_or_unknown_boot_evidence(driver, report):
    # Arrange: authority must be reported by the actual target.
    # Act: evaluate the independently malformed or missing evidence.
    findings = driver._evaluate_boot(report)
    # Assert: each case is a deployment refusal, never a legacy assumption.
    assert [finding.severity for finding in findings] == ["unknown"]


def test_storage_floor_uses_verified_wheel_instead_of_newer_clone(driver):
    # Arrange: a clone reports a newer version while the reviewed wheel is 1.0.
    report = {"boot": {"mode": "immutable"},
              "bindings": {"scitex-storage": {"verified": True, "version": "1.0", "mode": "wheel"}},
              "overlay": {"scitex-storage": {"version": "99.0", "clone": "stale"}}}
    # Act: choose the effective version for the normal floor comparator.
    actual = driver._effective("scitex-storage", report)
    # Assert: clone metadata cannot license immutable Storage.
    assert actual == ("1.0", "verified immutable wheel")


def test_nonzero_target_cannot_authorize_even_with_valid_json_report(driver):
    # Arrange: a real target subprocess emits a plausible report then fails.
    target = driver.targets.Target("cmd", "failed synthetic target", [sys.executable, "-c",
        "print('@@SCITEX_HUB_PREFLIGHT_REPORT_BEGIN@@');print('{}');"
        "print('@@SCITEX_HUB_PREFLIGHT_REPORT_END@@');raise SystemExit(1)"], True)
    # Act: interrogate the failed target through the actual subprocess boundary.
    # Assert: stdout never overrides process failure.
    with pytest.raises(driver.targets.TargetUnreachable, match="exited 1"):
        driver.targets.interrogate(target, "", {})


def test_post_verifier_manifest_replacement_refuses(snapshot, probe, tmp_path, state_scope):
    # Arrange: the external verification boundary is followed by a changed pin.
    path = _pinned(snapshot, tmp_path, state_scope)

    def verify_then_replace(*args, **kwargs):
        path.write_bytes(path.read_bytes() + b" ")
        return subprocess.CompletedProcess([], 0)

    state_scope.setattr(probe.subprocess, "run", verify_then_replace)
    # Act: re-read after the successful external verifier has returned.
    boot, _manifest = probe._boot_snapshot(tmp_path)
    # Assert: read-after-verification detects the replacement.
    assert boot["verified"] is False


def test_manifest_ancestor_symlink_refuses_before_read(tmp_path, probe):
    # Arrange: a valid-looking public path whose ancestor is a symlink.
    real = tmp_path / "real"
    real.mkdir()
    (real / "public.json").write_text("{}")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    # Act: use the real descriptor-relative manifest reader.
    # Assert: no ancestor symlink is followed.
    with pytest.raises(OSError):
        probe._read_manifest(alias / "public.json")


@pytest.mark.parametrize("verifier_status", [0, 2])
def test_executable_pth_runs_only_after_accepted_authority(snapshot, probe, driver, tmp_path, state_scope, verifier_status):
    # Arrange: a real executable .pth hook and a fresh isolated existing interpreter.
    pin = _pinned(snapshot, tmp_path, state_scope)
    installed = Path(snapshot["roots"][0]["path"])
    order = tmp_path / "order.txt"
    (installed / "boot_fixture_marker.py").write_text(
        f"with open({str(order)!r}, 'a') as handle: handle.write('site-hook\\n')\n")
    (installed / "zz_boot_fixture.pth").write_text("import boot_fixture_marker\n")
    code = f"""
import importlib.util,site,subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('isolated_probe',{probe.__file__!r})
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
site.getsitepackages=lambda prefixes=None:[{str(installed)!r}]
site.ENABLE_USER_SITE=False
def verifier_boundary(argv,**kwargs):
    with open({str(order)!r},'a') as handle: handle.write('verifier\\n')
    return subprocess.CompletedProcess(argv,{verifier_status})
probe.subprocess.run=verifier_boundary
probe._run({{'extra_syspath':['/app/.apps/scitex-storage/src']}})
"""
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "LANG": "C.UTF-8",
           "SCITEX_APPS_BOOT_MODE": "immutable", "SCITEX_APPS_BOOT_MANIFEST": str(pin),
           "SCITEX_APPS_BOOT_MANIFEST_SHA256": hashlib.sha256(pin.read_bytes()).hexdigest(),
           "SCITEX_APPS_BOOT_PROFILE": "reviewed-v3"}
    # Act: let real site.main process genuine .pth bindings after the guard boundary.
    result = subprocess.run(driver.targets.resolve("local").argv, input=code, env=env,
                            capture_output=True, text=True, timeout=20)
    report = json.loads(result.stdout.split(probe.REPORT_BEGIN)[1].split(probe.REPORT_END)[0])
    expected = {0: ["verifier", "site-hook"], 2: ["verifier"]}[verifier_status]
    # Assert: rejection never executes the hook; acceptance retains all six genuine bindings.
    assert (result.returncode == 0 and order.read_text().splitlines() == expected and
            report["boot"]["verified"] == (verifier_status == 0) and
            report["site_initialized_after_guard"] == (verifier_status == 0) and
            report["syspath_prepended"] == [])


def test_driver_accepts_only_complete_isolated_actual_bindings(snapshot, probe, driver):
    # Arrange: complete measured evidence from genuine site metadata and imports.
    report = {"boot": {"mode": "immutable", "verified": True, "profile": "reviewed-v3",
                       "manifest_sha256": "a" * 64}, "site_initialized_after_guard": True,
              "bindings": probe._active_bindings(snapshot)}
    # Act: evaluate the complete target evidence through the normal driver gate.
    findings = driver._evaluate_boot(report)
    # Assert: truthful complete authority and producer bindings are accepted.
    assert findings == []


def test_driver_refuses_preinitialized_site_despite_other_verified_evidence(snapshot, probe, driver):
    # Arrange: a custom runner cannot retrospectively attest its site initialization.
    report = {"boot": {"mode": "immutable", "verified": True, "profile": "reviewed-v3",
                       "manifest_sha256": "a" * 64}, "site_initialized_after_guard": False,
              "bindings": probe._active_bindings(snapshot)}
    # Act: evaluate otherwise genuine package/metadata/console evidence.
    findings = driver._evaluate_boot(report)
    # Assert: the missing pre-import boundary remains an explicit refusal.
    assert [finding.severity for finding in findings] == ["unknown"]


@pytest.mark.parametrize("target_spec", ["local", "image:synthetic-reviewed", "container:synthetic-reviewed"])
def test_builtin_target_starts_with_isolated_site_and_bytecode_disabled(tmp_path, state_scope, driver, target_spec):
    # Arrange: an available command locator, without invoking Docker or a target.
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\nexit 99\n")
    state_scope.setenv("PATH", str(tmp_path))
    # Act: resolve the real built-in target command.
    target = driver.targets.resolve(target_spec)
    # Assert: no built-in interpreter can process .pth before the probe guard.
    assert target.argv[-5:-1] == ["-I", "-S", "-B", "-c"]


@pytest.mark.parametrize("mode", [None, "", "legacy"])
@pytest.mark.parametrize("bytecode_disabled", [False, True])
def test_legacy_selector_preserves_original_stdin_import_and_site_semantics(tmp_path, driver, mode, bytecode_disabled):
    # Arrange: only cwd and declared PYTHONPATH provide these disposable modules.
    project = tmp_path / "project"
    project.mkdir()
    config = project / "config"
    config.mkdir()
    (config / "__init__.py").write_text("")
    (config / "bootstrap_fixture.py").write_text("ORIGIN = 'project'\n")
    declared = tmp_path / "declared"
    declared.mkdir()
    (declared / "env_fixture.py").write_text("ORIGIN = 'declared-PYTHONPATH'\n")
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"),
           "LANG": "C.UTF-8", "PYTHONPATH": str(declared),
           "PYTHONUSERBASE": str(tmp_path / "user-base")}
    env.update({key: value for key, value in {
        "SCITEX_APPS_BOOT_MODE": mode,
        "PYTHONDONTWRITEBYTECODE": "1" if bytecode_disabled else None,
    }.items() if value is not None})
    code = """
import config.bootstrap_fixture,env_fixture,json,site,sys
from pathlib import Path
print(json.dumps({'cwd':config.bootstrap_fixture.ORIGIN,'declared':env_fixture.ORIGIN,
 'path':sys.path,'user_site':site.ENABLE_USER_SITE,
 'flags':[sys.flags.isolated,sys.flags.no_site,sys.flags.no_user_site],
 'cache_written':[Path(m.__cached__).is_file() for m in [config.bootstrap_fixture,env_fixture]],
 'bytecode_disabled':sys.dont_write_bytecode,'payload':'received-once'}))
"""
    original = subprocess.run([sys.executable, "-"], input=code, cwd=project, env=env,
                              capture_output=True, text=True, timeout=20)
    for cache in tmp_path.rglob("__pycache__"):
        shutil.rmtree(cache)
    # Act: execute the actual built-in selector with its unchanged stdin payload.
    selected = subprocess.run(driver.targets.resolve("local").argv, input=code,
                              cwd=project, env=env, capture_output=True, text=True, timeout=20)
    # Assert: import paths, site flags and bytecode match the original interpreter.
    assert (original.returncode, selected.returncode, json.loads(selected.stdout)) == (
        0, 0, json.loads(original.stdout))


@pytest.mark.parametrize("mode", ["immutable", "unrecognized"])
def test_nonlegacy_selector_excludes_cwd_environment_and_site_before_payload(tmp_path, driver, mode):
    # Arrange: both paths contain importable sentinels outside target authority.
    (tmp_path / "cwd_fixture.py").write_text("raise RuntimeError('cwd executed')\n")
    declared = tmp_path / "declared"
    declared.mkdir()
    (declared / "env_fixture.py").write_text("raise RuntimeError('environment executed')\n")
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"), "LANG": "C.UTF-8",
           "PYTHONPATH": str(declared), "SCITEX_APPS_BOOT_MODE": mode}
    code = """
import importlib.util,json,sys
print(json.dumps({'modules':[importlib.util.find_spec(n) is None
 for n in ['cwd_fixture','env_fixture']],
 'flags':[sys.flags.isolated,sys.flags.no_site,sys.flags.no_user_site],
 'bytecode_disabled':sys.dont_write_bytecode,'payload':'received-once'}))
"""
    # Act: run the real target selector; neither sentinel may execute before the guard.
    selected = subprocess.run(driver.targets.resolve("local").argv, input=code,
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
    # Assert: the original payload reaches a still-isolated child exactly once.
    assert (selected.returncode, json.loads(selected.stdout)) == (0, {
        "modules": [True, True], "flags": [1, 1, 1],
        "bytecode_disabled": True, "payload": "received-once"})


@pytest.fixture
def hub_snapshot(snapshot, probe, state_scope):
    project = next(Path(row["path"]).parent.parent for row in snapshot["roots"]
                   if row["id"] == "scitex-cards")
    package = project / "apps"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "project_fixture.py").write_text("ORIGIN = 'verified-Hub-apps'\n")
    snapshot["roots"].append({"id": "hub", "kind": "hub", "path": str(project)})
    state_scope.setattr(probe, "HUB_PROJECT_ROOT", project)
    for name in list(sys.modules):
        if name == "apps" or name.startswith("apps."):
            state_scope.delitem(sys.modules, name)
    yield snapshot
    for name in list(sys.modules):
        if name == "apps" or name.startswith("apps."):
            sys.modules.pop(name, None)


def test_verified_hub_apps_import_retains_genuine_six_site_bindings(hub_snapshot, probe, tmp_path, state_scope, capsys):
    # Arrange: the external verifier seam accepts a pinned Hub apps root.
    _pinned(hub_snapshot, tmp_path, state_scope)
    state_scope.setattr(probe.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0))
    # Act: run normal imports after the real pin reread and active producer check.
    probe._run({"import_probes": [{"module": "apps.project_fixture"}],
                "extra_syspath": ["/app/.apps/scitex-storage/src"]})
    report = json.loads(capsys.readouterr().out.split(probe.REPORT_BEGIN)[1].split(probe.REPORT_END)[0])
    # Assert: exact Hub apps authority works independently of all six site bindings.
    assert (report["verified_hub_project_root"], report["imports"][0]["status"],
            sum(row["verified"] for row in report["bindings"].values()),
            report["syspath_prepended"], sys.modules["apps"].__file__) == (
        str(probe.HUB_PROJECT_ROOT), "ok", 6, [], str(probe.HUB_PROJECT_ROOT / "apps/__init__.py"))


@pytest.mark.parametrize("drift", ["absent", "foreign-path", "wrong-kind", "duplicate"])
def test_missing_or_conflicting_hub_authority_never_adds_project_path(hub_snapshot, probe, tmp_path, state_scope, capsys, drift):
    # Arrange: a verifier boundary alone cannot authorize an arbitrary import root.
    _hub_authority_drift(hub_snapshot, tmp_path, drift)
    _pinned(hub_snapshot, tmp_path, state_scope)
    state_scope.setattr(probe.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0))
    before = list(sys.path)
    # Act: request the genuine disposable Hub module without any clone synthesis.
    probe._run({"import_probes": [{"module": "apps.project_fixture"}]})
    report = json.loads(capsys.readouterr().out.split(probe.REPORT_BEGIN)[1].split(probe.REPORT_END)[0])
    # Assert: incomplete Hub authority remains a real missing import.
    assert (sys.path, report["verified_hub_project_root"], report["imports"][0]["status"]) == (
        before, None, "fatal")


def _hub_authority_drift(hub_snapshot, tmp_path, drift):
    hub = hub_snapshot["roots"][-1]
    if drift == "absent":
        hub_snapshot["roots"].pop()
    elif drift == "foreign-path":
        hub["path"] = str(tmp_path)
    elif drift == "wrong-kind":
        hub["kind"] = "app-source"
    else:
        hub_snapshot["roots"].append(dict(hub, id="hub-duplicate"))


@pytest.fixture
def bootstrap_snapshot(snapshot, state_scope):
    roots = {row["id"]: Path(row["path"]) for row in snapshot["roots"]}
    row = next(row for row in snapshot["distributions"] if row["name"] == "scitex-agent-container")
    source = roots[row["package"]["root"]] / "src"
    bootstrap = source / "_scitex_agent_container_bootstrap"
    bootstrap.mkdir()
    (bootstrap / "__init__.py").write_text(
        "def cli_entry_point():\n    raise RuntimeError('must never invoke CLI')\n")
    info = roots["site"] / row["metadata"]["path"]
    names = ("sac", "scitex-agent-container", "sac-statusline")
    values = ("_scitex_agent_container_bootstrap:cli_entry_point",
              "_scitex_agent_container_bootstrap:cli_entry_point",
              "scitex_agent_container._cli:main")
    (info / "entry_points.txt").write_text("[console_scripts]\n" + "".join(
        f"{name} = {value}\n" for name, value in zip(names, values, strict=True)))
    wrappers = []
    for name, value in zip(names, values, strict=True):
        module, attribute = value.split(":")
        wrapper = roots["bin"] / name
        wrapper.write_text(f"#!{sys.executable}\nfrom {module} import {attribute}\n{attribute}()\n")
        wrappers.append(wrapper)
    row["console_scripts"] = [{"root": "bin", "path": name} for name in names]
    record = info / "RECORD"
    record.write_text(record.read_text() + "".join(
        os.path.relpath(path, roots["site"]) + ",,\n" for path in wrappers if path.name != "scitex-agent-container"))
    _inventory_fixture_roots(snapshot["roots"])
    for name in list(sys.modules):
        if name == "_scitex_agent_container_bootstrap" or name.startswith("_scitex_agent_container_bootstrap."):
            state_scope.delitem(sys.modules, name)
    yield snapshot
    sys.modules.pop("_scitex_agent_container_bootstrap", None)


def test_same_producer_verified_top_level_bootstrap_retains_three_console_bindings(bootstrap_snapshot, probe):
    # Arrange: actual retained SAC console names point to a separately owned src module.
    expected = ["sac", "sac-statusline", "scitex-agent-container"]
    # Act: import the exact source-backed console object without calling it.
    actual = probe._active_bindings(bootstrap_snapshot)["scitex-agent-container"]
    # Assert: the bootstrap layout qualifies by its verified bytes, not package nesting.
    assert (actual["verified"], actual.get("console_scripts")) == (True, expected)


@pytest.mark.parametrize("drift", ["foreign", "missing-pin", "hash-conflict", "symlink"])
def test_bootstrap_requires_same_producer_regular_file_hash_authority(bootstrap_snapshot, probe, tmp_path, drift):
    # Arrange: corrupt one independent authority boundary while retaining console metadata.
    _bootstrap_authority_drift(bootstrap_snapshot, tmp_path, drift)
    # Act: ask the real resolver and loader to qualify its declared bootstrap.
    actual = probe._active_bindings(bootstrap_snapshot)["scitex-agent-container"]["verified"]
    # Assert: unverified source is refused before its console module is loaded.
    assert (actual, "_scitex_agent_container_bootstrap" in sys.modules) == (False, False)


def _bootstrap_authority_drift(snapshot, tmp_path, drift):
    root = next(row for row in snapshot["roots"] if row["id"] == "scitex-agent-container")
    relative = "src/_scitex_agent_container_bootstrap/__init__.py"
    path = Path(root["path"]) / relative
    if drift == "foreign":
        foreign = tmp_path / "foreign/_scitex_agent_container_bootstrap"
        foreign.mkdir(parents=True)
        (foreign / "__init__.py").write_bytes(path.read_bytes())
        sys.path.insert(0, str(foreign.parent))
    elif drift == "missing-pin":
        root["members"] = [member for member in root["members"] if member["path"] != relative]
    elif drift == "hash-conflict":
        path.write_text("raise RuntimeError('unverified bytes must not execute')\n")
    else:
        moved = path.with_name("original.py")
        path.rename(moved)
        path.symlink_to(moved.name)
