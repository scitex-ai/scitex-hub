#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/writer_app/test_slice1_stateless_reads.py
"""Writer separation Slice 1: stateless reads behind the existing wrapper.

Card hub-figrecipe-leaf-move-20261009 (writer scout c_80d007a8acf7).

Slice 1 covers the leaf ``viewer_page`` + status/metadata/bibliography GETs
dispatched through the SITE-3 wrapper
(``apps/workspace/writer_app/urls/writer_django.py``). Gate: authed render
parity (pages mount, read endpoints answer) with the wrapper byte-intact.

CUTOVER (this file, post-handover): the SITE-3 view functions this suite
drives are UNCHANGED — only their mount prefix moved (v2 paths live ONLY
at /apps/writer/old-direct/ in dev; the same function objects serve the
leaf paths at /apps/writer/ — see test_writer_route_flip_parity.py). The
v2-route and owner-render tests below take the ``writer_old_direct``
fixture; every direct view call is untouched. The R1 tripwire is now
generation-aware (2.43.9+ declares the policy; older leaves must not).

OPERATOR COUPLING CONSTRAINT
----------------------------
Leaves must not be tightly coupled to scitex-hub, in BOTH directions: the
leaf may depend only on the scitex-sdk stable API (never hub modules), and
the hub may talk to the leaf only through the generic plugin contract
(manifest, mount_policy, jail) — no leaf-specific imports, no per-app
bespoke hub code added. This slice therefore changes NO production code:
the wrapper stays byte-intact (it is the only bar on file-write paths) and
there is no generic-contract mechanism to build on yet (SDK 0.3.4 ships no
jail surface; the leaf declares no mount_policy — both pinned below as
fail-loud tripwires). What this module proves, DB-free, with no
leaf-code imports:

* the three v2 routes resolve and stay login-gated (anon -> 302);
* an authenticated owner with a project gets the leaf viewer/editor pages
  (200, scope marker — django_db, runs in CI where postgres exists) and
  the stateless-read GETs (200 + expected payloads, DB-free);
* a caller-forged ``?working_dir=`` never reaches the leaf (server dir wins);
* no-project still fails closed (pages -> /new/, API -> 404 JSON);
* the set of hub production modules importing ``scitex_writer`` does not
  grow (coupling guard);
* the SDK jail contract + leaf mount_policy gaps blocking Slice 2 are
  recorded as tests that fail LOUDLY once the upstream lands.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.infra.project_app.models import Project
from apps.workspace.writer_app.urls import writer_django as writer_urls

PASSWORD = "TestPass123!"  # pragma: allowlist secret

User = get_user_model()
RF = RequestFactory()

# Stateless-read endpoints served by the leaf behind the wrapper (URL
# strings of the leaf's published HTTP surface at scitex-writer 2.43.6;
# data, not imports — this module never imports scitex_writer code).
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


# -- SDK host doubles (scitex-writer>=2.43.9, DB-free) -----------------------
# The 2.43.9 leaf guards api_dispatch/editor_page/viewer_page with
# @project_boundary (scitex_writer/_django/_host_boundary.py), which demands
# the SDK host contract BEFORE the wrapper-injected ?working_dir= is ever
# read: scitex_sdk.host.project_access() -> project identity (settings
# SCITEX_PROJECT_PROVIDER via project_context.resolve_active_project) +
# storage root and write permission (settings SCITEX_PROJECT_STORAGE).
# Without them the guard answers 503 "Project capability is unavailable"
# (measured on /apps/writer/v2/ping: provider STATE_UNAVAILABLE, because the
# real HubProjectProvider needs a database these tests deliberately lack).
#
# These doubles provision that contract for the DB-free suite through the
# SAME two settings the real host uses — the leaf guard executes for real,
# nothing is bypassed. Authorization-first, mirroring HubProjectStorage:
# anonymous callers and unknown project ids get no path and no grant.
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


_SDK_TEST_PROVIDER_PATH = (
    "tests.apps.workspace.writer_app.test_slice1_stateless_reads._SDKTestProjectProvider"
)
_SDK_TEST_STORAGE_PATH = (
    "tests.apps.workspace.writer_app.test_slice1_stateless_reads._SDKTestProjectStorage"
)


@pytest.fixture
def workspace(tmp_path):
    """Minimal writer workspace (00_shared/ => is_workspace)."""
    (tmp_path / "00_shared" / "bib_files").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def resolve_to(workspace, monkeypatch):
    """Point the wrapper's server-side resolver at the fixture workspace.

    ... and provision the SDK host contract (2.43.9+) for the DB-free
    suite: the leaf @project_boundary reads project identity from
    SCITEX_PROJECT_PROVIDER and storage/permissions from
    SCITEX_PROJECT_STORAGE, neither of which the real Hub providers can
    answer without a database. The doubles above stand in through those
    same two settings, bound to this fixture's workspace.
    """

    def _bind(view):
        monkeypatch.setattr(view, "resolver", lambda request: workspace)

    _bind(writer_urls._editor_view)
    _bind(writer_urls._viewer_view)
    _bind(writer_urls._api_view)
    _SDKTestProjectStorage.root = workspace
    monkeypatch.setattr(settings, "SCITEX_PROJECT_PROVIDER", _SDK_TEST_PROVIDER_PATH)
    monkeypatch.setattr(settings, "SCITEX_PROJECT_STORAGE", _SDK_TEST_STORAGE_PATH)
    return workspace


def _get(view, path, user=None, **extra):
    request = RF.get(path, **extra)
    request.user = user if user is not None else _User()
    return view(request)


# -- mount contract ----------------------------------------------------
# CUTOVER: the v2 paths live ONLY at old-direct in dev now (the gate is off
# in the ambient prod-shaped suite, so reverse()/client drives need the
# writer_old_direct fixture, which reloads the real root urlconf with the
# explicit flag). Same views, same assertions — only the prefix moved.


def test_v2_routes_resolve(writer_old_direct):
    assert reverse("writer_app:writer_v2_editor") == "/apps/writer/old-direct/editor-v2/"
    assert reverse("writer_app:writer_v2_viewer") == "/apps/writer/old-direct/viewer-v2/"


def test_anon_viewer_is_login_gated():
    request = RF.get("/apps/writer/viewer-v2/")
    request.user = AnonymousUser()
    assert writer_urls.viewer_page(request).status_code == 302


def test_anon_editor_is_login_gated():
    request = RF.get("/apps/writer/editor-v2/")
    request.user = AnonymousUser()
    assert writer_urls.editor_page(request).status_code == 302


def test_anon_read_api_is_login_gated():
    request = RF.get("/apps/writer/v2/ping")
    request.user = AnonymousUser()
    assert writer_urls.api_dispatch(request, "ping").status_code == 302


# -- authed page parity (needs postgres; runs in CI) -----------------------


def _owner_with_workspace(tmp_path, username, slug):
    (tmp_path / "00_shared" / "bib_files").mkdir(parents=True)
    owner = User.objects.create_user(username=username, password=PASSWORD)
    project = Project.objects.create(
        slug=slug,
        owner=owner,
        name=slug,
        visibility="private",
        local_path=str(tmp_path),
    )
    owner.profile.last_active_repository = project
    owner.profile.save(update_fields=["last_active_repository"])
    return owner


@pytest.mark.django_db
def test_viewer_page_renders_for_owner(tmp_path, writer_old_direct):
    _owner_with_workspace(tmp_path, "slice1-owner", "slice1-study")
    client = Client()
    client.login(username="slice1-owner", password=PASSWORD)
    response = client.get("/apps/writer/old-direct/viewer-v2/")
    assert response.status_code == 200, response.content[:500]
    assert b"stx-app-scope" in response.content


@pytest.mark.django_db
def test_editor_page_renders_for_owner(tmp_path, writer_old_direct):
    _owner_with_workspace(tmp_path, "slice1-editor", "slice1-editor-study")
    client = Client()
    client.login(username="slice1-editor", password=PASSWORD)
    response = client.get("/apps/writer/old-direct/editor-v2/")
    assert response.status_code == 200, response.content[:500]
    assert b"stx-app-scope" in response.content


@pytest.mark.parametrize("endpoint", READ_ENDPOINTS_200)
def test_stateless_read_answers_200(resolve_to, endpoint):
    response = writer_urls.api_dispatch(
        _authed(f"/apps/writer/v2/{endpoint}"), endpoint
    )
    assert response.status_code == 200, (endpoint, response.content[:300])


def _authed(path, data=None):
    request = RF.get(path, data=data or {})
    request.user = _User()
    return request


def test_ping_payload(resolve_to):
    assert _body(writer_urls.api_dispatch(_authed("/apps/writer/v2/ping"), "ping")) == {
        "status": "ok"
    }


def test_project_info_names_server_workspace(resolve_to, workspace):
    body = _body(
        writer_urls.api_dispatch(_authed("/apps/writer/v2/api/project-info"), "api/project-info")
    )
    assert body["project_dir"] == str(workspace.resolve())
    assert body["project_name"] == workspace.resolve().name
    assert body["has_shared"] is True


def test_compile_status_shape(resolve_to):
    body = _body(
        writer_urls.api_dispatch(
            _authed("/apps/writer/v2/api/compile/status"), "api/compile/status"
        )
    )
    assert body["compiling"] is False
    assert body["result"] is None


def test_bibliography_reads_empty_on_fresh_workspace(resolve_to):
    assert _body(
        writer_urls.api_dispatch(_authed("/apps/writer/v2/api/bib/files"), "api/bib/files")
    ) == {"files": [], "count": 0}
    assert _body(
        writer_urls.api_dispatch(
            _authed("/apps/writer/v2/api/bib/entries"), "api/bib/entries"
        )
    ) == {"entries": [], "count": 0}


def test_dag_without_target_is_400(resolve_to):
    response = writer_urls.api_dispatch(_authed("/apps/writer/v2/api/dag"), "api/dag")
    assert response.status_code == 400


# -- wrapper bars preserved ----------------------------------------------


def test_forged_working_dir_never_reaches_leaf(resolve_to, workspace):
    request = _authed("/apps/writer/v2/api/project-info", data={"working_dir": "/victim/proj"})
    body = _body(writer_urls.api_dispatch(request, "api/project-info"))
    assert body["project_dir"] == str(workspace.resolve())


def test_no_project_viewer_redirects_to_new(monkeypatch):
    monkeypatch.setattr(writer_urls._viewer_view, "resolver", lambda request: None)
    response = _get(writer_urls.viewer_page, "/apps/writer/viewer-v2/")
    assert response.status_code == 302
    assert response["Location"] == "/new/"


def test_no_project_read_api_is_404_json(monkeypatch):
    monkeypatch.setattr(writer_urls._api_view, "resolver", lambda request: None)
    response = writer_urls.api_dispatch(_authed("/apps/writer/v2/ping"), "ping")
    assert response.status_code == 404
    assert "No active project" in _body(response)["error"]


def test_safe_method_with_foreign_origin_still_reads(resolve_to):
    request = RF.get("/apps/writer/v2/ping", HTTP_ORIGIN="https://evil.example")
    request.user = _User()
    assert writer_urls.api_dispatch(request, "ping").status_code == 200


# =====================================================================
# Generic-contract state (DB-free): coupling guard + Slice 2 tripwires.
# No scitex_writer code is imported anywhere in this module.
# =====================================================================

# Hub production modules allowed to import scitex_writer: the pre-existing
# SITE-3 wrapper + legacy writer surface. The cutover SHRINKS this set by
# one (urls/__init__.py no longer touches the leaf — it only re-exports the
# wrapper's leaf mount); it must only shrink further (leaf moves), never
# grow.
GRANDFATHERED_SCITEX_WRITER_IMPORTERS = frozenset(
    {
        "apps/workspace/writer_app/urls/writer_django.py",
        "apps/workspace/writer_app/views/editor/api/compilation_full_job.py",
        "apps/workspace/writer_app/views/overleaf/api.py",
        "apps/workspace/writer_app/services/compiler.py",
        "apps/workspace/writer_app/services/writer/compilation.py",
        "apps/infra/project_app/views/projects/live_viewer.py",
        "apps/infra/project_app/services/writer_workspace_layout.py",
    }
)


def _hub_prod_importers_of_scitex_writer():
    repo_root = Path(__file__).resolve().parents[4]
    found = set()
    for base in ("apps", "config"):
        for path in (repo_root / base).rglob("*.py"):
            try:
                text = path.read_text()
            except OSError:
                continue
            for line in text.splitlines():
                code = line.split("#", 1)[0].strip()
                if code.startswith("from scitex_writer") or code.startswith(
                    "import scitex_writer"
                ):
                    found.add(str(path.relative_to(repo_root)))
                    break
    return found


def test_no_new_bespoke_hub_imports_of_writer_leaf():
    assert _hub_prod_importers_of_scitex_writer() == GRANDFATHERED_SCITEX_WRITER_IMPORTERS


def _leaf_manifest():
    spec = importlib.util.find_spec("scitex_writer")
    assert spec is not None and spec.origin, "scitex-writer not installed"
    manifest = Path(spec.origin).parent / "_django" / "manifest.json"
    assert manifest.exists(), "leaf _django/manifest.json missing"
    return json.loads(manifest.read_text())


def test_leaf_mount_policy_matches_installed_generation():
    # R1 (writer lane, card hub-wrapper-plugin-writer-entrypoint-20260926):
    # the plugin contract is `mount_policy` {login_required, touches_files,
    # jail} in the leaf manifest, first carried by the 2.43.9 release
    # (writer #438 -> e14f6d79; hub floor scitex-writer>=2.43.9). The env
    # this suite runs in may still predate the publish (PyPI latest was
    # 2.43.6 at the cutover — no scitex.apps entry, no mount_policy key),
    # and the cutover is fail-closed under the older leaf, so this tripwire
    # pins GENERATION-CONSISTENCY, not a fixed generation: a 2.43.9+ leaf
    # WITHOUT the policy fails loudly (the floor's promise broke), and a
    # pre-2.43.9 leaf WITH an unexpected policy fails loudly too (the
    # wrapper's two-treatment contract was written against known shapes).
    from importlib.metadata import version

    manifest = _leaf_manifest()
    installed = tuple(int(x) for x in version("scitex-writer").split(".")[:3])
    if installed >= (2, 43, 9):
        policy = manifest.get("mount_policy")
        assert policy is not None, (
            "scitex-writer>=2.43.9 must declare manifest mount_policy "
            "(writer #438) — the hub floor promises it."
        )
        assert policy.get("login_required") is True
        assert policy.get("touches_files") is True
        jail = policy.get("jail") or {}
        assert jail.get("scope") == "project"
        assert jail.get("working_dir_param") == "working_dir"
        for param in ("path", "target", "output_file", "pdf"):
            assert param in jail.get("path_params", []), (
                f"jail.path_params lost {param!r} — the SITE-3 wrapper's "
                "threat model assumes these channels are declared."
            )
    else:
        assert "mount_policy" not in manifest, (
            "pre-2.43.9 leaf unexpectedly declares mount_policy — re-read "
            "the wrapper's two-treatment contract against this shape."
        )


def test_sdk_jail_contract_present():
    # The SDK jail surface (SDK: scitex_sdk/app/jail.py +
    # validate_mount_policy) has LANDED — it shipped in scitex-sdk 0.3.5
    # (absent from the published 0.3.4 wheel, present in 0.3.5+; the
    # previous missing-tripwire asserted the opposite and failed once CI
    # resolved 0.3.5). Slice 2 builds the Writer file/content write paths
    # on validate_mount_policy + JailScopedView per the FigRecipe #1068
    # shape, so this test pins the contract members Slice 2 needs. If it
    # FAILS, the SDK regressed (or the floor dropped below the contract):
    # fail loud, do NOT silently fall back to the bespoke wrapper.
    from scitex_sdk.app import jail

    for member in (
        "validate_mount_policy",  # mount-time declaration check
        "JailScopedView",  # host-enforced request bar
        "is_in_jail",  # containment primitive
        "resolve_against",  # path-join primitive
        "MOUNT_POLICY_KEY",  # manifest key ("mount_policy")
    ):
        assert hasattr(jail, member), f"scitex_sdk.app.jail.{member} missing"
    assert jail.MOUNT_POLICY_KEY == "mount_policy"


# EOF
