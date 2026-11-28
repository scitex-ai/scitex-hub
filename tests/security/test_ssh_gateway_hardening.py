"""The public SSH gateway: key-only logins, throttling, and the bridge gate.

The gateway runs for real on a loopback socket and is driven by a real
paramiko client. A login is checked up to "authenticated". The shell step needs
the Terminal Broker and SLURM, which the web terminal's own tests cover. The
WebSocket bridge authorisation view runs through the real URLconf.

No mocks.
"""

from __future__ import annotations

import socket
import threading
from uuid import uuid4

import paramiko
import pytest
from django.contrib.auth.models import User

from apps.infra.accounts_app.models import APIKey, WorkspaceSSHKey
from apps.infra.accounts_app.utils.ssh_key_validator import SSHKeyValidator
from apps.infra.workspace_app.management.commands.run_ssh_gateway import (
    serve_connection,
)
from apps.infra.workspace_app.services.ssh_gateway import (
    GatewayThrottle,
    ThrottleConfig,
)

pytestmark = [pytest.mark.security]

PASSWORD = "Correct-horse-1!"  # pragma: allowlist secret
BRIDGE_URL = "/apps/workspace/api/ssh-bridge/authorize/"


class Gateway:
    """The real accept loop body on 127.0.0.1:<ephemeral>."""

    def __init__(self, throttle: GatewayThrottle):
        self.throttle = throttle
        self.host_key = paramiko.RSAKey.generate(2048)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                client, addr = self.sock.accept()
            except OSError:
                return
            threading.Thread(
                target=serve_connection,
                args=(client, addr, self.host_key, self.throttle),
                daemon=True,
            ).start()

    def transport(self) -> paramiko.Transport:
        transport = paramiko.Transport(("127.0.0.1", self.port))
        transport.start_client(timeout=10)
        return transport

    def close(self):
        self.sock.close()


@pytest.fixture
def gateway():
    gw = Gateway(GatewayThrottle(ThrottleConfig(max_failures=3)))
    yield gw
    gw.close()


@pytest.fixture
def user_with_key(transactional_db):
    user = User.objects.create_user(
        username=f"ssh-{uuid4().hex[:10]}", password=PASSWORD
    )
    key = paramiko.Ed25519Key.from_private_key(_ed25519_private_key_file())
    public = f"{key.get_name()} {key.get_base64()}"
    WorkspaceSSHKey.objects.create(
        user=user,
        title="laptop",
        public_key=public,
        fingerprint=SSHKeyValidator.calculate_fingerprint(public),
        key_type="ed25519",
    )
    return user, key


def _ed25519_private_key_file():
    """A fresh OpenSSH-format ed25519 key (paramiko cannot generate ed25519)."""
    import io

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    )
    return io.StringIO(pem.decode())


def _other_key():
    return paramiko.Ed25519Key.from_private_key(_ed25519_private_key_file())


def _try_key(gateway, username, key) -> bool:
    """True only if the gateway authenticates ``username`` with ``key``.

    A refused connection (ban) fails before the SSH banner, which paramiko
    reports as SSHException; that is a "no" too.
    """
    try:
        transport = gateway.transport()
    except (paramiko.SSHException, OSError, EOFError):
        return False
    try:
        transport.auth_publickey(username, key)
        return transport.is_authenticated()
    except (paramiko.AuthenticationException, paramiko.SSHException, EOFError):
        return False
    finally:
        transport.close()


def test_registered_key_authenticates(gateway, user_with_key):
    # Arrange
    user, key = user_with_key
    # Act
    ok = _try_key(gateway, user.username, key)
    # Assert
    assert ok


def test_unregistered_key_is_rejected(gateway, user_with_key):
    # Arrange
    user, _key = user_with_key
    # Act
    ok = _try_key(gateway, user.username, _other_key())
    # Assert
    assert not ok


def test_correct_password_is_refused_over_the_wire(gateway, user_with_key):
    # Arrange
    user, _key = user_with_key
    transport = gateway.transport()
    # Act
    try:
        transport.auth_password(user.username, PASSWORD)
        authenticated = transport.is_authenticated()
    except paramiko.AuthenticationException:
        authenticated = False
    finally:
        transport.close()
    # Assert
    assert not authenticated


def test_server_advertises_publickey_only(gateway, user_with_key):
    # Arrange
    user, _key = user_with_key
    transport = gateway.transport()
    # Act
    try:
        transport.auth_none(user.username)
        allowed = []
    except paramiko.BadAuthenticationType as e:
        allowed = e.allowed_types
    finally:
        transport.close()
    # Assert
    assert allowed == ["publickey"]


def _fail_until_banned(gateway, username, attempts=3):
    for _ in range(attempts):
        _try_key(gateway, username, _other_key())
    # The failure is counted when the server side of the connection ends.
    import time

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if gateway.throttle.username_banned(username):
            return
        time.sleep(0.05)


def test_repeated_failures_ban_the_username_even_with_the_right_key(
    gateway, user_with_key
):
    # Arrange
    user, key = user_with_key
    _fail_until_banned(gateway, user.username)
    # Act
    ok = _try_key(gateway, user.username, key)
    # Assert
    assert not ok


def test_repeated_failures_ban_the_source_address(gateway, user_with_key):
    # Arrange
    user, _key = user_with_key
    _fail_until_banned(gateway, user.username)
    # Act
    admitted, reason = gateway.throttle.admit("127.0.0.1")
    # Assert
    assert reason == "banned"


@pytest.fixture
def bridge_user(db):
    return User.objects.create_user(username=f"br-{uuid4().hex[:10]}")


def test_bridge_refuses_an_anonymous_upgrade(client, db):
    # Arrange
    url = BRIDGE_URL
    # Act
    response = client.get(url)
    # Assert
    assert response.status_code == 401


def test_bridge_admits_a_signed_in_session(client, bridge_user):
    # Arrange
    client.force_login(bridge_user)
    # Act
    response = client.get(BRIDGE_URL)
    # Assert
    assert response.status_code == 204


def test_bridge_admits_an_api_key(client, bridge_user):
    # Arrange
    _api_key, raw = APIKey.create_key(bridge_user, "ssh bridge")
    # Act
    response = client.get(BRIDGE_URL, HTTP_AUTHORIZATION=f"Bearer {raw}")
    # Assert
    assert response.status_code == 204


def test_bridge_refuses_a_revoked_api_key(client, bridge_user):
    # Arrange
    api_key, raw = APIKey.create_key(bridge_user, "ssh bridge")
    api_key.is_active = False
    api_key.save(update_fields=["is_active"])
    # Act
    response = client.get(BRIDGE_URL, HTTP_AUTHORIZATION=f"Bearer {raw}")
    # Assert
    assert response.status_code == 401
