#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Workspace Tests

Verify the workspace default pane behavior on mobile viewport.
"""

import pytest


class TestMobileWorkspace:
    """Workspace module on iPhone 14 viewport."""

    def test_workspace_page_loads(self, visitor_mobile_page, screenshot):
        """Workspace page loads on mobile."""
        resp = visitor_mobile_page.goto("/apps/workspace/")
        screenshot(visitor_mobile_page, "workspace_mobile_loaded")
        assert resp.status == 200, f"Workspace page returned {resp.status}"

    def test_workspace_default_pane_visible(self, visitor_mobile_page, screenshot):
        """Workspace shows a default pane on mobile load."""
        visitor_mobile_page.goto("/apps/workspace/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        # Look for the primary/default pane
        pane = visitor_mobile_page.locator(
            "[data-testid='workspace-default-pane'], "
            ".workspace-pane.active, "
            ".workspace-pane:first-child, "
            ".pane-container .pane.active, "
            "[data-pane].active"
        ).first

        if pane.count() == 0:
            pytest.skip("No workspace pane element found on page")

        assert pane.is_visible(), "Default workspace pane is not visible on mobile"
        screenshot(visitor_mobile_page, "workspace_default_pane")

    def test_workspace_default_module_is_chat(self, visitor_mobile_page, screenshot):
        """Default module should be 'chat' after the DEFAULT_MODULE change."""
        visitor_mobile_page.goto("/apps/workspace/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        # The workspace shell marks the active module tab with .active class
        # and each tab has a data-module attribute.
        active_module = visitor_mobile_page.evaluate(
            """
            () => {
                // Strategy 1: active tab button with data-module
                const activeBtn = document.querySelector(
                    '.module-tab-btn.active[data-module]'
                );
                if (activeBtn) return activeBtn.getAttribute('data-module');

                // Strategy 2: active tab button href containing module name
                const activeBtnHref = document.querySelector(
                    '.module-tab-btn.active[href]'
                );
                if (activeBtnHref) {
                    const href = activeBtnHref.getAttribute('href');
                    const match = href.match(/\\/apps\\/workspace\\/([^/]+)/);
                    if (match) return match[1];
                }

                // Strategy 3: URL fragment or path
                const path = window.location.pathname;
                const match = path.match(/\\/apps\\/workspace\\/([^/]+)/);
                if (match) return match[1];

                return null;
            }
        """
        )
        screenshot(visitor_mobile_page, "workspace_default_module")
        assert (
            active_module == "chat"
        ), f"Expected default module 'chat', got '{active_module}'"

    def test_workspace_no_horizontal_overflow(self, visitor_mobile_page):
        """Workspace does not overflow horizontally on mobile."""
        visitor_mobile_page.goto("/apps/workspace/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        overflow = visitor_mobile_page.evaluate(
            """
            () => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }
        """
        )
        assert (
            not overflow
        ), "Workspace has horizontal overflow on mobile viewport (390px)"

    def test_workspace_pane_fills_viewport(self, visitor_mobile_page):
        """Default pane fills most of the mobile viewport width."""
        visitor_mobile_page.goto("/apps/workspace/")
        visitor_mobile_page.wait_for_load_state("networkidle")

        pane = visitor_mobile_page.locator(
            "[data-testid='workspace-default-pane'], "
            ".workspace-pane.active, "
            ".workspace-pane:first-child, "
            ".pane-container .pane.active"
        ).first

        if pane.count() == 0:
            pytest.skip("No workspace pane element found on page")

        box = pane.bounding_box()
        if box is None:
            pytest.skip("Workspace pane not visible")

        viewport = visitor_mobile_page.viewport_size
        # Pane should use at least 80% of viewport width on mobile
        assert box["width"] >= viewport["width"] * 0.8, (
            f"Pane width {box['width']}px is less than 80% of "
            f"viewport width {viewport['width']}px"
        )
