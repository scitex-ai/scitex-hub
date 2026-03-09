#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for DevAppStaticFinder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.workspace.apps_app.finders import DevAppStaticFinder


class TestDevAppStaticFinder(TestCase):
    """Test DevAppStaticFinder.find() and .list()."""

    def setUp(self):
        self.finder = DevAppStaticFinder()

    @override_settings(BASE_DIR=Path("/tmp/nonexistent_scitex_test"))
    def test_find_returns_none_when_no_users_dir(self):
        finder = DevAppStaticFinder()
        result = finder.find("pomodoro_app/css/pomodoro_app.css")
        self.assertIsNone(result)

    @override_settings(BASE_DIR=Path("/tmp/nonexistent_scitex_test"))
    def test_find_all_returns_empty_list_when_no_users_dir(self):
        finder = DevAppStaticFinder()
        result = finder.find("pomodoro_app/css/pomodoro_app.css", all=True)
        self.assertEqual(result, [])

    def test_find_returns_none_for_nonexistent_file(self):
        result = self.finder.find("nonexistent_app/does_not_exist.css")
        self.assertIsNone(result)

    def test_find_all_returns_empty_for_nonexistent_file(self):
        result = self.finder.find("nonexistent_app/does_not_exist.css", all=True)
        self.assertEqual(result, [])

    def test_find_returns_path_for_existing_dev_app_static(self):
        """Integration test: finds pomodoro_app CSS if it exists on disk."""
        result = self.finder.find("pomodoro_app/css/pomodoro_app.css")
        if result is not None:
            self.assertTrue(Path(result).is_file())
            self.assertIn("pomodoro_app/css/pomodoro_app.css", result)

    @override_settings(BASE_DIR=Path("/tmp/nonexistent_scitex_test"))
    def test_list_yields_nothing_when_no_users_dir(self):
        finder = DevAppStaticFinder()
        items = list(finder.list([]))
        self.assertEqual(items, [])

    @patch("apps.workspace.apps_app.finders.settings")
    def test_find_handles_permission_error(self, mock_settings):
        """Finder should not crash on PermissionError."""
        mock_settings.BASE_DIR = Path("/root")  # Typically inaccessible
        finder = DevAppStaticFinder()
        result = finder.find("anything.css")
        self.assertIsNone(result)


# EOF
