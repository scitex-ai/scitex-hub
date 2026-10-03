"""Exercise the real root launcher with disposable paths and mutation sentinels."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[5] / "deployment/docker/common/scripts/root-init.sh"


def _launcher(tmp_path, mode, verifier_status=0, python_mode="editable", source_text=None):
    app = tmp_path / "app"
    (app / "staticfiles/vite").mkdir(parents=True)
    (app / "staticfiles/vite/frozen.js").write_text("retained producer")
    (app / "staticfiles/runtime").mkdir()
    (app / "staticfiles/runtime/collected.css").write_text("runtime output")
    for relative in (".apps", ".cache/uv", ".cache/npm", "data", "logs", "run", ".scitex"):
        (app / relative).mkdir(parents=True, exist_ok=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    trace = tmp_path / "commands.jsonl"
    script = tmp_path / "root-init.sh"
    script.write_text(re.sub(r"/app(?=/|[\s\"'])", str(app), source_text or SOURCE.read_text()).replace(
        "/host/etc/passwd", str(tmp_path / "absent-passwd")))
    sentinel = (
        f"#!{sys.executable}\nimport json,os,sys\n"
        "name=os.path.basename(sys.argv[0])\n"
        "with open(os.environ['TRACE'],'a') as f: f.write(json.dumps([name,*sys.argv[1:]])+'\\n')\n"
        "if name=='python3': sys.exit(int(os.environ['VERIFY_STATUS']))\n"
        "if name=='stat': print('root')\n"
        "if name=='find':\n"
        " args=sys.argv[1:]\n"
        " args=[('999999' if x=='scitex' else '-uid' if x=='-user' else x) for x in args]\n"
        " os.execv('/usr/bin/find',['find',*args])\n"
    )
    for command in ("python3", "mkdir", "chown", "chmod", "gosu", "find", "stat", "rm",
                    "usermod", "groupmod", "groupadd", "pkill"):
        path = bin_dir / command
        path.write_text(sentinel)
        path.chmod(0o755)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "TRACE": str(trace),
           "VERIFY_STATUS": str(verifier_status), "SCITEX_APPS_BOOT_MODE": mode,
           "SCITEX_APPS_PYTHON_MODE": python_mode,
           "SCITEX_APPS_BOOT_MANIFEST": str(tmp_path / "public.json"),
           "SCITEX_APPS_BOOT_MANIFEST_SHA256": "a" * 64,
           "SCITEX_APPS_BOOT_PROFILE": "reviewed-v3"}
    result = subprocess.run(["/bin/bash", str(script), "entrypoint"], env=env,
                            capture_output=True, text=True, timeout=20)
    rows = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    return result, rows, app


@pytest.mark.parametrize("mode,status", [("immutable", 2), ("invalid", 0)])
def test_guard_refuses_before_identity_or_filesystem_mutation(tmp_path, mode, status):
    # Arrange: a refused authority or unknown mode with every mutation traced.
    allowed = {"python3"} if mode == "immutable" else set()
    # Act: execute the actual launcher against disposable path substitutions.
    result, rows, _app = _launcher(tmp_path, mode, status)
    # Assert: refusal precedes all mutation and privilege-drop commands.
    assert result.returncode != 0 and {row[0] for row in rows} <= allowed


def test_immutable_guard_uses_exact_apps_cli_before_runtime_mutation(tmp_path):
    # Arrange: an accepted verifier sentinel and public manifest authority.
    expected = ["python3", "-I", "-S", "-B", str(tmp_path / "app/scripts/apps/verify_immutable_boot.py"),
                "--manifest", str(tmp_path / "public.json"), "--sha256", "a" * 64,
                "--profile", "reviewed-v3", "--project-root", str(tmp_path / "app")]
    # Act: run the real launcher and inspect its first external command.
    _result, rows, _app = _launcher(tmp_path, "immutable")
    # Assert: the isolated approved verifier runs first with exact authority.
    assert rows[0] == expected


def test_immutable_preserves_producers_and_prunes_vite_from_static_chown(tmp_path):
    # Arrange: stale frozen Vite output beside collected runtime output.
    forbidden = ("node_modules", "/.apps", "/.cache", "site-packages", "/usr/local/bin", "/vite")
    # Act: execute actual find pruning, recording rather than applying chown.
    result, rows, app = _launcher(tmp_path, "immutable")
    mutations = [row for row in rows if row[0] in {"mkdir", "chown", "chmod", "rm"}]
    static = [row for row in mutations if any(str(app / "staticfiles") in arg for arg in row[1:])]
    # Assert: producer paths are untouched and runtime static ownership is non-recursive.
    assert (result.returncode == 0 and static and
            all("-R" not in row and "-r" not in row for row in static) and
            not any(any(part in arg for part in forbidden) for row in mutations for arg in row[1:]))


def test_immutable_keeps_runtime_data_logs_and_final_privilege_drop(tmp_path):
    # Arrange: only producer mutations are prohibited in this mode.
    # Act: observe actual command boundaries after successful verification.
    result, rows, app = _launcher(tmp_path, "immutable")
    created = {arg for row in rows if row[0] == "mkdir" for arg in row[1:]}
    # Assert: runtime leaves and the existing entrypoint ABI are retained.
    assert (result.returncode == 0 and {str(app / "data/slurm"), str(app / "logs"),
            str(app / "run"), str(app / ".scitex/hub/runtime/logs")} <= created and
            rows[-1] == ["gosu", "scitex", "entrypoint"])


def test_legacy_image_only_uses_existing_separate_verifier(tmp_path):
    # Arrange: the historical Python mode is independent of BOOT immutable.
    # Act: exercise the unchanged legacy path through command sentinels.
    _result, rows, _app = _launcher(tmp_path, "legacy", python_mode="image-only")
    verifiers = [row for row in rows if row[0] == "gosu" and "python" in row]
    # Assert: the original image dependency verifier still owns this mode.
    assert verifiers == [["gosu", "scitex", "python",
                          "/opt/scitex-image-contract/scripts/deploy/verify_image_dependency_contract.py"]]


@pytest.mark.parametrize("python_mode", ["editable", "image-only"])
def test_legacy_commands_match_frozen_original_launcher(tmp_path, python_mode):
    # Arrange: compare against the exact approved base rather than an expected mock list.
    baseline = subprocess.run(["git", "show",
        "eb89f0c4a8fb3f44424805f5f2955d31410536c4:deployment/docker/common/scripts/root-init.sh"],
        cwd=SOURCE.parents[4], capture_output=True, text=True, check=True, timeout=7).stdout
    # Act: execute both real launchers through the identical mutation sentinel.
    old, old_rows, _app = _launcher(tmp_path / "old", "legacy", python_mode=python_mode, source_text=baseline)
    new, new_rows, _app = _launcher(tmp_path / "new", "legacy", python_mode=python_mode)
    def normalize(rows, base):
        return [[arg.replace(str(base), "FIXTURE") for arg in row] for row in rows]
    # Assert: default legacy retains both producer behavior and entrypoint ABI.
    assert old.returncode == new.returncode and normalize(old_rows, tmp_path / "old") == normalize(new_rows, tmp_path / "new")
