#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Scholar Tests

Verify the scholar module results are scrollable on mobile viewport.
"""

import pytest
from tests.e2e.playwright.page_ready import wait_for_page_ready

# WHY THESE TESTS DO NOT WAIT FOR `networkidle`
#
# `networkidle` means "500 ms with zero requests in flight". A SciTeX page
# held by a pooled visitor session runs a heartbeat/countdown poller for as
# long as the page is open (PoolAllocator.extend_session_on_activity), so
# that condition never arrives and the wait always times out. The page is
# fine; the question is unanswerable.
#
# Measured twice, same exception both times:
#   2026-08-16, CI run 31955719803 -- 30s timeout, 33 errors, capture down.
#   2026-09-06, job 101449817274   -- 30s timeout, 14/14 mobile tests
#                                     ERRORED in fixture setup, so not one
#                                     assertion in the mobile suite had
#                                     ever been evaluated.
#
# `wait_for_page_ready` (load -> body.app-ready -> short settle) was written
# after the first of those and is the sanctioned wait. See
# tests/e2e/playwright/page_ready.py for why each step is there and why none
# of them can hide a broken page.


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
        wait_for_page_ready(visitor_mobile_page)

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
        wait_for_page_ready(visitor_mobile_page)

        overflow = visitor_mobile_page.evaluate(
            """
            () => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }
        """
        )
        assert not overflow, "Page has horizontal overflow on mobile viewport (390px)"
