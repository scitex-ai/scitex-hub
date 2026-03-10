"""SSH client connection handler.

Orchestrates auth → workspace setup → broker spawn → I/O forwarding.
"""

import asyncio
import logging
import socket

import paramiko

from .broker_client import SyncBrokerClient
from .io_forwarding import forward_io_broker
from .key_registration import handle_password_session
from .server_interface import SSHGateway

logger = logging.getLogger(__name__)


def handle_client(client: socket.socket, addr: tuple, host_key: paramiko.RSAKey):
    """Handle a single SSH client connection."""
    logger.info(f"New connection from {addr[0]}:{addr[1]}")

    try:
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)

        server = SSHGateway()
        transport.start_server(server=server)

        channel = transport.accept(20)
        if channel is None:
            logger.warning(f"No channel established for {addr[0]}")
            return

        server.event.wait(10)
        if not server.user:
            logger.warning(f"No authenticated user for {addr[0]}")
            channel.close()
            return

        # Password-only auth → key registration, no shell
        if server.auth_method == "password":
            logger.info(f"Password session for {server.username} — key registration")
            handle_password_session(channel, server.user)
            return

        # Public key auth → full shell via Terminal Broker
        _start_shell_session(channel, server)

    except paramiko.SSHException as e:
        error_msg = str(e)
        if "Error reading SSH protocol banner" in error_msg:
            if addr[0] == "127.0.0.1":
                logger.debug(f"Health check probe from {addr[0]}")
            else:
                logger.warning(f"No SSH handshake from {addr[0]}")
        else:
            logger.error(f"SSH error for {addr[0]}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error handling {addr[0]}: {e}", exc_info=True)
    finally:
        try:
            client.close()
        except Exception:
            pass


def _start_shell_session(channel: paramiko.Channel, server: SSHGateway):
    """Set up workspace and start a shell session via Terminal Broker."""
    from apps.workspace.console_app.views.terminal.config import USER_DATA_ROOT
    from apps.workspace.console_app.views.terminal.execution import (
        ContainerNotFoundError,
        select_container,
    )
    from apps.workspace.console_app.views.terminal.workspace import ensure_workspace
    from apps.infra.project_app.models import Project

    username = server.username
    logger.info(f"Shell session starting for user: {username}")

    # Look up home project
    project = (
        Project.objects.select_related("owner")
        .filter(owner=server.user, is_home=True)
        .first()
    )
    if not project:
        project = (
            Project.objects.select_related("owner").filter(owner=server.user).first()
        )
    if not project:
        channel.send(b"\x1b[1;31mNo projects found. Create one first.\x1b[0m\r\n")
        channel.close()
        return

    # Prepare paths
    user_data_dir = USER_DATA_ROOT / username
    project_dir = user_data_dir / "proj" / project.slug

    # Ensure workspace (sync wrapper)
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ensure_workspace(user_data_dir, username, project.slug))
        loop.close()
    except Exception as e:
        logger.error(f"Workspace setup failed: {e}")
        channel.send(f"\x1b[1;31mWorkspace setup failed: {e}\x1b[0m\r\n".encode())
        channel.close()
        return

    # Select container
    try:
        container_path = select_container(user_data_dir, project_dir)
    except ContainerNotFoundError as e:
        channel.send(f"\x1b[1;31m{e}\x1b[0m\r\n".encode())
        channel.close()
        return

    # Connect to Terminal Broker
    broker_client = SyncBrokerClient()
    try:
        broker_client.connect()
    except (ConnectionRefusedError, FileNotFoundError) as e:
        logger.error(f"Cannot connect to Terminal Broker: {e}")
        channel.send(
            b"\x1b[1;31mTerminal Broker not available. "
            b"Contact administrator.\x1b[0m\r\n"
        )
        channel.close()
        return

    resp = broker_client.spawn(
        username=username,
        user_data_dir=str(user_data_dir),
        project_dir=str(project_dir),
        container_path=container_path,
        project_slug=project.slug,
        screen_session=f"ssh-{id(channel) % 10000}",
    )

    if resp.get("status") != "ok":
        error = resp.get("error", "Unknown error")
        logger.error(f"Broker spawn failed: {error}")
        channel.send(f"\x1b[1;31mFailed to start terminal: {error}\x1b[0m\r\n".encode())
        broker_client.close()
        channel.close()
        return

    # Initial terminal size
    broker_client.resize(server.pty_height, server.pty_width)

    # Enable resize forwarding from SSHGateway
    server._broker_client = broker_client

    channel.send(
        f"\r\nWelcome to SciTeX Cloud, {username}!\r\n"
        f"Project: {project.slug}\r\n\r\n".encode()
    )

    forward_io_broker(channel, broker_client)
    broker_client.close()
    logger.info(f"Session ended for user: {username}")


# EOF
