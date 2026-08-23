#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_html_lang_follows_active_language.py
"""`<html lang>` must name the language actually being served.

MEASURED ON THE LIVE SITE 2026-08-23, after the Japanese landing page shipped:

    django_language cookie   ja
    every visible string     Japanese
    document.documentElement.lang   "en"      <- wrong

`templates/global_base.html` hardcoded `lang="en"`.

WHY THIS IS NOT COSMETIC, AND WHY NOTHING ELSE WOULD CATCH IT
A screen reader chooses its voice and its pronunciation rules from this
attribute, so a Japanese page announced as English is read aloud wrong — not
merely accented, but with the wrong phoneme set. Search engines index the page
under the declared language. This landing page exists so that Japanese
investors and lenders can read it, which is exactly the audience both of those
failures land on.

It is also invisible to every other check in this suite: the sweep in
test_landing_has_no_untranslated_text.py reads page TEXT, and the text was
perfectly Japanese. An ATTRIBUTE is not text. That is the whole reason this file
is separate rather than another case in the sweep.
"""

from __future__ import annotations

import re

import pytest
from django.template.loader import render_to_string
from django.utils import translation

BASE_TEMPLATE = "global_base.html"
_LANG_ATTR = re.compile(r"<html[^>]*\blang=\"([^\"]*)\"", re.I)


def _rendered_lang(language):
    from django.test import RequestFactory

    context = {
        "request": RequestFactory().get("/landing/"),
        "SITE_TAGLINE": "タグライン",
        "SCITEX_HUB_VERSION": "0.1.0",
        "CONTACT_EMAIL": "info@scitex.ai",
    }
    with translation.override(language):
        html = render_to_string(BASE_TEMPLATE, context)
    match = _LANG_ATTR.search(html)
    return match.group(1) if match else None


@pytest.mark.parametrize("language", ["ja", "en"])
def test_html_lang_matches_the_active_language(language):
    # Arrange
    expected = language
    # Act
    actual = _rendered_lang(language)
    # Assert
    assert actual == expected, (
        f"<html lang> is {actual!r} while serving {language!r}. A screen reader "
        "takes its pronunciation rules from this attribute."
    )


def _rendered_base(language="ja"):
    from django.test import RequestFactory

    context = {
        "request": RequestFactory().get("/landing/"),
        "SITE_TAGLINE": "タグライン",
        "SCITEX_HUB_VERSION": "0.1.0",
        "CONTACT_EMAIL": "info@scitex.ai",
    }
    with translation.override(language):
        return render_to_string(BASE_TEMPLATE, context)


def test_doctype_is_not_pushed_down_by_template_tags():
    """`<!DOCTYPE html>` must stay at the top of the response.

    I BROKE THIS MAKING THE FIX ABOVE. Adding `{% load i18n %}` and
    `{% get_current_language %}` as their own LINES put two extra newlines ahead
    of the doctype:

        before:  '\\n\\n<!DOCTYPE html>'
        after:   '\\n\\n\\n\\n<!DOCTYPE html>'

    A template tag renders to the empty string, but the LINE it sits on still
    emits its newline — and those newlines land before the doctype. Leading
    whitespace there can put a browser into QUIRKS MODE, which changes the box
    model for the whole site. That is a worse defect than the attribute I was
    fixing, and it was invisible to the lang assertions, which only look at the
    <html> tag.

    Fixed by putting both tags on the SAME line as the existing `{% load %}`, so
    the leading bytes are identical to before the change.
    """
    # Arrange — 2 is what develop had: the load line's newline plus one blank.
    expected_max = 2
    # Act
    html = _rendered_base()
    leading = len(html) - len(html.lstrip())
    # Assert
    assert leading <= expected_max, (
        f"{leading} whitespace characters precede <!DOCTYPE html>. Template "
        "tags on their own lines each emit a newline; put them on one line."
    )


def test_doctype_is_the_first_markup():
    """Paired with the count above: whitespace is not the only way to break it."""
    # Arrange
    expected = "<!doctype"
    # Act
    actual = _rendered_base().lstrip()[: len(expected)].lower()
    # Assert
    assert actual == expected


def test_the_two_languages_do_not_render_the_same_lang():
    """Control. A hardcoded value passes one case above by coincidence.

    With `lang="en"` hardcoded, the en case passes and only the ja case fails —
    so a reader skimming a green-except-one run could mistake it for a flake.
    Asserting the two DIFFER states the actual property: the attribute varies
    with the language.
    """
    # Arrange
    japanese = _rendered_lang("ja")
    # Act
    english = _rendered_lang("en")
    # Assert
    assert japanese != english, (
        f"<html lang> is {japanese!r} in both languages — it is not following "
        "the active language at all."
    )
