"""Run the public SSH gateway for user workspaces.

Usage:
    python manage.py run_ssh_gateway --port 2200 --host 0.0.0.0

Key-only logins; the shell is spawned by the Terminal Broker in the user's
allocation. Connection and failed-login limits: see
apps/infra/workspace_app/services/ssh_gateway/throttle.py and
docs/ops/ssh-gateway.md.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
from pathlib import Path

import paramiko
from django.core.management.base import BaseCommand

from apps.infra.workspace_app.services.ssh_gateway import (
    GatewayThrottle,
    SSHGateway,
    ThrottleConfig,
    handle_client,
)
from apps.infra.workspace_app.services.ssh_gateway.server_interface import (
    log_auth_event,
)
from apps.infra.workspace_app.services.ssh_key_manager import SSHKeyManager

__all__ = ["Command", "SSHGateway", "serve_connection"]

logger = logging.getLogger(__name__)


def serve_connection(client, addr, host_key, throttle: GatewayThrottle) -> None:
    """Admission check, then the SSH session; always releases the slot."""
    source = addr[0]
    admitted, reason = throttle.admit(source)
    if not admitted:
        log_auth_event("connection-refused", source, reason=reason)
        try:
            client.close()
        except OSError:
            pass
        return
    try:
        handle_client(client, addr, host_key, throttle)
    finally:
        throttle.release(source)


class Command(BaseCommand):
    help = "Run SSH gateway for user workspaces"

    def add_arguments(self, parser):
        parser.add_argument("--host", type=str, default="0.0.0.0")
        parser.add_argument("--port", type=int, default=2200)
        parser.add_argument(
            "--host-key",
            type=str,
            default=None,
            help="Path to SSH host key (default: managed host key)",
        )

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        host_key = self._load_host_key(options["host_key"])
        throttle = GatewayThrottle(ThrottleConfig.from_env())
        self.stdout.write(f"SSH gateway limits: {throttle.config}")

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind((options["host"], options["port"]))
            server_socket.listen(100)
            self.stdout.write(
                self.style.SUCCESS(
                    f"SSH Gateway listening on {options['host']}:{options['port']}"
                )
            )
            while True:
                client, addr = server_socket.accept()
                threading.Thread(
                    target=serve_connection,
                    args=(client, addr, host_key, throttle),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            self.stdout.write("\nShutting down SSH gateway...")
        finally:
            server_socket.close()

    def _load_host_key(self, host_key_path):
        if not host_key_path:
            manager = SSHKeyManager()
            host_key = manager.load_or_generate_host_key()
            self.stdout.write(
                f"Host key fingerprint: {manager.get_host_key_fingerprint(host_key)}"
            )
            return host_key
        path = Path(host_key_path)
        if path.exists():
            return paramiko.RSAKey.from_private_key_file(str(path))
        host_key = paramiko.RSAKey.generate(3072)
        path.parent.mkdir(parents=True, exist_ok=True)
        host_key.write_private_key_file(str(path))
        path.chmod(0o600)
        return host_key


# EOF
