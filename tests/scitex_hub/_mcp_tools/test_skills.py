#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_mcp_tools/test_skills.py
"""The §5 skills tools must actually read hub's bundled skills.

audit-mcp-tools §5 checks only that tools NAMED `hub_skills_list` /
`hub_skills_get` exist. A pair of stubs returning `[]` would satisfy the
auditor completely, so the audit is not evidence that these work — these
tests are.
"""

from __future__ import annotations

from scitex_hub._mcp_tools.skills import skills_dir, skills_get, skills_list


def test_bundled_skills_are_discoverable():
    # Arrange
    minimum = 1
    # Act
    names = skills_list()
    # Assert
    assert len(names) >= minimum, (
        f"skills_list() found {len(names)} skills under {skills_dir()}. The "
        "package bundles skill documents; finding none means the directory "
        "moved and the MCP tools now report an empty catalogue."
    )


def test_listed_name_round_trips_into_get():
    """The name list() hands out must be the name get() accepts.

    Guards the stem-vs-filename split: list() returns stems, and returning
    filenames instead would leave every listed name unreadable.
    """
    # Arrange
    first = skills_list()[0]
    # Act
    result = skills_get(first)
    # Assert
    assert "content" in result, (
        f"skills_get({first!r}) returned {sorted(result)} — a name from "
        "skills_list() must resolve."
    )


def test_missing_skill_names_the_alternatives():
    # Arrange
    expected_error = "not found"
    # Act
    result = skills_get("definitely-not-a-skill")
    # Assert
    assert result.get("error") == expected_error and result.get("available")


def test_traversal_token_cannot_escape_the_bundle():
    """`..` in the name must not read outside the skills directory.

    The name reaches the filesystem, so this is the one input here that
    could expose an arbitrary file if the containment check regressed.
    """
    # Arrange
    expected_error = "not found"
    # Act
    result = skills_get("../../../../../../etc/passwd")
    # Assert
    assert result.get("error") == expected_error, (
        "a traversal token resolved to a real file — skills_get must confirm "
        "the resolved path is inside the skills directory before reading."
    )


# EOF
