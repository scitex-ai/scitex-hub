#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for DevAppStaticFinder."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

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

    def test_find_handles_permission_error(self):
        """Finder returns None instead of crashing when data/users is unreadable.

        Hermetic: builds a real ``data/users`` directory under a temp BASE_DIR
        and strips its read/execute bits so ``Path.iterdir()`` raises a genuine
        ``PermissionError``. This exercises ``_safe_iterdir``'s handler without
        ``unittest.mock`` (STX-NM00x) and without touching a root-owned path
        like ``/root/data/users`` (which made the prior version fail in CI).
        """
        # Arrange
        tmp_base = Path(tempfile.mkdtemp())
        users_dir = tmp_base / "data" / "users"
        users_dir.mkdir(parents=True)
        (users_dir / "someowner").mkdir()
        # Remove read+execute so iterdir() raises PermissionError, but the
        # directory still stat()s as a dir so users_dir.is_dir() is True.
        os.chmod(users_dir, 0)
        self.addCleanup(
            lambda: (
                os.chmod(users_dir, stat.S_IRWXU),
                __import__("shutil").rmtree(tmp_base, ignore_errors=True),
            )
        )

        # Act
        with override_settings(BASE_DIR=tmp_base):
            result = DevAppStaticFinder().find("anything.css")

        # Assert
        self.assertIsNone(result)


# EOF
