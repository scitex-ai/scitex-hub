#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redis URLs gain the deployment's password, and only when one is set."""

import importlib.util
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from config.settings._redis_auth import (
    PASSWORD_ENV,
    authenticated_redis_url,
    with_redis_password,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_password_is_added_to_a_plain_url():
    # Arrange
    url = "redis://redis:6379/1"
    # Act
    result = with_redis_password(url, "pw")
    # Assert
    assert result == "redis://:pw@redis:6379/1"


def test_url_without_password_is_unchanged_when_none_is_configured():
    # Arrange
    url = "redis://redis:6379/1"
    # Act
    result = with_redis_password(url, None)
    # Assert
    assert result == url


def test_explicit_password_in_url_wins():
    # Arrange
    url = "redis://:already@redis:6379/1"
    # Act
    result = with_redis_password(url, "other")
    # Assert
    assert result == url


def test_non_redis_url_is_unchanged():
    # Arrange -- the test suite's in-memory broker.
    url = "memory://"
    # Act
    result = with_redis_password(url, "pw")
    # Assert
    assert result == url


def test_special_characters_survive_the_round_trip():
    # Arrange
    password = "a/b:c@d%e f"
    # Act
    parsed = urlsplit(with_redis_password("rediss://redis:6380/0", password))
    # Assert
    assert (unquote(parsed.password), parsed.hostname, parsed.port) == (
        password,
        "redis",
        6380,  # stx-allow: STX-NL001
    )


def test_username_is_kept():
    # Arrange
    url = "redis://hub@redis:6379/2"
    # Act
    result = with_redis_password(url, "pw")
    # Assert
    assert result == "redis://hub:pw@redis:6379/2"


def test_empty_env_value_means_no_password():
    # Arrange
    environ = {PASSWORD_ENV: ""}
    # Act
    result = authenticated_redis_url("redis://redis:6379/1", environ)
    # Assert
    assert result == "redis://redis:6379/1"


_SETTINGS_CELERY = REPO_ROOT / "config" / "settings" / "settings_celery.py"


_CELERY_ENV = (PASSWORD_ENV, "SCITEX_HUB_TEST_MODE", "SCITEX_HUB_CELERY_BROKER_URL")


@pytest.fixture
def celery_env():
    """Clear the variables settings_celery reads; restore them afterwards."""
    saved = {name: os.environ.pop(name) for name in _CELERY_ENV if name in os.environ}
    yield os.environ
    for name in _CELERY_ENV:
        os.environ.pop(name, None)
    os.environ.update(saved)


def _celery_broker():
    """Execute the real settings_celery.py under the current environment."""
    spec = importlib.util.spec_from_file_location(
        "_probe_settings_celery", _SETTINGS_CELERY
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CELERY_BROKER_URL


def test_celery_broker_setting_carries_the_password(celery_env):
    # Arrange -- the real settings file, not a copy of its logic.
    celery_env[PASSWORD_ENV] = "probe-value"
    # Act
    broker = _celery_broker()
    # Assert
    assert broker == "redis://:probe-value@redis:6379/1"


def test_celery_broker_setting_is_unchanged_without_a_password(celery_env):
    # Arrange -- the fixture removed SCITEX_HUB_REDIS_PASSWORD.
    celery_env.pop(PASSWORD_ENV, None)
    # Act
    broker = _celery_broker()
    # Assert
    assert broker == "redis://redis:6379/1"
