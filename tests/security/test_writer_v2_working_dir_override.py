#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_writer_v2_working_dir_override.py
"""Exploit-regression: writer v2 caller-supplied ?working_dir= cross-tenant read/write.

CONFIRMED VULNERABILITY
-----------------------
``apps/workspace/writer_app/urls/writer_django.py`` mounts the shared
``scitex_writer._django`` API at ``/apps/writer/v2/<endpoint>`` behind
``@login_required``. Its ``_inject_project_context`` wrapper was meant to bind
each request to the caller's own project, but it RETURNED EARLY when the caller
already supplied ``working_dir`` -- so ``?working_dir=<victim path>`` passed
through unvalidated. The writer package then resolves files under that
``working_dir``, giving any authenticated caller (including a pooled
``visitor-*`` account, i.e. the public) a cross-tenant READ and WRITE.

THE FIX
-------
``_inject_project_context`` now ALWAYS overrides ``working_dir`` from the
authenticated user's current project, and FAILS CLOSED (strips any
caller-supplied ``working_dir``) whenever no project can be resolved. No
frontend passes ``working_dir`` over HTTP, so overriding breaks nothing.

WHY THESE TESTS LOOK LIKE THIS
------------------------------
Behavioural, not source-text. They build a real request via ``RequestFactory``,
run the REAL ``_inject_project_context``, and assert on the resulting
``request.GET`` -- the attacker's value must NOT survive. The unauthenticated
paths are DB-free; they directly prove the fail-closed strip that the removed
early-return used to defeat. One assertion per test (STX-TQ007).
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.writer_app.urls.writer_django import (
    _inject_project_context,
    _strip_working_dir,
)

pytestmark = [pytest.mark.security]

VICTIM = "/data/users/victim/proj/secret/.scitex/writer"


def _req(working_dir=None):
    qs = f"?working_dir={working_dir}" if working_dir is not None else ""
    return RequestFactory().get(f"/apps/writer/v2/api/sections{qs}")


def test_strip_working_dir_removes_the_param():
    # Arrange
    request = _req(VICTIM)
    # Act
    _strip_working_dir(request)
    # Assert
    assert "working_dir" not in request.GET


def test_unauthenticated_caller_working_dir_is_not_honoured():
    # Arrange: login_required guards the real route, but the wrapper must
    # itself fail closed on an unauthenticated request.
    request = _req(VICTIM)
    request.user = AnonymousUser()
    # Act
    _inject_project_context(request)
    # Assert
    assert request.GET.get("working_dir") != VICTIM


def test_unauthenticated_caller_working_dir_is_stripped_entirely():
    # Arrange: the vulnerability was the early-return that preserved a caller
    # value; after the fix an unauthenticated attacker value is stripped.
    request = _req(VICTIM)
    request.user = AnonymousUser()
    # Act
    _inject_project_context(request)
    # Assert
    assert "working_dir" not in request.GET


@pytest.mark.django_db
def test_authenticated_caller_working_dir_never_survives():
    # Arrange
    from django.contrib.auth import get_user_model

    User = get_user_model()
    attacker = User.objects.create_user(
        username="wv2-attacker",
        email="wv2-attacker@example.com",
        password="Password123!",  # pragma: allowlist secret
    )
    request = _req(VICTIM)
    request.user = attacker
    request.session = {}
    # Act
    _inject_project_context(request)
    # Assert: overridden to the user's own project, or stripped (fail closed);
    # never the attacker-supplied path.
    assert request.GET.get("working_dir") != VICTIM
