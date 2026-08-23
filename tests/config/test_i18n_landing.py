#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_i18n_landing.py
"""Japanese landing page: automatic language selection, catalogs, and switcher.

WHY THIS FILE EXISTS
--------------------
Django resolves a missing translation by returning the msgid — the English
source string. So EVERY failure mode in this feature is silent: a template that
lost its {% trans %}, a catalog that was never compiled, a locale directory
absent from LOCALE_PATHS, and a correctly-working English page all render
IDENTICALLY. Nothing raises, nothing logs, and the page is simply in the wrong
language.

That is why every assertion here is PAIRED with its opposite-language control.
"hero contains 'ゲストとして試す' under ja" alone is a decent test; without the
matching "hero contains 'Enter as visitor' under en" it would still pass if the
catalog somehow translated unconditionally, and — more importantly — the pair
is what proves the RENDER is language-sensitive rather than the fixture being.

WHY THE FIXTURE COMPILES
------------------------
`*.mo` is gitignored (.gitignore:278), so a fresh checkout has catalogs in
source form only. The image build compiles them; these tests do the same thing
in-process so they exercise the real .po content rather than a stale artifact
left over from someone's last run.

Operator context (2026-08-23): the landing page is read by investors and lenders
in Japan — 「日本の会社でビジコンやら融資やらでも外部の方が見られた方が良いので」 —
and the switch must be AUTOMATIC from the visitor's browser preference:
「アクセス者の言語 preference を取って自動で日本語英語切り替えるようにしてほしいです」.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import NoReverseMatch, reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HERO_TEMPLATE = "public_app/landing_partials/landing_hero.html"
SWITCHER_TEMPLATE = "global_base_partials/language_switcher.html"

# One string per surface, chosen because each proves a DIFFERENT link in the
# chain: the constant path (branding.py -> context processor), the plain
# template path, and the interpolating one (blocktrans).
CTA_EN = "Enter as visitor"
CTA_JA = "ゲストとして試す"


def _reverse_or_none(name):
    """reverse(), returning None instead of raising, so the test keeps one assert.

    A NoReverseMatch here means the route is absent, which is exactly the thing
    under test — turning it into a value keeps the failure on the assertion line
    rather than in an exception handler.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo before any assertion reads a catalog.

    Uses the project's own compile step rather than `compilemessages`, because
    msgfmt is absent from this container AND from the prod image; see
    scripts/i18n/compile_catalogs.py for the measurements.
    """
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"catalog compilation failed ({result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # Django caches translation objects per language; anything loaded before
    # the .mo existed would be an empty catalog that never reloads.
    translation.trans_real._translations.clear()
    yield


# ---------------------------------------------------------------------------
# The constraint that marking branding strings actually broke
# ---------------------------------------------------------------------------
def test_branding_stays_importable_while_settings_are_composing():
    """config/branding.py must not import Django at module scope.

    Its docstring has said so for a long time; this asserts it, because the
    docstring did not stop me from adding ``from django.utils.translation
    import gettext_noop`` and breaking every environment's settings import.

    ``settings_shared.py`` calls ``branding.normalize_env(...)`` while composing
    settings, so a Django import here is circular: django.utils.translation ->
    django.conf.settings -> config.settings -> settings_shared -> back into a
    half-executed config.branding, where ``normalize_env`` does not exist yet.

    Run in a SUBPROCESS on purpose. In-process the module is already imported
    and fully initialized by the time any test runs, so an in-process import
    passes no matter what — it would be a check that cannot fail.
    """
    # Arrange — DJANGO_SETTINGS_MODULE must be SET, since it is what makes
    # django.conf.settings resolve back into config.settings and close the loop.
    environment = dict(os.environ)
    environment["DJANGO_SETTINGS_MODULE"] = "config.settings.settings_dev"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    # Act
    result = subprocess.run(
        [sys.executable, "-c", "import config.branding"],
        cwd=str(PROJECT_ROOT),
        env=environment,
        capture_output=True,
        text=True,
    )
    # Assert
    assert result.returncode == 0, (
        "config/branding.py is no longer importable during settings "
        f"composition:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def test_japanese_is_a_configured_language():
    # Arrange
    expected = "ja"
    # Act
    codes = [code for code, _name in settings.LANGUAGES]
    # Assert
    assert expected in codes, f"LANGUAGES={settings.LANGUAGES}"


def test_locale_paths_include_the_project_catalog_root():
    """Project-level catalogs are NOT auto-discovered — only <app>/locale/ is.

    A project-root locale/ directory reaches Django ONLY via LOCALE_PATHS, so
    dropping that setting silently reverts the whole site to English.
    """
    # Arrange
    expected = PROJECT_ROOT / "locale"
    # Act
    configured = [Path(p).resolve() for p in settings.LOCALE_PATHS]
    # Assert
    assert expected.resolve() in configured, f"LOCALE_PATHS={settings.LOCALE_PATHS}"


def test_set_language_endpoint_is_routed():
    """{% url 'set_language' %} in the switcher hard-fails without this route."""
    # Arrange
    expected = "/i18n/setlang/"
    # Act
    actual = _reverse_or_none("set_language")
    # Assert
    assert actual == expected, "django.conf.urls.i18n not included in config/urls.py"


# ---------------------------------------------------------------------------
# Automatic selection from the browser's Accept-Language header
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("ja", "ja"),
        ("ja-JP,ja;q=0.9,en;q=0.8", "ja"),
        ("en-US,en;q=0.9", "en"),
        # An unsupported language must fall back to English rather than 404 or
        # half-translate. Operator, 2026-08-23: 「日本語、英語、意外は私が見ても
        # わからないので今のところは非対応で問題ないです」
        ("fr-FR,fr;q=0.9", "en"),
    ],
)
def test_accept_language_header_selects_the_language(header, expected):
    # Arrange
    request = RequestFactory().get("/", HTTP_ACCEPT_LANGUAGE=header)
    # Act
    actual = translation.get_language_from_request(request, check_path=False)
    # Assert
    assert actual == expected, f"Accept-Language {header!r} chose {actual!r}"


# ---------------------------------------------------------------------------
# The catalog actually carries translations
# ---------------------------------------------------------------------------
def test_catalog_translates_under_japanese():
    # Arrange
    expected = CTA_JA
    # Act
    with translation.override("ja"):
        actual = translation.gettext(CTA_EN)
    # Assert
    assert actual == expected


def test_catalog_leaves_english_alone():
    """Control for the test above — see the module docstring on paired checks."""
    # Arrange
    expected = CTA_EN
    # Act
    with translation.override("en"):
        actual = translation.gettext(CTA_EN)
    # Assert
    assert actual == expected


# ---------------------------------------------------------------------------
# The hero renders in the selected language
# ---------------------------------------------------------------------------
@pytest.fixture
def hero_context():
    return {
        "SITE_TAGLINE": "tagline",
        "SITE_TAGLINE_SECONDARY": "secondary",
        "SCITEX_HUB_VERSION": "0.1.0",
        "CONTACT_EMAIL": "info@scitex.ai",
    }


def test_hero_renders_japanese(hero_context):
    # Arrange
    expected = CTA_JA
    # Act
    with translation.override("ja"):
        html = render_to_string(HERO_TEMPLATE, hero_context)
    # Assert
    assert expected in html


def test_hero_leaves_no_untranslated_english_cta(hero_context):
    """Catches a {% trans %} that was dropped during an edit."""
    # Arrange
    forbidden = CTA_EN
    # Act
    with translation.override("ja"):
        html = render_to_string(HERO_TEMPLATE, hero_context)
    # Assert
    assert forbidden not in html


def test_hero_renders_english(hero_context):
    """Control: the same template, the other language."""
    # Arrange
    expected = CTA_EN
    # Act
    with translation.override("en"):
        html = render_to_string(HERO_TEMPLATE, hero_context)
    # Assert
    assert expected in html


def test_hero_blocktrans_keeps_the_interpolated_version(hero_context):
    """A blocktrans whose placeholder name drifts drops the value silently."""
    # Arrange
    expected_version = "0.1.0"
    # Act
    with translation.override("ja"):
        html = render_to_string(HERO_TEMPLATE, hero_context)
    # Assert
    assert expected_version in html


def test_hero_blocktrans_is_translated(hero_context):
    """Paired with the test above: the banner must be Japanese, not just filled."""
    # Arrange
    expected = "アルファ版"
    # Act
    with translation.override("ja"):
        html = render_to_string(HERO_TEMPLATE, hero_context)
    # Assert
    assert expected in html


# ---------------------------------------------------------------------------
# The switcher
# ---------------------------------------------------------------------------
@pytest.fixture
def switcher_html():
    request = RequestFactory().get("/landing/")
    with translation.override("ja"):
        return render_to_string(SWITCHER_TEMPLATE, {"request": request})


def test_switcher_targets_the_set_language_endpoint(switcher_html):
    # Arrange
    expected = 'action="/i18n/setlang/"'
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_switcher_posts_rather_than_gets(switcher_html):
    """set_language requires POST since Django 4.0; a GET is answered 405."""
    # Arrange
    expected = 'method="post"'
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_switcher_offers_english(switcher_html):
    """name_local, so each option reads in its own language."""
    # Arrange
    expected = "English"
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_switcher_offers_japanese(switcher_html):
    # Arrange
    expected = "日本語"
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_switcher_marks_the_current_language(switcher_html):
    # Arrange
    expected = "selected"
    # Act
    japanese_option_index = switcher_html.index('value="ja"')
    tail = switcher_html[japanese_option_index : japanese_option_index + 80]
    # Assert
    assert expected in tail, f"ja option not preselected under ja: {tail!r}"


def test_switcher_returns_to_the_current_page(switcher_html):
    """Without `next`, set_language redirects to "/" and loses the visitor."""
    # Arrange
    expected = 'name="next" value="/landing/"'
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual
