#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guards for the upstream scitex-writer mount (card
hub-mount-writer-django-app-20260707).

The ``scitex_writer._django`` app must be installed under the explicit
``WriterEditorConfig`` path (a bare module entry falls back to app label
``_django`` and collides with ``figrecipe._django``'s identical fallback).

THE RAW ``/writer/`` URL MOUNT IS GONE ON PURPOSE (card
sec-working-dir-passthrough-family, SITE 3). It used to be
``path("writer/", include("scitex_writer._django.urls"))`` — the package's own
urlconf, mounted with NO ``@login_required``, NO CSRF, and honouring a
caller-supplied ``?working_dir=``, i.e. an UNAUTHENTICATED arbitrary-path
directory read. It was verified leaking on production
(``GET /writer/api/files?working_dir=/tmp`` -> 200, directory listing) and was
tourniqueted at the edge with an nginx ``return 403`` while the code fix landed.

An nginx rule is a mitigation, not a guard: it lives outside the application,
so it protects exactly one deployment and neither dev nor staging (which run no
nginx at all). Removing the mount in code is the actual fix, and the assertions
below are what keep it removed. The legitimate, login-gated writer lives at
``/apps/writer/`` and is unaffected.

THE nginx TOURNIQUET IS NOW GONE (2026-08-17). ``location /writer/ { return
403; }`` was deleted from deployment/docker/common/nginx/nginx_prod.conf. It
was not merely dead: it sat IN FRONT of the legacy 301 that this repo promises
(config/urls_legacy_redirects.py, ``LEGACY_APP_NAMES`` contains "writer"), so
every surviving ``/writer/`` link answered 403 instead of taking the reader to
the working app. ``TestLegacyWriterPrefixRedirects`` below pins the redirect
that the block was intercepting, so the removal is asserted rather than
assumed — and so nothing re-adds a blanket 403 without a red test.
"""

from importlib.util import find_spec

import pytest
from django.test import Client

_WRITER_INSTALLED = find_spec("scitex_writer") is not None


@pytest.mark.skipif(not _WRITER_INSTALLED, reason="scitex-writer not installed")
def test_writer_app_installed_via_explicit_appconfig_path():
    # Arrange
    from django.conf import settings

    # Act
    entry_present = (
        "scitex_writer._django.apps.WriterEditorConfig" in settings.INSTALLED_APPS
    )

    # Assert
    assert entry_present is True


def test_writer_root_url_does_not_reach_the_raw_upstream_namespace():
    # Arrange: /writer/ must NOT resolve into the package's own urlconf. It now
    # falls through to the legacy redirect (config/urls_legacy_redirects.py,
    # LEGACY_APP_NAMES contains "writer"), which is a plain RedirectView and
    # carries no view_name in the "writer:" namespace.
    from django.urls import Resolver404, resolve

    # Act
    try:
        view_name = resolve("/writer/").view_name
    except Resolver404:
        view_name = ""

    # Assert
    assert not view_name.startswith("writer:")


def test_no_urlpattern_includes_the_raw_scitex_writer_urlconf():
    # Arrange: the security invariant itself — nothing anywhere may re-mount the
    # package urlconf. Asserted against the RESOLVED urlconf, so a re-add under
    # any prefix (or via a second include) is caught, not just the old line.
    from django.urls import get_resolver

    def _module_names(patterns):
        # ``urlconf_name`` is a module for ``include("a.b.urls")``, a plain str
        # in some paths, and a LIST of patterns for ``include([...])`` or a
        # namespace tuple. Only the first two name a module; a list is not
        # hashable and has no __name__, so yield nothing for it and rely on the
        # recursion below to walk what it contains.
        for entry in patterns:
            nested = getattr(entry, "url_patterns", None)
            if nested is None:
                continue
            raw = getattr(entry, "urlconf_name", None)
            name = getattr(raw, "__name__", None)
            if isinstance(name, str):
                yield name
            elif isinstance(raw, str):
                yield raw
            yield from _module_names(nested)

    # Act
    mounted = set(_module_names(get_resolver().url_patterns))

    # Assert
    assert "scitex_writer._django.urls" not in mounted


@pytest.mark.django_db
class TestLegacyWriterPrefixRedirects:
    """What the removed nginx ``location /writer/ { return 403; }`` blocked.

    The block guarded a mount that no longer exists, and in doing so it broke
    the thing that replaced it. These assert the replacement behaviour in
    Django, where it is checked on every push rather than on whoever next
    reads an nginx conf.
    """

    def test_legacy_writer_prefix_is_a_permanent_redirect(self):
        # Arrange
        http = Client()
        # Act
        response = http.get("/writer/")
        # Assert
        assert response.status_code == 301

    def test_legacy_writer_prefix_redirects_to_the_gated_apps_mount(self):
        # Arrange — a 301 to the wrong place would still be a 301
        http = Client()
        # Act
        response = http.get("/writer/")
        # Assert
        assert response.headers["Location"] == "/apps/writer/"

    def test_legacy_writer_api_path_is_not_served(self):
        # Arrange — the exact probe that leaked before the mount was removed.
        # ``follow=True`` because APPEND_SLASH 301s this to /writer/api/files/
        # first; asserting on the un-followed response would pin the redirect
        # rather than the outcome, and a redirect is not an answer.
        http = Client()
        # Act
        response = http.get(
            "/writer/api/files", {"working_dir": "/tmp"}, follow=True
        )
        # Assert — no handler answers under the legacy prefix any more
        assert response.status_code == 404
