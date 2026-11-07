"""Direct-source policy and real Git snapshot controls; no serving mutations."""

import copy
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(
    os.environ.get("SCITEX_PREFLIGHT_TEST_ROOT", Path(__file__).resolve().parents[2])
)
DEPLOY = ROOT / "scripts/deploy"
sys.path.insert(0, str(DEPLOY))
environment = importlib.import_module("preflight_environment")
TargetUnreachable = importlib.import_module("preflight_targets").TargetUnreachable


def _document(tmp_path):
    app = tmp_path / "hub"
    app.mkdir()
    script = app / "deployment/docker/docker_dev/install_ecosystem.sh"
    script.parent.mkdir(parents=True)
    script.write_bytes(
        (
            DEPLOY.parent.parent / "deployment/docker/docker_dev/install_ecosystem.sh"
        ).read_bytes()
    )
    (app / "pyproject.toml").write_text(
        '[project]\nname="scitex-hub"\nversion="0.22.0a6"\n'
    )
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    (sdk / "pyproject.toml").write_text(
        '[project]\nname="scitex-sdk"\nversion="0.3.23"\n'
    )
    mounts = [
        {"type": "bind", "source": str(app), "target": "/app"},
        {"type": "bind", "source": str(sdk), "target": "/scitex-sdk"},
        {"type": "bind", "source": str(tmp_path / "empty"), "target": "/scitex-io"},
        {
            "type": "bind",
            "source": str(tmp_path / "private-users"),
            "target": "/app/data/users",
        },
    ]
    return {
        "name": "scitex-hub-dev",
        "services": {
            role: {
                "image": "owned-image:future",
                "environment": {"NEVER_EXPOSE": "private-marker"},
                "entrypoint": [
                    "/usr/bin/tini",
                    "--",
                    "/app/deployment/docker/docker_dev/entrypoint.sh",
                ],
                "volumes": copy.deepcopy(mounts),
            }
            for role in environment.PYTHON_ROLES
        },
    }


def test_direct_bound_development_uses_complete_prospective_profile(tmp_path):
    context = environment.parse_context(_document(tmp_path))
    assert context.mode == "direct-bind"
    assert environment.choose_target(context) == ("direct-bind", None)
    assert set(context.direct_sources) == {"/app", "/scitex-sdk"}
    assert context.direct_sources["/app"]["extras"] == "[all]"
    assert context.direct_sources["/scitex-sdk"]["extras"] == ""
    assert "private-marker" not in str(context.summary())


@pytest.mark.parametrize(
    "replacement", ["image:bare", "container:serving", "local", "cmd:other"]
)
def test_direct_bound_profile_cannot_be_replaced_by_a_bare_or_current_target(
    tmp_path, replacement
):
    context = environment.parse_context(_document(tmp_path))
    with pytest.raises(TargetUnreachable, match="complete prospective profile"):
        environment.choose_target(context, replacement)


@pytest.mark.parametrize(
    "target", ["/app/src", "/app/config", "/usr/local/lib/python3.11/site-packages"]
)
def test_unmodelled_python_overlay_is_refused(tmp_path, target):
    document = _document(tmp_path)
    document["services"]["celery_worker"]["volumes"].append(
        {"type": "bind", "source": "/owned", "target": target}
    )
    with pytest.raises(TargetUnreachable, match="overlay"):
        environment.parse_context(document)


def test_roles_must_share_the_same_package_source(tmp_path):
    document = _document(tmp_path)
    document["services"]["celery_beat"]["volumes"][1]["source"] = "/different-source"
    with pytest.raises(TargetUnreachable, match="source binds disagree"):
        environment.parse_context(document)


def test_direct_bound_remote_context_never_reads_local_lookalike_sources(tmp_path):
    with pytest.raises(TargetUnreachable, match="Docker host"):
        environment.parse_context(_document(tmp_path), allow_direct=False)


def test_non_development_missing_mode_is_still_refused(tmp_path):
    document = _document(tmp_path)
    document["name"] = "scitex-hub-prod"
    with pytest.raises(TargetUnreachable, match="explicitly declare"):
        environment.parse_context(document)


def test_canonical_extras_are_kept_without_a_reduced_profile():
    from _direct_bind.context import requested_roots

    rows = requested_roots(
        (
            DEPLOY.parent.parent / "deployment/docker/docker_dev/install_ecosystem.sh"
        ).read_text()
    )
    expected = {
        "/app": "[all]",
        "/scitex-python": "[all]",
        "/figrecipe": "[all]",
        "/scitex-writer": "[all]",
        "/scitex-scholar": "[all]",
        "/scitex-dev": "[all]",
        "/scitex-agent-container": "[gui]",
        "/scitex-live-paper": "[server]",
    }
    assert {name: rows[name]["extras"] for name in expected} == expected


def test_real_git_snapshot_keeps_identity_and_rejects_later_source_changes(tmp_path):
    from _direct_bind import snapshot

    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", str(source)], check=True, capture_output=True)
    snapshot.git(source, "config", "user.name", "Owned fixture")
    snapshot.git(source, "config", "user.email", "fixture@example.invalid")
    original = '[project]\nname="owned-fixture"\nversion="1.0.0"\n'
    (source / "pyproject.toml").write_text(original)
    snapshot.git(source, "add", "pyproject.toml")
    snapshot.git(source, "commit", "-m", "Owned fixture")
    destination = tmp_path / "snapshots"
    destination.mkdir()
    rows, objects = snapshot.prepare(
        {"/app": {"source": str(source), "extras": "[all]"}}, destination
    )
    assert Path(rows["/app"]["snapshot"], "pyproject.toml").read_text() == original
    assert rows["/app"]["head"] == snapshot.git(source, "rev-parse", "HEAD")
    assert str(source / ".git/objects") in objects
    snapshot.verify(rows)
    (source / "pyproject.toml").write_text(original.replace("1.0.0", "2.0.0"))
    with pytest.raises(ValueError, match="commit development source"):
        snapshot.verify(rows)
    assert Path(rows["/app"]["snapshot"], "pyproject.toml").read_text() == original
