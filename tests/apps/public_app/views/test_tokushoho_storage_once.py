#!/usr/bin/env python3
# -*- coding: utf- -*-
"""The storage text is published ONCE, in its DEDICATED column, and NOT
repeated in the 備考 cell.

WHY THIS IS ITS OWN TEST. ``test_tokushoho.py`` asserts that every ``included``
item appears on the page. That catches a MISSING column, but it is satisfied by
a page that prints the same text TWICE — and printing it twice is exactly what
the 備考-exclusion rule exists to prevent. So this asserts the other half of
the contract: the storage text appears once per row that carries it, and no
more.

The defect it guards was measured, not imagined: the dedicated column was built
by a formatter family that phrased the same attribute differently from
``included_items()``. Because 備考 excludes these attributes on purpose, the
included phrasing rendered NOWHERE. Both outcomes — absent, or present twice —
are the failure this test distinguishes.

NOTE (2026-09-11): the pricing SSoT is now English-sourced and /tokushoho/
forces translation.override("ja"), so the storage text only exists in the
compiled .mo. The needle is DERIVED from each row's own ``row["storage"]``
(computed under ja) rather than hardcoded — a hardcoded JA string silently
drifts whenever the catalog wording changes and makes the control vacuous,
which is exactly how this test was failing on develop.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[4]  # tests/apps/public_app/views/ -> repo root


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo before any JA assertion reads a catalog.

    The storage text rendered on the forced-JA /tokushoho/ page lives only in
    the compiled .mo (gitignored; not compiled by the CI pytest step). Same
    fixture as test_i18n_landing / test_tokushoho.
    """
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"catalog compilation failed ({result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    translation.trans_real._translations.clear()
    yield


class StandardStoragePublishedOnceTest(TestCase):
    def _ja_rows(self):
        from apps.infra.public_app.pricing import published_price_rows

        with translation.override("ja"):
            return published_price_rows()

    def test_the_storage_text_is_published_exactly_once_per_row(self):
        """Once per row that carries storage — never twice, never zero times.

        The needle is DERIVED from each row's own ``row["storage"]`` (the value
        the dedicated column renders), so this cannot drift into a hardcoded
        string that silently contradicts the catalogue. Rows may share the same
        storage value (both subscriptions are 50 GB), so the count is per
        DISTINCT string: the page must show it exactly as many times as there
        are rows carrying that value — one per row, no more.
        """
        # Arrange — distinct storage values and how many rows carry each.
        rows = self._ja_rows()
        carrying = [row["storage"] for row in rows if (row.get("storage") or "").strip()]
        assert carrying, (
            "Control: no published row carries a storage value today, so the "
            "count assertion below would pass vacuously. If the catalogue "
            "changed, update this test deliberately."
        )

        # Act
        content = self.client.get(reverse("public_app:tokushoho")).content.decode("utf-8")

        # Assert — each distinct storage value appears once per row that
        # carries it. More than that means it leaked into a second cell (the
        # 備考 column, which exists to prevent the duplication).
        for text in dict.fromkeys(carrying):  # distinct, order-preserving
            found = content.count(text)
            expected = carrying.count(text)
            assert found == expected, (
                f"storage {text!r} should appear once for each of the "
                f"{expected} row(s) that carry it, but appears {found} time(s) "
                "on the page — 0 means the dedicated column isn't publishing "
                "it, more than expected means it leaked into a second cell "
                "(e.g. 備考, which exists to prevent it)."
            )

    def test_the_storage_text_is_not_repeated_inside_the_remarks_cell(self):
        """The exclusion, asserted directly against the data the page consumes.

        The 備考 cell renders ``row["remarks"]`` (or falls back to
        ``row["description"]``) — never the storage phrasing. If the storage
        value ever lands in those, the page states the same number twice, which
        a presence-only assertion would not notice.
        """
        # Arrange
        rows = self._ja_rows()

        checked = 0
        for row in rows:
            storage = (row.get("storage") or "").strip()
            if not storage:
                continue
            checked += 1
            # Assert — 備考 (the column OR its description fallback) does not
            # carry the storage text, so it is not repeated.
            remarks = row.get("remarks") or []
            description = row.get("description") or ""
            assert not any(storage in remark for remark in remarks), (
                f"{row['label']}: storage {storage!r} appears in BOTH its "
                "dedicated column and the 備考 remarks, so the page states the "
                "same number twice."
            )
            assert storage not in description, (
                f"{row['label']}: storage {storage!r} is repeated in the "
                "description fallback that 備考 renders when remarks is empty."
            )

        assert checked, "Control: no row carried a storage value; the loop was vacuous."
