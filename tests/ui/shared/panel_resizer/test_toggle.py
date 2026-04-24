#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-08
# File: tests/e2e/shared/panel_resizer/test_toggle.py

"""E2E tests for panel toggle collapse/expand functionality."""

import pytest
from playwright.sync_api import Page

from .conftest import show_step, highlight_element, login_and_navigate, visual_click
from scitex_browser import show_test_result


class TestPanelToggle:
    """Tests for panel toggle collapse/expand functionality."""

    def test_toggle_button_collapses_panel(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Clicking toggle button collapses the sidebar panel."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip(f"{workspace_app['name']} workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        toggle_btn = page.locator("#stx-shell-sidebar__toggle")

        if toggle_btn.count() == 0:
            pytest.skip("No toggle button found")

        show_step(page, 1, 4, "Testing toggle collapse...", "info")

        initial_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        initial_width = sidebar.evaluate("el => el.offsetWidth")
        show_step(page, 2, 4, f"Initial: collapsed={initial_collapsed}, width={initial_width}px", "info")

        show_step(page, 3, 4, "Clicking toggle button...", "info")
        highlight_element(page, "#stx-shell-sidebar__toggle", 500)
        visual_click(page, "#stx-shell-sidebar__toggle")
        page.wait_for_timeout(300)

        new_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        new_width = sidebar.evaluate("el => el.offsetWidth")

        assert new_collapsed != initial_collapsed, "Toggle did not change collapse state"

        if new_collapsed:
            show_step(page, 4, 4, f"Panel collapsed: {initial_width}px → {new_width}px ✓", "success")
        else:
            show_step(page, 4, 4, f"Panel expanded: {initial_width}px → {new_width}px ✓", "success")
        show_test_result(page, True, "Toggle collapse test passed", delay_ms=2000)

    def test_toggle_button_expands_panel(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Clicking toggle button on collapsed panel expands it."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip(f"{workspace_app['name']} workspace not available")

        sidebar = page.locator(workspace_app["sidebar"])
        toggle_btn = page.locator("#stx-shell-sidebar__toggle")

        if toggle_btn.count() == 0:
            pytest.skip("No toggle button found")

        show_step(page, 1, 4, "Testing toggle expand...", "info")

        is_collapsed = sidebar.evaluate("el => el.classList.contains('collapsed')")
        if not is_collapsed:
            show_step(page, 2, 4, "Collapsing panel first...", "info")
            visual_click(page, "#stx-shell-sidebar__toggle")
            page.wait_for_timeout(300)
        else:
            show_step(page, 2, 4, "Panel already collapsed", "info")

        show_step(page, 3, 4, "Clicking toggle to expand...", "info")
        highlight_element(page, "#stx-shell-sidebar__toggle", 500)
        visual_click(page, "#stx-shell-sidebar__toggle")
        page.wait_for_timeout(300)

        is_expanded = not sidebar.evaluate("el => el.classList.contains('collapsed')")
        width = sidebar.evaluate("el => el.offsetWidth")

        assert is_expanded, "Panel should be expanded"
        assert width > 100, f"Expanded panel should be wider than 100px, got {width}px"

        show_step(page, 4, 4, f"Panel expanded to {width}px ✓", "success")
        show_test_result(page, True, "Toggle expand test passed", delay_ms=2000)

    def test_toggle_icon_updates(
        self, page: Page, base_url: str, test_credentials: dict, workspace_app: dict
    ):
        """Toggle button icon updates when panel state changes."""
        if not login_and_navigate(page, base_url, test_credentials, workspace_app):
            pytest.skip(f"{workspace_app['name']} workspace not available")

        toggle_btn = page.locator("#stx-shell-sidebar__toggle")
        if toggle_btn.count() == 0:
            pytest.skip("No toggle button found")

        icon = toggle_btn.locator("i")
        if icon.count() == 0:
            pytest.skip("No icon in toggle button")

        show_step(page, 1, 3, "Testing icon state updates...", "info")

        initial_classes = icon.get_attribute("class")
        show_step(page, 2, 3, f"Initial icon: {initial_classes}", "info")

        highlight_element(page, "#stx-shell-sidebar__toggle", 500)
        visual_click(page, "#stx-shell-sidebar__toggle")
        page.wait_for_timeout(300)

        new_classes = icon.get_attribute("class")

        assert initial_classes != new_classes, "Icon class should change on toggle"
        show_step(page, 3, 3, f"Icon changed: {initial_classes} → {new_classes} ✓", "success")
        show_test_result(page, True, "Icon update test passed", delay_ms=2000)
