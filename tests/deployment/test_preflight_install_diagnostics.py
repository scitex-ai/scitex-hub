"""Keep failed prospective-install output private, including expired installs."""

import importlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(
    os.environ.get("SCITEX_PREFLIGHT_TEST_ROOT", Path(__file__).resolve().parents[2])
)
sys.path.insert(0, str(ROOT / "scripts/deploy"))
target = importlib.import_module("_direct_bind.target")
TargetUnreachable = importlib.import_module("preflight_targets").TargetUnreachable


@pytest.mark.guards(
    defect="A timed-out editable install dropped captured diagnostics instead of retaining them privately."
)
@pytest.mark.parametrize("expires", [False, True], ids=["failed", "expired"])
def test_failed_install_keeps_private_output_and_runs_owned_cleanup(
    tmp_path, monkeypatch, expires
):
    # Arrange: Docker operations are owned fixtures; the install child is real.
    real_run = subprocess.run
    cleaned = []
    calls = []
    workspace = tmp_path / "owned-workspace"
    stdout_marker = b"private-stdout-canary\n"
    stderr_marker = b"private-stderr-canary\n"
    child = (
        "import sys,time; sys.stdin.buffer.read(); "
        "sys.stdout.buffer.write(" + repr(stdout_marker) + "); sys.stdout.flush(); "
        "sys.stderr.buffer.write("
        + repr(stderr_marker)
        + "); sys.stderr.flush(); "
        + ("time.sleep(10)" if expires else "sys.exit(2)")
    )

    def make_workspace(**kwargs):
        workspace.mkdir()
        return str(workspace)

    def docker_run(argv, **kwargs):
        assert argv[0] == "docker"
        if argv[1:3] == ["exec", "-i"]:
            assert argv[-2:] == ["python3", "/preflight-profile.py"]
            calls.append(kwargs)
            return real_run([sys.executable, "-I", "-S", "-c", child], **kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(target.tempfile, "mkdtemp", make_workspace)
    monkeypatch.setattr(target.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(
        target.subprocess,
        "check_output",
        lambda *args, **kwargs: json.dumps([{"Id": "sha256:owned"}]).encode(),
    )
    monkeypatch.setattr(target.subprocess, "run", docker_run)
    monkeypatch.setattr(target.snapshot, "prepare", lambda *args: ({}, []))
    monkeypatch.setattr(
        target.DirectBindTarget, "_close", lambda self: cleaned.append(self.token)
    )
    deadline = 0.2

    # Act: a failed or expired install must still refuse preparation.
    with pytest.raises(TargetUnreachable) as error:
        target.DirectBindTarget(
            SimpleNamespace(image="owned:fixture", direct_sources={}), deadline
        )

    # Assert: preserve bytes privately, keep the deadline, and clean owned state.
    logs = list(tmp_path.glob("scitex-hub-preflight-*.private.log"))
    assert len(logs) == 1
    assert logs[0].read_bytes() == stdout_marker + stderr_marker
    assert stat.S_IMODE(logs[0].stat().st_mode) == 0o600
    assert str(logs[0]) in str(error.value)
    assert "private-stdout-canary" not in str(error.value)
    assert "private-stderr-canary" not in str(error.value)
    assert calls[0]["timeout"] == deadline
    assert set(json.loads(calls[0]["input"])) == {"sources", "uid", "gid"}
    assert len(cleaned) == 1


@pytest.mark.guards(
    defect="An owned cleanup failure hid the original prospective preparation failure."
)
def test_cleanup_failure_retains_both_causes_privately(tmp_path, monkeypatch):
    workspace = tmp_path / "owned-workspace"
    workspace.mkdir()
    monkeypatch.setattr(target.tempfile, "mkdtemp", lambda **kwargs: str(workspace))
    monkeypatch.setattr(target.tempfile, "tempdir", str(tmp_path))

    def fail_preparation(self, context):
        raise subprocess.CalledProcessError(
            2,
            ["docker", "create", "owned-fixture"],
            output=b"private-preparation-stdout",
            stderr=b"private-preparation-stderr",
        )

    def fail_cleanup(self):
        raise RuntimeError("private-cleanup-cause")

    monkeypatch.setattr(target.DirectBindTarget, "_prepare", fail_preparation)
    monkeypatch.setattr(target.DirectBindTarget, "_close", fail_cleanup)
    with pytest.raises(TargetUnreachable) as error:
        target.prepare(SimpleNamespace(), 300)

    logs = list(tmp_path.glob("scitex-hub-preflight-*.private.log"))
    assert len(logs) == 1
    payload = logs[0].read_bytes()
    for marker in (
        b"private-preparation-stdout",
        b"private-preparation-stderr",
        b"private-cleanup-cause",
    ):
        assert marker in payload
        assert marker.decode() not in str(error.value)
    assert stat.S_IMODE(logs[0].stat().st_mode) == 0o600
    assert str(logs[0]) in str(error.value)
