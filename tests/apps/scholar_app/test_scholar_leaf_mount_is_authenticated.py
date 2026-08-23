#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/scholar_app/test_scholar_leaf_mount_is_authenticated.py
"""The mounted scitex-scholar leaf must never answer an anonymous request.

WHY THIS FILE IS NOT OPTIONAL
-----------------------------
The leaf's views carry no decorator. Hub has already shipped the raw-mount
version of this mistake once, for WRITER, and removed it as a P0
(sec-working-dir-passthrough-family SITE 3 — see the note in config/urls.py).
The wrapper in scholar_app/urls/scholar_django.py exists to prevent a repeat,
and this file is what keeps the wrapper honest: delete the decoration and these
tests fail.

WHY THE TESTS DRIVE THE CALLBACK DIRECTLY
-----------------------------------------
Asserting through the test client would pull in sessions, middleware and a
database, and would then be testing the middleware stack as much as the mount.
Resolving the URL and calling the callback with an explicitly anonymous request
tests exactly one thing — is THIS view gated — and needs no database.

A structural check (``hasattr(view, "__wrapped__")``) was rejected: it passes for
any decorator at all, including one that does not authenticate.
"""

from __future__ import annotations

import importlib
import sys

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve

MOUNT = "/apps/scholar/v2/"

# Every route the leaf publishes, so a new upstream route that hub forgets to
# gate shows up as a failure here rather than as an open endpoint.
LEAF_ROUTES = [
    "",
    "api/health",
    "api/graph/network",
    "api/graph/related",
    "api/graph/paper",
    "api/graph/health",
]


@pytest.fixture
def anonymous_request():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    return request


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_every_leaf_route_is_mounted(route):
    """A route that silently does not exist renders as a dead graph, not an error."""
    # Arrange
    url = MOUNT + route
    # Act
    match = resolve(url)
    # Assert
    assert match is not None, f"{url} does not resolve"


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_anonymous_request_is_not_served(route, anonymous_request):
    """login_required redirects rather than rendering — 302, never 200."""
    # Arrange
    view = resolve(MOUNT + route).func
    # Act
    response = view(anonymous_request)
    # Assert
    assert response.status_code == 302, (
        f"{MOUNT + route} answered {response.status_code} to an ANONYMOUS "
        "request — the leaf is publicly exposed."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_anonymous_request_is_sent_to_login(route, anonymous_request):
    """Paired with the test above: a 302 to the wrong place is still a leak."""
    # Arrange
    view = resolve(MOUNT + route).func
    # Act
    response = view(anonymous_request)
    # Assert
    assert "/auth/login/" in response.url or "login" in response.url, (
        f"{MOUNT + route} redirected to {response.url!r}, which is not a login "
        "page — the request was diverted, not authenticated."
    )


LEAF_MODULE = "scitex_scholar._django.urls"
_ABSENT = object()


@pytest.fixture
def module_with_broken_leaf():
    """Reload scholar_django with the leaf genuinely unimportable, then restore.

    NO MOCK LIBRARY. Binding a sys.modules entry to None is a REAL import-system
    state that makes `import` raise ImportError — the same interpreter machinery
    that produced the dev-container failure, not a stand-in for it. The module is
    then reloaded for real and its actual urlpatterns are read.
    """
    import apps.workspace.scholar_app.urls.scholar_django as module

    saved = sys.modules.get(LEAF_MODULE, _ABSENT)
    sys.modules[LEAF_MODULE] = None
    try:
        yield importlib.reload(module)
    finally:
        if saved is _ABSENT:
            sys.modules.pop(LEAF_MODULE, None)
        else:
            sys.modules[LEAF_MODULE] = saved
        # Restore the real module for every other test in the session.
        importlib.reload(module)


def test_a_broken_leaf_does_not_take_down_the_urlconf(module_with_broken_leaf):
    """The outage this guard exists to prevent, reproduced.

    MEASURED 2026-08-23, minutes after #687 merged and before it was deployed:
    scholar 1.9.0's views import `mount_prefix` from `scitex_app.embed`, and the
    scitex-app in the dev container is 0.6.1 and does not export it. Both are
    editable installs from bind-mounted working trees, so hub's
    `scitex-scholar>=1.9.0` floor governs neither.

    Unguarded, that ImportError propagates out of scholar_app/urls/__init__.py
    into config/urls.py and every URL hub serves stops resolving — the landing
    page included. Reaching the module at all is the assertion.
    """
    # Arrange
    expected = []
    # Act
    actual = module_with_broken_leaf.urlpatterns
    # Assert
    assert actual == expected


def test_a_broken_leaf_is_reported_not_swallowed(module_with_broken_leaf, caplog):
    """Paired with the test above: degrading quietly would be its own defect.

    The constitution forbids silent fallbacks. Omitting the routes is the right
    behaviour ONLY because the reason is written down where an operator will
    find it, so the log line is part of the contract, not decoration.
    """
    # Arrange — the fixture already has the leaf unimportable; reload inside the
    # capture so the module-scope logger call is recorded.
    module = module_with_broken_leaf
    # Act
    with caplog.at_level("ERROR"):
        importlib.reload(module)
    # Assert
    assert any("could not be imported" in r.message for r in caplog.records)


def test_wrapper_refuses_a_urlconf_it_cannot_gate():
    """A nested include() would leave its inner routes ungated; refuse to mount.

    This is the failure mode the module is most likely to meet: upstream
    reorganises its urlconf, hub's decoration silently applies to a resolver
    instead of a view, and the routes inside it are published unauthenticated.
    """
    # Arrange
    from django.urls import include, path

    from apps.workspace.scholar_app.urls.scholar_django import (
        ImproperlyGatedURLConf,
        _gated,
    )

    nested = [path("nested/", include(([], "x"), namespace="x"))]
    gate = _gated
    # Act
    attempt = lambda: gate(nested)  # noqa: E731 - deferred so Assert owns the raise
    # Assert
    with pytest.raises(ImproperlyGatedURLConf):
        attempt()
