#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile Workspace Tests

Verify the workspace default pane behavior on mobile viewport.
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
        wait_for_page_ready(visitor_mobile_page)

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
        """Default module should be 'chat' after the DEFAULT_MODULE change.

        The legacy 3-pane robot-icon chat shell was retired: a direct hit on
        /apps/workspace/ (which defaults to module="chat") now redirects to the
        canonical /chat/ route, where chat renders as the active pane in the
        unified workspace layout (see workspace_app/views.py:workspace_shell and
        global_base.html — #pane-chat is server-rendered with the "active" class
        and data-initial-pane="chat" when request.initial_pane == "chat").

        The old test probed the retired .module-tab-btn module bar on the
        retired /apps/workspace/ route, which no longer exists, so it reported
        None. This asserts the CURRENT contract: on the authenticated mobile
        context, /chat/ marks the chat pane active.
        """
        visitor_mobile_page.goto("/chat/")
        wait_for_page_ready(visitor_mobile_page)

        active_module = visitor_mobile_page.evaluate(
            """
            () => {
                // Strategy 1: the pane server-rendered active with data-pane
                const activePane = document.querySelector(
                    '.workspace-pane.active[data-pane]'
                );
                if (activePane) return activePane.getAttribute('data-pane');

                // Strategy 2: the body's initial-pane marker set by /chat/,
                // /console/, /files/ (consumed by the sidebar to open the pane).
                const initial = document.body.getAttribute('data-initial-pane');
                if (initial) return initial;

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
        wait_for_page_ready(visitor_mobile_page)

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
        wait_for_page_ready(visitor_mobile_page)

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
