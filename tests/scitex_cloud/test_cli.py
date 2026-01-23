#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_cloud/test_cli.py

"""Tests for scitex_cloud CLI commands."""

import pytest
from click.testing import CliRunner

from scitex_cloud import __version__
from scitex_cloud.cli.main import main


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
        assert "SciTeX Cloud" in result.output
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
        assert "nas" in result.output


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


# EOF
