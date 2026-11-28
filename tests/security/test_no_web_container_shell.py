"""Regression: the web application never runs a user's shell command itself.

Two endpoints used to do so for any signed-in account:

* ``/apps/llm/api/bash/`` ran ``bash -c <command>`` in the web container
  (the AI chat "!" prefix).
* ``/apps/workspace/api/exec/`` ran the command through ``docker exec`` in a
  per-user container driven from the web application.

Both are retired (410, request body never read). The SSH gateway also stops
accepting passwords: paramiko hands every ``password`` userauth request to
``check_auth_password`` regardless of the advertised methods.

Real URLconf through the Django test client, a signed-in non-staff user, real
paramiko constants. No mocks.
"""

from __future__ import annotations

import json
from uuid import uuid4

import paramiko
import pytest
from django.contrib.auth.models import User

pytestmark = [pytest.mark.security, pytest.mark.django_db]

ROUTES = ["/apps/llm/api/bash/", "/apps/workspace/api/exec/"]
PASSWORD = "Correct-horse-1!"  # pragma: allowlist secret


@pytest.fixture
def marker(tmp_path):
    return tmp_path / "PWNED"


@pytest.fixture
def signed_in(client):
    user = User.objects.create_user(username=f"u-{uuid4().hex[:10]}")
    client.force_login(user)
    return client


@pytest.mark.parametrize("url", ROUTES)
def test_shell_route_is_gone_for_a_signed_in_user(signed_in, marker, url):
    # Arrange
    body = json.dumps({"command": f"touch {marker}"})
    # Act
    response = signed_in.post(url, body, content_type="application/json")
    # Assert
    assert response.status_code == 410


@pytest.mark.parametrize("url", ROUTES)
def test_shell_route_runs_nothing(signed_in, marker, url):
    # Arrange
    body = json.dumps({"command": f"touch {marker}"})
    # Act
    signed_in.post(url, body, content_type="application/json")
    # Assert
    assert not marker.exists()


@pytest.mark.parametrize("url", ROUTES)
def test_shell_route_runs_nothing_for_a_form_post(signed_in, marker, url):
    # Arrange
    form = {"command": f"touch {marker}"}
    # Act
    signed_in.post(url, form)
    # Assert
    assert not marker.exists()


@pytest.fixture
def gateway_user():
    return User.objects.create_user(
        username=f"ssh-{uuid4().hex[:10]}", password=PASSWORD
    )


def test_ssh_gateway_refuses_a_correct_password(gateway_user):
    # Arrange
    from apps.infra.workspace_app.management.commands.run_ssh_gateway import (
        SSHGateway,
    )

    gateway = SSHGateway()
    # Act
    result = gateway.check_auth_password(gateway_user.username, PASSWORD)
    # Assert
    assert result == paramiko.AUTH_FAILED


def test_ssh_gateway_password_attempt_binds_no_user(gateway_user):
    # Arrange
    from apps.infra.workspace_app.management.commands.run_ssh_gateway import (
        SSHGateway,
    )

    gateway = SSHGateway()
    # Act
    gateway.check_auth_password(gateway_user.username, PASSWORD)
    # Assert
    assert gateway.user is None


def test_ssh_gateway_refuses_keyboard_interactive(gateway_user):
    # Arrange
    from apps.infra.workspace_app.management.commands.run_ssh_gateway import (
        SSHGateway,
    )

    gateway = SSHGateway()
    # Act
    result = gateway.check_auth_interactive(gateway_user.username, "")
    # Assert
    assert result == paramiko.AUTH_FAILED
