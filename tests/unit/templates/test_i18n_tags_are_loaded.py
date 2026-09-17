#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A template that uses an i18n tag has to {% load i18n %} first.

Measured 2026-09-17 on the pytest-matrix job: `video_player.html` gained
`{% blocktranslate %}` in an aria-label and every test that rendered or compiled
it failed with

    TemplateSyntaxError: Invalid block tag on line 173: 'blocktranslate',
    expected 'elif', 'else' or 'endif'. Did you forget to register or load this tag?

because the i18n tags are NOT builtin in this project's template engine — the
project's own templates all load the library (i18n tags worked only by that
habit, and one grep for `{% load` was all that was missing). The mistake is
invisible in a browser and invisible to a template linter: djLint parses the
file happily. It only shows up when Django compiles the template, which in CI is
16 minutes away from the push.

This guard is the cheap version: a text scan, no Django, no settings, so it runs
wherever pytest does. Comments are stripped first — `landing.html` explains the
"%" escaping of `{% trans %}` in prose, and a naive scan reads that as a use.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOTS = (REPO_ROOT / "templates", REPO_ROOT / "apps")
SKIP_PARTS = ("node_modules", "staticfiles", "/media/", ".venv", "venv")

USES_I18N = re.compile(r"{%\s*(trans|blocktrans|blocktranslate)\b")
LOADS = re.compile(r"{%\s*load\s+([^%]*)%}")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
DJANGO_COMMENT = re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.DOTALL)


def template_files() -> list[Path]:
    found = []
    for root in TEMPLATE_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.html")):
            text = str(path)
            if any(part in text for part in SKIP_PARTS):
                continue
            found.append(path)
    return found


def loaded_libraries(body: str) -> set[str]:
    return {
        name
        for match in LOADS.findall(body)
        for name in match.split()
    }


def uses_i18n_tags(body: str) -> bool:
    stripped = DJANGO_COMMENT.sub("", HTML_COMMENT.sub("", body))
    return bool(USES_I18N.search(stripped))


def test_the_scan_finds_templates_at_all():
    # Arrange / Act / Assert: an empty scan would make the guard vacuous.
    assert len(template_files()) > 100


def test_every_template_using_i18n_tags_loads_i18n():
    # Arrange
    offenders = []
    for path in template_files():
        body = path.read_text(encoding="utf-8", errors="replace")
        if uses_i18n_tags(body) and "i18n" not in loaded_libraries(body):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    # Act / Assert
    assert offenders == [], (
        "these templates use {% trans %}/{% blocktranslate %} without {% load i18n %}: "
        f"{offenders}"
    )


def test_the_scan_ignores_i18n_tags_mentioned_in_comments():
    # Arrange: the real file that makes comment-stripping necessary.
    body = '<!-- removes the "%", which {% trans %} doubles -->\n{% load static %}'
    # Act / Assert
    assert uses_i18n_tags(body) is False
    assert uses_i18n_tags("{% blocktranslate %}x{% endblocktranslate %}") is True


@pytest.mark.parametrize(
    "body,expected",
    [
        ("{% load i18n %}", {"i18n"}),
        ("{% load i18n static %}", {"i18n", "static"}),
        ("{% load static i18n %}", {"i18n", "static"}),
    ],
)
def test_loaded_libraries_reads_multi_name_loads(body, expected):
    # Arrange / Act / Assert
    assert loaded_libraries(body) == expected
