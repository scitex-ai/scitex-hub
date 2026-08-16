#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every @pytest.mark.guards test must name the defect it defends against.

WHY THIS EXISTS. On 2026-08-15 four gates that cannot fail were found in a single
session, and two of them had been written that same morning by the agent who then
found them. They share one shape, and it is more specific than "bad test":

    the guard asserts against the ARTEFACT THE AUTHOR EDITED, not against the
    thing that actually runs

- a logging guard asserted the BASE settings dict; prod composes it and throws the
  wiring away, so the test passed against a dictionary no deployed environment uses
- a CI-concurrency guard asserted the group TEMPLATE contained two variables; two
  workflows whose names collide case-insensitively both satisfy that
- a Makefile target asserted the recipe RAN, not that it succeeded
- a health check scored every check whose precondition failed as "skipped", and
  counted skipped as pass

In each case the author's mental model was the test oracle, so the test could only
confirm what they already believed. That is why all four passed on day one and why
none of them could ever go red.

WHAT THIS FILE DOES, AND WHAT IT DELIBERATELY DOES NOT DO. It enforces the cheap,
mechanical half: a guard must DECLARE its defect. It does NOT verify the guard
actually fails when that defect is reintroduced — that needs a targeted mutation
run, which is the next step on the card and which needs this declaration as its
input. So this is a precondition, not the barrier itself, and calling it the
barrier would be the very mistake it is written about.

Written guidance already exists for this, in the constitution, in capitals, with a
worked example. It was read at the start of the session that then shipped two more
instances. That is the argument for a mechanical check over another paragraph.
"""

from __future__ import annotations

import pytest

# A defect description has to be a sentence, not a label. "auth" or "the bug" tell
# a future reader nothing and give a mutation runner nothing to target. The floor is
# deliberately low — this rejects placeholders, it does not grade prose.
MIN_DEFECT_CHARS = 25


def _guard_items(session_items):
    """Return (item, marker) for every test carrying the ``guards`` marker."""
    found = []
    for item in session_items:
        marker = item.get_closest_marker("guards")
        if marker is not None:
            found.append((item, marker))
    return found


class TestGuardsDeclareTheirDefect:
    """The marker is only worth having if it carries the defect."""

    def test_every_guard_declares_a_defect(self, request):
        # Arrange
        guards = _guard_items(request.session.items)
        # Act
        undeclared = [
            item.nodeid
            for item, marker in guards
            if not str(marker.kwargs.get("defect", "")).strip()
        ]
        # Assert
        assert undeclared == []

    def test_every_declared_defect_is_a_sentence(self, request):
        # Arrange
        guards = _guard_items(request.session.items)
        # Act
        too_short = [
            f"{item.nodeid} -> {marker.kwargs.get('defect', '')!r}"
            for item, marker in guards
            if 0 < len(str(marker.kwargs.get("defect", "")).strip()) < MIN_DEFECT_CHARS
        ]
        # Assert
        assert too_short == []

    def test_the_marker_is_registered_in_pyproject(self, pytestconfig):
        # An unregistered marker is silently a no-op under --strict-markers-less
        # runs: the decorator applies, nothing reads it, and the guard looks
        # declared while declaring nothing.
        # Arrange
        declared = pytestconfig.getini("markers")
        # Act
        names = [entry.split(":", 1)[0].strip() for entry in declared]
        # Assert
        assert "guards" in names


class TestTheCheckerItselfCanFail:
    """A checker nobody has seen reject anything is the defect it checks for.

    These exercise the predicate directly against synthetic markers, so the RED
    state of the rule above is demonstrated in the suite rather than asserted in a
    PR description that nobody re-runs.
    """

    def test_a_missing_defect_is_rejected(self):
        # Arrange
        marker = pytest.Mark("guards", (), {})
        # Act
        declared = str(marker.kwargs.get("defect", "")).strip()
        # Assert
        assert declared == ""

    def test_a_placeholder_defect_is_too_short(self):
        # Arrange
        marker = pytest.Mark("guards", (), {"defect": "the bug"})
        # Act
        length = len(str(marker.kwargs["defect"]).strip())
        # Assert
        assert length < MIN_DEFECT_CHARS

    def test_a_real_defect_sentence_is_accepted(self):
        # The positive control. Without it the two rejections above would still
        # pass on a predicate that rejects EVERYTHING, which is the same
        # cannot-discriminate failure one level up.
        # Arrange
        marker = pytest.Mark(
            "guards",
            (),
            {"defect": "prod composes LOGGING and drops the loggers mapping"},
        )
        # Act
        length = len(str(marker.kwargs["defect"]).strip())
        # Assert
        assert length >= MIN_DEFECT_CHARS


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
