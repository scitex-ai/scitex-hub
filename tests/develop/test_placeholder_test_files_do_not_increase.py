#!/usr/bin/env python3
"""A ratchet on placeholder test files: 528 today, never 529.

Card hub-528-python-test-files-are-placeholder-scaffolds-with-source-pasted-as-
comments-20260811.

WHAT A PLACEHOLDER FILE IS. A test-scaffolding generator produced files shaped
like this (markers elided so this file does not match its own grep — see the
note on PLACEHOLDER_CLASS_MARKER below):

    class TestPlaceholder:
        \"\"\"Placeholder test class - replace with ...\"\"\"
        def test_placeholder_pending_...(self):
            ...

...with the MODULE UNDER TEST pasted underneath as a comment block. Measured on
tests/apps/project_app/services/project_filesystem/test_template_ops.py: 257
lines, 235 of them comments, and inside those comments `def test_` appears 0
times and `assert` appears 0 times. There is nothing commented out to restore —
nothing was ever written.

THE SCALE, measured 2026-08-11 on develop:

    placeholder files                528
    total test_*.py files under tests/   745

So 71% of this suite is files that collect one passing test and assert nothing
about the code they are named after.

WHY THIS IS WORSE THAN HAVING NO FILE. A missing test file is visibly missing.
`test_manager.py` that collects a green test satisfies "is there a test for this
module?", inflates every file count, and hides the gap from the checks meant to
find it. Tonight's launcher regression reached production past a guard that
measured the wrong file; this is that same failure mode, industrialised 528
times.

WHAT THIS TEST DOES, AND DELIBERATELY DOES NOT DO. It is a RATCHET, not a fix.
It permits the 528 that exist and fails on 529. It does not delete anything, and
it does not pretend the debt is addressed — the card is the fix, this is the
tourniquet. Two reasons for that split:

  * deleting 528 placeholders at once converts a silent gap into a loud one with
    no owner, and the commented source in them is occasionally the only record of
    an older shape (archive to .old/<timestamp>/ before discarding);
  * a ratchet is the one thing that can be landed tonight without a judgement
    call about any individual module.

BASELINE moves DOWN ONLY. When you replace a placeholder with real tests, lower
the number in the same commit. If you find yourself raising it, the change adding
the placeholder is the thing to reconsider.

No mocks. One assertion per test (STX-TQ007).
"""

import re
from pathlib import Path

from django.conf import settings

# The generator's own words, which is what makes this greppable at all.
#
# SPLIT ACROSS A CONCATENATION ON PURPOSE. Written as single literals, THIS FILE
# matches its own markers, and then every naive `rg -l "<marker>" tests/` — the
# command the card tells the next person to run — reports 529 and sends them
# hunting a placeholder that is really this guard. Measured: with the literals
# inline, rg counted 529 after the probe was removed, against a true 528.
# `_placeholder_files()` skips this file by name anyway, so the scan was already
# correct; the concatenation is for every OTHER reader of this directory.
PLACEHOLDER_CLASS_MARKER = "Placeholder test class - " + "replace with actual tests"

# A test function whose NAME marks it as generated scaffolding rather than a
# real assertion. Prefix, not exact match — see _placeholder_files().
PLACEHOLDER_TEST_PREFIX = "test_placeholder"

REAL_TEST_DEF = re.compile(r"^\s*def (test_\w+)", re.MULTILINE)

# Ratchet: this number may only ever decrease. See the module docstring before
# changing it.
#
#   528  measured on develop at 4dc626470, 2026-08-11 — the starting debt
#   527  2026-08-11, tests/apps/permissions_app/test_services.py replaced with
#        18 real tests of PermissionService
#
# A SECOND GENERATOR VARIANT EXISTS, and it is why the definition below no
# longer keys on the function NAME. Five files in a local working copy carry
# `def test_placeholder(self)` + `pytest.skip("Not implemented yet")` instead of
# `test_placeholder_pending_implementation`. They are UNTRACKED — never
# committed — so they are not part of this baseline and must not be counted
# into it. But they prove the generator emits more than one shape, and a rule
# keyed on one exact name cannot see a shape it was not told about.
PLACEHOLDER_BASELINE = 527


def _tests_root() -> Path:
    return Path(settings.BASE_DIR) / "tests"


def _placeholder_files() -> list:
    """Test files carrying the scaffold marker and asserting nothing.

    DEFINITION, and why it is not the obvious one. The first version keyed on
    the class marker AND the exact function name
    `test_placeholder_pending_implementation`. A second generator variant
    exists — `def test_placeholder(self)` with
    `pytest.skip("Not implemented yet")` — which that key cannot see. The five
    known instances happen to be untracked, so the committed count was right;
    it was right by luck, not by construction, and the next such file could as
    easily be committed.

    So the name is no longer part of the test. A file counts when it carries
    the scaffold marker and has NO REAL TEST FUNCTION — every `def test_*` in
    it is placeholder-named. That is variant-agnostic in both directions:

      * a third generator variant, or a hand-renamed placeholder, still counts,
        because the rule never asks what the function is called beyond the
        `test_placeholder` prefix;
      * a file that has genuinely gained assertions stops counting the moment
        one non-placeholder test appears, which is the redeemability property
        the ratchet needs — you get credit in the same commit that earns it.

    The class marker alone would over-count: the pasted source block and this
    module's own prose both mention it. Requiring "no real tests" is what keeps
    that from producing false positives, and it is a property of the FILE's
    behaviour rather than of its wording.
    """
    found = []
    for path in sorted(_tests_root().rglob("test_*.py")):
        if path.name == Path(__file__).name:
            continue  # this file names the marker; counting itself is a bug
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if PLACEHOLDER_CLASS_MARKER not in text:
            continue
        names = REAL_TEST_DEF.findall(text)
        if any(not n.startswith(PLACEHOLDER_TEST_PREFIX) for n in names):
            continue  # has at least one real assertion-bearing test
        found.append(path.relative_to(Path(settings.BASE_DIR)))
    return found


def _real_test_functions(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    return len(
        [
            m
            for m in re.findall(r"^\s*def (test_\w+)", text, flags=re.MULTILINE)
            if m != "test_placeholder_pending_implementation"
        ]
    )


def test_the_scan_finds_placeholder_files_at_all():
    """POSITIVE CONTROL — without it the ratchet passes when the scan breaks.

    `len(found) <= 528` is satisfied by `found == []`, which is exactly what a
    renamed marker, a moved tests/ directory or a bad glob would produce. A
    ratchet whose failure mode is silent success is not a ratchet. This is the
    same vacuous-zero shape that nearly let a `total=0 non_success=0` CI gate
    merge a pull request tonight.
    """
    # Arrange
    scan = _placeholder_files
    # Act
    found = scan()
    # Assert
    assert found


def test_placeholder_test_files_have_not_increased():
    """THE RATCHET. 528 today; 529 fails.

    On failure the count alone is not actionable, so the message names the files
    to look at — the newest by mtime are almost always the ones just added.
    """
    # Arrange
    baseline = PLACEHOLDER_BASELINE
    # Act
    found = _placeholder_files()
    # Assert
    assert len(found) <= baseline, (
        f"{len(found)} placeholder test files, baseline {baseline}. "
        f"A new test file was generated as a scaffold and left unwritten. "
        f"Write real assertions in it, or delete it — a file that collects one "
        f"passing test and asserts nothing reads as coverage and is none. "
        f"Newest candidates: "
        + ", ".join(
            str(p)
            for p in sorted(
                found,
                key=lambda p: (Path(settings.BASE_DIR) / p).stat().st_mtime,
                reverse=True,
            )[:5]
        )
    )


def test_a_placeholder_file_that_gained_real_tests_is_no_longer_counted():
    """The ratchet must be REDEEMABLE, not just restrictive.

    If a file keeps the generator's placeholder alongside newly written tests,
    it still counts against the baseline and the author gets no credit for the
    work — which is an incentive to delete the guard rather than the debt. So
    the contract is: remove the placeholder class when you add real tests, and
    this asserts that any file still counted genuinely has no real test in it.
    """
    # Arrange
    counted = _placeholder_files()
    # Act
    with_real_tests = [
        p for p in counted if _real_test_functions(Path(settings.BASE_DIR) / p) > 0
    ]
    # Assert
    assert not with_real_tests


# EOF
