"""Private recovery descriptors retain owner identity without deleting inputs."""

import importlib
import json
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(
    os.environ.get("SCITEX_PREFLIGHT_TEST_ROOT", Path(__file__).resolve().parents[2])
)
sys.path.insert(0, str(ROOT / "scripts/deploy"))
preserve = importlib.import_module(
    "_direct_bind.pending_creation"
).preserve_pending_creation


@pytest.fixture
def pending(tmp_path):
    tmp_path.chmod(0o700)
    (tmp_path / "owner.json").write_text(json.dumps({"token": "owned-token"}))
    (tmp_path / "source-canary").write_text("retained input")
    return SimpleNamespace(
        workspace=tmp_path,
        token="owned-token",
        image="sha256:fixture",
        install_name="owned-install",
        probe_name="owned-probe",
        volume="owned-volume",
        stage="create owned preparation container",
        environ={"SECRET": "not-for-output"},
    )


def test_pending_descriptor_is_private_and_keeps_inputs(pending):
    message = preserve(pending)
    marker = pending.workspace / "pending-creation.json"
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    assert json.loads(marker.read_text())["token"] == pending.token
    assert (pending.workspace / "source-canary").read_text() == "retained input"
    assert "not-for-output" not in marker.read_text() + message


def test_retaining_the_same_owned_creation_is_idempotent(pending):
    first = preserve(pending)
    before = (pending.workspace / "pending-creation.json").read_bytes()
    assert preserve(pending) == first
    assert (pending.workspace / "pending-creation.json").read_bytes() == before


def test_foreign_owner_is_refused_without_deleting_inputs(pending):
    (pending.workspace / "owner.json").write_text(
        json.dumps({"token": "another-owner"})
    )
    with pytest.raises(ValueError, match="workspace identity changed"):
        preserve(pending)
    assert not (pending.workspace / "pending-creation.json").exists()
    assert (pending.workspace / "source-canary").exists()


def test_descriptor_symlink_is_refused_without_touching_its_target(
    pending, tmp_path_factory
):
    target = tmp_path_factory.mktemp("unrelated-owner") / "outside-descriptor"
    target.write_text("unrelated input")
    (pending.workspace / "pending-creation.json").symlink_to(target)
    with pytest.raises(ValueError, match="not a regular file"):
        preserve(pending)
    assert target.read_text() == "unrelated input"
