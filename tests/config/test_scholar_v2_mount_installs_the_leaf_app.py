#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A mounted view is not a mounted app: scholar's templates need its AppConfig installed.

apps/workspace/scholar_app/urls/scholar_django.py mounts scitex-scholar's Django
VIEWS at /apps/scholar/v2/. Until 2026-09-05 nothing added scitex-scholar's Django
APP to INSTALLED_APPS, and Django's app_directories template loader walks
INSTALLED_APPS and nothing else — so the view's own template,
scitex_scholar/_django/templates/scholar/scholar.html, was on disk in the
installed wheel and unreachable. Measured on production after the rebuild:
every visitor request to /apps/scholar/v2/ answered 500 with
TemplateDoesNotExist; anonymous requests never reached the view (login
redirect), so curl looked healthy while every real user got the error page.

The fix registers ``scitex_scholar._django.apps.ScholarEditorConfig`` next to
the other optional leaf apps in config/settings/_optional_apps.py, guarded on
importability like its siblings.

WHAT EACH TEST IS FOR
  optional_apps_include_the_scholar_leaf   the one line that is the fix, read
                                           from the builder with a real
                                           importability probe.
  the_leaf_is_installed_in_django          the app registry actually holds it
                                           once settings load (not just the
                                           list literal).
  the_view_template_resolves               the template Django could not find
                                           now resolves through the loaders the
                                           real settings configure.
  the_control_a_hub_only_registry_cannot_see_it
                                           the same lookup against an engine
                                           whose app registry lacks the leaf
                                           fails — the detector sees the defect
                                           it was written for.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from django.apps import apps
from django.template import TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates
from django.template.loader import get_template

REPO = Path(__file__).resolve().parents[2]
OPTIONAL_APPS = REPO / "config" / "settings" / "_optional_apps.py"
LEAF_CONFIG = "scitex_scholar._django.apps.ScholarEditorConfig"
LEAF_TEMPLATE = "scholar/scholar.html"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("scitex_scholar") is None,
    reason="scitex-scholar is not installed here; the guard is meaningful only where the leaf exists",
)


@pytest.fixture(name="optional_apps", scope="module")
def _optional_apps():
    """Load the builder by path, as test_optional_app_resolution.py does."""
    spec = importlib.util.spec_from_file_location("_optional_apps_under_test", OPTIONAL_APPS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_optional_apps_include_the_scholar_leaf(optional_apps) -> None:
    # Arrange — the real builder against the real environment.
    entries = optional_apps.optional_upstream_apps()
    # Act
    present = LEAF_CONFIG in entries
    # Assert
    assert present, entries


def test_the_leaf_is_installed_in_django() -> None:
    # Arrange — settings are loaded by pytest-django; the registry is live.
    installed = apps.is_installed("scitex_scholar._django")
    # Act
    label = apps.get_app_config("scholar_editor").name if installed else None
    # Assert
    assert label == "scitex_scholar._django", installed


def test_the_view_template_resolves() -> None:
    # Arrange — the template scitex_scholar._django.views.index renders.
    name = LEAF_TEMPLATE
    # Act
    template = get_template(name)
    # Assert
    assert template.origin.name.endswith("scitex_scholar/_django/templates/scholar/scholar.html"), template.origin.name


def test_the_control_a_hub_only_registry_cannot_see_it() -> None:
    # Arrange — an engine configured like hub's but with NO app directories:
    # this is what the template lookup amounted to before the leaf was
    # installed, and it must fail, or the passing test above proves nothing.
    engine = DjangoTemplates(
        {
            "NAME": "hub-only",
            "DIRS": [str(REPO / "templates")],
            "APP_DIRS": False,
            "OPTIONS": {},
        }
    )
    # Act
    lookup = lambda: engine.get_template(LEAF_TEMPLATE)  # noqa: E731 - the act under test
    # Assert
    with pytest.raises(TemplateDoesNotExist):
        lookup()
