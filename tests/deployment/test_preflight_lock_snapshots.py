"""Actual Git/npm lock state survives snapshots; unrelated edits are refused."""

import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(
    os.environ.get("SCITEX_PREFLIGHT_TEST_ROOT", Path(__file__).resolve().parents[2])
)
sys.path.insert(0, str(ROOT / "scripts/deploy"))
snapshot = importlib.import_module("_direct_bind.snapshot")


@pytest.fixture
def node_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    snapshot.git(tmp_path, "init", str(source))
    snapshot.git(source, "config", "user.name", "Owned fixture")
    snapshot.git(source, "config", "user.email", "fixture@example.invalid")
    (source / "package.json").write_text('{"name":"owned-fixture"}')
    (source / "package-lock.json").write_text('{"lockfileVersion":3}')
    nested = source / "src/node"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text('{"name":"owned-nested"}')
    snapshot.git(source, "add", ".")
    snapshot.git(source, "commit", "-m", "Owned Node fixture")
    return source


def prepare(source, tmp_path):
    destination = tmp_path / "snapshots"
    destination.mkdir()
    rows, _ = snapshot.prepare(
        {"/app": {"source": str(source), "extras": ""}}, destination
    )
    return rows, Path(rows["/app"]["snapshot"])


def test_generated_tracked_and_untracked_locks_keep_their_exact_bytes(
    node_source, tmp_path
):
    tracked = b'{"lockfileVersion":3,"generated":"tracked"}\n'
    untracked = b'{"lockfileVersion":3,"generated":"new"}\n'
    (node_source / "package-lock.json").write_bytes(tracked)
    (node_source / "src/node/package-lock.json").write_bytes(untracked)
    rows, copy = prepare(node_source, tmp_path)
    assert (copy / "package-lock.json").read_bytes() == tracked
    assert (copy / "src/node/package-lock.json").read_bytes() == untracked
    assert rows["/app"]["dirty_locks"]["package-lock.json"]["status"] == " M"
    assert rows["/app"]["dirty_locks"]["src/node/package-lock.json"]["status"] == "??"
    snapshot.verify(rows)


def test_generated_locks_are_rechecked_after_installation(node_source, tmp_path):
    path = node_source / "package-lock.json"
    path.write_text('{"lockfileVersion":3,"generated":1}')
    rows, _ = prepare(node_source, tmp_path)
    path.write_text('{"lockfileVersion":3,"generated":2}')
    with pytest.raises(ValueError, match="changed"):
        snapshot.verify(rows)


@pytest.mark.parametrize("filename", ["uncommitted.py", "package.json", "secrets.json"])
def test_other_source_edits_are_not_hidden_by_the_lock_exception(
    node_source, tmp_path, filename
):
    (node_source / filename).write_text("{}")
    with pytest.raises(ValueError, match="commit development source"):
        prepare(node_source, tmp_path)


def test_current_source_lock_symlinks_cannot_read_external_files(node_source, tmp_path):
    external = tmp_path / "outside.json"
    external.write_text('{"lockfileVersion":3}')
    path = node_source / "package-lock.json"
    path.unlink()
    path.symlink_to(external)
    with pytest.raises(ValueError, match="commit development source"):
        prepare(node_source, tmp_path)
