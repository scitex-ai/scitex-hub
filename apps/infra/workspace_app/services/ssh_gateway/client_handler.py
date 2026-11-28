"""SSH client connection handler.

admission (throttle) -> key auth -> spend gate -> broker spawn -> I/O.

The shell is spawned by the Terminal Broker exactly like the web terminal:
inside the user's SLURM allocation under Apptainer, with the environment the
broker builds for user processes. The gateway never starts a shell itself.
"""

from __future__ import annotations

import asyncio
import logging
import socket

import paramiko

from .broker_client import SyncBrokerClient
from .io_forwarding import forward_io_broker
from .server_interface import SSHGateway, log_auth_event
from .throttle import GatewayThrottle

logger = logging.getLogger(__name__)

BANNER_TIMEOUT_SECONDS = 15
AUTH_TIMEOUT_SECONDS = 30
CHANNEL_TIMEOUT_SECONDS = 20


def _refuse(channel: paramiko.Channel, message: str) -> None:
    try:
        channel.send(f"\x1b[1;31m{message}\x1b[0m\r\n".encode())
    finally:
        channel.close()


def handle_client(
    client: socket.socket,
    addr: tuple,
    host_key: paramiko.PKey,
    throttle: GatewayThrottle,
):
    """Handle one TCP connection. ``throttle.admit`` was already granted."""
    source = addr[0]
    server = SSHGateway(source=source, throttle=throttle)
    transport = None
    authenticated = False
    try:
        transport = paramiko.Transport(client)
        transport.banner_timeout = BANNER_TIMEOUT_SECONDS
        transport.auth_timeout = AUTH_TIMEOUT_SECONDS
        transport.add_server_key(host_key)
        transport.start_server(server=server)

        channel = transport.accept(CHANNEL_TIMEOUT_SECONDS)
        authenticated = bool(
            transport.is_authenticated()
            and server.user is not None
            and transport.get_username() == server.username
        )
        if channel is None or not authenticated:
            if channel is not None:
                channel.close()
            return

        throttle.record_success(source, server.username)
        log_auth_event("login", source, server.username, key=server.key_title)

        server.event.wait(10)
        if not server.event.is_set():
            _refuse(channel, "Only interactive shells are supported.")
            return
        _start_shell_session(channel, server)
        log_auth_event("logout", source, server.username)

    except paramiko.SSHException as e:
        if "Error reading SSH protocol banner" in str(e):
            logger.debug("No SSH handshake from %s", source)
        else:
            logger.warning("SSH error for %s: %s", source, e)
    except Exception:
        logger.exception("Error handling %s", source)
    finally:
        if not authenticated and server.attempted_username is not None:
            for key in throttle.record_failed_connection(
                source, server.attempted_username
            ):
                log_auth_event("ban", source, server.attempted_username, key=key)
        if transport is not None:
            transport.close()
        try:
            client.close()
        except Exception:
            pass


def _start_shell_session(channel: paramiko.Channel, server: SSHGateway) -> None:
    """Spawn the user's shell through the Terminal Broker and forward I/O."""
    from apps.infra.project_app.models import Project
    from apps.infra.spend_app.services import gate
    from apps.infra.spend_app.services.enforcement import require_terminal
    from apps.workspace.console_app.views.terminal._runtime_preflight import (
        TerminalConfigurationError,
        validate_terminal_host_paths,
    )
    from apps.workspace.console_app.views.terminal.config import (
        SLURM_CONTAINER_PATH,
        SLURM_USER_DATA_ROOT,
        USER_DATA_ROOT,
    )
    from apps.workspace.console_app.views.terminal.execution import (
        ContainerNotFoundError,
        check_slurm_status,
        select_container,
    )
    from apps.workspace.console_app.views.terminal.workspace import ensure_workspace

    user = server.user
    username = server.username

    try:
        require_terminal(user)
    except gate.Refused as e:
        _refuse(channel, e.message)
        return

    project = (
        Project.objects.filter(owner=user, is_home=True).first()
        or Project.objects.filter(owner=user).first()
    )
    if project is None:
        _refuse(channel, "No projects found. Create one in the Hub first.")
        return

    user_data_dir = USER_DATA_ROOT / username
    project_dir = user_data_dir / "proj" / project.slug
    try:
        validate_terminal_host_paths(SLURM_CONTAINER_PATH, str(SLURM_USER_DATA_ROOT))
        asyncio.run(ensure_workspace(user_data_dir, username, project.slug))
        select_container(user_data_dir, project_dir)
    except (TerminalConfigurationError, ContainerNotFoundError) as e:
        logger.error("Shell setup refused for %s: %s", username, e)
        _refuse(channel, "Your workspace is not available right now.")
        return
    except Exception:
        logger.exception("Workspace setup failed for %s", username)
        _refuse(channel, "Workspace setup failed.")
        return

    slurm_available, slurm_status = check_slurm_status()
    if not slurm_available:
        logger.warning("SLURM unavailable for SSH login: %s", slurm_status)
        _refuse(channel, "Computing resources are temporarily unavailable.")
        return

    broker_client = SyncBrokerClient()
    try:
        broker_client.connect()
    except OSError as e:
        logger.error("Cannot connect to Terminal Broker: %s", e)
        _refuse(channel, "Terminal service not available.")
        return

    slurm_user_dir = SLURM_USER_DATA_ROOT / username
    resp = broker_client.spawn(
        username=username,
        user_data_dir=str(slurm_user_dir),
        project_dir=str(slurm_user_dir / "proj" / project.slug),
        container_path=SLURM_CONTAINER_PATH,
        project_slug=project.slug,
        screen_session=f"ssh-{id(channel) % 10000}",
    )
    if resp.get("status") != "ok":
        logger.error("Broker spawn failed for %s: %s", username, resp.get("error"))
        broker_client.close()
        _refuse(channel, "Failed to start your terminal.")
        return

    broker_client.resize(server.pty_height, server.pty_width)
    server._broker_client = broker_client
    channel.send(
        f"\r\nWelcome to SciTeX Hub, {username}!\r\nProject: {project.slug}\r\n\r\n".encode()
    )
    try:
        forward_io_broker(channel, broker_client)
    finally:
        broker_client.close()


# EOF
