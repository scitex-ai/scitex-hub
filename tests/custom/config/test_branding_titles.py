# -*- coding: utf-8 -*-
# File: tests/custom/config/test_branding_titles.py
"""The browser tab TITLE (config/branding.py).

Operator contract -- one pattern everywhere:

    <Detail> · <App> — SciTeX            hub, production
    <App> — SciTeX (dev|staging)         hub, non-production
    <App> — SciTeX (standalone)          a standalone app, any environment

The product name is spelled EXACTLY "SciTeX"; app names are Capitalized
("Todo", never "todo"); the version never appears; and a hub-embedded app must
be distinguishable from the same app running standalone.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.infra.project_app.templatetags import branding_tags
from config import branding

from ._branding_helpers import FakeRequest, render


# ---------------------------------------------------------------------------
# Names: Capitalized, and the brand is exactly "SciTeX"
# ---------------------------------------------------------------------------
def test_site_name_is_exactly_scitex():
    # Arrange
    expected = "SciTeX"

    # Act
    actual = branding.SITE_NAME

    # Assert
    assert actual == expected


@pytest.mark.parametrize("app_name", sorted(set(branding.APP_NAMES.values())))
def test_app_names_are_capitalized(app_name):
    """Operator: "Cards", never "cards"; "FigRecipe", never "figrecipe"."""
    # Arrange
    first_char = app_name[0]

    # Act
    capitalized = first_char.isupper()

    # Assert
    assert capitalized, f"{app_name!r} must be Capitalized"


def test_every_app_the_operator_named_has_a_title():
    # Arrange
    expected = {
        "Cards",
        "Writer",
        "Scholar",
        "FigRecipe",
        "Console",
        "Clew",
        "Explore",
        "Projects",
        "Storage",
        "Store",
        "Docs",
        "Tools",
    }

    # Act
    configured = set(branding.APP_NAMES.values())

    # Assert
    assert expected <= configured, f"missing: {expected - configured}"


# The upstream scitex-writer package's own Django app. It is the ONE app still
# mounted at the root, because hub's native writer_app currently occupies
# /apps/writer/; retiring the native one is tracked separately. Every other app
# lives under /apps/<name>/.
_ROOT_MOUNTED_APPS = {"/writer/"}


def test_every_app_prefix_is_a_path_that_actually_exists():
    """A title prefix that matches no real route silently names nothing.

    app_for_path() matches with str.startswith. The map used to be keyed on bare
    names ("/scholar/", "/figrecipe/", ...) while the real routes are
    /apps/scholar/, /apps/figrecipe/ — so NONE of those entries ever matched a
    request, and every one of those apps rendered a tab titled just "SciTeX".
    The old tests missed it because they asserted app_for_path("/figrecipe/...")
    — a URL that 404s — instead of the URL a user is actually on.

    So assert the invariant, not the examples: an app prefix is /apps/<name>/,
    with the root mounts named explicitly above.
    """
    # Arrange
    prefixes = set(branding.APP_NAMES)

    # Act
    off_pattern = {
        p for p in prefixes if not p.startswith("/apps/") and p not in _ROOT_MOUNTED_APPS
    }

    # Assert
    assert not off_pattern, (
        f"{off_pattern} match no /apps/ route and are not declared root mounts — "
        "they would silently produce no tab title"
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/writer/", "Writer"),
        ("/apps/cards/", "Cards"),
        ("/apps/figrecipe/some/deep/page", "FigRecipe"),
        ("/social/explore/", "Explore"),  # longest prefix wins over /explore/
        ("/browse/", "Files"),
        ("/", None),
        ("/settings/", None),
    ],
)
def test_app_for_path(path, expected):
    # Arrange: the parameters supply the request path and the expected label.

    # Act
    actual = branding.app_for_path(path)

    # Assert
    assert actual == expected


# ---------------------------------------------------------------------------
# The title pattern
# ---------------------------------------------------------------------------
def test_hub_production_title_is_unmarked():
    # Arrange
    expected = "Writer — SciTeX"

    # Act
    title = branding.page_title(app="Writer", env="production")

    # Assert
    assert title == expected


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ("development", "Writer — SciTeX (dev)"),
        ("staging", "Writer — SciTeX (staging)"),
    ],
)
def test_hub_non_production_titles_are_marked(env, expected):
    # Arrange: the parameters supply the environment and its expected title.

    # Act
    title = branding.page_title(app="Writer", env=env)

    # Assert
    assert title == expected


def test_standalone_title_carries_the_standalone_marker():
    """Operator: a standalone app must be tellable from the tab alone."""
    # Arrange
    expected = "Writer — SciTeX (standalone)"

    # Act
    title = branding.page_title(
        app="Writer", env="production", mode=branding.MODE_STANDALONE
    )

    # Assert
    assert title == expected


def test_standalone_title_differs_from_hub_embedded_title():
    # Arrange
    hub = branding.page_title(app="Writer", env="production", mode=branding.MODE_HUB)

    # Act
    standalone = branding.page_title(
        app="Writer", env="production", mode=branding.MODE_STANDALONE
    )

    # Assert
    assert standalone != hub


def test_standalone_marker_wins_over_environment():
    # Arrange
    expected = "Writer — SciTeX (standalone)"

    # Act
    title = branding.page_title(
        app="Writer", env="development", mode=branding.MODE_STANDALONE
    )

    # Assert
    assert title == expected


def test_detail_precedes_the_app():
    # Arrange
    expected = "my-proj · Writer — SciTeX"

    # Act
    title = branding.page_title(app="Writer", detail="my-proj", env="production")

    # Assert
    assert title == expected


def test_title_without_an_app_is_just_the_brand():
    # Arrange
    expected = "SciTeX"

    # Act
    title = branding.page_title(env="production")

    # Assert
    assert title == expected


def test_title_without_an_app_still_carries_the_environment_marker():
    # Arrange
    expected = "SciTeX (dev)"

    # Act
    title = branding.page_title(env="development")

    # Assert
    assert title == expected


@pytest.mark.parametrize("env", branding.KNOWN_ENVS)
def test_title_never_contains_a_version(env):
    """Operator disliked a prominent version; it stays out of the tab.

    The detail is deliberately digit-free, so any digit in the result could
    only have come from a version being spliced into the title.
    """
    # Arrange
    title = branding.page_title(app="Writer", detail="proj", env=env)

    # Act
    digits = [ch for ch in title if ch.isdigit()]

    # Assert
    assert not digits, f"version leaked into the tab title: {title!r}"


def test_page_title_requires_an_explicit_environment():
    """No implicit env default -- a missing environment is a loud error."""
    # Arrange
    app = "Writer"

    # Act
    # Assert
    with pytest.raises(TypeError):
        branding.page_title(app=app)


# ---------------------------------------------------------------------------
# Django wiring: the template tag
# ---------------------------------------------------------------------------
@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_template_tag_builds_the_title_from_the_request_path():
    # Arrange
    context = {"request": FakeRequest("/apps/scholar/")}

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "Scholar — SciTeX"


@override_settings(SCITEX_ENV="development", SCITEX_APP_MODE=branding.MODE_HUB)
def test_template_tag_marks_the_development_environment():
    # Arrange
    context = {"request": FakeRequest("/apps/cards/")}

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "Cards — SciTeX (dev)"


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_STANDALONE)
def test_template_tag_marks_a_standalone_app():
    # Arrange
    context = {"request": FakeRequest("/writer/")}

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "Writer — SciTeX (standalone)"


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_template_tag_uses_the_current_project_as_detail():
    # Arrange
    class _Project:
        slug = "my-proj"

    context = {"request": FakeRequest("/writer/"), "current_project": _Project()}

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "my-proj · Writer — SciTeX"


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_template_tag_uses_the_profile_username_as_detail():
    # Arrange
    class _User:
        username = "ywatanabe"

    context = {"request": FakeRequest("/u/ywatanabe/"), "profile_user": _User()}

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "ywatanabe — SciTeX"


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_template_tag_honours_an_explicit_page_title_detail():
    """A view supplies the detail; the brand suffix is still appended once."""
    # Arrange
    context = {"request": FakeRequest("/apps/scholar/"), "page_title_detail": "Library"}

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "Library · Scholar — SciTeX"


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_explicit_page_title_detail_wins_over_the_project_slug():
    # Arrange
    class _Project:
        slug = "my-proj"

    context = {
        "request": FakeRequest("/apps/scholar/"),
        "current_project": _Project(),
        "page_title_detail": "Library",
    }

    # Act
    title = branding_tags.page_title(context)

    # Assert
    assert title == "Library · Scholar — SciTeX"


# ---------------------------------------------------------------------------
# End-to-end: the tag must actually LOAD in a real template.
#
# The tests above call the tag FUNCTION directly, which would still pass even
# if `{% load branding_tags %}` were unresolvable -- in which case every page in
# the hub would raise TemplateSyntaxError. This renders a real template.
# ---------------------------------------------------------------------------
@override_settings(SCITEX_ENV="development", SCITEX_APP_MODE=branding.MODE_HUB)
def test_page_title_tag_is_loadable_and_renders_in_a_real_template():
    # Arrange
    source = "{% load branding_tags %}<title>{% page_title %}</title>"

    # Act
    html = render(source)

    # Assert
    assert html == "<title>Writer — SciTeX (dev)</title>"
