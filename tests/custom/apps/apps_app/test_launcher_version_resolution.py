#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher version-resolution regression — guest tiles show the pip SSOT.

Field bug (real-iPhone test of live prod, 2026-07-12): every launcher tile
showed "v0.1.0". Root cause: the workspace context processor overwrote each
registry module's pip-resolved version (``registry._resolve_version``, the
SSOT added in PR #350) with the seed ``ModuleVersion`` "0.1.0" DB row that
``seed_apps`` creates for every built-in. Because ``ModuleConfig`` objects
are process-global, that placeholder then leaked into the launcher grid
(``_build_tiles`` reads ``ModuleConfig.version``) on the NEXT request, so a
guest browsing after any authenticated render saw v0.1.0 on every tile.

Why the pre-existing ``test_writer_tile_version_matches_manifest_ssot`` did
not catch it: it compares the tile version against ``get_module(...).version``
— the SAME shared object, so both read "0.1.0" post-clobber and the tautology
passes. These tests instead compare against the INDEPENDENT installed-package
version and drive the real guest launcher AFTER an authenticated render (the
request that historically clobbered the shared registry state).

All tests use the real Django test DB via ``django.test.TestCase`` — no mocks
(same conventions as ``test_launcher_guest_mode.py``); AAA + one assertion
each.
"""

import importlib.metadata as importlib_metadata
import unittest

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.workspace_app import registry as registry_mod
from apps.workspace.apps_app.views import helpers as apps_helpers


def _installed_version_or_none(dist_name):
    try:
        return importlib_metadata.version(dist_name)
    except importlib_metadata.PackageNotFoundError:
        return None


_WRITER_PIP_VERSION = _installed_version_or_none("scitex-writer")


class GuestLauncherVersionResolutionTest(TestCase):
    """Guest launcher tiles must carry the pip SSOT, never the "0.1.0" seed."""

    @classmethod
    def setUpTestData(cls):
        # seed_apps attributes the built-in modules to this author.
        User.objects.create_user(
            username="ywatanabe",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.regular_user = User.objects.create_user(
            username="reg-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.pool_visitor = User.objects.create_user(
            username="visitor-001",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        # Force the launcher to (re)seed the built-in AppsModule + the
        # ModuleVersion "0.1.0" placeholder rows inside this test's
        # transaction, so the DB is in the exact state that triggers the bug.
        apps_helpers._builtins_ensured = False
        # ModuleConfig objects are process-global; snapshot their versions so a
        # (pre-fix) clobber during this test cannot leak into other tests.
        self._version_snapshot = {
            m.name: m.version for m in registry_mod.get_all_modules()
        }

    def tearDown(self):
        for mod in registry_mod.get_all_modules():
            if mod.name in self._version_snapshot:
                mod.version = self._version_snapshot[mod.name]

    @staticmethod
    def _tile(resp, name):
        return next(
            (t for t in resp.context["tiles"] if t["name"] == name),
            None,
        )

    def _render_guest_after_authenticated(self):
        """Authenticated render first (historically clobbers the shared
        registry version), then the guest render whose tiles we assert on."""
        self.client.force_login(self.regular_user)
        self.client.get("/")
        self.client.force_login(self.pool_visitor)
        return self.client.get("/")

    @unittest.skipIf(
        _WRITER_PIP_VERSION is None,
        "scitex-writer is not installed in this environment",
    )
    def test_guest_launcher_writer_tile_shows_installed_pip_version(self):
        # Arrange — the SSOT is the installed package, read independently.
        expected = _WRITER_PIP_VERSION
        # Act
        resp = self._render_guest_after_authenticated()
        writer_tile = self._tile(resp, "writer")
        # Assert
        assert writer_tile is not None and writer_tile["version"] == expected

    def test_guest_launcher_hub_internal_home_tile_omits_version_label(self):
        # Arrange — "home" (repo_app) ships no pip_package, so it must show
        # no version label at all (not "v0.1.0").
        # Act
        resp = self._render_guest_after_authenticated()
        home_tile = self._tile(resp, "home")
        # Assert
        assert home_tile is not None and home_tile["version_label"] == ""

    def test_guest_launcher_no_builtin_tile_shows_seed_placeholder(self):
        # Arrange — "0.1.0" is the seed_apps placeholder that must never reach
        # a rendered tile for any built-in registry module.
        # Act
        resp = self._render_guest_after_authenticated()
        leaked = [t["name"] for t in resp.context["tiles"] if t["version"] == "0.1.0"]
        # Assert
        assert leaked == []


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
