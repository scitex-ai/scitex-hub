#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-08
# File: tests/e2e/shared/panel_resizer/test_persistence.py

"""E2E tests for panel localStorage persistence."""

import pytest
from playwright.sync_api import Page

from .conftest import show_step, login_and_navigate, visual_drag, visual_click
from scitex.browser import show_test_result


class TestLocalStoragePersistence:
    """Tests for localStorage state persistence."""

    def test_width_persists_after_reload(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Panel width is restored after page reload."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip(f"{workspace_app['name']} workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        resizer = page.locator(workspace_app["resizer"])

        show_step(page, 1, 5, "Testing width persistence...", "info")

        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        if is_collapsed:
            toggle_btn = page.locator("#sidebar-toggle")
            if toggle_btn.count() > 0:
                visual_click(page, "#sidebar-toggle")
                page.wait_for_timeout(300)

        resizer_box = resizer.bounding_box()
        if resizer_box:
            show_step(page, 2, 5, "Resizing panel by +50px...", "info")
            start_x = resizer_box["x"] + resizer_box["width"] / 2
            start_y = resizer_box["y"] + resizer_box["height"] / 2
            visual_drag(page, start_x, start_y, start_x + 50, start_y, steps=10)
            page.wait_for_timeout(300)

        width_before = sidebar.evaluate("el => el.offsetWidth")
        show_step(page, 3, 5, f"Width before reload: {width_before}px", "info")

        show_step(page, 4, 5, "Reloading page...", "info")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(2000)

        width_after = sidebar.evaluate("el => el.offsetWidth")

        assert abs(width_after - width_before) < 50, \
            f"Width changed too much: {width_before}px -> {width_after}px"
        show_step(page, 5, 5, f"Width persisted: {width_before}px → {width_after}px ✓", "success")
        show_test_result(page, True, "Width persistence test passed", delay_ms=2000)

    def test_collapse_state_persists_after_reload(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Panel collapse state is restored after page reload."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip(f"{workspace_app['name']} workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        toggle_btn = page.locator("#sidebar-toggle")

        if toggle_btn.count() == 0:
            pytest.skip("No toggle button found")

        show_step(page, 1, 4, "Testing collapse state persistence...", "info")

        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        if not is_collapsed:
            show_step(page, 2, 4, "Collapsing panel...", "info")
            visual_click(page, "#sidebar-toggle")
            page.wait_for_timeout(300)

        collapsed_before = sidebar.evaluate("el => el.classList.contains('collapsed')")
        assert collapsed_before, "Panel should be collapsed"
        show_step(page, 2, 4, "Panel collapsed ✓", "success")

        show_step(page, 3, 4, "Reloading page...", "info")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(2000)

        collapsed_after = sidebar.evaluate("el => el.classList.contains('collapsed')")

        assert collapsed_after == collapsed_before, \
            f"Collapse state changed: {collapsed_before} -> {collapsed_after}"
        show_step(page, 4, 4, "Collapse state persisted ✓", "success")
        show_test_result(page, True, "Collapse persistence test passed", delay_ms=2000)
