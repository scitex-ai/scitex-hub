#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./tests/security/test_gitea_token_gitconfig.py

"""Regression gate: the Gitea ADMIN token must never land on tenant-readable disk.

Finding (``sec-gitea-admin-token-plaintext-in-user-gitconfig``)
--------------------------------------------------------------
Project provisioning cloned each user's repo with the platform Gitea ADMIN
token embedded in the URL and then ran ``git remote set-url origin
http://<user>:<TOKEN>@gitea:3000/...``. The token therefore came to rest in
``<project>/.git/config`` — and that working tree is bind-mounted read/write
into the tenant's Apptainer console at ``/workspace``. Any tenant could

    cat /workspace/.git/config

and walk away with the platform admin credential: read/write on EVERY other
tenant's repository. App submission (``_push_to_registry_branch``) leaked the
same token into the dev project's ``.git/config`` the same way.

How these tests work
--------------------
A real git origin is served over HTTP (dumb protocol, static files) and the
REAL production provisioning code is driven against it. Then we act as the
tenant: walk every byte of the resulting working tree looking for the admin
token. No mocking of the code under test, no "the function exists" checks.

Fast (~2 s, no test database): the origin is a static file server over a bare
repo and the Project is a duck-typed stand-in.
"""

from __future__ import annotations

import base64
import contextlib
import functools
import http.server
import os
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import override_settings

pytestmark = pytest.mark.security

# The platform admin credential we plant. Distinctive so a byte-scan of the
# tenant-visible tree cannot produce a false negative.
ADMIN_TOKEN = "gt0kEN-SCITEX-ADMIN-LEAK-CANARY-0123456789abcdef"
EXPECTED_BASIC = "Basic " + base64.b64encode(f"{ADMIN_TOKEN}:".encode()).decode()
OWNER = "alice"
SLUG = "my-paper"
APPS_ORG = "scitex-apps"
APP_REPO = "my-app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a real git command; raise loudly on failure (fixtures must not lie)."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


def _scan_for_token(root: Path) -> list:
    """Act as the tenant: every readable byte under the bind-mounted tree."""
    needle = ADMIN_TOKEN.encode()
    hits = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            if needle in path.read_bytes():
                hits.append(str(path.relative_to(root)))
        except OSError:
            continue
    return hits


def _make_bare_repo(served_root: Path, owner: str, repo: str) -> None:
    source = served_root.parent / f"src-{owner}-{repo}"
    source.mkdir(parents=True)
    _git("init", "-q", "-b", "main", str(source))
    (source / "README.md").write_text("hello\n")
    _git("add", "-A", cwd=source)
    _git(
        "-c", "user.email=t@example.com", "-c", "user.name=t",
        "commit", "-q", "-m", "init", cwd=source,
    )
    bare = served_root / owner / f"{repo}.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    _git("clone", "-q", "--bare", str(source), str(bare))
    _git("update-server-info", cwd=bare)


class _RecordingHandler(http.server.SimpleHTTPRequestHandler):
    """Static file server that records the Authorization header per request."""

    seen: list = []

    def do_GET(self):  # noqa: N802 - http.server API
        type(self).seen.append((self.path, self.headers.get("Authorization")))
        return super().do_GET()

    def log_message(self, *args):  # silence stderr spam
        pass


class _Owner:
    username = OWNER
    email = "alice@example.com"

    def get_full_name(self):
        return "Alice Example"


class _FakeProject:
    """Duck-typed Project — the signal only reads attributes, never the DB."""

    is_org_owned = False
    is_app = True  # skip the heavy scitex-structure scaffolding
    slug = SLUG
    owner = _Owner()
    git_clone_path = ""
    directory_created = False

    def save(self, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def no_interactive_git():
    """Guarantee git can never block on a credential prompt in this suite."""
    saved = {k: os.environ.get(k) for k in ("GIT_TERMINAL_PROMPT", "GIT_ASKPASS")}
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_ASKPASS"] = "/bin/true"
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def fake_gitea(tmp_path: Path):
    """A real git origin over HTTP, recording the Authorization header."""
    served = tmp_path / "served"
    served.mkdir()
    _make_bare_repo(served, OWNER, SLUG)
    _make_bare_repo(served, APPS_ORG, APP_REPO)

    handler_cls = type("_Handler", (_RecordingHandler,), {"seen": []})
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(handler_cls, directory=str(served))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield SimpleNamespace(
            url=f"http://127.0.0.1:{server.server_address[1]}",
            auth_headers=lambda: [a for _p, a in handler_cls.seen if a],
        )
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def provisioned_workspace(tmp_path: Path, fake_gitea):
    """Run the REAL project-provisioning code against the fake Gitea origin."""
    from apps.infra.project_app.signals.project_initialization import (
        _clone_gitea_repo_to_data_dir,
    )

    base_dir = tmp_path / "django"
    base_dir.mkdir()
    with override_settings(
        BASE_DIR=str(base_dir), GITEA_URL=fake_gitea.url, GITEA_TOKEN=ADMIN_TOKEN
    ):
        _clone_gitea_repo_to_data_dir(_FakeProject())
    return SimpleNamespace(
        project_dir=base_dir / "data" / "users" / OWNER / "proj" / SLUG,
        gitea=fake_gitea,
    )


@pytest.fixture
def registry_submission(tmp_path: Path, fake_gitea):
    """Run the REAL app-submission push against the fake Gitea origin.

    The dumb-HTTP origin is read-only, so the push itself fails — irrelevant
    here: the leak happened BEFORE the push, when the remote URL was written
    into the user-readable project's ``.git/config``.
    """
    from apps.workspace.apps_app.views import api_registry

    base_dir = tmp_path / "django"
    dev_dir = base_dir / "data" / "users" / OWNER / "proj" / APP_REPO
    dev_dir.mkdir(parents=True)
    _git("init", "-q", "-b", "main", str(dev_dir))
    (dev_dir / "app.py").write_text("# app\n")
    _git("add", "-A", cwd=dev_dir)
    _git(
        "-c", "user.email=t@example.com", "-c", "user.name=t",
        "commit", "-q", "-m", "init", cwd=dev_dir,
    )

    with override_settings(
        BASE_DIR=str(base_dir), GITEA_URL=fake_gitea.url, GITEA_TOKEN=ADMIN_TOKEN
    ):
        with contextlib.suppress(RuntimeError):
            api_registry._push_to_registry_branch(None, OWNER, APP_REPO)
    return SimpleNamespace(project_dir=dev_dir, gitea=fake_gitea)


@pytest.fixture
def legacy_poisoned_repo(tmp_path: Path) -> Path:
    """A repo cloned BEFORE the fix: origin still carries the admin token."""
    repo = tmp_path / "legacy"
    repo.mkdir()
    _git("init", "-q", "-b", "main", str(repo))
    _git(
        "remote", "add", "origin",
        f"http://{OWNER}:{ADMIN_TOKEN}@gitea:3000/{OWNER}/p.git",
        cwd=repo,
    )
    return repo


# ---------------------------------------------------------------------------
# EXPLOIT 1 — project provisioning
# ---------------------------------------------------------------------------
def test_project_provisioning_actually_clones_the_repo(provisioned_workspace):
    """Guard: without a real clone the leak assertions would be vacuous."""
    # Arrange
    config = provisioned_workspace.project_dir / ".git" / "config"
    # Act
    cloned = config.exists()
    # Assert
    assert cloned, f"no repo was cloned at {provisioned_workspace.project_dir}"


def test_project_workspace_contains_no_gitea_admin_token(provisioned_workspace):
    """THE exploit: tenant greps their bind-mounted /workspace for the token."""
    # Arrange
    project_dir = provisioned_workspace.project_dir
    # Act
    leaked = _scan_for_token(project_dir)
    # Assert
    assert not leaked, (
        "Gitea ADMIN token readable by the tenant under their bind-mounted "
        f"/workspace: {leaked}"
    )


def test_project_origin_url_carries_no_credentials(provisioned_workspace):
    """origin must be a bare URL — userinfo in origin IS the on-disk leak."""
    # Arrange
    project_dir = provisioned_workspace.project_dir
    # Act
    origin = _git("remote", "get-url", "origin", cwd=project_dir).stdout.strip()
    authority = origin.split("://", 1)[-1].split("/", 1)[0]
    # Assert
    assert "@" not in authority, f"origin still carries URL userinfo: {origin}"


def test_project_clone_still_authenticates_to_gitea(provisioned_workspace):
    """Removing the token from disk must not remove authentication."""
    # Arrange
    gitea = provisioned_workspace.gitea
    # Act
    headers = gitea.auth_headers()
    # Assert
    assert EXPECTED_BASIC in headers, (
        f"clone sent no Gitea credential at all; saw {headers}"
    )


# ---------------------------------------------------------------------------
# EXPLOIT 2 — app submission to the registry
# ---------------------------------------------------------------------------
def test_registry_submission_leaves_dev_project_free_of_admin_token(
    registry_submission,
):
    """Pre-fix the registry remote was ``http://scitex-admin:<TOKEN>@…``."""
    # Arrange
    project_dir = registry_submission.project_dir
    # Act
    leaked = _scan_for_token(project_dir)
    # Assert
    assert not leaked, (
        "Gitea ADMIN token persisted into the user's dev project by app "
        f"submission: {leaked}"
    )


def test_registry_submission_still_authenticates_to_gitea(registry_submission):
    """The push must still carry the credential — via the environment."""
    # Arrange
    gitea = registry_submission.gitea
    # Act
    headers = gitea.auth_headers()
    # Assert
    assert EXPECTED_BASIC in headers, (
        f"registry push sent no Gitea credential at all; saw {headers}"
    )


# ---------------------------------------------------------------------------
# Invariants of the replacement credential path
# ---------------------------------------------------------------------------
def test_auth_credential_is_scoped_to_the_gitea_origin():
    """A bare ``http.extraHeader`` would leak the admin token to any redirect."""
    # Arrange
    from apps.infra.project_app.services import git_service

    # Act
    env = git_service.build_gitea_auth_env(
        token=ADMIN_TOKEN, gitea_url="http://gitea:3000/", base_env={}
    )
    # Assert
    assert env["GIT_CONFIG_KEY_0"] == "http.http://gitea:3000.extraHeader"


def test_auth_credential_value_is_the_gitea_basic_header():
    # Arrange
    from apps.infra.project_app.services import git_service

    # Act
    env = git_service.build_gitea_auth_env(
        token=ADMIN_TOKEN, gitea_url="http://gitea:3000", base_env={}
    )
    # Assert
    assert env["GIT_CONFIG_VALUE_0"] == f"Authorization: {EXPECTED_BASIC}"


def test_auth_credential_never_prompts_when_token_is_missing():
    """No credential must fail loud, never hang on an interactive prompt."""
    # Arrange
    from apps.infra.project_app.services import git_service

    # Act
    env = git_service.build_gitea_auth_env(
        token="", gitea_url="http://gitea:3000", base_env={}
    )
    # Assert
    assert env == {"GIT_TERMINAL_PROMPT": "0"}


@pytest.mark.parametrize(
    "poisoned,clean",
    [
        (
            f"http://alice:{ADMIN_TOKEN}@gitea:3000/alice/p.git",
            "http://gitea:3000/alice/p.git",
        ),
        (
            f"http://{ADMIN_TOKEN}@gitea:3000/alice/p.git",
            "http://gitea:3000/alice/p.git",
        ),
        # No userinfo: an '@' in the PATH must survive untouched.
        ("http://gitea:3000/alice/re@po.git", "http://gitea:3000/alice/re@po.git"),
        ("git@github.com:alice/p.git", "git@github.com:alice/p.git"),
    ],
)
def test_strip_url_credentials_only_removes_userinfo(poisoned, clean):
    # Arrange
    from apps.infra.project_app.services import git_service

    # Act
    result = git_service.strip_url_credentials(poisoned)
    # Assert
    assert result == clean


def test_legacy_poisoned_repo_fixture_really_holds_the_token(legacy_poisoned_repo):
    """Guard: the de-poisoning test below must not be vacuous."""
    # Arrange
    repo = legacy_poisoned_repo
    # Act
    hits = _scan_for_token(repo)
    # Assert
    assert hits, "fixture failed to poison the repo"


def test_sanitize_origin_url_depoisons_a_pre_fix_repo(legacy_poisoned_repo):
    """Repos cloned before the fix must be cleaned when provisioning touches them."""
    # Arrange
    from apps.infra.project_app.services import git_service

    # Act
    git_service.sanitize_origin_url(legacy_poisoned_repo)
    # Assert
    assert not _scan_for_token(legacy_poisoned_repo), (
        "admin token still on disk after sanitize_origin_url()"
    )

# EOF
