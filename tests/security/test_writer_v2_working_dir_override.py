#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_writer_v2_working_dir_override.py
"""Exploit-regression: writer v2 caller-supplied ?working_dir= cross-tenant read/write.

CONFIRMED VULNERABILITY
-----------------------
``apps/workspace/writer_app/urls/writer_django.py`` mounts the shared
``scitex_writer._django`` API at ``/apps/writer/v2/<endpoint>`` behind
``@login_required``. Its wrapper was meant to bind each request to the caller's
own project, but it RETURNED EARLY when the caller already supplied
``working_dir`` -- so ``?working_dir=<victim path>`` passed through unvalidated.
The writer package then resolves files under that ``working_dir``, giving any
authenticated caller (including a pooled ``visitor-*`` account, i.e. the public)
a cross-tenant READ and WRITE.

WHY THIS FILE WAS REWRITTEN (2026-07-24)
----------------------------------------
The first fix added module-level helpers ``_inject_project_context`` /
``_strip_working_dir`` to the writer wrapper, and this file imported them
directly. The pass-through FAMILY fix then replaced that hand-rolled wrapper
with the shared ``WorkingDirScopedView`` -- the sweep had found THREE divergent
hand-rolled copies of the same idea, two carrying the same early-return -- so
those two symbols no longer exist. Importing them here would fail at COLLECTION
time and take this whole module (and the Security Regression Gates job) red.

The security PROPERTY is unchanged, so the test is ported, not dropped: an
attacker-supplied ``working_dir`` must never reach the downstream package view,
and a request that cannot resolve a project must FAIL CLOSED. These now assert
that property against the real shared implementation.

WHY THESE TESTS LOOK LIKE THIS
------------------------------
Behavioural, not source-text: they build a real request via ``RequestFactory``,
run the REAL ``WorkingDirScopedView``, and observe what the downstream view
actually receives. A name or docstring claiming containment is not evidence it
holds -- this repo has shipped a "fix" whose docstring said ``relative_to``
while the code still did ``startswith``. Collaborators are injected (the
resolver and the downstream view), which is the shape the production class was
built for, so these are DB-free and do not need scitex-writer installed. One
assertion per test (STX-TQ007).
"""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.infra.project_app.services.working_dir_resolver import (
    WorkingDirScopedView,
)

pytestmark = [pytest.mark.security]

VICTIM = "/data/users/victim/proj/secret/.scitex/writer"
MINE = "/data/users/me/proj/mine"


def _req(working_dir=None):
    qs = f"?working_dir={working_dir}" if working_dir is not None else ""
    return RequestFactory().get(f"/apps/writer/v2/api/sections{qs}")


class _Spy:
    """Downstream package view that records what it was handed."""

    def __init__(self):
        self.called = False
        self.seen_working_dir = "<never-called>"

    def __call__(self, request, *args):
        self.called = True
        self.seen_working_dir = request.GET.get("working_dir")
        return HttpResponse("ok")


def _view(spy, resolved):
    """Real WorkingDirScopedView with a fake server-side resolver."""
    return WorkingDirScopedView(
        spy,
        resolver=lambda request: resolved,
        on_missing=lambda request: HttpResponse("no project", status=404),
    )


def test_attacker_working_dir_never_reaches_downstream():
    # Arrange
    spy = _Spy()
    request = _req(VICTIM)
    # Act
    _view(spy, MINE)(request)
    # Assert
    assert spy.seen_working_dir != VICTIM


def test_downstream_receives_the_server_resolved_dir():
    # Arrange
    spy = _Spy()
    request = _req(VICTIM)
    # Act
    _view(spy, MINE)(request)
    # Assert
    assert spy.seen_working_dir == MINE


def test_working_dir_is_overridden_even_when_caller_supplies_none():
    # Arrange: the override must be unconditional, not a "default when absent".
    spy = _Spy()
    request = _req()
    # Act
    _view(spy, MINE)(request)
    # Assert
    assert spy.seen_working_dir == MINE


def test_duplicate_working_dir_params_leave_no_attacker_value():
    # Arrange: a smuggled second value must not survive the override.
    spy = _Spy()
    request = RequestFactory().get(
        f"/apps/writer/v2/api/sections?working_dir={VICTIM}&working_dir={MINE}"
    )
    # Act
    _view(spy, MINE)(request)
    # Assert
    assert VICTIM not in request.GET.getlist("working_dir")


def test_unresolvable_project_fails_closed_without_calling_downstream():
    # Arrange: no project resolves -> the package view must never run.
    spy = _Spy()
    request = _req(VICTIM)
    # Act
    _view(spy, None)(request)
    # Assert
    assert spy.called is False


def test_unresolvable_project_returns_the_fail_closed_response():
    # Arrange
    spy = _Spy()
    request = _req(VICTIM)
    # Act
    response = _view(spy, None)(request)
    # Assert
    assert response.status_code == 404
