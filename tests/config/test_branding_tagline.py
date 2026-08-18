#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_branding_tagline.py
"""The landing TAGLINE pair (config/branding.py).

Operator request 2026-07-30 22:34Z, in three messages that converge on a
two-line tagline:

    Research Automation for AI and Humans
    Open-source Scientific Research Automation Ecosystem

The third message supersedes the first: it fixes both the capitalization
("Title case でも") and the spelling -- the operator's first message read
"scitentific". That typo is what these tests exist to keep off the site, so the
spelling assertion is paired: "Scientific" must be present AND "scitentific"
must be absent. A bare absence assertion would pass vacuously if the constant
were deleted entirely.

Single source of truth: both lines are defined in config/branding.py and reach
templates only through the site_branding context processor. No template may
hardcode either line.
"""

from __future__ import annotations

from config import branding
from config.context_processors import site_branding

EXPECTED_PRIMARY = "Research Automation for AI and Humans"
EXPECTED_SECONDARY = "Open-source Scientific Research Automation Ecosystem"


# ---------------------------------------------------------------------------
# The constants themselves
# ---------------------------------------------------------------------------
def test_primary_tagline_is_the_operator_text():
    # Arrange
    expected = EXPECTED_PRIMARY
    # Act
    actual = branding.SITE_TAGLINE
    # Assert
    assert actual == expected


def test_secondary_tagline_is_the_operator_text():
    # Arrange
    expected = EXPECTED_SECONDARY
    # Act
    actual = branding.SITE_TAGLINE_SECONDARY
    # Assert
    assert actual == expected


def test_secondary_tagline_spells_scientific_correctly():
    """Positive half of the spelling pair -- see the module docstring."""
    # Arrange
    expected_word = "Scientific"
    # Act
    actual = branding.SITE_TAGLINE_SECONDARY
    # Assert
    assert expected_word in actual


def test_secondary_tagline_does_not_carry_the_scitentific_typo():
    """Negative half. Non-vacuous: the test above proves the string exists."""
    # Arrange
    typo = "scitentific"
    # Act
    actual = branding.SITE_TAGLINE_SECONDARY.lower()
    # Assert
    assert typo not in actual


# ---------------------------------------------------------------------------
# Reaching templates: only via the context processor (SSoT)
# ---------------------------------------------------------------------------
def test_context_processor_exposes_the_secondary_tagline():
    """Without this key the hero renders an EMPTY paragraph, not an error --
    Django resolves an unknown template variable to "". That silent blank is
    exactly why this is asserted rather than assumed."""
    # Arrange
    request = None  # site_branding ignores the request
    # Act
    context = site_branding(request)
    # Assert
    assert context["SITE_TAGLINE_SECONDARY"] == EXPECTED_SECONDARY


def test_context_processor_still_exposes_the_primary_tagline():
    # Arrange
    request = None
    # Act
    context = site_branding(request)
    # Assert
    assert context["SITE_TAGLINE"] == EXPECTED_PRIMARY


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
