#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A GitHub link written without its host is a same-origin 404, not a link.

WHY THIS EXISTS.

``href="/scitex-ai/scitex-hub/issues"`` looks like a GitHub URL and is not one.
The leading ``/`` makes it a path on scitex.ai, so the browser asks OUR server
for it and gets a 404 page. Nothing errors at build time, nothing errors at
render time, and the anchor text still reads "Bug Reports" — so the defect is
invisible in review and invisible in the template. It is only visible to the
person who clicks it, and they are a prospective customer.

MEASURED 2026-08-18 on the live site, before this guard existed:

    /scitex-ai/scitex-hub/issues        301 -> .../issues/  -> 404
    /scitex-ai/                                             -> 404

Note the 301: Django's ``APPEND_SLASH`` redirects first, so a probe that reads
only the FIRST status code sees a 3xx and can conclude the link is fine. The
404 is one hop further on. Follow redirects before believing a link works.

FIVE were live at once — four on the landing page's community section
(Report a Bug, Request a Feature, Join Discussions, and the "tracked publicly
on SciTeX Hub" note) and one in the global footer (Bug Reports). Two of the
five were found only AFTER widening the search from the string already known
(``issues``) to the CLASS (``href="/scitex-ai/``). Searching for the symptom
you have already seen finds exactly the instances you have already seen; this
test asserts the class.

WHY A TEST AND NOT A CODE REVIEW NOTE. The correct form appears ~12 times in
this tree and the broken form appeared 5 times, so the convention was already
established and still lost. A rule that must be remembered is forgotten at
exactly the moment it matters.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Directories holding Django templates. Kept explicit rather than globbing the
#: whole repo: node_modules and build output contain vendored HTML whose links
#: are not ours to police, and a scan that walks them reports other people's
#: defects as ours.
_TEMPLATE_ROOTS = (
    _REPO_ROOT / "templates",
    _REPO_ROOT / "apps",
)

#: A same-origin href whose first path segment is our GitHub ORG name. That
#: shape is only ever written by someone who meant github.com and dropped the
#: host -- scitex.ai has no ``/scitex-ai/`` route and never has.
_SAME_ORIGIN_GITHUB_RE = re.compile(r'href="/scitex-ai/')

#: The correct form, used as the POSITIVE CONTROL. If the scan finds none of
#: these it did not read the templates, and a clean result proves nothing.
_ABSOLUTE_GITHUB_RE = re.compile(r'href="https://github\.com/')


def _html_files() -> list[Path]:
    files: list[Path] = []
    for root in _TEMPLATE_ROOTS:
        if root.is_dir():
            files.extend(root.rglob("*.html"))
    return files


@pytest.fixture(name="link_scan", scope="module")
def _link_scan() -> tuple[list[str], int]:
    """Return (offending "path:line" strings, count of correctly-formed links).

    Both halves come from ONE pass over the same files, so the control cannot
    accidentally describe a different population than the assertion.
    """
    offenders: list[str] = []
    absolute = 0
    for path in _html_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _SAME_ORIGIN_GITHUB_RE.search(line):
                rel = path.relative_to(_REPO_ROOT)
                offenders.append(f"{rel}:{lineno}")
            absolute += len(_ABSOLUTE_GITHUB_RE.findall(line))
    return offenders, absolute


def test_the_template_scan_actually_read_the_templates(
    link_scan: tuple[list[str], int],
) -> None:
    # Arrange -- POSITIVE CONTROL, and it is a separate test rather than a
    # second assert so a red run says which half broke. Without it, "no
    # offenders" is returned identically by a clean tree and by a scan that
    # read nothing at all (wrong root, renamed directory, unreadable files).
    _, absolute = link_scan

    # Act
    found_known_good = absolute > 0

    # Assert
    assert found_known_good, (
        f"positive control failed: not a single href=\"https://github.com/...\" "
        f"was found under {[str(r) for r in _TEMPLATE_ROOTS]}. THE SCAN IS "
        f"WRONG, NOT THE TEMPLATES -- check the roots exist and contain .html "
        f"files. Do not read this as 'the links are fine'."
    )


def test_no_github_link_is_written_as_a_same_origin_path(
    link_scan: tuple[list[str], int],
) -> None:
    # Arrange -- the defect: a GitHub URL missing its host, which resolves
    # against scitex.ai and 404s. The control test above proves this scan runs.
    offenders, _ = link_scan

    # Act
    # (the scan is the act; performed once in the fixture)

    # Assert
    assert offenders == [], (
        f"these hrefs start with '/scitex-ai/', which is a PATH ON scitex.ai, "
        f"not a GitHub URL -- the browser asks our own server and gets a 404: "
        f"{offenders}. Write the full host: "
        f'href="https://github.com/scitex-ai/...". Measured 2026-08-18: these '
        f"answer 301 then 404, so a probe reading only the first status code "
        f"sees a redirect and wrongly concludes the link works."
    )
