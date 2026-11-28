"""Regression: user shells never inherit the server's environment.

The terminal broker runs with the server's environment (database, cache,
Django, payment and API credentials). A user's shell used to start from a
copy of it, and on the shared-allocation path ``apptainer exec instance://``
passes the caller's environment straight into the container.

These tests put realistic secret NAMES (fake values) into the real process
environment, spawn a real shell through the production ``Shell`` PTY class,
and read the environment that shell actually received. No mocks.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest

from apps.workspace.console_app.services.terminal_broker.shell import Shell
from apps.workspace.console_app.services.user_process_env import (
    SECRET_NAME_RE,
    user_process_env,
)

pytestmark = pytest.mark.security

SERVER_SECRETS = {
    "SECRET_KEY": "x",
    "SCITEX_HUB_DJANGO_SECRET_KEY": "x",
    "POSTGRES_PASSWORD": "x",
    "SCITEX_HUB_DB_PASSWORD_PROD": "x",
    "SCITEX_HUB_GITEA_TOKEN": "x",
    "SENTRY_DSN": "x",
    "STRIPE_SECRET_KEY": "x",
    "STRIPE_WEBHOOK_SECRET": "x",
    "DATABASE_URL": "x",
    "REDIS_URL": "x",
    "AWS_ACCESS_KEY_ID": "x",
    "SCITEX_HUB_ONSITE_SECRET": "x",
    "SCITEX_HUB_EMAIL_HOST": "smtp.invalid",
    "APPTAINERENV_DB_PASSWORD": "x",
    "APPTAINER_DOCKER_PASSWORD": "x",
}

#: Credentials that belong to the user the shell is for.
USER_SCOPED = re.compile(
    r"^(APPTAINERENV_)?(SCITEX_HUB_ONSITE_KEY(_EPOCH)?|SCITEX_API_TOKEN)$"
)


@pytest.fixture
def server_env():
    saved = {k: os.environ.get(k) for k in SERVER_SECRETS}
    os.environ.update(SERVER_SECRETS)
    try:
        yield SERVER_SECRETS
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _shell_env_names(tmp_path: Path) -> set[str]:
    out = tmp_path / "env.txt"
    shell = Shell(
        shell_id="test-shell",
        allocation_id="test-alloc",
        username="alice",
        screen_session="scitex-0",
        command=["/bin/sh", "-c", f"env > {out}; sleep 3"],
    )
    shell.spawn()
    deadline = time.time() + 10
    while time.time() < deadline and not (out.exists() and out.stat().st_size):
        time.sleep(0.1)
    shell.close()
    names = set()
    for line in out.read_text().splitlines():
        if "=" in line:
            names.add(line.split("=", 1)[0])
    return names


def test_real_shell_receives_none_of_the_server_secrets(server_env, tmp_path):
    # Arrange
    secret_names = set(server_env)
    # Act
    names = _shell_env_names(tmp_path)
    # Assert
    assert names.isdisjoint(secret_names), sorted(names & secret_names)


def test_real_shell_has_no_secret_shaped_names_but_its_own(server_env, tmp_path):
    # Arrange
    allowed = USER_SCOPED
    # Act
    names = _shell_env_names(tmp_path)
    # Assert
    assert (
        sorted(n for n in names if SECRET_NAME_RE.search(n) and not allowed.match(n))
        == []
    )


def test_real_shell_keeps_a_usable_path(server_env, tmp_path):
    # Arrange
    expected = "PATH"
    # Act
    names = _shell_env_names(tmp_path)
    # Assert
    assert expected in names


def test_unlisted_server_variable_is_not_copied():
    # Arrange
    server = {"PATH": "/usr/bin", "SCITEX_HUB_EMAIL_HOST": "smtp.invalid"}
    # Act
    env = user_process_env(server)
    # Assert
    assert "SCITEX_HUB_EMAIL_HOST" not in env


def test_container_injection_variables_are_not_copied():
    # Arrange
    server = {"APPTAINERENV_FOO": "1", "APPTAINER_BIND": "/data"}
    # Act
    env = user_process_env(server)
    # Assert
    assert "APPTAINERENV_FOO" not in env


def test_container_runtime_configuration_is_kept():
    # Arrange
    server = {"APPTAINER_BIND": "/data"}
    # Act
    env = user_process_env(server)
    # Assert
    assert env.get("APPTAINER_BIND") == "/data"
