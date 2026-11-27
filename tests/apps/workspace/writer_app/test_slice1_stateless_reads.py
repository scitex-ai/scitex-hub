#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/writer_app/test_slice1_stateless_reads.py
"""Writer leaf reads, driven through the GENERIC plugin mount at /apps/writer/.

Card hub-figrecipe-leaf-move-20261009 (writer scout c_80d007a8acf7), ported
when the hub-side SITE-3 wrapper was retired (card
hub-writer-leaf-generic-mount-20261127).

The hub no longer injects ``?working_dir=``: every request reaches the leaf
view the installed leaf urlconf declares, through the hub's login wrapper,
and the leaf's own ``@project_boundary`` authorizes it through the SDK host
contract (``scitex_sdk.host.project_access``: project identity, storage
root, write grant). What this module proves, with no leaf-code imports:

* the leaf pages and v2 twins resolve at /apps/writer/ and stay
  login-gated (anon -> 302);
* an authenticated owner with a project gets the leaf viewer/editor pages
  (200, scope marker — django_db, runs in CI where postgres exists) and the
  stateless-read GETs (200 + expected payloads, DB-free);
* a caller-forged ``?working_dir=`` has no authority: the leaf answers from
  the SDK-provided project root, never the forged path;
* no project fails closed in the leaf (404 JSON);
* the leaf manifest still declares its mount policy and the SDK jail
  contract is present.
"""

from __future__ import annotations

import dataclasses
import importlib.metadata
import importlib.util
import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, override_settings
from django.urls import resolve, reverse

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret

User = get_user_model()
RF = RequestFactory()
ROOT = "/apps/writer/"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("scitex_writer._django.urls") is None,
    reason="scitex-writer is not installed here",
)

# Stateless-read endpoints of the leaf's published HTTP surface (URL strings,
# data — this module never imports scitex_writer code).
READ_ENDPOINTS_200 = [
    "ping",
    "api/project-info",
    "api/compile/status",
    "api/files",
    "api/sections",
    "api/bib/files",
    "api/bib/entries",
    "api/figures",
    "api/tables",
    "api/hints",
    "api/claims-metadata",
    "api/scholar/status",
]


def _body(response):
    return json.loads(response.content.decode())


class _User:
    def __init__(self, username="slice1-owner"):
        self.username = username
        self.is_authenticated = True


# -- SDK host doubles (DB-free) -------------------------------------------------
# The leaf's @project_boundary demands the SDK host contract:
# scitex_sdk.host.project_access() -> project identity (settings
# SCITEX_PROJECT_PROVIDER via project_context.resolve_active_project) +
# storage root and write permission (settings SCITEX_PROJECT_STORAGE). The
# real Hub providers need a database these tests deliberately lack, so these
# doubles provision the contract through the SAME two settings the real host
# uses — the leaf guard executes for real, nothing is bypassed.
_SDK_TEST_PROJECT_ID = "slice1-owner/slice1-study"


@dataclasses.dataclass(frozen=True)
class _SDKTestProjectEntry:
    id: str
    name: str
    detail: str = ""


class _SDKTestProjectProvider:
    """Identity double: one accessible project, stored, never a database."""

    project_id = _SDK_TEST_PROJECT_ID
    project_name = "slice1-study"

    def list_projects(self, request):
        if not getattr(getattr(request, "user", None), "is_authenticated", False):
            return []
        return [_SDKTestProjectEntry(id=self.project_id, name=self.project_name)]

    def last_visited(self, request):
        if not getattr(getattr(request, "user", None), "is_authenticated", False):
            return None
        return self.project_id

    def remember(self, request, project_id):
        return None


class _SDKTestProjectStorage:
    """Storage + permissions double: the fixture workspace, owner may write."""

    root = None

    def _authorized(self, project_id, request):
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        if not project_id or project_id != _SDKTestProjectProvider.project_id:
            return False
        return self.root is not None

    def project_path(self, project_id, request):
        if not self._authorized(project_id, request):
            return None
        return str(self.root)

    def can_write(self, project_id, request):
        return bool(self._authorized(project_id, request))


class _NoProjectProvider(_SDKTestProjectProvider):
    """Identity double for a user with no project at all."""

    def list_projects(self, request):
        return []

    def last_visited(self, request):
        return None


_HERE = "tests.apps.workspace.writer_app.test_slice1_stateless_reads"


@pytest.fixture
def workspace(tmp_path):
    """Minimal writer workspace (00_shared/ => is_workspace)."""
    (tmp_path / "00_shared" / "bib_files").mkdir(parents=True)
    return tmp_path


def _host_settings(provider):
    """The SDK host contract, injected through the settings the host uses."""
    return override_settings(
        SCITEX_PROJECT_PROVIDER=f"{_HERE}.{provider}",
        SCITEX_PROJECT_STORAGE=f"{_HERE}._SDKTestProjectStorage",
    )


@pytest.fixture
def sdk_host(workspace):
    """Provision the SDK host contract, bound to the fixture workspace."""
    _SDKTestProjectStorage.root = workspace
    with _host_settings("_SDKTestProjectProvider"):
        yield workspace


def _dispatch(request):
    """Serve ``request`` exactly as the root urlconf routes it."""
    match = resolve(request.path)
    return match.func(request, *match.args, **match.kwargs)


def _authed(path, data=None, **extra):
    request = RF.get(path, data=data or {}, **extra)
    request.user = _User()
    return request


def _anonymous(path):
    request = RF.get(path)
    request.user = AnonymousUser()
    return request


# -- mount contract ----------------------------------------------------------------


def test_v2_editor_twin_resolves_at_the_leaf_mount():
    # Arrange
    name = "writer:writer_v2_editor"
    # Act
    url = reverse(name)
    # Assert
    assert url == ROOT + "editor-v2/"


def test_anon_viewer_is_login_gated():
    # Arrange
    request = _anonymous(ROOT + "viewer/")
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 302


def test_anon_editor_is_login_gated():
    # Arrange
    request = _anonymous(ROOT)
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 302


def test_anon_read_api_is_login_gated():
    # Arrange
    request = _anonymous(ROOT + "ping")
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 302


# -- authed page parity (needs postgres; runs in CI) ------------------------------


@pytest.fixture
def slice1_owner_factory():
    """Create owners with REAL on-disk workspaces, cleaned up afterwards.

    The leaf guards the page with the SDK host contract
    (``HubProjectStorage.project_path`` -> ``get_project_root_path``, which
    needs ``data/users/<owner>/proj/<slug>/`` ON DISK), so the workspace is
    created the way the product creates it (filesystem manager). The
    database rolls back per test; the filesystem does not, hence the
    finalizer.
    """
    import shutil

    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    roots = []

    def make(username, slug):
        owner = User.objects.create_user(username=username, password=PASSWORD)
        project = Project.objects.create(
            slug=slug,
            owner=owner,
            name=slug,
            visibility="private",
        )
        manager = get_project_filesystem_manager(owner)
        _created, root = manager.create_project_directory(project, use_template=False)
        assert root is not None, "filesystem manager did not create a workspace"
        (root / "00_shared" / "bib_files").mkdir(parents=True, exist_ok=True)
        owner.profile.last_active_repository = project
        owner.profile.save(update_fields=["last_active_repository"])
        roots.append(root)
        return owner

    yield make
    for root in roots:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.django_db
def test_viewer_page_renders_for_owner(slice1_owner_factory):
    # Arrange
    slice1_owner_factory("slice1-owner", "slice1-study")
    client = Client()
    client.login(username="slice1-owner", password=PASSWORD)
    # Act
    response = client.get(ROOT + "viewer/")
    # Assert
    assert b"stx-app-scope" in response.content, response.content[:500]


@pytest.mark.django_db
def test_editor_page_renders_for_owner(slice1_owner_factory):
    # Arrange
    slice1_owner_factory("slice1-editor", "slice1-editor-study")
    client = Client()
    client.login(username="slice1-editor", password=PASSWORD)
    # Act
    response = client.get(ROOT)
    # Assert
    assert b"stx-app-scope" in response.content, response.content[:500]


@pytest.mark.django_db
def test_project_less_editor_navigation_goes_to_new_project():
    # Arrange — a signed-in user who owns no project, opening the editor
    User.objects.create_user(username="slice1-empty", password=PASSWORD)
    client = Client()
    client.login(username="slice1-empty", password=PASSWORD)
    # Act
    response = client.get(ROOT, HTTP_ACCEPT="text/html")
    # Assert — the hub honours the leaf's mount_policy.requires_project
    # (declared since scitex-writer 2.45.2, the hub floor)
    assert (response.status_code, response.get("Location")) == (302, "/new/")


# -- stateless reads (DB-free) ---------------------------------------------------


@pytest.mark.parametrize("endpoint", READ_ENDPOINTS_200)
def test_stateless_read_answers_200(sdk_host, endpoint):
    # Arrange
    request = _authed(ROOT + endpoint)
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 200, (endpoint, response.content[:300])


def test_ping_reports_status_ok(sdk_host):
    # Arrange
    request = _authed(ROOT + "ping")
    # Act
    body = _body(_dispatch(request))
    # Assert
    assert body == {"status": "ok"}


def test_project_info_names_server_workspace(sdk_host, workspace):
    # Arrange
    request = _authed(ROOT + "api/project-info")
    # Act
    body = _body(_dispatch(request))
    # Assert
    assert (body["project_dir"], body["has_shared"]) == (
        str(workspace.resolve()),
        True,
    )


def test_compile_status_shape(sdk_host):
    # Arrange
    request = _authed(ROOT + "api/compile/status")
    # Act
    body = _body(_dispatch(request))
    # Assert
    assert (body["compiling"], body["result"]) == (False, None)


def test_bibliography_files_read_empty_on_fresh_workspace(sdk_host):
    # Arrange
    request = _authed(ROOT + "api/bib/files")
    # Act
    body = _body(_dispatch(request))
    # Assert
    assert body == {"files": [], "count": 0}


def test_dag_without_target_is_400(sdk_host):
    # Arrange
    request = _authed(ROOT + "api/dag")
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 400


# -- leaf boundary bars ----------------------------------------------------------


def test_forged_working_dir_never_reaches_leaf(sdk_host, workspace, tmp_path_factory):
    # Arrange — a real directory the caller does not own
    victim = tmp_path_factory.mktemp("victim")
    (victim / "00_shared").mkdir()
    request = _authed(ROOT + "api/project-info", data={"working_dir": str(victim)})
    # Act
    body = _body(_dispatch(request))
    # Assert — the SDK-provided root wins; the forged path has no authority
    assert body["project_dir"] == str(workspace.resolve())


def test_no_project_read_api_is_404_json(workspace):
    # Arrange
    _SDKTestProjectStorage.root = workspace
    request = _authed(ROOT + "ping")
    # Act
    with _host_settings("_NoProjectProvider"):
        response = _dispatch(request)
    # Assert
    assert (response.status_code, "error" in _body(response)) == (404, True)


def test_unsafe_method_without_csrf_token_is_refused(sdk_host):
    # Arrange — the leaf keeps its own CSRF decision (no hub exemption)
    request = RF.post(ROOT + "api/preview", data="{}", content_type="application/json")
    request.user = _User()
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 403


def test_safe_method_with_foreign_origin_still_reads(sdk_host):
    # Arrange
    request = _authed(ROOT + "ping", HTTP_ORIGIN="https://evil.example")
    # Act
    response = _dispatch(request)
    # Assert
    assert response.status_code == 200


# -- generic-contract state (DB-free) ----------------------------------------------


def _leaf_manifest():
    # The umbrella alias may replace __spec__; installed distribution files
    # remain the authoritative manifest location without importing the leaf.
    distribution = importlib.metadata.distribution("scitex-writer")
    relative = "scitex_writer/_django/manifest.json"
    assert relative in {str(path) for path in distribution.files or ()}
    manifest = Path(distribution.locate_file(relative))
    return json.loads(manifest.read_text())


def test_leaf_mount_policy_is_login_gated():
    # Arrange
    manifest = _leaf_manifest()
    # Act
    policy = manifest.get("mount_policy") or {}
    # Assert — the generic mount login-wraps the whole leaf urlconf from this
    assert policy.get("login_required") is True


def test_sdk_jail_contract_present():
    # Arrange — the generic mount validates mount_policy with this contract
    from scitex_sdk.app import jail

    # Act
    missing = [
        member
        for member in ("validate_mount_policy", "is_in_jail", "MOUNT_POLICY_KEY")
        if not hasattr(jail, member)
    ]
    # Assert
    assert missing == []


# EOF
