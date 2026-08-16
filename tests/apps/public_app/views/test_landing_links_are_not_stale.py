#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No landing partial may point at a retired personal-account repository.

WHAT HAPPENED, 2026-08-16. Re-enabling two long-dormant landing partials
was about to ship this to the public landing page:

    github_url='https://github.com/ywatanabe1989/SciTeX-Vis'

`gh repo view` on it: "Could not resolve to a Repository". A dead link,
under a personal account, for a product that is now `scitex-ai/figrecipe`
and is no longer called Visualizer. It had sat in a commented-out include
for long enough that the org migration and the rename both passed it by.

The operator caught the stale NAME by eye and named the general hazard
exactly: 「コメントアウトしてあるからって古い情報のままなので」 — being
commented out does not keep content fresh, it only stops anyone reviewing
it. Markup that is not rendered is markup that is not checked.

WHAT THIS GUARDS. Every github.com URL in the landing partials belongs to
the `scitex-ai` organisation. That is a mechanical, offline property: it
catches leftovers under a personal account without needing network access
in CI, and it would have caught this one.

WHAT IT DOES NOT DO: it does not check that each repo EXISTS or is public.
That needs the network and would make the suite fail on GitHub's
availability rather than on this repo's correctness. Org membership is the
part that goes stale silently; a deleted org repo is a louder event.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings

# Where the landing page's own markup lives.
LANDING_PARTIALS_GLOB = "apps/infra/public_app/templates/public_app/landing*/**/*.html"
LANDING_ROOT_GLOB = "apps/infra/public_app/templates/public_app/landing*.html"

GITHUB_URL = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")

CANONICAL_ORG = "scitex-ai"

# Orgs that are legitimately not ours — third-party references are fine.
THIRD_PARTY_OK = {
    "umami-software",
    "python",
    "django",
}

# Repositories that really do still live under a personal account. Each entry
# is a claim that was CHECKED, not assumed, and it must stay checkable:
#
#   ywatanabe1989/scitex-linter — verified 2026-08-16 with `gh repo view`:
#       exists, public, and `scitex-ai/scitex-linter` does not exist. So this
#       is a live link, not a leftover, and rewriting it to the org would
#       BREAK it. It was the reason this sweep needed an exception at all:
#       the org-ownership heuristic is a proxy for "retired", and this is the
#       case where the proxy is wrong.
#
# If one of these moves to the org, delete the entry — the test will then
# demand the URL be updated, which is the point.
KNOWN_PERSONAL_REPOS = {
    "ywatanabe1989/scitex-linter",
}


def _repo_root() -> Path:
    return Path(settings.BASE_DIR)


def _landing_files() -> list[Path]:
    root = _repo_root()
    files = set(root.glob(LANDING_PARTIALS_GLOB)) | set(root.glob(LANDING_ROOT_GLOB))
    return sorted(files)


def _foreign_owner_links() -> list[str]:
    offenders = []
    for path in _landing_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for owner, repo in GITHUB_URL.findall(text):
            if owner == CANONICAL_ORG or owner in THIRD_PARTY_OK:
                continue
            if f"{owner}/{repo}" in KNOWN_PERSONAL_REPOS:
                continue
            offenders.append(f"{path.relative_to(_repo_root())}: {owner}/{repo}")
    return offenders


class TestLandingLinksAreNotStale:
    def test_the_sweep_actually_reads_landing_markup(self):
        """Vacuity check: a glob that matches nothing would pass everything."""
        # Arrange
        files = _landing_files()

        # Act
        count = len(files)

        # Assert
        assert count > 0, "found no landing templates — the glob is wrong"

    def test_the_sweep_finds_github_links_at_all(self):
        """Second vacuity check: files present but no links would also pass."""
        # Arrange
        text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace") for p in _landing_files()
        )

        # Act
        found = GITHUB_URL.findall(text)

        # Assert
        assert found, "no github.com links found in landing markup — check the regex"

    @pytest.mark.guards(
        defect=(
            "a dormant landing partial pointed at ywatanabe1989/SciTeX-Vis, a "
            "personal-account repo that no longer resolves, for a product since "
            "renamed and moved to scitex-ai/figrecipe"
        )
    )
    def test_every_github_link_belongs_to_the_org(self):
        # Arrange
        expected = []

        # Act
        offenders = _foreign_owner_links()

        # Assert
        assert offenders == expected, (
            "landing markup links to repositories outside "
            f"'{CANONICAL_ORG}': {offenders}. Personal-account URLs survive org "
            "migrations and renames because nobody re-reads markup that is not "
            "rendered."
        )
