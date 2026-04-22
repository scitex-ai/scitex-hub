#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_cloud/test_no_interactive_prompts.py

"""CLI spec §2 compliance — no interactive prompts.

Every refactored command must:
- succeed (or fail for another reason) when value comes from flag / env;
- exit with code 2 and a stderr guidance message when the value is
  missing everywhere, instead of blocking on stdin.

These tests invoke CLI commands under ``CliRunner`` with
``input=""`` so that any residual ``click.prompt`` / ``click.confirm``
would block and surface as a test failure.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from scitex_cloud._cli._gitea_auth import login as gitea_login
from scitex_cloud._cli._gitea_auth import logout as gitea_logout
from scitex_cloud._cli._gitea_repo import delete as repo_delete
from scitex_cloud._cli.project import project_delete
from scitex_cloud._cli.setup import setup as setup_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """Strip SCITEX_CLOUD_* env and point HOME to a clean tmp dir.

    Prevents the developer's real config file from affecting tests.
    """
    for name in [
        "SCITEX_CLOUD_WORKSPACE_USER",
        "SCITEX_CLOUD_WORKSPACE_PASSWORD",
        "SCITEX_CLOUD_WORKSPACE_URL",
        "SCITEX_CLOUD_GITEA_USER",
        "SCITEX_CLOUD_GITEA_PASSWORD",
        "SCITEX_CLOUD_GITEA_TOKEN",
        "SCITEX_CLOUD_GITEA_URL",
        "SCITEX_CLOUD_ENV",
        "SCITEX_CLOUD_CONFIG",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


class TestSetupNoPrompt:
    def test_missing_env_fails_fast(self, runner, isolated_env):
        result = runner.invoke(setup_cmd, [], input="")
        assert result.exit_code == 2, result.output
        assert "SCITEX_CLOUD_ENV" in result.output

    def test_env_from_envvar(self, runner, isolated_env, monkeypatch):
        monkeypatch.setenv("SCITEX_CLOUD_ENV", "nonexistent-env")
        result = runner.invoke(setup_cmd, [], input="")
        # Either invalid-choice exit 2 or ENVIRONMENTS-specific path;
        # the key property is: no prompt, no hang.
        assert result.exit_code in (1, 2), result.output
        assert "Username" not in result.output
        assert "Password" not in result.output


class TestGiteaLoginNoPrompt:
    def test_missing_all_credentials_fails_fast(self, runner, isolated_env):
        with patch(
            "scitex_cloud._cli._gitea_utils.get_gitea_url", return_value="https://x"
        ):
            result = runner.invoke(gitea_login, [], input="")
        assert result.exit_code == 2, result.output
        assert "gitea credentials missing" in result.output.lower()

    def test_token_from_envvar_skips_username_flow(
        self, runner, isolated_env, monkeypatch
    ):
        monkeypatch.setenv("SCITEX_CLOUD_GITEA_TOKEN", "envtoken")
        with (
            patch(
                "scitex_cloud._cli._gitea_utils.get_gitea_url", return_value="https://x"
            ),
            patch("scitex_cloud._cli._gitea_auth.run_tea") as run_tea,
        ):
            result = runner.invoke(gitea_login, [], input="")
        assert result.exit_code == 0, result.output
        run_tea.assert_called_once()
        args = run_tea.call_args.args
        assert "--token" in args
        assert "envtoken" in args


class TestGiteaLogoutNoPrompt:
    def test_delete_token_without_password_fails_fast(
        self, runner, isolated_env, monkeypatch
    ):
        monkeypatch.setenv("SCITEX_CLOUD_GITEA_URL", "https://x")
        monkeypatch.setenv("SCITEX_CLOUD_GITEA_USER", "u")
        result = runner.invoke(
            gitea_logout,
            ["--delete-token", "--url", "https://x", "--user", "u"],
            input="",
        )
        assert result.exit_code == 2, result.output
        assert "password" in result.output.lower()


class TestProjectDeleteNoPrompt:
    def test_delete_without_yes_fails_fast(self, runner, isolated_env):
        result = runner.invoke(project_delete, ["my-project"], input="")
        assert result.exit_code == 2, result.output
        assert "--yes" in result.output

    def test_delete_with_yes_calls_backend(self, runner, isolated_env, monkeypatch):
        with patch("scitex_cloud.project.project_delete") as backend:
            result = runner.invoke(project_delete, ["my-project", "--yes"], input="")
        assert result.exit_code == 0, result.output
        backend.assert_called_once_with("my-project")


class TestRepoDeleteNoPrompt:
    def test_delete_without_yes_fails_fast(self, runner, isolated_env):
        result = runner.invoke(repo_delete, ["owner/repo"], input="")
        assert result.exit_code == 2, result.output
        assert "--yes" in result.output


# EOF
