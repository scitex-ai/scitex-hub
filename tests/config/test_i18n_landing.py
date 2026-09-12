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
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client, RequestFactory
from django.urls import NoReverseMatch, reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HERO_TEMPLATE = "public_app/landing_partials/landing_hero.html"
DEMOS_TEMPLATE = "public_app/landing_partials/landing_demos.html"
COMMITMENT_TEMPLATE = "public_app/landing_partials/landing_commitment.html"
SWITCHER_TEMPLATE = "global_base_partials/language_switcher.html"

# One string per surface, chosen because each proves a DIFFERENT link in the
# chain: the constant path (branding.py -> context processor), the plain
# template path, and the interpolating one (blocktrans).
CTA_EN = "Try SciTeX for Free"
CTA_JA = "SciTeX を無料で試す"


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
# English by default: Accept-Language no longer auto-selects Japanese
# ---------------------------------------------------------------------------
# 2026-09-11 supersedes the 2026-08-23 "automatic from browser preference"
# decision: the landing must render English for an anonymous visitor even when
# the browser advertises Accept-Language: ja. Japanese appears only after the
# visitor explicitly selects it (footer switcher -> django_language cookie).
@pytest.mark.parametrize(
    "header",
    [
        "ja",
        "ja-JP,ja;q=0.9,en;q=0.8",
        "en-US,en;q=0.9",
        "fr-FR,fr;q=0.9",
    ],
)
def test_english_default_middleware_strips_language_preference(header):
    """EnglishDefaultLanguageMiddleware removes the browser preference when
    the visitor has made no explicit choice, so LocaleMiddleware falls through
    to LANGUAGE_CODE (English) instead of auto-selecting from Accept-Language.
    `get_language_from_request` alone would still pick ja — that is exactly the
    hole the middleware closes, so apply it before resolving."""
    from apps.infra.public_app.middlewares import EnglishDefaultLanguageMiddleware

    request = RequestFactory().get("/", HTTP_ACCEPT_LANGUAGE=header)
    middleware = EnglishDefaultLanguageMiddleware(lambda r: r)
    middleware(request)
    actual = translation.get_language_from_request(request, check_path=False)
    assert actual == "en", (
        f"Accept-Language {header!r} must NOT auto-select Japanese once the "
        f"middleware strips it; expected 'en', got {actual!r}."
    )


def test_explicit_ja_cookie_is_preserved_despite_english_browser():
    """An explicit django_language=ja (footer switcher) survives the middleware
    and beats an en-advertising browser — the user's choice is honored."""
    from apps.infra.public_app.middlewares import EnglishDefaultLanguageMiddleware

    request = RequestFactory().get(
        "/", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9",
        **{"HTTP_COOKIE": "django_language=ja"},
    )
    middleware = EnglishDefaultLanguageMiddleware(lambda r: r)
    middleware(request)
    actual = translation.get_language_from_request(request, check_path=False)
    assert actual == "ja"


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
# The rest of the landing page
# ---------------------------------------------------------------------------
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

# (template, japanese, english) for each partial marked after the hero.
# landing_announcement.html is deliberately ABSENT: all 22 of its lines are
# HTML comments, so it renders nothing and has nothing to translate.
PARTIAL_CASES = [
    (DEMOS_TEMPLATE, "SciTeX エコシステム", "SciTeX Ecosystem"),
    (DEMOS_TEMPLATE, "科学図表エディタ", "Scientific figure editor"),
    (DEMOS_TEMPLATE, "研究室で自前運用", "Self-host for your lab"),
    (COMMITMENT_TEMPLATE, "科学への私たちの約束", "Our Commitment to Science"),
    (COMMITMENT_TEMPLATE, "研究者お一人おひとりへ", "To Individual Researchers"),
    (COMMITMENT_TEMPLATE, "利益よりも科学を優先します", "Prioritize science over profit"),
]


def _visible(html):
    """Rendered HTML minus comments — what a reader actually sees.

    NOT cosmetic. Without it, `test_partial_leaves_no_visible_english` fails on
    CORRECT output: landing_commitment.html carries layout notes like
    `<!-- To Individual Researchers - Radial dots (personal spotlight) -->`, so
    the English string survives in the source while the heading itself is fully
    translated. Asserting against raw HTML measures the template, not the page.
    """
    return _HTML_COMMENT.sub("", html)


@pytest.mark.parametrize(
    ("template", "japanese", "english"), PARTIAL_CASES, ids=str
)
def test_partial_renders_japanese(template, japanese, english, hero_context):
    # Arrange
    expected = japanese
    # Act
    with translation.override("ja"):
        html = _visible(render_to_string(template, hero_context))
    # Assert
    assert expected in html


@pytest.mark.parametrize(
    ("template", "japanese", "english"), PARTIAL_CASES, ids=str
)
def test_partial_renders_english(template, japanese, english, hero_context):
    """Control: the same template under en must still be English."""
    # Arrange
    expected = english
    # Act
    with translation.override("en"):
        html = _visible(render_to_string(template, hero_context))
    # Assert
    assert expected in html


@pytest.mark.parametrize(
    ("template", "japanese", "english"), PARTIAL_CASES, ids=str
)
def test_partial_leaves_no_visible_english(template, japanese, english, hero_context):
    """A dropped {% trans %} shows up here and nowhere else."""
    # Arrange
    forbidden = english
    # Act
    with translation.override("ja"):
        html = _visible(render_to_string(template, hero_context))
    # Assert
    assert forbidden not in html


@pytest.mark.parametrize("brand", ["Scholar", "Writer", "Console", "FigRecipe"])
def test_product_names_survive_translation(brand, hero_context):
    """A brand name translated is a brand name lost — these must NOT be marked."""
    # Arrange
    expected = brand
    # Act
    with translation.override("ja"):
        html = render_to_string(DEMOS_TEMPLATE, hero_context)
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


@pytest.fixture
def switcher_en_html():
    """The toggle rendered under en — the control for every ja assertion."""
    request = RequestFactory().get("/landing/")
    with translation.override("en"):
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


def test_switcher_lists_all_configured_languages(switcher_html):
    """A DROPDOWN lists every configured language (operator 2026-09-12: the
    2-state toggle became a multi-language dropdown), so under ja BOTH
    English and 日本語 appear, each as a real set_language form.
    """
    # Arrange
    expected = ("English", "日本語")
    # Act
    actual = switcher_html
    # Assert
    assert all(name in actual for name in expected)


def test_switcher_submits_the_other_language_under_ja(switcher_html):
    """The LABEL is cosmetic; this is the part that actually switches."""
    # Arrange
    expected = 'name="language" value="en"'
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_switcher_offers_japanese_under_en(switcher_en_html):
    # Arrange
    expected = "日本語"
    # Act
    actual = switcher_en_html
    # Assert
    assert expected in actual


def test_switcher_submits_japanese_under_en(switcher_en_html):
    # Arrange
    expected = 'name="language" value="ja"'
    # Act
    actual = switcher_en_html
    # Assert
    assert expected in actual


def test_switcher_reuses_the_header_button_class(switcher_html):
    """No bespoke colours. The operator rejected the first version for looking
    unlike its neighbours; reusing a shared button class is what makes it
    inherit the brand tokens. (2026-09-12: the 2-state toggle became a
    multi-language dropdown whose trigger reuses .header-btn, the same class
    Sign in / Sign up use.)"""
    # Arrange
    expected = 'class="header-btn'
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_switcher_returns_to_the_current_page(switcher_html):
    """Without `next`, set_language redirects to "/" and loses the visitor."""
    # Arrange
    expected = 'name="next" value="/landing/"'
    # Act
    actual = switcher_html
    # Assert
    assert expected in actual


def test_no_raw_multiline_django_comments_in_header_partial():
    """A multi-line {# #} is NOT a valid Django comment — Django's {# #} is
    single-line only, so a block whose opening {# and closing #} are on
    different lines renders VERBATIM to every visitor (operator-observed on
    PR #769, 2026-09-11). The header partial must use {% comment %} for
    anything spanning lines. Scans the template source (no DB needed)."""
    from pathlib import Path

    header = (Path(__file__).resolve().parents[2] / "templates" / "global_base_partials" / "global_header.html").read_text(encoding="utf-8")
    lines = header.splitlines()
    offenders = []
    open_line = None
    for i, line in enumerate(lines, 1):
        # A {# that is not closed by #} on the same line opens a raw block.
        if open_line is None and "{#" in line and "#}" not in line:
            # ignore {% comment %} (valid multi-line) lines
            if "{% comment %}" not in line:
                open_line = i
        elif open_line is not None and "#}" in line:
            offenders.append((open_line, i))
            open_line = None
    if open_line is not None:
        offenders.append((open_line, len(lines)))
    assert not offenders, (
        f"multi-line raw {{# #}} comment(s) would render verbatim: "
        f"{[f'lines {a}-{b}' for a, b in offenders]}"
    )


# ---------------------------------------------------------------------------
# The rendered pricing page is fully localized in BOTH directions.
#
# This is the assertion class the 66 pricing/SSOT tests could not catch: they
# check pricing.py's output (already translated) and the template label (a real
# JA msgid), but never the RENDERED PAGE. The bug they missed (found 2026-09-11
# via a live switch-click) was a DOUBLE translation: pricing.py localizes
# price/price_note/included at call time, and landing_pricing.html applied
# |translate_dynamic to those already-JA strings again. The JA catalog has no
# JA msgids, so Django fell back to the en catalog's stale develop-era reverse
# mappings (msgid "月額 1,490円" -> "¥1,490/month") and reverted them to English
# on the Japanese page. The rendered-page check below fails if that regresses.
# ---------------------------------------------------------------------------
def _landing(client_cookie=None):
    from django.test import Client

    c = Client()
    if client_cookie:
        c.cookies["django_language"] = client_cookie
    return c.get(
        "/landing/", HTTP_ACCEPT_LANGUAGE="ja-JP,ja;q=0.9,en;q=0.5"
    ).content.decode("utf-8", "replace")


def test_landing_pricing_renders_fully_english_by_default():
    html = _landing()
    # Two-plan row (Free pane dropped 2026-09-12): Cloud | On-Prem. Prices are
    # ALWAYS USD on the marketing card (operator: "drop the yen at all").
    assert '<html lang="en"' in html
    assert "Cloud" in html and "On-Prem" in html
    assert "$19/mo" in html and "$39/mo" in html
    assert 'data-variant="academic"' in html and 'data-variant="general"' in html
    assert "30-day free trial" in html
    assert "32 GB storage per month (Standard speed)" in html
    assert "$10 compute credit" in html
    assert "Traffic within normal use" in html
    # NO Japanese price data leaks into the English default
    for ja in ("クラウド", "月額 1,490円", "通常利用の範囲の通信", "円相当"):
        assert ja not in html, f"Japanese {ja!r} leaked into the English default landing"


def test_landing_pricing_renders_fully_japanese_when_selected():
    html = _landing(client_cookie="ja")
    # JA renders the plan copy Japanese, but prices stay USD (operator:
    # "always use USD for clarity" — the yen reference lives on /tokushoho/).
    assert '<html lang="ja"' in html
    assert "クラウド" in html and "オンプレ" in html
    assert "$19/mo" in html and "$39/mo" in html
    assert "学術" in html and "非学術" in html
    assert "30日間の無料トライアル" in html
    assert "32 GB ストレージ / 月 (Standard speed)" in html
    assert "$10 の計算クレジット" in html
    assert "通常利用の範囲の通信" in html
    # NO Japanese yen price (the SSoT yen values) leaks onto the USD card
    for jp in ("月額 1,490円", "円相当の計算クレジット"):
        assert jp not in html, f"JPY {jp!r} leaked onto the USD landing"
