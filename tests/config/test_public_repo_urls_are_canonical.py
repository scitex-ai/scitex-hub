#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public pages must not link to the ARCHIVED repo or to migrated owners.

WHY THIS TEST EXISTS, and why the archived repo is the dangerous one.
``https://github.com/SciTex-AI/SciTeX-Cloud`` does **not** 404. GitHub resolves
owner/repo case-insensitively, so it lands on ``scitex-ai/scitex-cloud`` — a repo
that is ARCHIVED and whose own description reads "Superseded by scitex-hub — the
SciTeX web application now lives there". Measured anonymously 2026-08-03:

    ls-remote SciTeX-Cloud   rc=0 -> 835296a52eb9...  (only refs/heads/develop)
    this codebase                    develop be1764f32..., main 02f84ff6...

Different SHAs. A visitor who runs the ``git clone`` line we published gets a
DIFFERENT, six-month-stale repository **and no error at all**. A dead link is
loud; this fails quietly, which is why it survived on public pages unnoticed.

HOW THE REPLACEMENTS WERE CHOSEN — measurement, not inference.
Every migrated URL below was probed anonymously, and GitHub's own 301 named the
successor. The redirect is the authority on "what did this repo become", so
these mappings required no guessing:

    ywatanabe1989/scitex-code  -> 301 -> scitex-ai/scitex-python
    ywatanabe1989/scitex-todo  -> 301 -> scitex-ai/scitex-cards
    ywatanabe1989/figrecipe    -> 301 -> scitex-ai/figrecipe

That distinction matters, because two proposals from the analysis pass were
REFUTED by probing:
  * ``SciTeX-AI/scitex`` was proposed as ``scitex-python``. Its redirect actually
    goes to ``scitex-ai/scitex-ai``.
  * ``ywatanabe1989/scitex`` was proposed as ``scitex-writer``. That URL is a hard
    404 with no redirect, so there is no evidence for any successor and it was
    left alone.
Applying either would have replaced a broken link with a confidently wrong one.

WHAT THIS TEST DOES NOT GATE, deliberately.
Seven URLs in these pages are 404 with no measurable successor (SciTeX-Doc,
SciTeX-Viz, SciTeX-Engine, SciTeX-Search, SciTeX-Code under the old org, plus
ywatanabe1989/SciTeX-Vis and ywatanabe1989/scitex). They are NOT pinned here,
because the fix is a product decision — delete the row, or name the successor —
and encoding a guess in a test would make the guess permanent. ``scitex-linter``
is likewise untouched: it is still LIVE at the personal owner (200, no redirect),
so "migrate it" would be wrong.

This test does not hit the network. It pins strings whose status was measured
once, so CI stays hermetic and fast.
"""

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Public-facing surfaces: what a visitor renders, plus the packaging/doc metadata
# that carries a repo URL outward (PyPI project links, published Sphinx docs, and
# the error pages served when the site is DOWN — precisely when someone goes
# looking for the source).
_SCAN_DIRS = (
    "apps/infra/public_app/templates",
    "apps/workspace/docs_app/templates",
    "docs/sphinx",
    "deployment/docker/common/nginx/error-pages",
)
_SCAN_FILES = ("pyproject.toml", "README.md", ".scitex-apps.json")

# Each entry: the forbidden substring, and why. No blanket owner ban — that would
# also flag `scitex-linter`, which legitimately still lives at the personal owner.
_FORBIDDEN = {
    "github.com/SciTex-AI/SciTeX-Cloud": (
        "the ARCHIVED repo — resolves 200 and silently clones a six-month-stale "
        "codebase. Use github.com/scitex-ai/scitex-hub."
    ),
    "github.com/ywatanabe1989/scitex-code": "301 -> scitex-ai/scitex-python",
    "github.com/ywatanabe1989/SciTeX-Code": "301 -> scitex-ai/scitex-python",
    "github.com/ywatanabe1989/figrecipe": "301 -> scitex-ai/figrecipe",
    "github.com/ywatanabe1989/scitex-writer": "301 -> scitex-ai/scitex-writer",
    "github.com/ywatanabe1989/SciTeX-Writer": "301 -> scitex-ai/scitex-writer",
    "github.com/ywatanabe1989/crossref-local": "301 -> scitex-ai/crossref-local",
    "github.com/ywatanabe1989/openalex-local": "301 -> scitex-ai/openalex-local",
    "github.com/ywatanabe1989/scitex-dataset": "301 -> scitex-ai/scitex-dataset",
    "github.com/ywatanabe1989/scitex-todo": "301 -> scitex-ai/scitex-cards",
    "github.com/ywatanabe1989/scitex-ui": "301 -> scitex-ai/scitex-ui",
}


def _targets():
    out = []
    for d in _SCAN_DIRS:
        root = _REPO_ROOT / d
        if root.is_dir():
            out.extend(p for p in root.rglob("*") if p.is_file())
    out.extend(_REPO_ROOT / f for f in _SCAN_FILES if (_REPO_ROOT / f).is_file())
    return out


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


_ALL = _targets()


def test_scan_found_files():
    # Arrange — DISCOVERY CONTROL. If a directory is renamed this glob silently
    # matches nothing and every assertion below passes by scanning air.
    discovered = _ALL
    # Act
    count = len(discovered)
    # Assert
    assert count > 20, (
        f"only {count} public-facing files discovered; the sweep below is vacuous "
        f"until this is fixed. Do not lower this bound to go green."
    )


def test_canonical_urls_are_actually_present():
    # Arrange — POSITIVE CONTROL. Every other assertion here is negative ("string
    # X is absent"), and a negative assertion passes for free when the corpus is
    # empty or the reader is broken. This proves the same files DO contain the
    # canonical form, so an absence below is a measurement.
    canonical = "github.com/scitex-ai/"
    # Act
    hits = sum(_read(p).count(canonical) for p in _ALL)
    # Assert
    assert hits > 0, (
        "no canonical github.com/scitex-ai/ reference found anywhere in the "
        "scanned corpus — the scan is not reading what it thinks it is"
    )


@pytest.mark.parametrize("needle,reason", sorted(_FORBIDDEN.items()))
def test_no_stale_repo_url(needle, reason):
    # Arrange
    corpus = _ALL
    # Act
    offenders = [
        str(p.relative_to(_REPO_ROOT)) for p in corpus if needle in _read(p)
    ]
    # Assert
    assert offenders == [], (
        f"{needle!r} appears in {offenders}. {reason}\n"
        f"These URLs reach real users: public templates, the PyPI project page, "
        f"published docs, and the 502 page shown when the site is down."
    )
