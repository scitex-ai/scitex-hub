#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_landing_has_no_untranslated_text.py
"""Fail when a rendered landing partial still shows English under `ja`.

WHY THIS EXISTS — it is the durable form of a correction, not a new idea.

I reported the Japanese landing page complete on the strength of reading
templates. The operator asked whether I was actually looking at the page
(2026-08-23):

    実際にスクリーンショットを撮って見ていますかすなわち抜け漏れがあるんですよね
    のソースコードからこうなっているはずだ。ではなくて、スクリーンショットを見て
    と言うようにしないと

He was right. My source scan said two files remained; an innerText sweep of the
running page found 71 untranslated strings. Three separate mechanisms hid them,
and none is visible from the templates I had chosen to open:

  * features/*.html is not included by landing.html DIRECTLY, so a "what does
    landing.html include" scan never reaches it;
  * text trailing an inline <i> icon does not match a `>text<` pattern;
  * global_header.html's Sign in / Sign up sit at y=14 — the top of the page.

Enumerating by hand is what failed. So this test does not enumerate: it renders
each partial and fails on ANY leftover Latin text, which means a string nobody
marked shows up as a FAILURE rather than as something the operator finds.

WHY AN ALLOWLIST AND NOT A LIST OF EXPECTED STRINGS
An expected-strings list has to be updated whenever the copy changes, and a
stale one passes while the page regresses. The allowlist instead names the
things that are CORRECTLY English — brands, commands, identifiers — which change
far more slowly than the prose around them. Anything not on it must be
translated or explicitly added here with a reason.
"""

from __future__ import annotations

import re

import pytest
from django.template.loader import render_to_string
from django.utils import translation

# Partials that make up the public landing page. features/v01/* is absent on
# purpose: measured 0 references, dead code.
LANDING_PARTIALS = [
    "public_app/landing_partials/landing_hero.html",
    "public_app/landing_partials/landing_commitment.html",
    "public_app/landing_partials/landing_demos.html",
    "public_app/landing_partials/features/scholar_features.html",
    "public_app/landing_partials/features/writer_features.html",
    "public_app/landing_partials/features/code_features.html",
    "public_app/landing_partials/features/viz_features.html",
    "public_app/landing_partials/features/hub_features.html",
]

# Text that is CORRECTLY English. Each entry is a thing whose English form IS
# its Japanese form — a product name, a shell command, an identifier, a licence.
# Translating any of these would be the bug.
ALLOWED = {
    # brands and product names
    "SciTeX", "Scholar", "Writer", "Console", "FigRecipe", "GitHub", "PyPI",
    "Claude", "Code", "Django", "Python", "matplotlib", "LaTeX", "Docker",
    "Singularity", "SLURM", "YAML", "MCP", "API", "REST", "PDF", "HPC",
    "LLM", "AI", "ML", "DB", "R",
    # commands, identifiers, literals
    "pip install scitex", "scitex mcp install", "@scitex.session",
    "scitex.session", "[all]", "all", "import", "video",
    "AGPL", "v3.0", "167M+", "40+",
    # A shell-comment inside a code sample. Translating the comment would make
    # the sample no longer copy-pasteable as shown.
    "Add to Claude Code PyPI GitHub", "Add",
    # "Web API" survives inside the Japanese 「Web API ドキュメント」 — it names
    # the product surface and romanising it would lose the meaning.
    "Web API",
    # The language toggle's label is the language you are switching TO, so under
    # ja it reads "English" BY DESIGN. Translating it would make the button
    # describe the state the reader is already in.
    "English",
    # contact
    "info@scitex.ai",
}

# NOTE ON "video" AND "import": these appear INSIDE the Japanese translations —
# 「video タグに対応していません」 and 「import を変えるだけで動きます」 — because
# they name a HTML element and a Python keyword. The sweep flagging them is the
# instrument working correctly; they belong here rather than being romanised
# into katakana, which would make the sentences say something less precise.

_TAG = re.compile(r"<[^>]+>")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
# <script> and <style> CONTENT is not page text. Stripping only the tags leaves
# the CSS and JS behind, and the first run of this sweep duly reported
# 'module-demo-container', 'max-width', 'console.error' and 'vite' as
# untranslated copy — an instrument reading the wrong layer.
_NON_TEXT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_ENTITY = re.compile(r"&[a-zA-Z][a-zA-Z0-9]{1,8};?")
_WS = re.compile(r"\s+")
_VERSION = re.compile(r"v?\d+(?:\.\d+)*")

CONTEXT = {
    "SITE_TAGLINE": "タグライン",
    "SITE_TAGLINE_SECONDARY": "サブタグライン",
    "SITE_DESCRIPTION": "説明",
    "SCITEX_HUB_VERSION": "0.1.0",
    "CONTACT_EMAIL": "info@scitex.ai",
}


def _visible_text(html):
    """Strip comments and tags, leaving what a reader would see.

    ORDER MATTERS, and every step here was added because the previous version
    reported something that is not page text:

      1. comments   — landing_commitment.html carries layout notes like
                      `<!-- To Individual Researchers - Radial dots -->`, which
                      produced a FAILURE on correct output;
      2. script/style CONTENT — stripping only tags left CSS and JS behind, so
                      'max-width', 'console.error' and 'vite' were reported as
                      untranslated copy;
      3. entities   — `&rarr;` became the bare word 'rarr'.
    """
    html = _COMMENT.sub("", html)
    html = _NON_TEXT.sub(" ", html)
    html = _TAG.sub(" ", html)
    return _WS.sub(" ", _ENTITY.sub(" ", html))


def _untranslated_words(text):
    """Latin word-runs that are not on the allowlist."""
    leftovers = []
    for chunk in re.findall(r"[A-Za-z][A-Za-z0-9'’.@/+\-]*(?:\s+[A-Za-z][A-Za-z0-9'’.@/+\-]*)*", text):
        chunk = chunk.strip(" .,—→")
        if not chunk or len(chunk) < 3:
            continue
        if chunk in ALLOWED:
            continue
        # Version strings are data, not copy, and the value changes with every
        # release — allowlisting the literal would go stale immediately. Matched
        # as a SHAPE so v0.1.0 in the test context and v0.19.0 on the live site
        # are both covered.
        if _VERSION.fullmatch(chunk):
            continue
        # A run may be an allowed token plus punctuation, or several allowed
        # tokens in a row ("Docker Singularity SLURM"). Only report a run that
        # contains at least one word nobody has accounted for.
        words = [w for w in re.split(r"[\s/+]+", chunk) if len(w) > 2]
        if words and all(w.strip(".,'’") in ALLOWED for w in words):
            continue
        leftovers.append(chunk)
    return leftovers


# The shell every page renders inside. Kept separate because these need a
# `request` in context, and because the operator named BOTH of them:
#   「フッターも英語のままですね」「ヘッダーにあったほうがいい」
# Leaving them out is what let me almost report the footer as done on the
# strength of a probe that was reading HTML comments as page text.
CHROME_PARTIALS = [
    "global_base_partials/global_footer.html",
    "global_base_partials/language_switcher.html",
]


@pytest.fixture
def chrome_context():
    from django.test import RequestFactory

    return {**CONTEXT, "request": RequestFactory().get("/landing/")}


@pytest.mark.parametrize("template", CHROME_PARTIALS)
def test_chrome_has_no_untranslated_text_under_japanese(template, chrome_context):
    # Arrange
    expected = []
    # Act
    with translation.override("ja"):
        leftovers = _untranslated_words(
            _visible_text(render_to_string(template, chrome_context))
        )
    # Assert
    assert leftovers == expected, (
        f"{template} still shows English under ja: {leftovers}."
    )


@pytest.mark.parametrize("template", LANDING_PARTIALS)
def test_partial_has_no_untranslated_text_under_japanese(template):
    # Arrange
    expected = []
    # Act
    with translation.override("ja"):
        leftovers = _untranslated_words(_visible_text(render_to_string(template, CONTEXT)))
    # Assert
    assert leftovers == expected, (
        f"{template} still shows English under ja: {leftovers}. "
        "Mark it with {% trans %} and add the translation, or — if it is a "
        "brand, command or identifier — add it to ALLOWED with a reason."
    )


@pytest.mark.parametrize("template", LANDING_PARTIALS)
def test_partial_still_renders_english_under_english(template):
    """Control. Without it, a partial that renders NOTHING would pass above.

    An empty render has no leftover Latin either, so the sweep alone cannot tell
    "fully translated" from "broken template".
    """
    # Arrange
    minimum_words = 1
    # Act
    with translation.override("en"):
        words = _untranslated_words(_visible_text(render_to_string(template, CONTEXT)))
    # Assert
    assert len(words) >= minimum_words, (
        f"{template} rendered no English text at all under en — the template is "
        "empty or broken, and the ja sweep above would pass vacuously."
    )
