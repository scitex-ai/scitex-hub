#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/llm_app/views/bash.py

Security-critical: verify that the bash exec endpoint:
- Requires authentication
- Validates CWD stays within user's filesystem jail
- Falls back to the jail root when a project slug cannot be resolved

No-mock policy (STX-NM00x): the jail predicates only read ``user.username``,
so an unsaved real ``User`` instance is a sufficient, honest collaborator.
The project-lookup fallback is exercised against the real ORM with a slug
that does not exist, so ``Project.DoesNotExist`` fires for real.
"""

import json
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

# llm_app is mounted at /apps/llm/ in config/urls.py (post app-reorg);
# resolve by name so the test does not hard-code the mount prefix.
_BASH_URL = reverse("llm_app:api_bash_exec")

_TEST_PW = "Testpass123!"  # pragma: allowlist secret


def _user(username="alice"):
    """An unsaved real User — enough for username-only jail predicates."""
    return User(username=username)


class TestValidatePathInUserJail(TestCase):
    """validate_path_in_user_jail: core security predicate"""

    def test_user_root_is_inside_jail(self):
        # Arrange
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        user = _user("alice")
        jail = get_user_data_root(user)
        # Act
        result = validate_path_in_user_jail(user, jail)
        # Assert
        assert result is True

    def test_subdir_inside_jail(self):
        # Arrange
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        user = _user("alice")
        subpath = get_user_data_root(user) / "myproject" / "data"
        # Act
        result = validate_path_in_user_jail(user, subpath)
        # Assert
        assert result is True

    def test_other_user_dir_is_outside_jail(self):
        # Arrange
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        alice = _user("alice")
        bob_dir = get_user_data_root(_user("bob"))
        # Act
        result = validate_path_in_user_jail(alice, bob_dir)
        # Assert
        assert result is False

    def test_traversal_attack_blocked(self):
        """Path traversal like /app/data/users/alice/../../bob must be blocked."""
        # Arrange
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
            validate_path_in_user_jail,
        )

        alice = _user("alice")
        traversal = get_user_data_root(alice) / ".." / ".." / "bob"
        # Act
        result = validate_path_in_user_jail(alice, traversal)
        # Assert
        assert result is False

    def test_etc_is_outside_jail(self):
        """Absolute path /etc must not pass jail validation."""
        # Arrange
        from apps.infra.project_app.services.filesystem.permissions import (
            validate_path_in_user_jail,
        )

        user = _user("alice")
        # Act
        result = validate_path_in_user_jail(user, Path("/etc"))
        # Assert
        assert result is False

    def test_tmp_is_outside_jail(self):
        """Absolute path /tmp must not pass jail validation."""
        # Arrange
        from apps.infra.project_app.services.filesystem.permissions import (
            validate_path_in_user_jail,
        )

        user = _user("alice")
        # Act
        result = validate_path_in_user_jail(user, Path("/tmp"))
        # Assert
        assert result is False


class TestBashExecAuthentication(TestCase):
    """api_bash_exec requires login"""

    def _login(self, username):
        User.objects.create_user(username, password=_TEST_PW)
        self.client.login(username=username, password=_TEST_PW)

    def test_unauthenticated_request_redirects(self):
        # Arrange
        body = json.dumps({"command": "ls"})
        # Act
        response = self.client.post(
            _BASH_URL, data=body, content_type="application/json"
        )
        # Assert
        # login_required redirects to login page
        assert response.status_code in (302, 403)

    def test_get_method_not_allowed(self):
        # Arrange
        self._login("bash_test_alice")
        # Act
        response = self.client.get(_BASH_URL)
        # Assert
        assert response.status_code == 405

    def test_missing_command_returns_400(self):
        # Arrange
        self._login("bash_test_alice2")
        # Act
        response = self.client.post(
            _BASH_URL, data=json.dumps({}), content_type="application/json"
        )
        # Assert
        assert response.status_code == 400

    def test_missing_command_error_mentions_command(self):
        # Arrange
        self._login("bash_test_alice2b")
        # Act
        response = self.client.post(
            _BASH_URL, data=json.dumps({}), content_type="application/json"
        )
        # Assert
        assert "command" in json.loads(response.content).get("error", "").lower()

    def test_invalid_json_returns_400(self):
        # Arrange
        self._login("bash_test_alice3")
        # Act
        response = self.client.post(
            _BASH_URL, data="not-json", content_type="application/json"
        )
        # Assert
        assert response.status_code == 400


class TestGetProjectCwd(TestCase):
    """_get_project_cwd: always returns a path within the user's jail"""

    def test_no_slug_returns_jail_root(self):
        # Arrange
        from apps.infra.llm_app.views.bash import _get_project_cwd
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
        )

        user = User.objects.create_user("cwd_user_noslug", password=_TEST_PW)
        # Act
        result = _get_project_cwd(user, "")
        # Assert
        assert result == get_user_data_root(user)

    def test_bad_slug_falls_back_to_jail(self):
        """If project lookup fails, fall back to jail root (never raise)."""
        # Arrange
        from apps.infra.llm_app.views.bash import _get_project_cwd
        from apps.infra.project_app.services.filesystem.permissions import (
            get_user_data_root,
        )

        user = User.objects.create_user("cwd_user_badslug", password=_TEST_PW)
        # Act
        result = _get_project_cwd(user, "nonexistent-slug")
        # Assert
        assert result == get_user_data_root(user)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
