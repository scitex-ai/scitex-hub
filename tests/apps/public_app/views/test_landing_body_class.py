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
    """Scan templates; return ``(hits, scanned)``.

    ``hits`` is 'path:line' for every ``{#`` whose ``#}`` is on a LATER line.
    ``scanned`` is how many files were actually examined -- returned so the
    caller can assert the scan DID work. See the note on the exclusion below
    for why that count is not optional.
    """
    root = Path(settings.BASE_DIR)
    hits = []
    scanned = 0
    for glob in TEMPLATE_GLOBS:
        for path in root.glob(glob):
            # Exclusions are matched against the path RELATIVE to BASE_DIR, not
            # the absolute path. Absolute matching was a silent, total failure:
            # every agent works in a git worktree under `<repo>/.worktrees/<x>/`,
            # so BASE_DIR itself contains ".worktrees" and an absolute substring
            # test skipped EVERY file. Measured: scanned=0, hits=[], test green,
            # while templates/global_base.html held the very defect this file
            # exists to catch. It would still have worked in CI (which checks out
            # at a plain path) -- i.e. inert exactly where a developer runs it.
            rel = str(path.relative_to(root))
            if ".worktrees" in rel or "node_modules" in rel:
                continue
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                if "{#" in line and "#}" not in line.split("{#", 1)[1]:
                    hits.append("%s:%d" % (rel, lineno))
    return hits, scanned


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
        """Asserts the class is set -- but do NOT read this as the guard.

        MEASURED: this test PASSES on the broken template. Python's
        ``html.parser`` is more forgiving than a browser: fed the leaked-comment
        body tag it emits the junk words as attributes AND still reconstructs
        ``class='workspace-page landing-page'``. Chrome does not -- there
        ``document.body.className`` was ``'app-ready'`` alone.

        So no Django-test-client assertion about the class being PRESENT can
        detect this defect; the divergence is in the parser, not the bytes. The
        real guard is test_body_has_no_garbage_attributes_from_a_leaked_comment,
        which asserts junk is ABSENT and does fail on the broken template.
        This test remains useful for the ordinary regression -- someone deleting
        the class logic outright -- and for nothing subtler.
        """
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

    def test_sweep_actually_examined_template_files(self):
        """Anti-vacuity guard, asserting on the SWEEP'S OWN counter.

        The first version of this guard globbed separately and asserted ">50
        files matched". That certified a sweep which had examined ZERO files,
        because the guard and the sweep disagreed about exclusions -- the guard
        applied none. A guard must measure the work the checked code did, not
        recompute something adjacent and hope they agree.
        """
        # Arrange
        minimum = 50
        # Act
        _hits, scanned = _multiline_django_comments()
        # Assert
        assert scanned > minimum, "sweep examined only %d files" % scanned

    def test_no_multiline_django_comments_anywhere(self):
        # Arrange
        expected = []
        # Act
        actual, _scanned = _multiline_django_comments()
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
