#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The scitex-cards AppConfig rename window, asserted in both directions.

On 2026-08-16 scitex-cards' ``develop`` renamed its Django AppConfig
``ScitexTodoConfig`` -> ``ScitexCardsConfig`` with no alias, while every
published wheel through 0.40.0 still shipped the old name. Hub installs the
BRANCH (``.scitex-apps.json`` pins ``git_ref: "develop"``,
``scripts/apps/install_apps.sh`` pip-installs it, in CI and in root-init.sh at
prod container start) and also resolves the package from PyPI elsewhere — so
both names are live at once and hub must accept either.

Getting it wrong is not a warning. ``django.setup()`` raises and the site does
not start:

    ImportError: Module 'scitex_cards._django.apps' does not contain a
    'ScitexTodoConfig' class. Choices are: 'ScitexAppConfig',
    'ScitexCardsConfig'.

That is what took down the Playwright E2E job, and prod is one container
restart from the same failure.

WHY THIS LOADS THE MODULE BY PATH. ``config/__init__.py`` imports celery, so
``import config.settings._optional_apps`` drags in the whole Django app just to
reach a resolver that deliberately has no Django dependency. Loading the file
directly keeps this suite runnable wherever bash and python are — and asserts
that independence rather than assuming it, which matters because this resolver
runs during settings import, before Django is configured.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "config" / "settings" / "_optional_apps.py"

NEW_NAME = "ScitexCardsConfig"
OLD_NAME = "ScitexTodoConfig"


@pytest.fixture(name="optional_apps", scope="module")
def _optional_apps():
    """Load config/settings/_optional_apps.py with no package import."""
    spec = importlib.util.spec_from_file_location(
        "_optional_apps_under_test", MODULE_PATH
    )
    assert spec and spec.loader, f"could not load {MODULE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolves_the_new_name_when_upstream_has_renamed(optional_apps) -> None:
    # Arrange — scitex-cards develop: renamed, no alias.
    apps_module = SimpleNamespace(**{NEW_NAME: object(), "ScitexAppConfig": object()})

    # Act
    path = optional_apps.cards_appconfig_path(apps_module)

    # Assert
    assert path == f"scitex_cards._django.apps.{NEW_NAME}"


def test_resolves_the_old_name_on_every_published_wheel(optional_apps) -> None:
    # Arrange — PyPI through 0.40.0: old name only. Hub still resolves the
    # package from PyPI in some install paths, so this is not a legacy case.
    apps_module = SimpleNamespace(**{OLD_NAME: object(), "ScitexAppConfig": object()})

    # Act
    path = optional_apps.cards_appconfig_path(apps_module)

    # Assert
    assert path == f"scitex_cards._django.apps.{OLD_NAME}"


def test_prefers_the_new_name_when_upstream_ships_the_alias(optional_apps) -> None:
    # Arrange — the shape if upstream does the migration properly. Preferring
    # the new name is what lets hub stop depending on the deprecated one.
    apps_module = SimpleNamespace(
        **{NEW_NAME: object(), OLD_NAME: object(), "ScitexAppConfig": object()}
    )

    # Act
    path = optional_apps.cards_appconfig_path(apps_module)

    # Assert
    assert path == f"scitex_cards._django.apps.{NEW_NAME}"


def test_refuses_loudly_when_upstream_renames_again(optional_apps) -> None:
    # Arrange — a third name nobody taught hub about.
    apps_module = SimpleNamespace(SomeFutureConfig=object(), ScitexAppConfig=object())

    # Act / Assert — must NOT be an ImportError: optional_upstream_apps treats
    # that as "not installed, skip", which would drop the board mount silently.
    with pytest.raises(RuntimeError) as excinfo:
        optional_apps.cards_appconfig_path(apps_module)

    message = str(excinfo.value)
    assert NEW_NAME in message and OLD_NAME in message, message
    assert "SomeFutureConfig" in message, (
        "the refusal must report what it actually FOUND, not only what it "
        f"wanted — otherwise the reader cannot tell what upstream did: {message}"
    )


def test_refusal_is_not_an_importerror(optional_apps) -> None:
    # Arrange — POSITIVE CONTROL for the test above. `pytest.raises(RuntimeError)`
    # would also pass if the code raised a subclass of both, and ImportError is
    # precisely the type that gets swallowed one frame up.
    apps_module = SimpleNamespace(ScitexAppConfig=object())

    # Act
    with pytest.raises(Exception) as excinfo:  # noqa: PT011 - type is the assertion
        optional_apps.cards_appconfig_path(apps_module)

    # Assert
    assert not isinstance(excinfo.value, ImportError), (
        "cards_appconfig_path raised an ImportError; optional_upstream_apps "
        "catches that and would silently drop the cards mount."
    )
