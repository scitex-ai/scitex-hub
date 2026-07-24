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
"""

from importlib.util import find_spec

import pytest

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
        for entry in patterns:
            nested = getattr(entry, "url_patterns", None)
            if nested is None:
                continue
            yield getattr(entry, "urlconf_name", None)
            yield from _module_names(nested)

    # Act
    mounted = {
        getattr(mod, "__name__", mod)
        for mod in _module_names(get_resolver().url_patterns)
        if mod is not None
    }

    # Assert
    assert "scitex_writer._django.urls" not in mounted
