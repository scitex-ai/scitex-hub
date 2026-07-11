#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/workspace_app/views.py — workspace_module_content.

Regression coverage for browser-sweep #1: installed custom workspace apps
(e.g. scitex-agentic-journal-app, scitex-live-paper-app) 500'd on
``GET /apps/workspace/content/<app>/`` because their synthesized
``apps_app/user_apps/<app>_partial.html`` path does not resolve on disk.
The view now embeds such apps via the generic
``apps_app/user_app_embed.html`` partial instead.
"""

import pytest
from django.contrib.auth import get_user_model
from django.template import TemplateDoesNotExist
from django.test import TestCase

from apps.infra.workspace_app import registry
from apps.infra.workspace_app.registry import ModuleConfig, register_module

_USER_APP = "test-user-app-embed"
_SHELL_HEADER = {"HTTP_X_WORKSPACE_SHELL": "1"}


def _unregister(name):
    """Drop a runtime-registered module from the global registry."""
    registry._registry_by_name.pop(name, None)
    registry._registry[:] = [m for m in registry._registry if m.name != name]


class WorkspaceModuleContentTests(TestCase):
    """The AJAX content endpoint renders installed user apps generically."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="ws-embed-tester", password="Password123!"
        )
        self.client.force_login(self.user)
        # A user app whose synthesized per-app partial does NOT exist on
        # disk — the exact shape that 500'd in production.
        register_module(
            ModuleConfig(
                name=_USER_APP,
                label="Test User App",
                app_name="apps_app",
                icon_fa="fas fa-puzzle-piece",
                partial_template=f"apps_app/user_apps/{_USER_APP}_partial.html",
                context_builder=(
                    "apps.workspace.apps_app.services.app_context."
                    "build_user_app_context"
                ),
            )
        )
        self.addCleanup(_unregister, _USER_APP)

    def _content_url(self, module):
        return f"/apps/workspace/content/{module}/"

    def test_installed_user_app_returns_200(self):
        # Arrange
        url = self._content_url(_USER_APP)
        # Act
        resp = self.client.get(url, **_SHELL_HEADER)
        # Assert
        assert resp.status_code == 200

    def test_installed_user_app_uses_generic_embed_template(self):
        # Arrange
        url = self._content_url(_USER_APP)
        # Act
        resp = self.client.get(url, **_SHELL_HEADER)
        # Assert
        assert "apps_app/user_app_embed.html" in [t.name for t in resp.templates]

    def test_installed_user_app_iframes_its_mounted_route(self):
        # Arrange
        url = self._content_url(_USER_APP)
        # Act
        resp = self.client.get(url, **_SHELL_HEADER)
        # Assert
        assert f'src="/apps/u/{_USER_APP}/"' in resp.content.decode()

    def test_direct_access_without_shell_header_is_forbidden(self):
        # Arrange
        url = self._content_url(_USER_APP)
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 403

    def test_missing_builtin_partial_is_not_masked(self):
        # Arrange
        register_module(
            ModuleConfig(
                name="test-broken-builtin",
                label="Broken Builtin",
                app_name="some_builtin_app",
                icon_fa="fas fa-bug",
                partial_template="some_builtin_app/does_not_exist_partial.html",
            )
        )
        self.addCleanup(_unregister, "test-broken-builtin")
        url = self._content_url("test-broken-builtin")

        # Act
        def request_broken_module():
            return self.client.get(url, **_SHELL_HEADER)

        # Assert
        with pytest.raises(TemplateDoesNotExist):
            request_broken_module()


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
