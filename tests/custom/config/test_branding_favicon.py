# -*- coding: utf-8 -*-
# File: tests/custom/config/test_branding_favicon.py
"""The favicon COLOUR encodes the ENVIRONMENT (config/branding.py).

Operator contract: prod / staging / dev must be distinguishable from the tab
icon alone --

    production  -> white snake on NAVY   (the official product look)
    staging     -> NAVY snake on WHITE   ("ネイビーのヘビーなもの")
    development -> white snake on GREEN

All three are the SAME brand mark, differing only in colour. The choice is
driven by ``settings.SCITEX_ENV`` -- i.e. by which settings module Django is
running as -- never by ``DEBUG`` and never hardcoded per-template.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import override_settings

from config import branding
from config.context_processors import scitex_env

from ._branding_helpers import FakeRequest, favicon_svg, render


# ---------------------------------------------------------------------------
# Environment normalization -- no silent fallback
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("development", branding.ENV_DEVELOPMENT),
        ("dev", branding.ENV_DEVELOPMENT),
        ("staging", branding.ENV_STAGING),
        ("stag", branding.ENV_STAGING),
        ("production", branding.ENV_PRODUCTION),
        ("prod", branding.ENV_PRODUCTION),
        ("  PROD  ", branding.ENV_PRODUCTION),
    ],
)
def test_normalize_env_accepts_canonical_names_and_aliases(raw, expected):
    # Arrange: the parameters supply the raw value and its canonical form.

    # Act
    result = branding.normalize_env(raw)

    # Assert
    assert result == expected


@pytest.mark.parametrize("bad", ["", None, "prd", "local", "production2"])
def test_normalize_env_raises_on_unknown(bad):
    """A typo'd environment must fail loudly, not silently serve prod's icon."""
    # Arrange
    unknown_env = bad

    # Act
    # Assert
    with pytest.raises(ValueError):
        branding.normalize_env(unknown_env)


def test_normalize_mode_raises_on_unknown():
    # Arrange
    unknown_mode = "embedded"

    # Act
    # Assert
    with pytest.raises(ValueError):
        branding.normalize_mode(unknown_mode)


# ---------------------------------------------------------------------------
# The colour map
# ---------------------------------------------------------------------------
def test_each_environment_gets_a_distinct_favicon():
    # Arrange
    envs = branding.KNOWN_ENVS

    # Act
    icons = {branding.favicon_for_env(env) for env in envs}

    # Assert
    assert len(icons) == len(envs)


@pytest.mark.parametrize(
    ("env", "suffix"),
    [
        ("production", "white-bg-navy.svg"),
        ("staging", "navy-bg-white.svg"),
        ("development", "white-bg-green.svg"),
    ],
)
def test_favicon_colour_matches_the_operator_specification(env, suffix):
    # Arrange: the parameters carry the operator's colour spec.

    # Act
    icon = branding.favicon_for_env(env)

    # Assert
    assert icon.endswith(suffix)


def test_favicon_for_env_raises_on_unknown():
    # Arrange
    unknown_env = "prd"

    # Act
    # Assert
    with pytest.raises(ValueError):
        branding.favicon_for_env(unknown_env)


# ---------------------------------------------------------------------------
# The assets themselves
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("env", branding.KNOWN_ENVS)
def test_favicon_asset_exists_on_disk(env):
    """A renamed/removed icon would 404 the tab icon silently -- catch it here."""
    # Arrange
    path = settings.BASE_DIR / "static" / branding.favicon_for_env(env)

    # Act
    exists = path.is_file()

    # Assert
    assert exists, f"missing favicon asset for {env}: {path}"


@pytest.mark.parametrize("token", ['id="scitex-logo"', "snake-fill"])
@pytest.mark.parametrize("env", branding.KNOWN_ENVS)
def test_favicon_is_the_scitex_brand_mark(env, token):
    """All three envs are the SAME brand mark, differing only in colour."""
    # Arrange
    svg = favicon_svg(env)

    # Act
    present = token in svg

    # Assert
    assert present, f"{env} favicon is not the SciTeX brand mark ({token!r})"


@pytest.mark.parametrize(
    "declaration",
    [".bg-fill { fill: #ffffff; }", ".snake-fill { fill: #1a2a40;"],
)
def test_staging_favicon_is_navy_on_white(declaration):
    """The operator's 'ネイビーのヘビーなもの': navy mark on a white background."""
    # Arrange
    svg = favicon_svg("staging")

    # Act
    present = declaration in svg

    # Assert
    assert present, f"staging favicon missing {declaration!r}"


# ---------------------------------------------------------------------------
# Django wiring
# ---------------------------------------------------------------------------
@override_settings(SCITEX_ENV="staging")
def test_context_processor_publishes_the_environment_favicon():
    # Arrange
    expected = branding.favicon_for_env("staging")

    # Act
    ctx = scitex_env(FakeRequest("/"))

    # Assert
    assert ctx["SCITEX_FAVICON"] == expected


@override_settings(SCITEX_ENV="staging", SCITEX_APP_MODE=branding.MODE_HUB)
def test_context_processor_publishes_the_environment_marker():
    # Arrange
    expected = "staging"

    # Act
    ctx = scitex_env(FakeRequest("/"))

    # Assert
    assert ctx["SCITEX_ENV_MARKER"] == expected


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_context_processor_leaves_production_unmarked():
    # Arrange
    request = FakeRequest("/")

    # Act
    ctx = scitex_env(request)

    # Assert
    assert ctx["SCITEX_ENV_MARKER"] is None


@override_settings(SCITEX_ENV="production")
def test_context_processor_serves_navy_in_production():
    # Arrange
    request = FakeRequest("/")

    # Act
    ctx = scitex_env(request)

    # Assert
    assert ctx["SCITEX_FAVICON"].endswith("white-bg-navy.svg")


@override_settings(SCITEX_ENV="development")
def test_favicon_is_not_driven_by_debug():
    """DEBUG is a debug flag, not an environment: flipping it must not change
    the tab icon. Only SCITEX_ENV may."""
    # Arrange
    expected = branding.favicon_for_env("development")

    # Act
    with override_settings(DEBUG=True):
        with_debug = scitex_env(FakeRequest("/"))["SCITEX_FAVICON"]
    with override_settings(DEBUG=False):
        without_debug = scitex_env(FakeRequest("/"))["SCITEX_FAVICON"]

    # Assert
    assert with_debug == without_debug == expected


@override_settings(SCITEX_ENV="staging")
def test_static_favicon_resolves_to_the_environment_icon_url():
    """Proves SCITEX_FAVICON reaches the template AND {% static %} accepts it."""
    # Arrange
    source = '{% load static %}<link href="{% static SCITEX_FAVICON %}" />'

    # Act
    html = render(source)

    # Assert
    assert "scitex-icon-navy-bg-white.svg" in html
