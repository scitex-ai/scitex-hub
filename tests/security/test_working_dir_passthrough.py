#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_working_dir_passthrough.py
"""Exploit-regression: ``?working_dir=`` (and friends) pass-through family.

CONFIRMED VULNERABILITY (card sec-working-dir-passthrough-family)
----------------------------------------------------------------
Thin Django wrappers delegate to installed SciTeX packages (writer,
figrecipe, storage) and are supposed to inject the authenticated user's
OWN project directory as ``?working_dir=``. Two wrappers only injected
when the caller had NOT already supplied one::

    def _inject_project_context(request):
        if not request.user.is_authenticated: return
        if request.GET.get("working_dir"): return   # <-- PASS-THROUGH

so a caller-supplied ABSOLUTE path passed straight through to the package,
whose downstream ``get_or_create_project`` only checks the path EXISTS —
no ownership, no containment — and then WRITES a symlink into it
(``ensure_scholar_library_link``). One wrapper (figrecipe) had NO auth at
all. A fourth mount (``/apps/storage/``) served the upstream handler RAW:
unauthenticated recursive scan over ANY host directory.

The fix makes the injection an OVERRIDE (the caller's value is discarded,
the working_dir is derived purely server-side from the user's current
project) and FAILS CLOSED when no project resolves; adds ``@login_required``
to the figrecipe routes; removes the raw ``/writer/`` mount; and — since
the 2026-09-26 pure-plugin conversion — DELETES the ``/apps/storage/``
wrapper entirely: Storage is a pure plugin mount behind its
manifest-declared login boundary, the leaf index browses volume-keyed
directories (no free-form path), and the leaf project-file API contains
``?path=`` to the project root (SITE 4 tests below drive the real leaf).

STYLE (mirrors tests/security/test_onsite_auth_bypass.py)
---------------------------------------------------------
DB-FREE, NO ``monkeypatch``. Each test DRIVES THE REAL
production object and observes state. The production wrappers take their
collaborators as constructor arguments (``WorkingDirScopedView`` — the same
dependency-injection shape as
``OnSiteAuthMiddleware.user_lookup``), so the tests construct the very same
object with hand-rolled fakes:

  * a ``resolver`` fake stands in for the DB-backed project lookup and
    returns a fixed project directory (or ``None`` for the no-project case);
  * a ``Recorder`` downstream captures the value the wrapper actually
    forwarded (``request.GET['working_dir']`` / ``?path=``), so we OBSERVE
    the value, not merely a status code.

The auth tests drive the REAL ``@login_required`` URL views with an
``AnonymousUser`` — no DB, because the login gate short-circuits first.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.project_app.services.working_dir_resolver import (
    WorkingDirScopedView,
)
from apps.workspace.figrecipe_app.urls import figrecipe as figrecipe_urls
from apps.workspace.writer_app.urls import writer_django as writer_urls

pytestmark = pytest.mark.security

RF = RequestFactory()

# The victim path an attacker would try to smuggle in — unmistakably NOT
# the caller's own project directory.
ATTACKER_DIR = "/home/victim/secret-project"
# The server-derived project directory the wrapper MUST use instead.
ALICE_PROJECT_DIR = str(
    (Path(settings.BASE_DIR) / "data" / "users" / "alice" / "proj" / "p1").resolve()
)


class FakeUser:
    """Authenticated stand-in (no DB row), like onsite's FakeUser."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, username="alice"):
        self.username = username


class Recorder:
    """Hand-rolled downstream fake: records what the wrapper forwarded."""

    def __init__(self):
        self.calls = []

    def __call__(self, request, *args):
        self.calls.append(
            {
                "working_dir": request.GET.get("working_dir"),
                "recipe": request.GET.get("recipe"),
                "path": request.GET.get("path"),
                "args": args,
            }
        )
        return HttpResponse("downstream-ok")


def _resolver_returning(path):
    """A real (non-mock) resolver collaborator: request -> Path."""

    def _resolve(request):
        return Path(path)

    return _resolve


def _resolver_returning_none(request):
    return None


def _prepare_writer_api(query, resolver):
    """Build (recorder, view, request) for the writer api wrapper."""
    recorder = Recorder()
    view = WorkingDirScopedView(
        recorder, resolver=resolver, on_missing=writer_urls._no_project_json
    )
    request = RF.get("/apps/writer/v2/api/files", query)
    request.user = FakeUser("alice")
    return recorder, view, request


def _prepare_figrecipe_api(query, resolver):
    """Build (recorder, view, request) for the figrecipe api wrapper (GET)."""
    recorder = Recorder()
    view = WorkingDirScopedView(
        recorder,
        resolver=resolver,
        on_missing=figrecipe_urls._no_project_json,
        guard=figrecipe_urls._reject_out_of_jail_paths,
    )
    request = RF.get("/apps/figrecipe/figrecipe/api/switch", query)
    request.user = FakeUser("alice")
    return recorder, view, request


def _prepare_figrecipe_api_post(body, resolver):
    """Build (recorder, view, request) for a JSON-body figrecipe api call.

    The exploit for DEFECT 1 rode the POST body (``{"path": "<abs>"}``),
    which ``handle_api_switch`` reads as ``data.get("path")`` and joins to
    working_dir — so the guard must inspect the body, not only the query.
    """
    recorder = Recorder()
    view = WorkingDirScopedView(
        recorder,
        resolver=resolver,
        on_missing=figrecipe_urls._no_project_json,
        guard=figrecipe_urls._reject_out_of_jail_paths,
    )
    request = RF.post(
        "/apps/figrecipe/figrecipe/api/switch",
        data=json.dumps(body),
        content_type="application/json",
    )
    request.user = FakeUser("alice")
    return recorder, view, request


# =====================================================================
# SITE 1 — writer wrapper (authenticated cross-tenant pass-through)
# =====================================================================
def test_writer_override_discards_caller_supplied_working_dir():
    # Arrange
    recorder, view, request = _prepare_writer_api(
        {"working_dir": ATTACKER_DIR}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/files")
    # Assert — downstream saw the SERVER-derived dir, never the attacker's
    assert recorder.calls[0]["working_dir"] == ALICE_PROJECT_DIR


def test_writer_normal_request_resolves_own_project():
    # Arrange — anti-regression twin: no ?working_dir= supplied
    recorder, view, request = _prepare_writer_api(
        {}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/files")
    # Assert
    assert recorder.calls[0]["working_dir"] == ALICE_PROJECT_DIR


def test_writer_fail_closed_status_is_404():
    # Arrange — no project resolves
    _recorder, view, request = _prepare_writer_api(
        {"working_dir": ATTACKER_DIR}, _resolver_returning_none
    )
    # Act
    response = view(request, "api/files")
    # Assert
    assert response.status_code == 404


def test_writer_fail_closed_does_not_dispatch_to_package():
    # Arrange
    recorder, view, request = _prepare_writer_api(
        {"working_dir": ATTACKER_DIR}, _resolver_returning_none
    )
    # Act
    view(request, "api/files")
    # Assert — package view NEVER reached when no project resolves
    assert recorder.calls == []


def test_writer_api_anonymous_is_redirected():
    # Arrange
    request = RF.get("/apps/writer/v2/api/files", {"working_dir": ATTACKER_DIR})
    request.user = AnonymousUser()
    # Act
    response = writer_urls.api_dispatch(request, "api/files")
    # Assert — login_required gate on the real URL view
    assert response.status_code == 302


# =====================================================================
# SITE 2 — figrecipe wrapper (was COMPLETELY UNAUTHENTICATED)
# =====================================================================
def test_figrecipe_override_discards_caller_supplied_working_dir():
    # Arrange
    recorder, view, request = _prepare_figrecipe_api(
        {"working_dir": ATTACKER_DIR}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/switch")
    # Assert
    assert recorder.calls[0]["working_dir"] == ALICE_PROJECT_DIR


def test_figrecipe_absolute_recipe_outside_jail_status_is_403():
    # Arrange
    _recorder, view, request = _prepare_figrecipe_api(
        {"recipe": "/etc/passwd"}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    response = view(request, "api/switch")
    # Assert
    assert response.status_code == 403


def test_figrecipe_absolute_recipe_outside_jail_is_not_dispatched():
    # Arrange
    recorder, view, request = _prepare_figrecipe_api(
        {"recipe": "/etc/passwd"}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/switch")
    # Assert
    assert recorder.calls == []


def test_figrecipe_relative_recipe_is_dispatched():
    # Arrange — a normal relative recipe must still work
    recorder, view, request = _prepare_figrecipe_api(
        {"recipe": "examples/01_line.yaml"}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/switch")
    # Assert
    assert recorder.calls != []


# --- DEFECT 1: ABSOLUTE ``path`` in the JSON body escapes working_dir -----
# ``full_path = working_dir / file_path`` — pathlib DISCARDS working_dir
# when file_path is absolute, so the old ``recipe``-only guard never saw it.
def test_figrecipe_absolute_path_body_outside_jail_status_is_403():
    # Arrange
    _recorder, view, request = _prepare_figrecipe_api_post(
        {"path": "/home/victim/secret-project/.scitex/figs/fig.yaml"},
        _resolver_returning(ALICE_PROJECT_DIR),
    )
    # Act
    response = view(request, "api/switch")
    # Assert
    assert response.status_code == 403


def test_figrecipe_absolute_path_body_is_not_dispatched():
    # Arrange
    recorder, view, request = _prepare_figrecipe_api_post(
        {"path": "/etc/passwd"}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/switch")
    # Assert — the package handler is NEVER reached with an absolute body path
    assert recorder.calls == []


# --- DEFECT 2: RELATIVE ``../`` traversal escapes the jail ----------------
# ``Path("../...").is_absolute()`` is False, so the old absolute-only guard
# returned None (no block) and the package resolved the traversal outside.
def test_figrecipe_relative_traversal_recipe_status_is_403():
    # Arrange
    _recorder, view, request = _prepare_figrecipe_api(
        {"recipe": "../../../../../../home/victim/proj/.scitex/figs/fig.yaml"},
        _resolver_returning(ALICE_PROJECT_DIR),
    )
    # Act
    response = view(request, "api/switch")
    # Assert
    assert response.status_code == 403


def test_figrecipe_relative_traversal_recipe_is_not_dispatched():
    # Arrange
    recorder, view, request = _prepare_figrecipe_api(
        {"recipe": "../../../../../../home/victim/proj/.scitex/figs/fig.yaml"},
        _resolver_returning(ALICE_PROJECT_DIR),
    )
    # Act
    view(request, "api/switch")
    # Assert
    assert recorder.calls == []


def test_figrecipe_relative_traversal_in_body_path_is_403():
    # Arrange — the same ``../`` escape via the POST body ``path`` param
    _recorder, view, request = _prepare_figrecipe_api_post(
        {"path": "../../../../../../etc/passwd"},
        _resolver_returning(ALICE_PROJECT_DIR),
    )
    # Act
    response = view(request, "api/switch")
    # Assert
    assert response.status_code == 403


# --- Anti-regression twin: a legitimate in-jail body ``path`` still works --
def test_figrecipe_in_jail_body_path_is_dispatched():
    # Arrange — a normal relative path inside the user's project
    recorder, view, request = _prepare_figrecipe_api_post(
        {"path": "figures/fig1.yaml"}, _resolver_returning(ALICE_PROJECT_DIR)
    )
    # Act
    view(request, "api/switch")
    # Assert — containment must NOT block a legitimate in-jail path
    assert recorder.calls != []


def test_figrecipe_api_anonymous_is_redirected():
    # Arrange
    request = RF.get(
        "/apps/figrecipe/figrecipe/api/files", {"working_dir": ATTACKER_DIR}
    )
    request.user = AnonymousUser()
    # Act
    response = figrecipe_urls.api_dispatch_with_context(request, "api/files")
    # Assert — the headline hole: anonymous must now be rejected
    assert response.status_code == 302


def test_figrecipe_editor_page_anonymous_is_redirected():
    # Arrange
    request = RF.get("/apps/figrecipe/figrecipe/")
    request.user = AnonymousUser()
    # Act
    response = figrecipe_urls.editor_page(request)
    # Assert — the routed editor_page was also undecorated before the fix
    assert response.status_code == 302


# =====================================================================
# SITE 4 — storage (was unauthenticated arbitrary-dir scan)
# =====================================================================
# The hub-side wrapper (``JailScopedScanView`` + ``storage_app`` views) is
# DELETED: /apps/storage/ is a pure plugin mount behind the
# manifest-declared login boundary. What the exploit needed — an
# unauthenticated free-form ``?path=`` scan — no longer exists anywhere on
# the host path: the leaf index browses volume-keyed directories
# (``?volume=&dir=``; escapes raise ``OutsideVolume``) and the leaf
# project-file API takes project-RELATIVE ``?path=`` contained to the
# project root (absolute reads are denied before any filesystem access).
#
# These tests drive the REAL leaf views with stub users. The leaf exposes
# ``project_files._GET_CURRENT_PROJECT`` as its documented test seam, so no
# test needs the ORM (this dev container's database role cannot create
# test databases) and none mocks the leaf itself.
def _leaf_storage_views():
    return pytest.importorskip(
        "scitex_storage._django.views", reason="scitex-storage not installed"
    )


def _leaf_project_scope(tmp_path):
    """A fake in-scope project rooted at ``tmp_path`` via the leaf seam."""
    project_files = pytest.importorskip(
        "scitex_storage._django.project_files",
        reason="scitex-storage not installed",
    )
    project = SimpleNamespace(get_local_path=lambda: tmp_path)
    return mock.patch.object(
        project_files,
        "_GET_CURRENT_PROJECT",
        lambda request, user=None: project,
    )


def _storage_request(path="/apps/storage/", query=None):
    request = RF.get(path, query or {})
    request.user = FakeUser("alice")
    return request


def test_storage_project_api_absolute_path_is_denied(tmp_path):
    # Arrange — the CONFIRMED exploit was an absolute ?path= (/etc) handed
    # to a recursive scan. The leaf project API roots every read at the
    # project dir; an absolute ?path= resolves outside it.
    views = _leaf_storage_views()
    request = _storage_request(
        "/apps/storage/api/list", {"path": "/etc"}
    )
    # Act
    with _leaf_project_scope(tmp_path):
        response = views.project_list(request)
    # Assert — denied before any filesystem access, never a listing.
    assert response.status_code == 403
    assert response.json()["error"] == "permission_denied"


def test_storage_project_api_traversal_is_denied(tmp_path):
    # Arrange
    views = _leaf_storage_views()
    request = _storage_request(
        "/apps/storage/api/list", {"path": "../../etc"}
    )
    # Act
    with _leaf_project_scope(tmp_path):
        response = views.project_list(request)
    # Assert
    assert response.status_code == 403
    assert response.json()["error"] == "permission_denied"


def test_storage_project_api_relative_read_still_works(tmp_path):
    # Arrange — containment must not over-block: a relative read inside
    # the project root still lists. (The anti-regression twin.)
    views = _leaf_storage_views()
    (tmp_path / "notes.txt").write_text("hello")
    request = _storage_request("/apps/storage/api/list", {"path": ""})
    # Act
    with _leaf_project_scope(tmp_path):
        response = views.project_list(request)
    # Assert
    assert response.status_code == 200
    assert "notes.txt" in response.json()["files"]


def test_storage_unknown_volume_is_refused():
    # Arrange — the leaf answers 403 when find_volume finds nothing (fail
    # closed), before rendering anything.
    views = _leaf_storage_views()
    request = _storage_request("/apps/storage/", {"volume": "no-such-volume"})
    # Act
    from apps.workspace.console_app.models import ComputeIdentity

    manager = mock.Mock()
    manager.filter.return_value.first.return_value = None
    with mock.patch.object(ComputeIdentity, "objects", manager):
        response = views.index(request)
    # Assert
    assert response.status_code == 403


def test_storage_escaping_dir_is_refused():
    # Arrange
    views = _leaf_storage_views()
    request = _storage_request(
        "/apps/storage/", {"volume": "workspace", "dir": "../../.."}
    )
    # Act
    from apps.workspace.console_app.models import ComputeIdentity

    manager = mock.Mock()
    manager.filter.return_value.first.return_value = None
    with mock.patch.object(ComputeIdentity, "objects", manager):
        response = views.index(request)
    # Assert
    assert response.status_code == 403


def test_storage_anonymous_is_redirected():
    # Arrange — the login boundary is the leaf-declared mount_policy,
    # enforced by the generic mount (no hub wrapper).
    pytest.importorskip(
        "scitex_storage._django.urls", reason="scitex-storage not installed"
    )
    from django.test import Client
    from django.urls import Resolver404, resolve

    try:
        resolve("/apps/storage/")
    except Resolver404:
        pytest.skip("storage mount is not in this environment's URLconf")
    # Act — the mount boundary redirects before any view runs.
    response = Client().get("/apps/storage/?path=/etc", follow=False)
    # Assert
    assert response.status_code == 302
    assert response["Location"].startswith("/auth/login/")


def test_storage_in_jail_browsing_still_lists(tmp_path):
    # Arrange — the anti-regression twin: a directory inside the
    # requester's own volume still browses. The hub provider is stubbed to
    # hand out a tmp-backed workspace volume (hub code, fair game); the
    # leaf index + listing + render are all real.
    views = _leaf_storage_views()
    (tmp_path / "report.csv").write_text("a,b\n")
    request = _storage_request(
        "/apps/storage/", {"volume": "workspace", "dir": ""}
    )
    fake_volumes = [
        {
            "key": "workspace",
            "label": "Workspace files",
            "path": str(tmp_path),
            "machine": "test",
        }
    ]
    from apps.infra.project_app.models import Project

    manager = mock.Mock()
    manager.select_related.return_value.get.side_effect = Project.DoesNotExist
    # Act
    with (
        mock.patch(
            "apps.workspace.apps_app.services.plugin_volumes.user_volumes",
            return_value=fake_volumes,
        ),
        mock.patch.object(Project, "objects", manager),
        mock.patch(
            "apps.workspace.apps_app.views.launcher.get_pinned_module_names",
            return_value=[],
            create=True,
        ),
        mock.patch(
            "apps.infra.public_app.templatetags.site_dock.dock_items",
            return_value=[],
        ),
    ):
        response = views.index(request)
    # Assert
    assert response.status_code == 200
    assert "report.csv" in response.content.decode()


def test_storage_wrapper_gone_is_not_shadowed():
    # Arrange — the old anonymous-redirect test drove storage_views.index
    # directly; that module no longer exists, so this pins its absence
    # instead of re-testing the mount boundary twice.
    import importlib.util

    # Act / Assert
    assert importlib.util.find_spec("apps.workspace.storage_app.views") is None


# =====================================================================
# SITE 2 (cont.) — figrecipe CHANNEL 3 (URL <path:endpoint> SEGMENT)
# =====================================================================
# figrecipe/_django/views.api_dispatch slices a filesystem path off the URL
# segment for two parameterized endpoints — a channel the query/body guard
# NEVER sees. ``api/file-content/<remainder>`` was the CONFIRMED residual
# cross-tenant hole: its handler resolves the remainder against the process
# cwd (== BASE_DIR == /app on the server) and jails with a
# ``str.startswith(cwd)`` that CONTAINS every tenant (BASE_DIR/data/users/*),
# so an absolute/``..`` remainder reads a VICTIM's figure.
#
# A path INSIDE another tenant (bob) — the cross-tenant read the guard closes.
VICTIM_FILE_SEG = "data/users/bob/proj/p1/.scitex/figs/fig.png"
# The equivalent path inside alice's OWN jail — the anti-regression twin.
ALICE_FILE_SEG = "data/users/alice/proj/p1/.scitex/figs/fig.png"
# Alice's jail ROOT (data/users/alice), for the compose ``..``-in-filename case.
ALICE_JAIL_ROOT = str(Path(settings.BASE_DIR) / "data" / "users" / "alice")


def _prepare_figrecipe_endpoint(endpoint, *, body=None, resolver=None):
    """Build ``(recorder, view, request)`` for an arbitrary figrecipe endpoint.

    The test's Act step forwards ``endpoint`` as the URL ``<path:endpoint>``
    capture — exactly as the routed ``api_dispatch_with_context`` passes it —
    so the guard sees the URL SEGMENT, not merely the query/body. A ``body``
    makes it a JSON POST (for the body-sink channels).
    """
    resolver = resolver or _resolver_returning(ALICE_PROJECT_DIR)
    recorder = Recorder()
    view = WorkingDirScopedView(
        recorder,
        resolver=resolver,
        on_missing=figrecipe_urls._no_project_json,
        guard=figrecipe_urls._reject_out_of_jail_paths,
    )
    if body is None:
        request = RF.get("/apps/figrecipe/figrecipe/api")
    else:
        request = RF.post(
            "/apps/figrecipe/figrecipe/api",
            data=json.dumps(body),
            content_type="application/json",
        )
    request.user = FakeUser("alice")
    return recorder, view, request


# --- CHANNEL 3: api/file-content/<remainder> cross-tenant READ -----------
def test_figrecipe_file_content_cross_tenant_segment_status_is_403():
    # Arrange — alice reaches into bob's jail via the URL segment
    endpoint = "api/file-content/" + VICTIM_FILE_SEG
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    response = view(request, endpoint)
    # Assert — the confirmed residual hole is now closed
    assert response.status_code == 403


def test_figrecipe_file_content_cross_tenant_segment_is_not_dispatched():
    # Arrange
    endpoint = "api/file-content/" + VICTIM_FILE_SEG
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    view(request, endpoint)
    # Assert — the package handler NEVER runs on a cross-tenant segment
    assert recorder.calls == []


def test_figrecipe_file_content_absolute_segment_status_is_403():
    # Arrange — a leading slash makes the remainder ABSOLUTE (pathlib then
    # discards the BASE_DIR base entirely).
    endpoint = "api/file-content//home/victim/secret.png"
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    response = view(request, endpoint)
    # Assert
    assert response.status_code == 403


def test_figrecipe_file_content_relative_descent_segment_status_is_403():
    # Arrange — ``../`` climb out of BASE_DIR
    endpoint = "api/file-content/../../../../../../etc/passwd"
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    response = view(request, endpoint)
    # Assert
    assert response.status_code == 403


def test_figrecipe_file_content_in_jail_segment_is_dispatched():
    # Arrange — anti-regression twin: alice reading her OWN figure
    endpoint = "api/file-content/" + ALICE_FILE_SEG
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    view(request, endpoint)
    # Assert — reaching downstream proves the guard did NOT block (no 403)
    assert recorder.calls != []


# --- CHANNEL 3: api/gallery/thumbnail/<name> package-dir READ ------------
def test_figrecipe_thumbnail_traversal_segment_status_is_403():
    # Arrange — ``../`` climb out of the read-only package examples dir
    endpoint = "api/gallery/thumbnail/../../../../etc/passwd"
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    response = view(request, endpoint)
    # Assert
    assert response.status_code == 403


def test_figrecipe_thumbnail_plain_name_is_dispatched():
    # Arrange — a normal flat template name must still resolve
    endpoint = "api/gallery/thumbnail/plot_scatter"
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint)
    # Act
    view(request, endpoint)
    # Assert — reaching downstream proves the guard did NOT block
    assert recorder.calls != []


# =====================================================================
# SITE 2 (cont.) — figrecipe CHANNEL 2 body sinks (base != working_dir)
# =====================================================================
# --- api/compose WRITE sink: BODY working_dir used verbatim --------------
def test_figrecipe_compose_absolute_working_dir_write_status_is_403():
    # Arrange — arbitrary host-directory WRITE via the JSON body working_dir
    endpoint = "api/compose"
    body = {"working_dir": ATTACKER_DIR, "filename": "x"}
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    response = view(request, endpoint)
    # Assert
    assert response.status_code == 403


def test_figrecipe_compose_absolute_working_dir_write_is_not_dispatched():
    # Arrange
    endpoint = "api/compose"
    body = {"working_dir": ATTACKER_DIR, "filename": "x"}
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    view(request, endpoint)
    # Assert — nothing is written; the handler never runs
    assert recorder.calls == []


def test_figrecipe_compose_filename_traversal_write_status_is_403():
    # Arrange — in-jail working_dir but a ``..`` in filename escapes it
    endpoint = "api/compose"
    body = {"working_dir": ALICE_JAIL_ROOT, "filename": "../evil"}
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    response = view(request, endpoint)
    # Assert — the EXACT out-path (working_dir / filename.png) is validated
    assert response.status_code == 403


def test_figrecipe_compose_in_jail_write_is_dispatched():
    # Arrange — anti-regression twin: writing into alice's own project
    endpoint = "api/compose"
    body = {"working_dir": ALICE_PROJECT_DIR, "filename": "composed"}
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    view(request, endpoint)
    # Assert — reaching downstream proves the guard did NOT block
    assert recorder.calls != []


# --- add_image_from_url: file:// local-file READ (SSRF/LFI) --------------
def test_figrecipe_add_image_file_scheme_url_status_is_403():
    # Arrange — file:// reads an arbitrary local file via urllib
    endpoint = "add_image_from_url"
    body = {"url": "file:///app/data/users/bob/proj/p1/.scitex/figs/fig.png"}
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    response = view(request, endpoint)
    # Assert
    assert response.status_code == 403


def test_figrecipe_add_image_http_url_is_dispatched():
    # Arrange — anti-regression twin: a legitimate remote http(s) image URL
    endpoint = "add_image_from_url"
    body = {"url": "https://example.com/x.png"}
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    view(request, endpoint)
    # Assert — reaching downstream proves http(s) is NOT blocked
    assert recorder.calls != []


# --- api/gallery/add: template read from package examples dir ------------
def test_figrecipe_gallery_add_template_traversal_status_is_403():
    # Arrange — ``../`` climb out of the package examples dir
    endpoint = "api/gallery/add"
    body = {"template": "../../../../etc/passwd"}
    _recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    response = view(request, endpoint)
    # Assert
    assert response.status_code == 403


def test_figrecipe_gallery_add_plain_template_is_dispatched():
    # Arrange — anti-regression twin: a normal flat template name
    endpoint = "api/gallery/add"
    body = {"template": "plot_scatter"}
    recorder, view, request = _prepare_figrecipe_endpoint(endpoint, body=body)
    # Act
    view(request, endpoint)
    # Assert — reaching downstream proves the guard did NOT block
    assert recorder.calls != []


# EOF
