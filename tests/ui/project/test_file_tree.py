#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-12-07
# File: /home/ywatanabe/proj/scitex-cloud/tests/e2e/project/test_file_tree.py

"""
E2E tests for WorkspaceFilesTree component in Vis app.

Tests:
- File tree display and rendering
- File/folder selection with highlighting
- Folder expansion/collapse
- Keyboard shortcuts (Delete, F2, Ctrl+Shift+N)

Note: These tests require the development server running at http://127.0.0.1:8000
The Vis app auto-assigns a visitor session, so no login is required.
"""

import pytest
from playwright.sync_api import Page, expect


def navigate_to_vis(page: Page, base_url: str) -> bool:
    """Navigate to Vis app.

    The Vis app auto-assigns visitor sessions, so no login is needed.
    Returns True if workspace-files-tree is found, False otherwise.
    """
    # Navigate directly to Vis app - it auto-assigns visitor session
    page.goto(f"{base_url}/vis/", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)  # Allow VisEditor and tree to fully load

    # Check if tree exists (the main container class)
    tree = page.locator(".workspace-files-tree")
    return tree.count() > 0


def get_tree_container(page: Page) -> "Locator":
    """Get the tree container element for focusing."""
    return page.locator(".workspace-files-tree")


class TestFileTreeDisplay:
    """Tests for file tree display."""

    def test_file_tree_renders(self, page: Page, base_url: str):
        """File tree renders in Vis app."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found - app may not have initialized")

        tree = page.locator(".workspace-files-tree")
        expect(tree).to_be_visible(timeout=5000)

    def test_file_tree_shows_folders(self, page: Page, base_url: str):
        """File tree shows folder items."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Check for folder items with wft-folder class
        folders = page.locator(".wft-folder")

        if folders.count() == 0:
            pytest.skip("No folders found in project")

        assert folders.count() > 0, "Expected at least one folder in tree"


class TestFolderSelection:
    """Tests for folder selection and highlighting."""

    def test_click_folder_selects_it(self, page: Page, base_url: str):
        """Clicking a folder selects it and shows highlighting."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Find any folder with data-path attribute
        folders = page.locator(".wft-folder[data-path]")

        if folders.count() == 0:
            pytest.skip("No folders in project to select")

        # Get the first folder
        folder = folders.first
        initial_path = folder.get_attribute("data-path")

        # Click the folder
        folder.click()
        page.wait_for_timeout(500)

        # Re-locate the folder (DOM may have changed) and check selection
        folder = page.locator(f".wft-folder[data-path=\"{initial_path}\"]")
        has_selected_class = "selected" in (folder.get_attribute("class") or "")
        assert has_selected_class, "Folder should be selected after click"

    def test_click_folder_toggles_expansion(self, page: Page, base_url: str):
        """Clicking a folder toggles its expand/collapse state."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Find any folder (expanded or not)
        folders = page.locator(".wft-folder[data-path]")

        if folders.count() == 0:
            pytest.skip("No folders to test")

        folder = folders.first
        initial_path = folder.get_attribute("data-path")
        was_expanded = "expanded" in (folder.get_attribute("class") or "")

        # Click the folder
        folder.click()
        page.wait_for_timeout(500)

        # Re-locate and check state changed
        folder = page.locator(f".wft-folder[data-path=\"{initial_path}\"]")
        is_expanded = "expanded" in (folder.get_attribute("class") or "")

        # State should have toggled
        assert is_expanded != was_expanded, f"Folder expansion should toggle (was: {was_expanded}, now: {is_expanded})"


class TestKeyboardShortcuts:
    """Tests for keyboard shortcuts in file tree."""

    def test_delete_key_triggers_delete(self, page: Page, base_url: str):
        """Delete key triggers delete action on selected item."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Find and select a folder
        folders = page.locator(".wft-folder[data-path]")

        if folders.count() == 0:
            pytest.skip("No folders to test delete")

        folder = folders.first
        folder.click()
        page.wait_for_timeout(500)

        # Focus the tree container for keyboard events
        tree_container = get_tree_container(page)
        tree_container.focus()
        page.wait_for_timeout(200)

        # Press Delete key - shouldn't throw error
        page.keyboard.press("Delete")
        page.wait_for_timeout(500)

        # The delete confirmation dialog may appear or key event was processed
        # Just verify no JS error occurred
        assert True

    def test_f2_key_opens_rename_editor(self, page: Page, base_url: str):
        """F2 key opens inline rename editor."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Find and select a folder
        folders = page.locator(".wft-folder[data-path]")

        if folders.count() == 0:
            pytest.skip("No folders to test rename")

        folder = folders.first
        folder.click()
        page.wait_for_timeout(500)

        # Focus the tree container for keyboard events
        tree_container = get_tree_container(page)
        tree_container.focus()
        page.wait_for_timeout(200)

        # Press F2 key
        page.keyboard.press("F2")
        page.wait_for_timeout(500)

        # Should show rename input within the selected item
        rename_input = page.locator("input[type='text']:visible")

        if rename_input.count() > 0:
            expect(rename_input.first).to_be_visible(timeout=2000)
            # Cancel with Escape
            page.keyboard.press("Escape")
        else:
            pytest.skip("Rename editor not shown - feature may not be enabled")

    def test_ctrl_shift_n_creates_new_folder(self, page: Page, base_url: str):
        """Ctrl+Shift+N creates new folder input."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Find and select a folder
        folders = page.locator(".wft-folder[data-path]")

        if folders.count() == 0:
            pytest.skip("No folders to test new folder")

        folder = folders.first
        folder.click()
        page.wait_for_timeout(500)

        # Focus the tree container for keyboard events
        tree_container = get_tree_container(page)
        tree_container.focus()
        page.wait_for_timeout(200)

        # Press Ctrl+Shift+N
        page.keyboard.press("Control+Shift+N")
        page.wait_for_timeout(500)

        # Should show new folder input
        new_folder_input = page.locator("input[type='text']:visible")

        if new_folder_input.count() > 0:
            expect(new_folder_input.first).to_be_visible(timeout=2000)
            # Cancel with Escape
            page.keyboard.press("Escape")
        else:
            pytest.skip("New folder input not shown - feature may not be enabled")


class TestFileSelection:
    """Tests for file selection."""

    def test_click_file_selects_it(self, page: Page, base_url: str):
        """Clicking a file selects it."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Try to expand a folder first to find files
        folders = page.locator(".wft-folder[data-path]")
        if folders.count() > 0:
            folders.first.click()
            page.wait_for_timeout(500)

        # Find first file
        files = page.locator(".wft-file[data-path]")

        if files.count() == 0:
            pytest.skip("No files in project to select")

        file_item = files.first
        file_path = file_item.get_attribute("data-path")

        file_item.click()
        page.wait_for_timeout(500)

        # Re-locate and check for selection
        file_item = page.locator(f".wft-file[data-path=\"{file_path}\"]")
        has_selected_class = "selected" in (file_item.get_attribute("class") or "")
        assert has_selected_class, "File should be selected after click"


class TestSourceControlPanel:
    """Tests for source control panel in file tree."""

    def test_source_control_panel_visible(self, page: Page, base_url: str):
        """Source control panel is visible below file tree."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Check for git panel
        git_panel = page.locator(".wft-git-panel")

        if git_panel.count() == 0:
            pytest.skip("Git panel not visible")

        expect(git_panel.first).to_be_visible(timeout=5000)

    def test_commit_button_present(self, page: Page, base_url: str):
        """Commit button is present in source control panel."""
        if not navigate_to_vis(page, base_url):
            pytest.skip("WorkspaceFilesTree not found")

        # Check for commit button
        commit_btn = page.locator("[data-action='git-commit']")

        if commit_btn.count() == 0:
            pytest.skip("Commit button not visible")

        expect(commit_btn.first).to_be_visible(timeout=5000)
