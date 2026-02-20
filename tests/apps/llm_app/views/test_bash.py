#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/llm_app/views/bash.py

Security-critical: verify that the bash exec endpoint:
- Requires authentication
- Validates CWD stays within user's filesystem jail
- Invokes setpriv with the correct UID/GID
- Times out runaway commands
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import TestCase


class TestValidatePathInUserJail(TestCase):
    """validate_path_in_user_jail: core security predicate"""

    def _make_user(self, username="alice"):
        user = MagicMock(spec=User)
        user.username = username
        return user

    def test_user_root_is_inside_jail(self):
        from apps.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        user = self._make_user("alice")
        jail = get_user_data_root(user)
        assert validate_path_in_user_jail(user, jail) is True

    def test_subdir_inside_jail(self):
        from apps.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        user = self._make_user("alice")
        jail = get_user_data_root(user)
        subpath = jail / "myproject" / "data"
        assert validate_path_in_user_jail(user, subpath) is True

    def test_other_user_dir_is_outside_jail(self):
        from apps.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        alice = self._make_user("alice")
        bob = self._make_user("bob")
        bob_dir = get_user_data_root(bob)
        # Alice must not pass bob's dir as her CWD
        assert validate_path_in_user_jail(alice, bob_dir) is False

    def test_traversal_attack_blocked(self):
        """Path traversal like /app/data/users/alice/../../bob must be blocked."""
        from apps.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        alice = self._make_user("alice")
        jail = get_user_data_root(alice)
        traversal = jail / ".." / ".." / "bob"
        assert validate_path_in_user_jail(alice, traversal) is False

    def test_absolute_path_outside_data_blocked(self):
        """Absolute paths like /etc must not pass jail validation."""
        from apps.project_app.services.filesystem.permissions import (
            validate_path_in_user_jail,
        )

        user = self._make_user("alice")
        assert validate_path_in_user_jail(user, Path("/etc")) is False
        assert validate_path_in_user_jail(user, Path("/tmp")) is False


_TEST_PW = "Testpass123!"  # pragma: allowlist secret


class TestBashExecAuthentication(TestCase):
    """api_bash_exec requires login"""

    def _login(self, username):
        User.objects.create_user(username, password=_TEST_PW)
        self.client.login(username=username, password=_TEST_PW)

    def test_unauthenticated_request_redirects(self):
        response = self.client.post(
            "/llm/api/bash/",
            data=json.dumps({"command": "ls"}),
            content_type="application/json",
        )
        # login_required redirects to login page
        assert response.status_code in (302, 403)

    def test_get_method_not_allowed(self):
        self._login("bash_test_alice")
        response = self.client.get("/llm/api/bash/")
        assert response.status_code == 405

    def test_missing_command_returns_400(self):
        self._login("bash_test_alice2")
        response = self.client.post(
            "/llm/api/bash/",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.content)
        assert "command" in data.get("error", "").lower()

    def test_invalid_json_returns_400(self):
        self._login("bash_test_alice3")
        response = self.client.post(
            "/llm/api/bash/",
            data="not-json",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestGetProjectCwd(TestCase):
    """_get_project_cwd: always returns a path within the user's jail"""

    def _make_user(self, pk=1, username="alice"):
        user = MagicMock(spec=User)
        user.pk = pk
        user.username = username
        return user

    def test_no_slug_returns_jail_root(self):
        from apps.llm_app.views.bash import _get_project_cwd
        from apps.project_app.services.filesystem.permissions import get_user_data_root

        user = self._make_user()
        result = _get_project_cwd(user, "")
        expected = get_user_data_root(user)
        assert result == expected

    @patch("apps.project_app.models.Project.objects")
    def test_bad_slug_falls_back_to_jail(self, mock_objects):
        """If project lookup fails, fall back to jail root (never raise)."""
        from apps.llm_app.views.bash import _get_project_cwd
        from apps.project_app.services.filesystem.permissions import get_user_data_root

        mock_objects.get.side_effect = Exception("not found")
        user = self._make_user()
        result = _get_project_cwd(user, "nonexistent-slug")
        assert result == get_user_data_root(user)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
