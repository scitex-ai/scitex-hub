#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/test_cli.py

"""Tests for scitex_hub CLI commands.

Slice 6a of the CLI-standardization plan renamed the pilot verbs to
their canonical short forms (doctrine §1d): ``init``, ``deploy``,
``status``, ``logs``. The deprecated old spellings are covered in
``tests/scitex_hub/_cli/test_verb_renames.py``.
"""

import pytest
from click.testing import CliRunner

from scitex_hub import __version__
from scitex_hub._cli.main import main


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestMainCLI:
    """Tests for main CLI entry point."""

    def test_root_version_flag_prints_package_version(self, runner):
        """``--version`` output carries the package version string."""
        # Arrange
        args = ["--version"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert __version__ in result.output

    def test_root_help_exits_with_code_zero(self, runner):
        """``--help`` renders without error."""
        # Arrange
        args = ["--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert result.exit_code == 0

    def test_root_help_lists_canonical_verb_names(self, runner):
        """Root help advertises the slice-6a canonical verbs."""
        # Arrange
        args = ["--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(
            name in result.output for name in ("init", "deploy", "docker", "status")
        )


class TestInitCommand:
    """Tests for the init command (slice 6a: `setup` verb is banned)."""

    def test_init_help_lists_environment_choices(self, runner):
        """``init --help`` shows the --env option with its choices."""
        # Arrange
        args = ["init", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(token in result.output for token in ("--env", "dev", "prod"))


class TestDeployCommand:
    """Tests for the deploy command (slice 6a: canonical short verb)."""

    def test_deploy_help_lists_env_and_build_options(self, runner):
        """``deploy --help`` shows the --env and --build options."""
        # Arrange
        args = ["deploy", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(token in result.output for token in ("--env", "--build"))


class TestDockerCommand:
    """Tests for docker command group."""

    def test_docker_help_lists_container_verbs(self, runner):
        """``docker --help`` shows the container lifecycle leaves."""
        # Arrange
        args = ["docker", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(verb in result.output for verb in ("build", "up", "down"))

    def test_docker_subcommand_helps_exit_with_code_zero(self, runner):
        """Every docker leaf renders its --help without error."""
        # Arrange
        subcommands = ["build", "up", "down", "restart", "ps"]
        # Act
        results = [
            runner.invoke(main, ["docker", cmd, "--help"]) for cmd in subcommands
        ]
        # Assert
        assert all(result.exit_code == 0 for result in results)


class TestStatusCommand:
    """Tests for the status command (slice 6a: canonical short verb)."""

    def test_status_help_lists_environment_option(self, runner):
        """``status --help`` shows the --env option."""
        # Arrange
        args = ["status", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "--env" in result.output


class TestLogsCommand:
    """Tests for the logs command (slice 6a: canonical short verb)."""

    def test_logs_help_lists_follow_and_tail_options(self, runner):
        """``logs --help`` shows the --follow and --tail options."""
        # Arrange
        args = ["logs", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(token in result.output for token in ("--follow", "--tail"))


class TestGiteaCommand:
    """Tests for gitea command group."""

    def test_gitea_help_lists_repository_verbs(self, runner):
        """``gitea --help`` shows the repository leaves."""
        # Arrange
        args = ["gitea", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(verb in result.output for verb in ("clone", "create", "list"))

    def test_gitea_subcommand_helps_exit_with_code_zero(self, runner):
        """Every gitea leaf renders its --help without error."""
        # Arrange
        subcommands = [
            "clone",
            "create",
            "list",
            "search",
            "push",
            "pull",
            "show-status",
        ]
        # Act
        results = [
            runner.invoke(main, ["gitea", cmd, "--help"]) for cmd in subcommands
        ]
        # Assert
        assert all(result.exit_code == 0 for result in results)


class TestMcpCommand:
    """Tests for mcp command group."""

    def test_mcp_help_lists_server_verbs(self, runner):
        """``mcp --help`` shows the server lifecycle + introspection leaves."""
        # Arrange
        args = ["mcp", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(
            token in result.output for token in ("start", "doctor", "list-tools")
        )

    def test_mcp_start_help_lists_transport_options(self, runner):
        """``mcp start --help`` shows transport/host/port options."""
        # Arrange
        args = ["mcp", "start", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(
            token in result.output for token in ("--transport", "--host", "--port")
        )

    def test_mcp_list_tools_outputs_tool_inventory(self, runner):
        """``mcp list-tools`` names at least one tool domain."""
        # Arrange
        args = ["mcp", "list-tools"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "cloud" in result.output.lower() or "api" in result.output.lower()

    def test_mcp_list_tools_json_names_the_package(self, runner):
        """``mcp list-tools --json`` emits the scitex-hub server name."""
        # Arrange
        args = ["mcp", "list-tools", "--json"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert '"name": "scitex-hub"' in result.output


class TestListPythonApisCommand:
    """Tests for list-python-apis command."""

    def test_list_python_apis_help_lists_verbose_option(self, runner):
        """``list-python-apis --help`` shows the --verbose option."""
        # Arrange
        args = ["list-python-apis", "--help"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert "--verbose" in result.output


class TestHelpRecursive:
    """Tests for --help-recursive option."""

    def test_help_recursive_walks_command_groups(self, runner):
        """``--help-recursive`` includes the nested group names."""
        # Arrange
        args = ["--help-recursive"]
        # Act
        result = runner.invoke(main, args)
        # Assert
        assert all(name in result.output for name in ("gitea", "mcp", "docker"))


# EOF
