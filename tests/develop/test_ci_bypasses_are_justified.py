#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No CI step may silence its own exit status without a written reason.

WHY THIS EXISTS. On 2026-07-30 the Security Audit workflow was found to have
reported success every week for NINE consecutive weeks while being structurally
incapable of reporting a finding: `safety`, `bandit`, the dependency install AND
`manage.py check --deploy` all ended in ``|| true``. The repo carried 751 bandit
findings (15 HIGH) throughout. Fixed in #503.

That fix is currently protected by nothing but a comment. Someone can re-add
``|| true`` tomorrow and, because the badge would go green, nobody would notice
for another nine weeks. The constitution is explicit that the answer to a
recurring trap is a mechanical barrier rather than a written warning -- a rule
that must be remembered is forgotten at exactly the moment it matters.

HOW IT WORKS. ``|| true`` is not banned; it is sometimes correct (writing a
best-effort artifact, extracting an optional changelog section). What is banned is
an UNDECLARED one. This test pins the exact allowed set with a reason each, so
adding a new bypass fails here and the author must either justify it in
``ALLOWED_BYPASSES`` or not add it. That is the constitution's "exempt one at a
time, in a config file, each with a written reason -- reviewable, greppable, and
individually revisitable", applied to CI bypasses instead of lint rules.

THE ANTI-VACUITY GUARD BELOW IS DELIBERATELY SHAPED. Earlier the same day I wrote
a sweep whose guard globbed SEPARATELY, found 613 files, and passed -- while the
sweep beside it had examined ZERO, because its exclusion matched the absolute path
of the worktree it ran in. So here the scanner RETURNS its own file count and the
guard asserts on THAT. A guard must measure the work the checked code did, never
recompute something adjacent and hope the two agree.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

WORKFLOW_DIR = ".github/workflows"

# (workflow filename, distinctive substring of the line) -> why this one is OK.
# Add an entry ONLY with a reason a reviewer can evaluate. If the reason is
# "to make CI green", the correct action is to fix the command instead.
ALLOWED_BYPASSES = {
    (
        "security-audit.yml",
        "bandit-report.json",
    ): (
        "Writes the FULL bandit report (all severities) for the uploaded artifact "
        "so humans can triage. Its exit status must not gate the job because it "
        "reports LOW findings too. The actual gate is the SEPARATE "
        "`bandit -r apps/ config/ --severity-level high` invocation on the next "
        "line, which has no bypass. Verified 2026-07-30: exit 1 with 15 issues on "
        "this repo, exit 0 on an empty tree."
    ),
    (
        "tests.yml",
        "grep -c",
    ): (
        "`grep -c` EXITS 1 WHEN THE COUNT IS ZERO. This is inside a `$(...)` "
        "capturing a match count, so without `|| true` a legitimate count of 0 "
        "would abort the step under `set -e`. The bypass here makes the command "
        "yield '0' instead of failing -- it is not silencing a check, it is "
        "correcting a counting tool whose exit status means 'found nothing', not "
        "'went wrong'. Same quirk as `pgrep -c`. Note the guard FOUND this one: "
        "the author's own manual survey had missed it, which is the point of "
        "pinning the set rather than trusting a grep."
    ),
    (
        "pypi-publish-and-github-release-on-tag.yml",
        "release-notes.md",
    ): (
        "Extracts the current version's section from CHANGELOG.md for the GitHub "
        "release body. A missing/renamed section yields empty release notes, which "
        "is cosmetic; it must not block publishing an already-tested tag. The "
        "publish steps themselves are NOT bypassed."
    ),
}


def _scan_workflow_bypasses():
    """Return ``(bypasses, files_scanned)``.

    ``bypasses`` is a list of ``(filename, line_number, stripped_line)`` for every
    non-comment line containing ``|| true``. ``files_scanned`` is returned so the
    caller can assert the scan actually ran -- see the module docstring.
    """
    root = Path(settings.BASE_DIR) / WORKFLOW_DIR
    found = []
    scanned = 0
    for path in sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml")):
        scanned += 1
        for lineno, raw in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            line = raw.strip()
            # A comment mentioning `|| true` is documentation, not a bypass.
            # #503 deliberately explains the old bypasses in comments, so a naive
            # substring scan would flag its own explanation.
            if line.startswith("#"):
                continue
            if "|| true" in line:
                found.append((path.name, lineno, line))
    return found, scanned


def _is_allowed(filename, line):
    for (allowed_file, needle), _reason in ALLOWED_BYPASSES.items():
        if filename == allowed_file and needle in line:
            return True
    return False


class CiBypassesAreJustifiedTest(SimpleTestCase):
    """Every `|| true` in a workflow is in ALLOWED_BYPASSES with a reason."""

    def test_scan_actually_examined_workflow_files(self):
        """Anti-vacuity guard, asserting the SCANNER'S OWN counter.

        Without this, a wrong path or a bad glob makes every assertion below pass
        by examining nothing -- which is the exact failure this file exists to
        prevent, so it would be a poor joke to ship it here.
        """
        # Arrange
        minimum = 5
        # Act
        _bypasses, scanned = _scan_workflow_bypasses()
        # Assert
        assert scanned > minimum, "scanned only %d workflow files" % scanned

    def test_every_bypass_is_declared_with_a_reason(self):
        # Arrange
        expected_undeclared = []
        # Act
        bypasses, _scanned = _scan_workflow_bypasses()
        undeclared = [
            "%s:%d  %s" % (f, n, l) for f, n, l in bypasses if not _is_allowed(f, l)
        ]
        # Assert
        assert undeclared == expected_undeclared, (
            "CI step(s) silence their own exit status with no declared reason. "
            "A step that cannot fail is not a check. Either fix the command, or "
            "add an entry to ALLOWED_BYPASSES in %s explaining why this one is "
            "genuinely safe. Offenders: %s" % (__file__, undeclared)
        )

    def test_allowlist_has_no_stale_entries(self):
        """A declared bypass that no longer exists should be removed.

        Otherwise the allowlist accumulates permissions for code that is gone, and
        a future `|| true` on that same filename+substring is pre-approved by an
        entry nobody remembers writing.
        """
        # Arrange
        bypasses, _scanned = _scan_workflow_bypasses()
        # Act
        stale = [
            "%s :: %s" % (f, needle)
            for (f, needle) in ALLOWED_BYPASSES
            if not any(bf == f and needle in bl for bf, _bn, bl in bypasses)
        ]
        # Assert
        assert stale == [], (
            "ALLOWED_BYPASSES entries match nothing in the workflows -- delete "
            "them: %s" % stale
        )

    def test_every_allowlist_entry_states_a_reason(self):
        # Arrange
        too_short = 40
        # Act
        thin = [k for k, v in ALLOWED_BYPASSES.items() if len(v.strip()) < too_short]
        # Assert
        assert thin == [], (
            "these ALLOWED_BYPASSES entries have no substantive reason: %s" % thin
        )


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
