#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""External accounts are created when a user becomes active, not at sign-up.

Database tests driving the real signup, verification and sign-in endpoints
through the Django test client. Gitea is a real HTTP server on a loopback port
(a stand-in that records the admin calls the hub makes), so the hub's own
client, transport and error handling run unchanged.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from apps.infra.auth_app.models import EmailVerification

pytestmark = pytest.mark.django_db

PASSWORD = "Gx7-quiet-harbour-42"


class _GiteaStandIn:
    """Loopback HTTP server answering the two user endpoints the hub calls."""

    def __init__(self):
        self.created: list[str] = []
        self.users: set[str] = set()
        stand_in = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def _reply(self, status, body):
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                prefix = "/api/v1/users/"
                name = self.path[len(prefix) :] if self.path.startswith(prefix) else ""
                if name and name in stand_in.users:
                    self._reply(200, {"login": name})
                else:
                    self._reply(404, {"message": "user does not exist"})

            def do_POST(self):
                if self.path != "/api/v1/admin/users":
                    self._reply(404, {"message": "not found"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
                stand_in.created.append(data["username"])
                stand_in.users.add(data["username"])
                self._reply(201, {"login": data["username"]})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def gitea():
    with _GiteaStandIn() as stand_in:
        with override_settings(GITEA_URL=stand_in.url, GITEA_TOKEN="stand-in"):
            yield stand_in


def _signup(client, username, email):
    return client.post(
        reverse("auth_app:signup"),
        {
            "username": username,
            "email": email,
            "password": PASSWORD,
            "password2": PASSWORD,
            "agree_terms": "on",
        },
    )


def _verify(client, user, email):
    code = EmailVerification.objects.get(user=user).code
    return client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": email, "otp_code": code}),
        content_type="application/json",
    )


@pytest.fixture
def signed_up(client, gitea):
    _signup(client, "newcomer", "newcomer@example.com")
    return User.objects.get(username="newcomer")


def test_signup_leaves_the_account_inactive(signed_up):
    # Arrange
    user = signed_up
    # Act
    user.refresh_from_db()
    # Assert
    assert user.is_active is False


def test_signup_creates_no_gitea_account(signed_up, gitea):
    # Arrange
    user = signed_up
    # Act
    created = list(gitea.created)
    # Assert
    assert (user.username, created) == ("newcomer", [])


def test_verification_activates_the_account(client, signed_up):
    # Arrange
    user = signed_up
    # Act
    _verify(client, user, "newcomer@example.com")
    # Assert
    assert User.objects.get(pk=user.pk).is_active is True


def test_verification_creates_the_gitea_account(client, signed_up, gitea):
    # Arrange
    user = signed_up
    # Act
    _verify(client, user, "newcomer@example.com")
    # Assert
    assert gitea.created == ["newcomer"]


def test_account_created_active_is_provisioned_at_creation(gitea):
    # Arrange
    username = "staffmade"
    # Act
    User.objects.create_user(
        username=username, email="staffmade@example.com", password=PASSWORD
    )
    # Assert
    assert gitea.created == [username]


def test_later_saves_are_not_activations(gitea):
    # Arrange
    user = User.objects.create_user(
        username="staffmade", email="staffmade@example.com", password=PASSWORD
    )
    # Act
    user.first_name = "Staff"
    user.save()
    user.save(update_fields=["last_login"])
    User.objects.get(pk=user.pk).save()
    # Assert
    assert gitea.created == ["staffmade"]


def test_inactive_account_is_provisioned_on_activation(gitea):
    # Arrange
    user = User.objects.create_user(
        username="dormant",
        email="dormant@example.com",
        password=PASSWORD,
        is_active=False,
    )
    # Act
    user.is_active = True
    user.save(update_fields=["is_active"])
    # Assert
    assert gitea.created == ["dormant"]
