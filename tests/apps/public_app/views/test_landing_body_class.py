#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The body class reaches the BROWSER, and no template leaks a Django comment.

WHAT HAPPENED (prod, 2026-07-30). The footer was invisible to every visitor on
/landing/. The server was emitting ``class="workspace-page landing-page"``
correctly -- the bug was that a MULTI-LINE ``{# ... #}`` sat between two
attributes of the ``<body>`` tag. Django's ``{# #}`` is SINGLE-LINE ONLY, so a
multi-line one is never lexed as a comment and renders VERBATIM. Rendered
inside a tag, the browser parsed each word as a boolean attribute::

    hides=""  globally=""  restores=""  body.landing-page.=""  "footer=""  ...

and the embedded double quotes swallowed the real ``class`` attribute. The DOM
ended up with no ``landing-page`` class, workspace-layout.css hides
``.site-footer`` globally and restores it only for ``body.landing-page``, so the
footer stayed ``display: none``. The comment explaining the footer fix is what
broke the footer fix.

WHY THESE TESTS AND NOT A COMMENT SAYING "DON'T DO THAT". This is at least the
third occurrence of a leaked Django comment reaching users, and the previous
rounds were fixed by editing the template and writing a warning next to it. A
warning is re-read only by someone already looking at the line. The sweep test
below is a barrier: it fails on the NEXT one, anywhere in the template tree.

WHY THE BODY-CLASS TEST PARSES INSTEAD OF SUBSTRING-MATCHING. A plain
``assert b"landing-page" in resp.content`` PASSES on the broken output -- the
string was present the whole time, inside the leaked comment text. Only parsing
the tag's attributes distinguishes "the class is set" from "those characters
appear somewhere". A line-based regex is likewise blind here, because the
``<body>`` tag spans many lines.

No mocks -- real Django test client. One assertion per test (STX-TQ007).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.test import TestCase

LANDING_URL = "/landing/"

# Every place Django templates live in this repo.
TEMPLATE_GLOBS = ("templates/**/*.html", "apps/**/templates/**/*.html")


class _BodyAttrs(HTMLParser):
    """Capture the attributes of the first <body> as the BROWSER would parse it."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.attrs = None

    def handle_starttag(self, tag, attrs):
        if tag == "body" and self.attrs is None:
            self.attrs = dict(attrs)


def _body_classes(html):
    p = _BodyAttrs()
    p.feed(html)
    if p.attrs is None:
        return None
    return (p.attrs.get("class") or "").split()


def _multiline_django_comments():
    """Return 'path:line' for every ``{#`` whose ``#}`` is on a LATER line."""
    root = Path(settings.BASE_DIR)
    hits = []
    for glob in TEMPLATE_GLOBS:
        for path in root.glob(glob):
            if ".worktrees" in str(path) or "node_modules" in str(path):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                if "{#" in line and "#}" not in line.split("{#", 1)[1]:
                    hits.append("%s:%d" % (path.relative_to(root), lineno))
    return hits


class LandingBodyClassTest(TestCase):
    """The class attribute the browser parses must carry landing-page."""

    def test_landing_page_for_anonymous_returns_200(self):
        # Arrange
        url = LANDING_URL
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_body_tag_is_parseable(self):
        """Presence half: if <body> cannot be parsed at all, the class
        assertions below would be vacuous rather than failing."""
        # Arrange
        url = LANDING_URL
        # Act
        classes = _body_classes(self.client.get(url).content.decode())
        # Assert
        assert classes is not None, "no <body> start tag could be parsed"

    def test_body_carries_landing_page_class(self):
        """The actual prod symptom. Substring-matching passes on the broken
        output; parsing does not."""
        # Arrange
        url = LANDING_URL
        # Act
        classes = _body_classes(self.client.get(url).content.decode())
        # Assert
        assert "landing-page" in (classes or [])

    def test_body_carries_workspace_page_class(self):
        # Arrange
        url = LANDING_URL
        # Act
        classes = _body_classes(self.client.get(url).content.decode())
        # Assert
        assert "workspace-page" in (classes or [])

    def test_body_has_no_garbage_attributes_from_a_leaked_comment(self):
        """A leaked comment inside the tag becomes boolean attributes. Real
        body attributes are data-* / class / id / style, so anything containing
        a space-separated English word like 'globally' means a leak."""
        # Arrange
        url = LANDING_URL
        # Act
        parser = _BodyAttrs()
        parser.feed(self.client.get(url).content.decode())
        # Assert
        assert not [
            k
            for k in (parser.attrs or {})
            if not re.match(r"^(data-[\w-]+|class|id|style|lang|dir)$", k)
        ]

    def test_rendered_landing_leaks_no_django_comment_marker(self):
        """`{#` or `#}` in the OUTPUT means a comment was never lexed."""
        # Arrange
        url = LANDING_URL
        # Act
        body = self.client.get(url).content.decode()
        # Assert
        assert "{#" not in body and "#}" not in body


class TemplateCommentHygieneTest(TestCase):
    """Repo-wide barrier: no template may contain a multi-line ``{# #}``."""

    def test_template_tree_is_non_empty(self):
        """Presence half. Without this, a broken glob would make the sweep
        below pass by scanning nothing -- the failure mode this whole file
        exists to prevent."""
        # Arrange
        root = Path(settings.BASE_DIR)
        # Act
        found = [p for g in TEMPLATE_GLOBS for p in root.glob(g)]
        # Assert
        assert len(found) > 50, "template glob matched %d files" % len(found)

    def test_no_multiline_django_comments_anywhere(self):
        # Arrange
        expected = []
        # Act
        actual = _multiline_django_comments()
        # Assert
        assert actual == expected, (
            "multi-line {# #} renders VERBATIM to users -- use "
            "{%% comment %%}...{%% endcomment %%} instead. Offenders: %s" % actual
        )


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
