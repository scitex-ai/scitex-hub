#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Standard storage text is published ONCE, in its DEDICATED column.

WHY THIS IS ITS OWN TEST. ``test_tokushoho.py`` asserts that every ``included``
item appears on the page. That catches a MISSING column, but it is satisfied by a
page that prints the same text TWICE — and printing it twice is exactly what the
備考-exclusion rule exists to prevent. So this asserts the other half of the
contract: the text appears once per row that includes it, and no more.

The defect it guards was measured, not imagined: the dedicated column was built
by a SECOND formatter family that phrased the same attribute differently
("50 GB / プロジェクト / 月") from ``included_items()``
("ストレージ 50GB/プロジェクト/月（Standard）"). Because 備考 excludes these
attributes on purpose, the included phrasing rendered NOWHERE. Both outcomes —
absent, or present twice — are the failure this test distinguishes.
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

STANDARD_STORAGE = "ストレージ 50GB/プロジェクト/月（Standard）"


class StandardStoragePublishedOnceTest(TestCase):
    def test_the_standard_storage_text_is_published_exactly_once_per_row(self):
        """Once per row that includes it — never twice, never zero times.

        The expectation is DERIVED from the same catalogue the page renders, so
        this cannot drift into a hardcoded number that silently contradicts it.
        """
        # Arrange
        from apps.infra.public_app.pricing import published_price_rows

        rows = published_price_rows()
        including = [row for row in rows if STANDARD_STORAGE in row["included"]]
        assert including, (
            "Control: no published row includes the Standard storage text today, "
            "so the count assertion below would pass vacuously. If the catalogue "
            "changed, update this test deliberately."
        )

        # Act
        content = self.client.get(reverse("public_app:tokushoho")).content.decode(
            "utf-8"
        )

        # Assert — exactly one occurrence per row that includes it.
        found = content.count(STANDARD_STORAGE)
        assert found == len(including), (
            f"the Standard storage text should appear once for each of the "
            f"{len(including)} row(s) that include it, but it appears {found} "
            f"time(s) — {found} < {len(including)} means a dedicated column is not "
            f"publishing it, and {found} > {len(including)} means it is duplicated "
            f"(e.g. it leaked back into the 備考 cell, which exists to prevent it)."
        )

    def test_the_storage_text_is_not_repeated_inside_the_remarks_cell(self):
        """The exclusion, asserted directly against the data the page consumes.

        pricing.py drops ストレージ/計算クレジット/超過計算 from 備考 because each has
        its own column. If that drop is ever removed, the page still renders — it
        just says the same thing twice, which no presence-only assertion notices.
        """
        # Arrange
        from apps.infra.public_app.pricing import published_price_rows

        checked = 0
        for row in published_price_rows():
            if any("ストレージ" in item for item in row["included"]):
                checked += 1
                # Assert — the dedicated column carries it …
                assert "ストレージ" in (row["storage"] or ""), (
                    f"{row['label']}: the included storage item is not published "
                    "in its dedicated column"
                )
                # … and 備考 does not repeat it.
                assert not any(
                    "ストレージ" in remark for remark in (row["remarks"] or [])
                ), (
                    f"{row['label']}: ストレージ appears in BOTH its dedicated column "
                    "and 備考, so the page states the same number twice"
                )

        assert checked, "Control: no row carried a storage item; the loop was vacuous."
