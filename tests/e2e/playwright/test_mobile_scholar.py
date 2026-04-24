#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Scholar Tests

Verify the scholar module results are scrollable on mobile viewport.
"""

import pytest


class TestMobileScholar:
    """Scholar module on iPhone 14 viewport."""

    def test_scholar_page_loads(self, visitor_mobile_page, screenshot):
        """Scholar page loads on mobile."""
        resp = visitor_mobile_page.goto("/apps/scholar/")
        screenshot(visitor_mobile_page, "scholar_mobile_loaded")
        assert resp.status == 200, f"Scholar page returned {resp.status}"

    def test_scholar_results_scrollable(self, visitor_mobile_page, screenshot):
        """Scholar search results container is vertically scrollable on mobile."""
        visitor_mobile_page.goto("/apps/scholar/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        # Check for a scrollable results container
        # The container should have overflow-y: auto or scroll
        results = visitor_mobile_page.locator(
            "[data-testid='scholar-results'], "
            ".scholar-results, "
            "#scholar-results, "
            ".results-container, "
            ".search-results"
        ).first

        if results.count() == 0:
            pytest.skip("No scholar results container found on page")

        overflow_y = results.evaluate("el => window.getComputedStyle(el).overflowY")
        assert overflow_y in (
            "auto",
            "scroll",
        ), f"Results container overflow-y is '{overflow_y}', expected 'auto' or 'scroll'"

        screenshot(visitor_mobile_page, "scholar_results_scrollable")

    def test_scholar_no_horizontal_overflow(self, visitor_mobile_page):
        """Scholar page does not overflow horizontally on mobile."""
        visitor_mobile_page.goto("/apps/scholar/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        overflow = visitor_mobile_page.evaluate(
            """
            () => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }
        """
        )
        assert not overflow, "Page has horizontal overflow on mobile viewport (390px)"
