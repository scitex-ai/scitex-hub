#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/test_docker.py

"""Tests for scitex_hub Docker utilities."""

from unittest.mock import MagicMock, patch

import pytest

from scitex_hub._config._environments import Environment
from scitex_hub._utils._docker import DockerManager


@pytest.fixture
def mock_env():
    """Create mock environment."""
    return Environment(
        name="test",
        docker_compose_file="docker_test/docker-compose.yml",
        env_file=".env.test",
        host="localhost",
        port=8000,
        description="Test environment",
    )


@pytest.fixture
def docker_manager(mock_env, tmp_path):
    """Create DockerManager with mock environment."""
    return DockerManager(env=mock_env, project_root=tmp_path)


class TestDockerManager:
    """Tests for DockerManager class."""

    def test_init_with_env(self, mock_env, tmp_path):
        """Test initialization with explicit environment."""
        manager = DockerManager(env=mock_env, project_root=tmp_path)
        assert manager.env == mock_env
        assert manager.project_root == tmp_path

    def test_find_project_root(self, tmp_path):
        """Test _find_project_root finds pyproject.toml."""
        # Create pyproject.toml in tmp_path
        (tmp_path / "pyproject.toml").touch()

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            manager = DockerManager(env=MagicMock(), project_root=None)
            # When project_root is None, it should find it
            assert manager.project_root is not None

    @patch("subprocess.run")
    def test_build(self, mock_run, docker_manager):
        """Test build method calls docker compose build."""
        mock_run.return_value = MagicMock(returncode=0)
        result = docker_manager.build()
        assert result == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "compose" in call_args
        assert "build" in call_args

    @patch("subprocess.run")
    def test_build_no_cache(self, mock_run, docker_manager):
        """Test build with no_cache option."""
        mock_run.return_value = MagicMock(returncode=0)
        docker_manager.build(no_cache=True)
        call_args = mock_run.call_args[0][0]
        assert "--no-cache" in call_args

    @patch("subprocess.run")
    def test_up(self, mock_run, docker_manager):
        """Test up method calls docker compose up."""
        mock_run.return_value = MagicMock(returncode=0)
        result = docker_manager.up()
        assert result == 0
        call_args = mock_run.call_args[0][0]
        assert "up" in call_args
        assert "-d" in call_args

    @patch("subprocess.run")
    def test_down(self, mock_run, docker_manager):
        """Test down method calls docker compose down."""
        mock_run.return_value = MagicMock(returncode=0)
        result = docker_manager.down()
        assert result == 0
        call_args = mock_run.call_args[0][0]
        assert "down" in call_args

    @patch("subprocess.run")
    def test_down_with_volumes(self, mock_run, docker_manager):
        """Test down with volumes option."""
        mock_run.return_value = MagicMock(returncode=0)
        docker_manager.down(volumes=True)
        call_args = mock_run.call_args[0][0]
        assert "-v" in call_args

    @patch("subprocess.run")
    def test_restart(self, mock_run, docker_manager):
        """Test restart method."""
        mock_run.return_value = MagicMock(returncode=0)
        result = docker_manager.restart()
        assert result == 0
        call_args = mock_run.call_args[0][0]
        assert "restart" in call_args

    @patch("subprocess.run")
    def test_logs(self, mock_run, docker_manager):
        """Test logs method."""
        mock_run.return_value = MagicMock(returncode=0)
        result = docker_manager.logs()
        assert result == 0
        call_args = mock_run.call_args[0][0]
        assert "logs" in call_args

    @patch("subprocess.run")
    def test_logs_follow(self, mock_run, docker_manager):
        """Test logs with follow option."""
        mock_run.return_value = MagicMock(returncode=0)
        docker_manager.logs(follow=True)
        call_args = mock_run.call_args[0][0]
        assert "-f" in call_args

    @patch("subprocess.run")
    def test_ps(self, mock_run, docker_manager):
        """Test ps method."""
        mock_run.return_value = MagicMock(returncode=0)
        result = docker_manager.ps()
        assert result == 0
        call_args = mock_run.call_args[0][0]
        assert "ps" in call_args


# EOF
