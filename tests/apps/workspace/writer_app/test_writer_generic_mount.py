#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/writer_app/test_writer_generic_mount.py
"""/apps/writer/ is the writer leaf, mounted by the GENERIC plugin mount.

The hub keeps no list of writer route names. Every route the installed
leaf's own urlconf declares is served at /apps/writer/<route>, inside the
leaf's own ``writer`` namespace, login-gated by the leaf manifest's
``mount_policy.login_required``, with the leaf's own CSRF decision. The
expectations below are DERIVED from the installed leaf urlconf, so a route
the leaf adds or renames is covered with zero hub changes (the old
hard-coded allowlist omitted five such routes and logged an ERROR for each).

The dev-only old-direct reference (hub-native) is hoisted ahead of the leaf
mount, so the leaf's ``<path:endpoint>`` catch-all cannot swallow it.

NO DATABASE: resolving a URL and calling its callback with an anonymous
request tests exactly one thing — is THIS view gated.
"""

from __future__ import annotations

import importlib.util
import re

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve, reverse

from ._old_direct_gate import writer_old_direct  # noqa: F401 - pytest fixture

ROOT = "/apps/writer/"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("scitex_writer._django.urls") is None,
    reason="scitex-writer is not installed here",
)

RF = RequestFactory()

_SAMPLES = {"int": "1", "path": "api/files", "str": "x", "slug": "x", "uuid": "0" * 32}


def _leaf_patterns():
    if importlib.util.find_spec("scitex_writer._django.urls") is None:
        return []
    from scitex_writer._django.urls import urlpatterns

    return list(urlpatterns)


def _sample_path(entry) -> str:
    """A concrete URL for one leaf route (converters filled with samples)."""
    route = str(entry.pattern)
    return ROOT + re.sub(
        r"<(?:(\w+):)?\w+>", lambda m: _SAMPLES[m.group(1) or "str"], route
    )


LEAF_ROUTES = [pytest.param(e, id=e.name) for e in _leaf_patterns()]


@pytest.mark.parametrize("entry", LEAF_ROUTES)
def test_every_leaf_route_resolves_at_the_writer_mount(entry):
    # Arrange
    url = _sample_path(entry)
    # Act
    match = resolve(url)
    # Assert
    assert (match.namespace, match.url_name) == ("writer", entry.name)


@pytest.mark.parametrize("entry", LEAF_ROUTES)
def test_every_leaf_route_is_served_by_the_leaf_view(entry):
    # Arrange
    url = _sample_path(entry)
    # Act
    match = resolve(url)
    # Assert — the login wrapper wraps the leaf's own callback, nothing hub-side
    assert match.func.__wrapped__ is entry.callback


@pytest.mark.parametrize("entry", LEAF_ROUTES)
def test_every_leaf_route_redirects_anonymous_callers_to_login(entry):
    # Arrange
    url = _sample_path(entry)
    match = resolve(url)
    request = RF.get(url)
    request.user = AnonymousUser()
    # Act
    response = match.func(request, *match.args, **match.kwargs)
    # Assert
    assert response.status_code == 302


@pytest.mark.parametrize("entry", LEAF_ROUTES)
def test_every_leaf_route_keeps_the_leaf_csrf_decision(entry):
    # Arrange
    match = resolve(_sample_path(entry))
    # Act
    exempt = getattr(match.func, "csrf_exempt", False)
    # Assert
    assert exempt == getattr(entry.callback, "csrf_exempt", False)


def test_assistant_skill_route_reverses_to_the_leaf_editor():
    # Arrange — the route name the assistant skill declares
    from apps.infra.llm_app.skills import get_skill

    route = get_skill("writer").url_route
    # Act
    url = reverse(route)
    # Assert
    assert url == ROOT


def test_old_direct_is_not_hub_served_without_the_dev_gate():
    # Arrange
    url = ROOT + "old-direct/"
    # Act
    match = resolve(url)
    # Assert — the ambient (prod-shaped) suite has no hub legacy mount
    assert match.namespace != "writer_app"


def test_old_direct_reference_wins_over_the_leaf_catch_all(writer_old_direct):  # noqa: F811
    # Arrange
    url = ROOT + "old-direct/"
    # Act
    match = resolve(url)
    # Assert
    assert match.namespace == "writer_app"


def test_leaf_root_still_serves_the_leaf_with_old_direct_on(writer_old_direct):  # noqa: F811
    # Arrange
    url = ROOT
    # Act
    match = resolve(url)
    # Assert
    assert (match.namespace, match.url_name) == ("writer", "editor")


# EOF
