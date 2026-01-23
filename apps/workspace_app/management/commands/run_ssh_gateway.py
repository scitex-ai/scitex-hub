#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 20:40:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/workspace_app/management/commands/run_ssh_gateway.py
# ----------------------------------------
"""
Django management command to run SSH gateway for user workspaces.

Usage:
    python manage.py run_ssh_gateway --port 2200 --host 0.0.0.0
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
from pathlib import Path

import paramiko
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand

from apps.workspace_app.services.container_manager import UserContainerManager
from apps.workspace_app.services.ssh_key_manager import SSHKeyManager

__FILE__ = "./apps/workspace_app/management/commands/run_ssh_gateway.py"
__DIR__ = os.path.dirname(__FILE__)

# Configure logging
logger = logging.getLogger(__name__)


class SSHGateway(paramiko.ServerInterface):
    """
    SSH server interface for authenticating users and managing sessions.
    """

    def __init__(self, username: str | None = None):
        super().__init__()
        self.username = username
        self.user = None
        self.event = threading.Event()

    def check_auth_password(self, username: str, password: str) -> int:
        """
        Authenticate user against Django authentication system.

        Args:
            username: Username to authenticate
            password: Password to check

        Returns:
            paramiko.AUTH_SUCCESSFUL if authenticated, paramiko.AUTH_FAILED otherwise
        """
        logger.info(f"Password authentication attempt for user: {username}")
        try:
            user = authenticate(username=username, password=password)
            if user and user.is_active:
                self.user = user
                self.username = username
                logger.info(f"Password authentication successful for user: {username}")
                return paramiko.AUTH_SUCCESSFUL
        except Exception as e:
            logger.error(f"Password authentication error for user {username}: {e}")

        logger.warning(f"Password authentication failed for user: {username}")
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        """
        Authenticate user against registered SSH public keys.

        Args:
            username: Username to authenticate
            key: Public key provided by client

        Returns:
            paramiko.AUTH_SUCCESSFUL if authenticated, paramiko.AUTH_FAILED otherwise
        """
        logger.info(f"Public key authentication attempt for user: {username}")
        try:
            from django.contrib.auth import get_user_model
            from apps.accounts_app.models import WorkspaceSSHKey
            from apps.accounts_app.utils.ssh_key_validator import SSHKeyValidator
            import base64

            User = get_user_model()

            # Find user by username
            try:
                user = User.objects.get(username=username, is_active=True)
            except User.DoesNotExist:
                logger.warning(f"User not found: {username}")
                return paramiko.AUTH_FAILED

            # Get the public key fingerprint from the provided key
            # Convert paramiko key to OpenSSH format for fingerprint calculation
            key_type = key.get_name()
            key_data = key.get_base64()
            provided_key_str = f"{key_type} {key_data}"

            # Calculate fingerprint of provided key
            provided_fingerprint = SSHKeyValidator.calculate_fingerprint(provided_key_str)

            logger.debug(f"Provided key fingerprint: {provided_fingerprint}")

            # Check if user has a matching public key
            workspace_keys = WorkspaceSSHKey.objects.filter(
                user=user, fingerprint=provided_fingerprint
            )

            if workspace_keys.exists():
                # Update last used timestamp
                workspace_key = workspace_keys.first()
                from django.utils import timezone

                workspace_key.last_used_at = timezone.now()
                workspace_key.save(update_fields=["last_used_at"])

                self.user = user
                self.username = username
                logger.info(
                    f"Public key authentication successful for user: {username} (key: {workspace_key.title})"
                )
                return paramiko.AUTH_SUCCESSFUL

            logger.warning(
                f"Public key authentication failed for user: {username} (no matching key found)"
            )
            return paramiko.AUTH_FAILED

        except Exception as e:
            logger.error(f"Public key authentication error for user {username}: {e}", exc_info=True)
            return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        """
        Return allowed authentication methods.

        Args:
            username: Username requesting authentication

        Returns:
            Comma-separated list of allowed auth methods
        """
        # Only allow public key authentication for security
        return "publickey"

    def check_channel_request(self, kind: str, chanid: int) -> int:
        """
        Check if a channel request should be allowed.

        Args:
            kind: Type of channel being requested
            chanid: Channel ID

        Returns:
            paramiko.OPEN_SUCCEEDED if allowed
        """
        if kind == "session":
            logger.debug(f"Session channel request approved for channel {chanid}")
            return paramiko.OPEN_SUCCEEDED
        logger.warning(f"Channel request denied: {kind}")
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        """
        Handle shell request - spawn user container and forward I/O.

        Args:
            channel: SSH channel for this session

        Returns:
            True if shell request is granted
        """
        logger.info(f"Shell request for user: {self.username}")
        self.event.set()
        return True

    def check_channel_pty_request(
        self,
        channel: paramiko.Channel,
        term: bytes,
        width: int,
        height: int,
        pixelwidth: int,
        pixelheight: int,
        modes: bytes,
    ) -> bool:
        """
        Handle PTY (pseudo-terminal) request.

        Returns:
            True to allow PTY allocation
        """
        logger.debug(f"PTY request: term={term}, size={width}x{height}")
        return True


def forward_io(channel: paramiko.Channel, container_socket):
    """
    Forward I/O bidirectionally between SSH channel and container socket.

    Args:
        channel: SSH channel
        container_socket: Docker container exec socket
    """

    def channel_to_socket():
        """Forward data from SSH channel to container socket."""
        try:
            while True:
                data = channel.recv(1024)
                if not data:
                    break
                container_socket._sock.sendall(data)
        except Exception as e:
            logger.debug(f"Channel to socket forwarding ended: {e}")

    def socket_to_channel():
        """Forward data from container socket to SSH channel."""
        try:
            while True:
                data = container_socket._sock.recv(1024)
                if not data:
                    break
                channel.send(data)
        except Exception as e:
            logger.debug(f"Socket to channel forwarding ended: {e}")

    # Start bidirectional forwarding
    t1 = threading.Thread(target=channel_to_socket, daemon=True)
    t2 = threading.Thread(target=socket_to_channel, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def handle_client(client: socket.socket, addr: tuple, host_key: paramiko.RSAKey):
    """
    Handle a single SSH client connection.

    Args:
        client: Client socket
        addr: Client address tuple
        host_key: SSH host key for the server
    """
    logger.info(f"New connection from {addr[0]}:{addr[1]}")

    try:
        # Create SSH transport
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)
        transport.set_subsystem_handler("sftp", paramiko.SFTPServer)

        # Create server interface
        server = SSHGateway()
        transport.start_server(server=server)

        # Wait for authentication
        channel = transport.accept(20)
        if channel is None:
            logger.warning(f"No channel established for {addr[0]}")
            return

        # Wait for shell request
        server.event.wait(10)
        if not server.user:
            logger.warning(f"No authenticated user for {addr[0]}")
            channel.close()
            return

        logger.info(f"Shell session starting for user: {server.username}")

        # Get or create user container
        manager = UserContainerManager()
        container = manager.get_or_create_container(server.user)

        if not container:
            channel.send(b"Error: Failed to create workspace container\r\n")
            channel.close()
            return

        # Send welcome message
        welcome_msg = (
            f"\r\n"
            f"Welcome to SciTeX Cloud Workspace, {server.username}!\r\n"
            f"Container: {container.name}\r\n"
            f"\r\n"
        )
        channel.send(welcome_msg.encode())

        # Execute bash in container
        exec_instance = container.exec_run(
            ["/bin/bash"],
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True,
            socket=True,
        )

        # Forward I/O between SSH channel and container
        forward_io(channel, exec_instance.output)

        logger.info(f"Session ended for user: {server.username}")

    except Exception as e:
        logger.error(f"Error handling client {addr[0]}: {e}", exc_info=True)
    finally:
        try:
            client.close()
        except Exception:
            pass


class Command(BaseCommand):
    """Django management command to run SSH gateway."""

    help = "Run SSH gateway for user workspaces"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            type=str,
            default="0.0.0.0",
            help="Host to bind SSH server (default: 0.0.0.0)",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=2200,
            help="Port to listen on (default: 2200)",
        )
        parser.add_argument(
            "--host-key",
            type=str,
            default=None,
            help="Path to SSH host key (default: auto-generate)",
        )

    def handle(self, *args, **options):
        """Run the SSH gateway server."""
        host = options["host"]
        port = options["port"]
        host_key_path = options["host_key"]

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

        # Load or generate host key
        key_manager = SSHKeyManager()
        if host_key_path:
            # Use custom key path if provided
            if Path(host_key_path).exists():
                self.stdout.write(f"Loading host key from: {host_key_path}")
                host_key = paramiko.RSAKey.from_private_key_file(host_key_path)
            else:
                self.stdout.write("Generating ephemeral host key...")
                host_key = paramiko.RSAKey.generate(2048)
                host_key_path = Path(host_key_path)
                host_key_path.parent.mkdir(parents=True, exist_ok=True)
                host_key.write_private_key_file(str(host_key_path))
                self.stdout.write(f"Host key saved to: {host_key_path}")
        else:
            # Use key manager
            host_key = key_manager.load_or_generate_host_key()
            fingerprint = key_manager.get_host_key_fingerprint(host_key)
            self.stdout.write(f"Host key fingerprint: {fingerprint}")

        # Create server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((host, port))
            server_socket.listen(100)
            self.stdout.write(
                self.style.SUCCESS(f"SSH Gateway listening on {host}:{port}")
            )
            self.stdout.write("Press Ctrl+C to stop")

            # Accept connections
            while True:
                client, addr = server_socket.accept()
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client, addr, host_key),
                    daemon=True,
                )
                client_thread.start()

        except KeyboardInterrupt:
            self.stdout.write("\nShutting down SSH gateway...")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
            raise
        finally:
            server_socket.close()
            self.stdout.write("SSH Gateway stopped")


# EOF
