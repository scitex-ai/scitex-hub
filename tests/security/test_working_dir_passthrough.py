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
to the figrecipe routes; removes the raw ``/writer/`` mount; and routes
``/apps/storage/`` through a login-gated, jail-validated wrapper.

STYLE (mirrors tests/security/test_onsite_auth_bypass.py)
---------------------------------------------------------
DB-FREE, NO mock library, NO ``monkeypatch``. Each test DRIVES THE REAL
production object and observes state. The production wrappers take their
collaborators as constructor arguments (``WorkingDirScopedView`` /
``JailScopedScanView`` — the same dependency-injection shape as
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

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.project_app.services.working_dir_resolver import (
    WorkingDirScopedView,
)
from apps.workspace.figrecipe_app.urls import figrecipe as figrecipe_urls
from apps.workspace.storage_app import views as storage_views
from apps.workspace.storage_app.views import JailScopedScanView
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
# A path INSIDE alice's own jail (data/users/alice/...), for storage.
ALICE_JAIL_PATH = str(
    Path(settings.BASE_DIR) / "data" / "users" / "alice" / "proj" / "p1"
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


def _prepare_storage(path):
    """Build (recorder, view, request) for the storage scan wrapper."""
    recorder = Recorder()
    view = JailScopedScanView(recorder)
    request = RF.get("/apps/storage/", {"path": path})
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
# SITE 4 — storage wrapper (was unauthenticated arbitrary-dir scan)
# =====================================================================
def test_storage_out_of_jail_path_status_is_403():
    # Arrange
    _recorder, view, request = _prepare_storage("/etc")
    # Act
    response = view(request)
    # Assert
    assert response.status_code == 403


def test_storage_out_of_jail_path_is_not_scanned():
    # Arrange
    recorder, view, request = _prepare_storage("/etc")
    # Act
    view(request)
    # Assert — the recursive scan never ran on an out-of-jail path
    assert recorder.calls == []


def test_storage_in_jail_path_is_scanned():
    # Arrange — a path in the user's own jail must still work
    recorder, view, request = _prepare_storage(ALICE_JAIL_PATH)
    # Act
    view(request)
    # Assert
    assert recorder.calls != []


def test_storage_anonymous_is_redirected():
    # Arrange
    request = RF.get("/apps/storage/", {"path": "/etc"})
    request.user = AnonymousUser()
    # Act
    response = storage_views.index(request)
    # Assert — login_required gate on the real URL view
    assert response.status_code == 302


# EOF
