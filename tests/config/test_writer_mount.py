#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guards for the upstream scitex-writer mount (card
hub-mount-writer-django-app-20260707).

The mount is conditional: when the ``scitex_writer`` package is
importable, its contract-compliant ``_django`` app must be installed
under the explicit ``WriterEditorConfig`` path (a bare module entry
falls back to app label ``_django`` and collides with
``figrecipe._django``'s identical fallback) and URL-mounted at
``/writer/``. When the package is absent, neither must appear.
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


@pytest.mark.skipif(not _WRITER_INSTALLED, reason="scitex-writer not installed")
def test_writer_root_url_resolves_to_writer_namespace():
    # Arrange
    from django.urls import resolve

    # Act
    match = resolve("/writer/")

    # Assert
    assert match.view_name.startswith("writer:")


@pytest.mark.skipif(_WRITER_INSTALLED, reason="scitex-writer is installed")
def test_writer_url_absent_when_package_missing():
    # Arrange
    from django.urls import Resolver404, resolve

    # Act
    try:
        resolve("/writer/")
        resolved = True
    except Resolver404:
        resolved = False

    # Assert
    assert resolved is False
