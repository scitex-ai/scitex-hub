#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/test_cli.py

"""Tests for scitex_hub CLI commands."""

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

    def test_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "SciTeX Hub" in result.output
        assert "deploy" in result.output
        assert "docker" in result.output
        assert "setup" in result.output
        assert "status" in result.output


class TestSetupCommand:
    """Tests for setup command."""

    def test_setup_help(self, runner):
        """Test setup --help."""
        result = runner.invoke(main, ["setup", "--help"])
        assert result.exit_code == 0
        assert "--env" in result.output
        assert "dev" in result.output
        assert "prod" in result.output


class TestDeployCommand:
    """Tests for deploy command."""

    def test_deploy_help(self, runner):
        """Test deploy --help."""
        result = runner.invoke(main, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--build" in result.output


class TestDockerCommand:
    """Tests for docker command group."""

    def test_docker_help(self, runner):
        """Test docker --help."""
        result = runner.invoke(main, ["docker", "--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "up" in result.output
        assert "down" in result.output

    def test_docker_subcommands_help(self, runner):
        """Test docker subcommands have help."""
        subcommands = ["build", "up", "down", "restart", "ps"]
        for cmd in subcommands:
            result = runner.invoke(main, ["docker", cmd, "--help"])
            assert result.exit_code == 0


class TestStatusCommand:
    """Tests for status command."""

    def test_status_help(self, runner):
        """Test status --help."""
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0
        assert "--env" in result.output


class TestLogsCommand:
    """Tests for logs command."""

    def test_logs_help(self, runner):
        """Test logs --help."""
        result = runner.invoke(main, ["logs", "--help"])
        assert result.exit_code == 0
        assert "--follow" in result.output
        assert "--tail" in result.output


class TestGiteaCommand:
    """Tests for gitea command group."""

    def test_gitea_help(self, runner):
        """Test gitea --help."""
        result = runner.invoke(main, ["gitea", "--help"])
        assert result.exit_code == 0
        assert "clone" in result.output
        assert "create" in result.output
        assert "list" in result.output

    def test_gitea_subcommands_help(self, runner):
        """Test gitea subcommands have help."""
        subcommands = ["clone", "create", "list", "search", "push", "pull", "status"]
        for cmd in subcommands:
            result = runner.invoke(main, ["gitea", cmd, "--help"])
            assert result.exit_code == 0


class TestMcpCommand:
    """Tests for mcp command group."""

    def test_mcp_help(self, runner):
        """Test mcp --help."""
        result = runner.invoke(main, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "doctor" in result.output
        assert "list-tools" in result.output
        assert "installation" in result.output

    def test_mcp_start_help(self, runner):
        """Test mcp start --help."""
        result = runner.invoke(main, ["mcp", "start", "--help"])
        assert result.exit_code == 0
        assert "--transport" in result.output
        assert "--host" in result.output
        assert "--port" in result.output

    def test_mcp_list_tools(self, runner):
        """Test mcp list-tools shows tools."""
        result = runner.invoke(main, ["mcp", "list-tools"])
        assert result.exit_code == 0
        assert "cloud" in result.output.lower() or "api" in result.output.lower()

    def test_mcp_list_tools_json(self, runner):
        """Test mcp list-tools --json."""
        result = runner.invoke(main, ["mcp", "list-tools", "--json"])
        assert result.exit_code == 0
        assert '"name": "scitex-hub"' in result.output


class TestListPythonApisCommand:
    """Tests for list-python-apis command."""

    def test_list_python_apis_help(self, runner):
        """Test list-python-apis --help."""
        result = runner.invoke(main, ["list-python-apis", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output


class TestHelpRecursive:
    """Tests for --help-recursive option."""

    def test_help_recursive(self, runner):
        """Test --help-recursive shows all commands."""
        result = runner.invoke(main, ["--help-recursive"])
        assert result.exit_code == 0
        # Should show subcommands for groups
        assert "gitea" in result.output
        assert "mcp" in result.output
        assert "docker" in result.output


# EOF
