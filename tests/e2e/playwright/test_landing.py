#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Landing Page Tests

Verify the landing page loads correctly for anonymous users
on both mobile and desktop viewports.
"""


class TestLandingAnonymous:
    """Landing page for unauthenticated (anonymous) users."""

    def test_landing_loads_desktop(self, desktop_page, screenshot):
        """Landing page returns 200 and renders on desktop."""
        resp = desktop_page.goto("/")
        assert resp.status == 200, f"Landing page returned {resp.status}"
        screenshot(desktop_page, "landing_desktop")

    def test_landing_loads_mobile(self, mobile_page, screenshot):
        """Landing page returns 200 and renders on iPhone 14."""
        resp = mobile_page.goto("/")
        assert resp.status == 200, f"Landing page returned {resp.status}"
        screenshot(mobile_page, "landing_mobile")

    def test_landing_has_visible_content(self, desktop_page):
        """Landing page has visible text content (not blank)."""
        desktop_page.goto("/")
        body = desktop_page.locator("body")
        assert body.is_visible()
        text = body.inner_text()
        assert len(text.strip()) > 0, "Landing page body is empty"

    def test_landing_no_js_errors(self, desktop_context):
        """Landing page loads without console errors."""
        errors = []
        page = desktop_context.new_page()
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto("/")
        page.wait_for_load_state("networkidle")
        page.close()
        assert len(errors) == 0, f"JS errors on landing: {errors}"

    def test_landing_mobile_viewport_respected(self, mobile_page):
        """Mobile viewport is correctly set to 390x844."""
        mobile_page.goto("/")
        viewport = mobile_page.viewport_size
        assert viewport["width"] == 390, f"Width is {viewport['width']}, expected 390"
        assert (
            viewport["height"] == 844
        ), f"Height is {viewport['height']}, expected 844"
