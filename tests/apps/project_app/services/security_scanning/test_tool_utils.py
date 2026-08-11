#!/usr/bin/env python3
"""Severity mapping for security scanners: what an unrecognised label becomes.

Card hub-528-python-test-files-are-placeholder-scaffolds-...-20260811, second
burn-down unit. This file was a placeholder scaffold asserting nothing.

WHY THIS MODULE IS WORTH REAL TESTS. `_map_severity` translates every external
scanner's vocabulary into the four levels this codebase acts on. Its failure mode
is not an exception — it is a WRONG NUMBER on a security finding, which is the
kind of bug that gets triaged as "low priority" by the very field that is wrong.

THE FALLBACK IS A SILENT RE-RATING, IN BOTH DIRECTIONS. Anything the mapper does
not recognise becomes `"medium"`:

    "blocker"  -> "medium"     a DOWNGRADE   (some tools' top level)
    " high "   -> "medium"     a DOWNGRADE   (whitespace is not stripped)
    "trivial"  -> "medium"     an UPGRADE

Measured, not assumed: `severity.lower()` is compared against an exact-match
list, so a padded or unfamiliar label misses every branch and lands on the final
`return "medium"`.

These tests do NOT assert that this is correct — it may well be the right
default. They assert that it is what happens, so the behaviour is visible where
someone reviewing a suspiciously-medium finding will meet it, and so a future
change to the default is a deliberate act rather than a silent one.

No DB, no mocks — the mappers are pure static methods, so this suite runs in
milliseconds rather than paying the Gitea-signal cost that Project-touching tests
incur. One assertion per test (STX-TQ007).
"""

import pytest

from apps.infra.project_app.services.security_scanning.tool_utils import ToolUtilsMixin

MAP = ToolUtilsMixin._map_severity
MAP_BANDIT = ToolUtilsMixin._map_bandit_severity


# ── the four levels pass through unchanged ───────────────────────────────────


@pytest.mark.parametrize("level", ["critical", "high", "medium", "low"])
def test_a_known_level_is_returned_unchanged(level):
    """POSITIVE CONTROL plus the base case.

    If these ever stop round-tripping, every other assertion here is about a
    mapper that no longer speaks the codebase's own vocabulary.
    """
    # Arrange
    given = level
    # Act
    mapped = MAP(given)
    # Assert
    assert mapped == level


@pytest.mark.parametrize("given", ["CRITICAL", "High", "MeDiUm"])
def test_known_levels_are_case_insensitive(given):
    """Scanners disagree about case; the mapper lowercases first."""
    # Arrange
    expected = given.lower()
    # Act
    mapped = MAP(given)
    # Assert
    assert mapped == expected


# ── documented aliases ───────────────────────────────────────────────────────


@pytest.mark.parametrize("given", ["error", "severe"])
def test_error_and_severe_escalate_to_critical(given):
    """These are the only two labels that map UP to critical."""
    # Arrange
    alias = given
    # Act
    mapped = MAP(alias)
    # Assert
    assert mapped == "critical"


@pytest.mark.parametrize("given", ["warning", "moderate"])
def test_warning_and_moderate_map_to_medium(given):
    """Distinct from the fallback: these reach medium deliberately."""
    # Arrange
    alias = given
    # Act
    mapped = MAP(alias)
    # Assert
    assert mapped == "medium"


@pytest.mark.parametrize("given", ["info", "minor"])
def test_info_and_minor_map_to_low(given):
    """The only labels that map DOWN to low."""
    # Arrange
    alias = given
    # Act
    mapped = MAP(alias)
    # Assert
    assert mapped == "low"


# ── the fallback, which is the part worth knowing about ──────────────────────


def test_an_unknown_label_becomes_medium_which_can_be_a_downgrade():
    """THE FINDING. "blocker" is some tools' TOP severity and lands on medium.

    Pinned deliberately. The fallback is defensible — a mapper cannot invent a
    level for a word it does not know — but its consequence is that an unknown
    HIGH-side label is silently re-rated downward, and the field that would tell
    you is the field that is wrong. If a scanner is ever added whose vocabulary
    includes "blocker", this test is where the cost of that default is written
    down.
    """
    # Arrange
    from_another_tool = "blocker"
    # Act
    mapped = MAP(from_another_tool)
    # Assert
    assert mapped == "medium"


def test_surrounding_whitespace_defeats_the_match_and_downgrades():
    """A padded label misses every branch, because only case is normalised.

    `severity.lower()` is compared by exact membership, so " high " is not
    "high". A scanner that emits padded fields would have its HIGH findings
    silently recorded as medium — no error, no log line, just a wrong number.
    Cheap to fix with `.strip()`; pinned first so the fix is a visible change in
    behaviour rather than an invisible one.
    """
    # Arrange
    padded = " high "
    # Act
    mapped = MAP(padded)
    # Assert
    assert mapped == "medium"


def test_an_unknown_label_below_medium_is_silently_upgraded():
    """The fallback cuts both ways — "trivial" is raised, not lowered."""
    # Arrange
    below_medium = "trivial"
    # Act
    mapped = MAP(below_medium)
    # Assert
    assert mapped == "medium"


# ── bandit's own scale ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "given,expected", [("HIGH", "high"), ("MEDIUM", "medium"), ("LOW", "low")]
)
def test_bandit_levels_map_to_their_lowercase_equivalents(given, expected):
    """bandit emits uppercase; this mapper uppercases before looking up."""
    # Arrange
    from_bandit = given
    # Act
    mapped = MAP_BANDIT(from_bandit)
    # Assert
    assert mapped == expected


def test_bandit_mapping_is_case_insensitive():
    """Guards the direction: this one UPPERCASES, unlike _map_severity."""
    # Arrange
    lowercase_input = "high"
    # Act
    mapped = MAP_BANDIT(lowercase_input)
    # Assert
    assert mapped == "high"


def test_an_unknown_bandit_level_becomes_medium():
    """Same silent re-rating as _map_severity, same reason to pin it."""
    # Arrange
    unknown = "CRITICAL"  # bandit has no CRITICAL; it stops at HIGH
    # Act
    mapped = MAP_BANDIT(unknown)
    # Assert
    assert mapped == "medium"


# EOF
