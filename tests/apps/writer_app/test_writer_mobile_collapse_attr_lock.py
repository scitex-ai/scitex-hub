#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical barrier: the mobile-collapse flag must be on EVERY copy of the
Writer details resizer, not just one.

2026-08-04: the Details panel ate the whole viewport on a phone, leaving no
editor. The fix (#545) added ``data-collapse-on-narrow`` to the resizer in
``writer_partial.html`` — the HTMX partial — and shipped to production. The bug
did not move, because loading ``/apps/writer/`` directly renders ``index.html``,
which carries a SECOND copy of the same resizer that nobody patched. Verified on
live prod: the attribute was present in the container's template file and absent
from the served HTML.

The two copies had already drifted (``data-threshold`` 48 vs 40,
``data-dblclick-toggle`` on only one), which is what made the omission easy to
miss: they are not textually identical, so diffing them is noisy.

So this is a scan, not a note. It reads the real template tree and fails if any
element declaring ``id="writer-details-resizer"`` lacks the flag.

The scan carries its own controls, because a source scan that matches nothing
passes for free — the same vacuous-green shape that let the original bug
through: ``tests/e2e/playwright/test_mobile_writer.py`` SKIPS when it finds no
editor pane, and "no editor pane" IS the bug.
"""

import re
from pathlib import Path

# tests/apps/writer_app/<this file> -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
APPS_DIR = REPO_ROOT / "apps"

RESIZER_ID = "writer-details-resizer"
REQUIRED_ATTR = "data-collapse-on-narrow"
# An attribute every copy already carries — the positive control proving tag
# extraction actually captured the element's attributes.
CONTROL_ATTR = "data-h-resizer"

# The whole opening tag, across newlines: these attributes are one per line.
RESIZER_TAG = re.compile(
    r"<div\b[^>]*?id=\"" + re.escape(RESIZER_ID) + r"\"[^>]*?>",
    re.DOTALL,
)

SYNTHETIC_BAD_TAG = (
    f'<div class="h-resizer" id="{RESIZER_ID}" {CONTROL_ATTR}></div>'
)


def _templates():
    return [
        path
        for path in APPS_DIR.rglob("*.html")
        if "node_modules" not in path.parts
    ]


def _resizer_tags():
    """Every (relpath, tag_text) declaring the details resizer."""
    found = []
    for path in _templates():
        text = path.read_text(encoding="utf-8", errors="replace")
        if RESIZER_ID not in text:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for match in RESIZER_TAG.finditer(text):
            found.append((rel, match.group(0)))
    return found


class TestTheScanCanActuallyFail:
    """Controls. Without these, the assertion below passes for free."""

    def test_template_tree_is_not_empty(self):
        # Arrange
        expected_minimum = 50
        # Act
        templates = _templates()
        # Assert
        assert len(templates) > expected_minimum, (
            f"only {len(templates)} templates found under {APPS_DIR} — the root "
            "is misresolved, so any 'no violations' result is vacuous"
        )

    def test_resizer_is_declared_somewhere(self):
        # Arrange
        # Act
        tags = _resizer_tags()
        # Assert
        assert tags, (
            f"no element declaring id={RESIZER_ID!r} was found anywhere under "
            f"{APPS_DIR} — the scan matches nothing, so it cannot fail"
        )

    def test_more_than_one_copy_of_the_resizer_exists(self):
        # Arrange: the 2026-08-04 bug WAS the second, unpatched copy.
        # Act
        tags = _resizer_tags()
        # Assert
        assert len(tags) >= 2, (
            f"expected at least 2 declarations of id={RESIZER_ID!r}, found "
            f"{len(tags)}: {[rel for rel, _ in tags]}. If the copies were "
            "genuinely unified into one include, delete this test deliberately "
            "rather than letting it erode."
        )

    def test_tag_extraction_captures_attributes(self):
        # Arrange
        tags = _resizer_tags()
        # Act
        without_control = [rel for rel, tag in tags if CONTROL_ATTR not in tag]
        # Assert
        assert not without_control, (
            f"extracted tags in {without_control} lack the control attribute "
            f"{CONTROL_ATTR!r}, so extraction is broken and a missing "
            f"{REQUIRED_ATTR!r} would go unnoticed"
        )

    def test_regex_matches_a_synthetic_resizer_tag(self):
        # Arrange
        # Act
        match = RESIZER_TAG.search(SYNTHETIC_BAD_TAG)
        # Assert
        assert match is not None, (
            "the regex failed to match a hand-written resizer tag — it would "
            "also fail to match the real ones, passing vacuously"
        )

    def test_predicate_rejects_a_tag_missing_the_flag(self):
        # Arrange: red-before-green, inline.
        match = RESIZER_TAG.search(SYNTHETIC_BAD_TAG)
        # Act
        tag_text = match.group(0) if match else ""
        # Assert
        assert REQUIRED_ATTR not in tag_text, (
            "the synthetic bad tag unexpectedly contains the required "
            "attribute; this control no longer proves the check can fail"
        )


class TestEveryResizerCopyCollapsesOnNarrow:
    def test_all_copies_carry_the_flag(self):
        # Arrange
        tags = _resizer_tags()
        # Act
        offenders = [rel for rel, tag in tags if REQUIRED_ATTR not in tag]
        # Assert
        assert not offenders, (
            f"{REQUIRED_ATTR} missing from the Writer details resizer in: "
            f"{offenders}. On a 390px viewport the Details panel then takes the "
            "whole workspace and Writer has no editing surface. Every template "
            f"declaring id={RESIZER_ID!r} must carry it — patching only one copy "
            "is what shipped the 2026-08-04 regression to production."
        )


# EOF
