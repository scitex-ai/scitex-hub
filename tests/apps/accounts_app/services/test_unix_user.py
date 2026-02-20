#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/accounts_app/services/unix_user.py

Security-critical: these tests verify that the UID isolation system
correctly maps Django users to OS UIDs and enforces range bounds.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase


class TestGetUnixUid(TestCase):
    """get_unix_uid: deterministic UID = 100000 + user.pk"""

    def _make_user(self, pk):
        user = MagicMock()
        user.pk = pk
        user.username = f"user{pk}"
        return user

    def test_uid_is_100000_plus_pk(self):
        from apps.accounts_app.services.unix_user import get_unix_uid

        user = self._make_user(1)
        assert get_unix_uid(user) == 100001

    def test_uid_deterministic_different_pks(self):
        from apps.accounts_app.services.unix_user import get_unix_uid

        assert get_unix_uid(self._make_user(21)) == 100021
        assert get_unix_uid(self._make_user(99)) == 100099

    def test_uid_boundary_min(self):
        """pk=0 gives 100000 — right at the lower bound."""
        from apps.accounts_app.services.unix_user import UID_BASE, get_unix_uid

        user = self._make_user(0)
        assert get_unix_uid(user) == UID_BASE

    def test_uid_boundary_max(self):
        """pk=99999 gives 199999 — right at the upper bound."""
        from apps.accounts_app.services.unix_user import UID_MAX, get_unix_uid

        user = self._make_user(99999)
        assert get_unix_uid(user) == UID_MAX

    def test_uid_out_of_range_raises(self):
        """pk=100000 → uid=200000 — must raise ValueError, not silently run."""
        from apps.accounts_app.services.unix_user import get_unix_uid

        user = self._make_user(100000)
        with pytest.raises(ValueError, match="outside the allowed range"):
            get_unix_uid(user)

    def test_uids_are_distinct_per_user(self):
        """Two different users must never share a UID."""
        from apps.accounts_app.services.unix_user import get_unix_uid

        user_a = self._make_user(10)
        user_b = self._make_user(11)
        assert get_unix_uid(user_a) != get_unix_uid(user_b)


class TestSafeUnixUsername(TestCase):
    """_safe_unix_username: sanitize for POSIX compliance"""

    def _call(self, name):
        from apps.accounts_app.services.unix_user import _safe_unix_username

        return _safe_unix_username(name)

    def test_plain_name_unchanged(self):
        assert self._call("alice") == "alice"

    def test_at_sign_replaced(self):
        assert self._call("alice@example.com") == "alice_at_example.com"

    def test_space_replaced(self):
        assert self._call("first last") == "first_last"

    def test_truncated_to_32_chars(self):
        long_name = "a" * 50
        assert len(self._call(long_name)) == 32


class TestEnsureLinuxAccount(TestCase):
    """ensure_linux_account: idempotent, non-fatal on failure"""

    def _make_user(self, pk=42, username="testuser"):
        user = MagicMock()
        user.pk = pk
        user.username = username
        return user

    @patch("apps.accounts_app.services.unix_user.subprocess.run")
    def test_returns_true_when_account_already_exists(self, mock_run):
        """If `id <username>` succeeds (rc=0), return True without creating."""
        from apps.accounts_app.services.unix_user import ensure_linux_account

        mock_run.return_value = MagicMock(returncode=0)
        result = ensure_linux_account(self._make_user())
        assert result is True
        # Only the `id` check should run — no groupadd/useradd
        assert mock_run.call_count == 1

    @patch("apps.accounts_app.services.unix_user._get_user_data_root_str")
    @patch("apps.accounts_app.services.unix_user.subprocess.run")
    def test_creates_account_when_missing(self, mock_run, mock_data_root):
        """If `id` fails (rc=1), calls groupadd then useradd."""
        from apps.accounts_app.services.unix_user import ensure_linux_account

        mock_data_root.return_value = "/app/data/users/testuser"
        # First call: `id` → user not found
        # Second call: groupadd → success
        # Third call: useradd → success
        mock_run.side_effect = [
            MagicMock(returncode=1),  # id: not found
            MagicMock(returncode=0),  # groupadd: ok
            MagicMock(returncode=0),  # useradd: ok
        ]
        result = ensure_linux_account(self._make_user())
        assert result is True
        assert mock_run.call_count == 3

    @patch("apps.accounts_app.services.unix_user._get_user_data_root_str")
    @patch("apps.accounts_app.services.unix_user.subprocess.run")
    def test_returns_false_on_useradd_failure(self, mock_run, mock_data_root):
        """CalledProcessError from useradd returns False (non-fatal)."""
        from apps.accounts_app.services.unix_user import ensure_linux_account

        mock_data_root.return_value = "/app/data/users/testuser"
        mock_run.side_effect = [
            MagicMock(returncode=1),  # id: not found
            MagicMock(returncode=0),  # groupadd: ok
            subprocess.CalledProcessError(1, "useradd"),  # useradd: fails
        ]
        result = ensure_linux_account(self._make_user())
        assert result is False

    @patch("apps.accounts_app.services.unix_user.subprocess.run")
    def test_returns_false_on_unexpected_exception(self, mock_run):
        """Any unexpected exception returns False (non-fatal)."""
        from apps.accounts_app.services.unix_user import ensure_linux_account

        mock_run.side_effect = OSError("no such file")
        result = ensure_linux_account(self._make_user())
        assert result is False


class TestEnforceDataDirOwnership(TestCase):
    """enforce_data_dir_ownership: mkdir + chown + chmod 700"""

    def _make_user(self, pk=42, username="testuser"):
        user = MagicMock()
        user.pk = pk
        user.username = username
        return user

    @patch("apps.accounts_app.services.unix_user.subprocess.run")
    @patch("apps.accounts_app.services.unix_user.Path.mkdir")
    def test_runs_chown_and_chmod(self, mock_mkdir, mock_run):
        from apps.accounts_app.services.unix_user import enforce_data_dir_ownership

        mock_run.return_value = MagicMock(returncode=0)
        result = enforce_data_dir_ownership(self._make_user(pk=42))

        assert result is True
        # Two subprocess calls: chown then chmod
        assert mock_run.call_count == 2
        chown_args = mock_run.call_args_list[0][0][0]
        chmod_args = mock_run.call_args_list[1][0][0]
        assert chown_args[0] == "chown"
        assert "100042:100042" in chown_args
        assert chmod_args[0] == "chmod"
        assert "700" in chmod_args

    @patch("apps.accounts_app.services.unix_user.subprocess.run")
    @patch("apps.accounts_app.services.unix_user.Path.mkdir")
    def test_returns_false_on_chown_failure(self, mock_mkdir, mock_run):
        from apps.accounts_app.services.unix_user import enforce_data_dir_ownership

        mock_run.side_effect = subprocess.CalledProcessError(1, "chown")
        result = enforce_data_dir_ownership(self._make_user())
        assert result is False


class TestRunAsUser(TestCase):
    """run_as_user: validates UID range, builds setpriv command"""

    @patch("apps.accounts_app.services.unix_user.subprocess.Popen")
    def test_calls_setpriv_with_correct_uid_gid(self, mock_popen):
        from apps.accounts_app.services.unix_user import run_as_user

        mock_popen.return_value = MagicMock()
        run_as_user(100021, 100021, "echo hello", "/tmp", {"PATH": "/bin"})

        args = mock_popen.call_args[0][0]
        assert args[0] == "setpriv"
        assert "--reuid=100021" in args
        assert "--regid=100021" in args
        assert "--clear-groups" in args
        assert "echo hello" in args

    def test_raises_for_uid_below_range(self):
        """UID 0 (root) must be refused."""
        from apps.accounts_app.services.unix_user import run_as_user

        with pytest.raises(ValueError, match="outside allowed range"):
            run_as_user(0, 0, "id", "/tmp", {})

    def test_raises_for_uid_above_range(self):
        """UID 200000 is above UID_MAX."""
        from apps.accounts_app.services.unix_user import run_as_user

        with pytest.raises(ValueError, match="outside allowed range"):
            run_as_user(200000, 200000, "id", "/tmp", {})

    def test_raises_for_system_uid(self):
        """UID 1000 (typical system user) must be refused."""
        from apps.accounts_app.services.unix_user import run_as_user

        with pytest.raises(ValueError, match="outside allowed range"):
            run_as_user(1000, 1000, "id", "/tmp", {})


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
