"""Regression: on-site credentials never reach user-visible files.

On-site MCP auth used to copy the server's master on-site secret into the
``env`` block of every generated ``.agents/agents.json`` and ``.mcp.json``
(home and project). Those files live inside the user's project, may be
pushed with it, and hidden files of public projects were readable by any
signed-in account. With the master, anyone could sign as any user.

Now:

* generated configs carry no credential at all, and older configs are
  purged of credential fields;
* the generated files are gitignored in the project;
* a terminal session gets only its own user's derived key in the process
  environment, with the master removed;
* hidden paths of a project are served to its owner and collaborators only.

Real files on disk, real environment variables, the real Django views
against the test database. No mocks.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory

from apps.workspace.console_app.services.agents_config import (
    ensure_agents_config,
    ensure_claude_config,
    purge_credentials_from_config,
)
from apps.workspace.console_app.services.terminal_broker.session import (
    session_base_env,
)
from scitex_hub._mcp_tools.api import (
    ONSITE_EPOCH_HEADER,
    ONSITE_KEY_ENV,
    ONSITE_KEY_EPOCH_ENV,
    ONSITE_SECRET_ENV,
    ONSITE_SIG_HEADER,
    ONSITE_TS_HEADER,
    ONSITE_USER_HEADER,
    onsite_headers,
    verify_onsite,
    wsgi_meta_key,
)

pytestmark = pytest.mark.security

MASTER = "master-onsite-secret-for-tests"  # pragma: allowlist secret


@pytest.fixture
def master_in_env():
    saved = os.environ.get(ONSITE_SECRET_ENV)
    os.environ[ONSITE_SECRET_ENV] = MASTER
    try:
        yield MASTER
    finally:
        if saved is None:
            os.environ.pop(ONSITE_SECRET_ENV, None)
        else:
            os.environ[ONSITE_SECRET_ENV] = saved


@pytest.fixture
def generated_project(tmp_path, master_in_env):
    home = tmp_path / "home"
    project = home / "proj" / "demo"
    project.mkdir(parents=True)
    ensure_agents_config(project, force=True, username="alice")
    ensure_claude_config(home, project, force=True, username="alice")
    return project


def _meta(headers):
    return {wsgi_meta_key(k): v for k, v in headers.items()}


# --------------------------------------------------------------------------- #
# Generated files                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", [".agents/agents.json", ".mcp.json"])
def test_generated_config_does_not_contain_the_master(generated_project, name):
    # Arrange
    path = generated_project / name
    # Act
    text = path.read_text()
    # Assert
    assert MASTER not in text


@pytest.mark.parametrize("name", [".agents/agents.json", ".mcp.json"])
def test_generated_config_names_no_credential_variable(generated_project, name):
    # Arrange
    path = generated_project / name
    # Act
    text = path.read_text()
    # Assert
    assert not any(v in text for v in (ONSITE_SECRET_ENV, ONSITE_KEY_ENV))


def test_generated_files_are_gitignored(generated_project):
    # Arrange
    gitignore = generated_project / ".gitignore"
    # Act
    lines = set(gitignore.read_text().splitlines())
    # Assert
    assert {".agents/agents.json", ".agents/local.json", ".mcp.json"} <= lines


def test_legacy_config_is_purged_of_the_master(tmp_path):
    # Arrange
    legacy = tmp_path / ".mcp.json"
    legacy.write_text(
        json.dumps(
            {"mcpServers": {"scitex": {"env": {ONSITE_SECRET_ENV: MASTER, "X": "1"}}}}
        )
    )
    # Act
    purge_credentials_from_config(legacy)
    # Assert
    assert MASTER not in legacy.read_text()


def test_existing_config_is_purged_on_next_connect(tmp_path):
    # Arrange
    project = tmp_path / "proj"
    (project / ".agents").mkdir(parents=True)
    agents_json = project / ".agents" / "agents.json"
    agents_json.write_text(
        json.dumps(
            {"mcp": {"servers": {"scitex": {"env": {ONSITE_SECRET_ENV: MASTER}}}}}
        )
    )
    # Act
    ensure_agents_config(project, force=False, username="alice")
    # Assert
    assert MASTER not in agents_json.read_text()


# --------------------------------------------------------------------------- #
# Terminal session environment                                                 #
# --------------------------------------------------------------------------- #
def test_session_env_drops_the_master():
    # Arrange
    server_env = {ONSITE_SECRET_ENV: MASTER, "PATH": "/usr/bin"}
    # Act
    env = session_base_env(server_env, "alice")
    # Assert
    assert MASTER not in env.values()


def test_session_key_authenticates_its_own_user():
    # Arrange
    env = session_base_env({ONSITE_SECRET_ENV: MASTER}, "alice")
    headers = onsite_headers(
        "alice", env[ONSITE_KEY_ENV], int(env[ONSITE_KEY_EPOCH_ENV])
    )
    # Act
    username = verify_onsite(_meta(headers), MASTER)
    # Assert
    assert username == "alice"


def test_session_key_cannot_sign_for_another_user():
    # Arrange
    env = session_base_env({ONSITE_SECRET_ENV: MASTER}, "alice")
    headers = onsite_headers(
        "admin", env[ONSITE_KEY_ENV], int(env[ONSITE_KEY_EPOCH_ENV])
    )
    # Act
    username = verify_onsite(_meta(headers), MASTER)
    # Assert
    assert username is None


def test_session_without_master_gets_no_key():
    # Arrange
    server_env = {"PATH": "/usr/bin"}
    # Act
    env = session_base_env(server_env, "alice")
    # Assert
    assert ONSITE_KEY_ENV not in env


def test_signed_headers_carry_every_verified_field():
    # Arrange
    env = session_base_env({ONSITE_SECRET_ENV: MASTER}, "alice")
    # Act
    headers = onsite_headers(
        "alice", env[ONSITE_KEY_ENV], int(env[ONSITE_KEY_EPOCH_ENV]), now=time.time()
    )
    # Assert
    assert set(headers) == {
        ONSITE_USER_HEADER,
        ONSITE_TS_HEADER,
        ONSITE_EPOCH_HEADER,
        ONSITE_SIG_HEADER,
    }


# --------------------------------------------------------------------------- #
# Hidden paths of a public project                                             #
# --------------------------------------------------------------------------- #
@pytest.fixture
def public_project(db):
    from apps.infra.project_app.services.filesystem.paths import (
        get_user_base_path,
    )

    from apps.infra.project_app.models import Project
    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    owner = User.objects.create_user(username=f"own-{uuid4().hex[:12]}")
    project = Project.objects.create(
        owner=owner, slug="public-demo", name="public", visibility="public"
    )
    base = get_user_base_path(owner)
    root = base / project.slug
    root.mkdir(parents=True, exist_ok=True)
    assert get_project_filesystem_manager(owner).get_project_root_path(project) == root
    (root / "README.md").write_text("published")
    (root / ".mcp.json").write_text('{"private": true}')
    yield project
    shutil.rmtree(base.parent, ignore_errors=True)


def _read(project, user, path):
    from apps.infra.workspace_api.views.file_content import api_get_file_content

    request = RequestFactory().get("/", {"project_id": project.pk})
    request.user = user
    return api_get_file_content(request, path).status_code


def test_other_account_cannot_read_hidden_file_of_public_project(public_project):
    # Arrange
    other = User.objects.create_user(username=f"oth-{uuid4().hex[:12]}")
    # Act
    status = _read(public_project, other, ".mcp.json")
    # Assert
    assert status == 404


def test_other_account_still_reads_published_file(public_project):
    # Arrange
    other = User.objects.create_user(username=f"oth-{uuid4().hex[:12]}")
    # Act
    status = _read(public_project, other, "README.md")
    # Assert
    assert status == 200


def test_owner_reads_own_hidden_file(public_project):
    # Arrange
    owner = public_project.owner
    # Act
    status = _read(public_project, owner, ".mcp.json")
    # Assert
    assert status == 200


def test_collaborator_reads_hidden_file(public_project):
    # Arrange
    collaborator = User.objects.create_user(username=f"col-{uuid4().hex[:12]}")
    public_project.collaborators.add(collaborator)
    # Act
    status = _read(public_project, collaborator, ".mcp.json")
    # Assert
    assert status == 200
