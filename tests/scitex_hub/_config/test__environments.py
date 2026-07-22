#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_config/test__environments.py

"""Tests for scitex_hub configuration."""

import os

import pytest

from scitex_hub._config._environments import (
    ENVIRONMENTS,
    Environment,
    get_environment,
)


class TestEnvironment:
    """Tests for Environment dataclass."""

    def test_environment_attributes(self):
        """Test Environment has required attributes."""
        env = Environment(
            name="test",
            docker_compose_file="docker-compose.yml",
            env_file=".env.test",
            host="localhost",
            port=8000,
            description="Test environment",
        )
        assert env.name == "test"
        assert env.host == "localhost"
        assert env.port == 8000

    def test_env_path_property(self):
        """Test env_path returns correct path."""
        env = Environment(
            name="test",
            docker_compose_file="docker-compose.yml",
            env_file=".env.test",
            host="localhost",
            port=8000,
            description="Test",
        )
        assert str(env.env_path) == "deployment/docker/envs/.env.test"

    def test_compose_path_property(self):
        """Test compose_path returns correct path."""
        env = Environment(
            name="test",
            docker_compose_file="docker_test/docker-compose.yml",
            env_file=".env.test",
            host="localhost",
            port=8000,
            description="Test",
        )
        assert (
            str(env.compose_path) == "deployment/docker/docker_test/docker-compose.yml"
        )


class TestEnvironments:
    """Tests for predefined environments."""

    def test_dev_environment_exists(self):
        """Test dev environment is defined."""
        assert "dev" in ENVIRONMENTS
        assert ENVIRONMENTS["dev"].name == "dev"
        assert ENVIRONMENTS["dev"].host == "127.0.0.1"

    def test_prod_environment_exists(self):
        """Test prod environment is defined."""
        assert "prod" in ENVIRONMENTS
        assert ENVIRONMENTS["prod"].name == "prod"
        assert ENVIRONMENTS["prod"].host == "0.0.0.0"


class TestGetEnvironment:
    """Tests for get_environment function."""

    def test_get_dev_environment(self):
        """Test getting dev environment by name."""
        env = get_environment("dev")
        assert env.name == "dev"

    def test_get_prod_environment(self):
        """Test getting prod environment by name."""
        env = get_environment("prod")
        assert env.name == "prod"

    def test_invalid_environment_raises(self):
        """Test invalid environment name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown environment"):
            get_environment("invalid")

    def test_auto_detect_default(self):
        """Test auto-detect defaults to dev."""
        # Ensure SCITEX_HUB_ENV is not set
        old_value = os.environ.pop("SCITEX_HUB_ENV", None)
        try:
            env = get_environment(None)
            assert env.name == "dev"
        finally:
            if old_value:
                os.environ["SCITEX_HUB_ENV"] = old_value

    def test_auto_detect_from_env_var(self):
        """Test auto-detect from SCITEX_HUB_ENV."""
        old_value = os.environ.get("SCITEX_HUB_ENV")
        try:
            os.environ["SCITEX_HUB_ENV"] = "prod"
            env = get_environment(None)
            assert env.name == "prod"
        finally:
            if old_value:
                os.environ["SCITEX_HUB_ENV"] = old_value
            else:
                os.environ.pop("SCITEX_HUB_ENV", None)


# EOF
