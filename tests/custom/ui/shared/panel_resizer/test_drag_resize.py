#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-08
# File: tests/e2e/shared/panel_resizer/test_drag_resize.py

"""E2E tests for panel drag resize functionality across all workspace apps."""

import pytest
from playwright.sync_api import Page

from .conftest import show_step, highlight_element, login_and_navigate, visual_drag, visual_click
from scitex_browser import show_test_result


class TestDragResize:
    """Tests for drag resize functionality across all workspace apps."""

    def test_drag_resizer_changes_width(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Dragging the resizer changes panel width."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip(f"{workspace_app['name']} workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        resizer = page.locator(workspace_app["resizer"])

        show_step(page, 1, 5, "Testing drag resize...", "info")

        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        if is_collapsed:
            toggle_btn = page.locator("#stx-shell-sidebar__toggle")
            if toggle_btn.count() > 0:
                show_step(page, 2, 5, "Expanding collapsed panel first...", "info")
                toggle_btn.click()
                page.wait_for_timeout(500)

        initial_width = sidebar.evaluate("el => el.offsetWidth")
        show_step(page, 2, 5, f"Initial width: {initial_width}px", "info")

        resizer_box = resizer.bounding_box()
        if not resizer_box:
            pytest.skip("Cannot get resizer bounding box")

        start_x = resizer_box["x"] + resizer_box["width"] / 2
        start_y = resizer_box["y"] + resizer_box["height"] / 2
        end_x = start_x + 100

        show_step(page, 3, 5, "Highlighting resizer...", "info")
        highlight_element(page, workspace_app["resizer"], 500)

        show_step(page, 4, 5, "Dragging resizer +100px...", "info")
        visual_drag(page, start_x, start_y, end_x, start_y, steps=15)
        page.wait_for_timeout(300)

        final_width = sidebar.evaluate("el => el.offsetWidth")
        width_change = final_width - initial_width

        assert abs(width_change) > 20, f"Width should change by at least 20px, got {width_change}px"

        show_step(page, 5, 5, f"Width changed: {initial_width}px → {final_width}px ({width_change:+d}px) ✓", "success")
        show_test_result(page, True, "Drag resize test passed", delay_ms=2000)

    def test_drag_respects_minimum_width(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Dragging cannot make panel smaller than minimum width."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip("Scholar workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        resizer = page.locator(workspace_app["resizer"])

        show_step(page, 1, 4, "Testing minimum width constraint...", "info")

        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        if is_collapsed:
            toggle_btn = page.locator("#stx-shell-sidebar__toggle")
            if toggle_btn.count() > 0:
                toggle_btn.click()
                page.wait_for_timeout(500)

        resizer_box = resizer.bounding_box()
        if not resizer_box:
            pytest.skip("Cannot get resizer bounding box")

        start_x = resizer_box["x"] + resizer_box["width"] / 2
        start_y = resizer_box["y"] + resizer_box["height"] / 2
        end_x = start_x - 500

        show_step(page, 2, 4, "Attempting extreme shrink (-500px)...", "info")
        highlight_element(page, workspace_app["resizer"], 500)

        visual_drag(page, start_x, start_y, end_x, start_y, steps=25)
        page.wait_for_timeout(300)

        final_width = sidebar.evaluate("el => el.offsetWidth")
        show_step(page, 3, 4, f"Final width: {final_width}px", "info")

        min_width = 40
        assert final_width >= min_width, f"Width {final_width}px should be >= {min_width}px"
        show_step(page, 4, 4, f"Minimum width {min_width}px respected ✓", "success")
        show_test_result(page, True, "Minimum width test passed", delay_ms=2000)

    def test_drag_collapsed_panel_expands(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Dragging a collapsed panel should expand it."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip("Scholar workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        resizer = page.locator(workspace_app["resizer"])
        toggle_btn = page.locator("#stx-shell-sidebar__toggle")

        show_step(page, 1, 6, "Testing drag on collapsed panel...", "info")

        # Clear localStorage to ensure clean state
        page.evaluate("localStorage.removeItem('scholar_sidebar_state')")
        page.wait_for_timeout(200)

        # Check initial state
        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        show_step(page, 2, 6, f"Initial state: collapsed={is_collapsed}", "info")

        # If expanded, collapse it
        if not is_collapsed and toggle_btn.count() > 0:
            show_step(page, 2, 6, "Collapsing panel...", "info")
            # Use direct click instead of visual_click to avoid double-firing
            toggle_btn.click()
            page.wait_for_timeout(800)  # Wait longer for animation

        # Verify collapsed state
        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        show_step(page, 3, 6, f"After toggle: collapsed={is_collapsed}", "info")

        if not is_collapsed:
            # Try one more time with longer wait
            show_step(page, 3, 6, "Retrying collapse...", "warning")
            toggle_btn.click()
            page.wait_for_timeout(1000)
            is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")

        if not is_collapsed:
            show_test_result(page, False, "Could not collapse panel for test", delay_ms=2000)
            pytest.fail("Could not collapse panel for test - toggle button not working")

        show_step(page, 3, 6, "Panel collapsed ✓", "success")

        resizer_box = resizer.bounding_box()
        if not resizer_box:
            show_test_result(page, False, "Cannot get resizer bounding box", delay_ms=2000)
            pytest.fail("Cannot get resizer bounding box")

        show_step(page, 4, 6, "Highlighting resizer...", "info")
        highlight_element(page, workspace_app["resizer"], 500)

        start_x = resizer_box["x"] + resizer_box["width"] / 2
        start_y = resizer_box["y"] + resizer_box["height"] / 2
        end_x = start_x + 150

        show_step(page, 5, 6, "Dragging resizer +150px to expand...", "info")
        visual_drag(page, start_x, start_y, end_x, start_y, steps=15)
        page.wait_for_timeout(300)

        is_still_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        final_width = sidebar.evaluate("el => el.offsetWidth")

        if is_still_collapsed:
            show_test_result(page, False, "Panel should expand when dragging", delay_ms=2000)
        assert not is_still_collapsed, "Panel should expand when dragging from collapsed state"
        assert final_width > 100, f"Panel should be wider than 100px, got {final_width}px"
        show_step(page, 6, 6, f"Collapsed panel expanded to {final_width}px ✓", "success")
        show_test_result(page, True, "Collapsed panel expand test passed", delay_ms=2000)
