"""
Broker and Direct PTY Spawn — extracted from consumer.py for maintainability.

Provides:
- spawn_via_broker(): spawn PTY through terminal broker (preferred)
- spawn_direct(): spawn PTY directly via pty.fork() (fallback, deprecated)

Both accept a TerminalConsumer instance as their argument.
"""

import asyncio
import logging
import os
import pty
import select
import signal

from .config import USER_DATA_ROOT
from .execution import (
    check_slurm_status,
    exec_slurm_shell,
    select_container,
)
from .workspace import ensure_workspace

logger = logging.getLogger(__name__)


async def _wait_for_slurm_ready(consumer) -> bool:
    """Check SLURM readiness, waiting for daemon recovery if in transient state.

    Sends status messages to consumer's WebSocket.
    Returns True if node is ready, False if it failed.
    Closes the WebSocket with the appropriate code on failure.
    """
    from apps.workspace.console_app.services.terminal_broker.slurm_health import (
        ensure_node_ready,
        get_daemon,
    )

    node_ready, node_err = await asyncio.to_thread(ensure_node_ready)
    if node_ready:
        return True

    if node_err == "recovering":
        # Transient state — wait for daemon to fix it
        logger.info("SLURM node recovering — waiting for daemon (up to 60s)")
        await consumer.send(
            text_data="\x1b[1;33m⏳ Computing environment recovering, please wait...\x1b[0m\r\n"
        )
        daemon = await asyncio.to_thread(get_daemon)
        if daemon is not None:
            node_ready, node_err = await asyncio.to_thread(daemon.wait_for_ready, 60.0)
        if not node_ready:
            logger.error(f"SLURM recovery timed out: {node_err}")
            await consumer.send(
                text_data="\x1b[1;31m❌ Computing environment did not recover in time. Please try again shortly.\x1b[0m\r\n"
            )
            await consumer.close(code=4010)
            return False
        return True

    # Hard failure (node DOWN, SLURM not installed, etc.)
    logger.error(f"SLURM unavailable: {node_err}")
    await consumer.send(
        text_data="\x1b[1;31m❌ Computing resources temporarily unavailable. Please try again shortly.\x1b[0m\r\n"
    )
    await consumer.close(code=4010)
    return False


async def spawn_via_broker(consumer):
    """Spawn PTY via Terminal Broker (preferred method).

    Args:
        consumer: TerminalConsumer instance.
    """
    from .config import SLURM_CONTAINER_PATH, SLURM_USER_DATA_ROOT

    username = consumer.project.owner.username
    project_slug = consumer.project.slug
    user_data_dir = USER_DATA_ROOT / username
    project_dir = user_data_dir / "proj" / project_slug
    # SLURM jobs run on the host, not inside Docker — use host paths
    slurm_user_dir = SLURM_USER_DATA_ROOT / username
    slurm_project_dir = slurm_user_dir / "proj" / project_slug

    await ensure_workspace(user_data_dir, username, project_slug)

    # Auto-generate AI tool configs (user-home defaults + project-level)
    await asyncio.to_thread(
        consumer._setup_ai_configs,
        user_data_dir,
        project_dir,
        consumer.project.name,
        username,
    )

    try:
        container_path = await asyncio.to_thread(
            select_container, user_data_dir, project_dir
        )
    except Exception as e:
        from .execution import ContainerNotFoundError

        if isinstance(e, ContainerNotFoundError):
            await consumer.send(text_data=f"\x1b[1;31m❌ {e}\x1b[0m\r\n")
            await consumer.close(code=4003)
            return
        raise

    # Check SLURM availability; try daemon recovery for transient states
    slurm_available, slurm_status = await asyncio.to_thread(check_slurm_status)
    if not slurm_available:
        if not await _wait_for_slurm_ready(consumer):
            return

    try:
        from apps.workspace.console_app.services.terminal_client import (
            TerminalBrokerClient,
        )

        consumer.broker_client = TerminalBrokerClient()
        if not await consumer.broker_client.connect():
            raise Exception("Failed to connect to broker")

        # Set output callback to forward to WebSocket
        def on_output(data: bytes):
            asyncio.create_task(
                consumer.send(text_data=data.decode("utf-8", errors="replace"))
            )

        consumer.broker_client.set_output_callback(on_output)

        # Set session state callback to forward as JSON control messages
        # Use custom OSC escape so client can distinguish from terminal output
        def on_session_state(msg: dict):
            import json

            payload = json.dumps(msg)
            asyncio.create_task(consumer.send(text_data=f"\x1b]9997;{payload}\x07"))

        consumer.broker_client.set_session_state_callback(on_session_state)

        # Pass host paths for SLURM jobs (not Docker-internal paths)
        session_id = await consumer.broker_client.spawn(
            username=username,
            user_data_dir=slurm_user_dir,
            project_dir=slurm_project_dir,
            container_path=SLURM_CONTAINER_PATH,
            project_slug=project_slug,
            tmux_session=consumer.screen_session,
        )

        if not session_id:
            broker_error = (
                getattr(consumer.broker_client, "_last_spawn_error", None)
                or "Failed to spawn terminal session"
            )
            raise Exception(broker_error)

        logger.info(f"Terminal session started via broker: {session_id}")

    except Exception as e:
        logger.error(f"Broker spawn failed: {e}")
        await consumer.send(
            text_data=f"\x1b[1;31m❌ Failed to start terminal: {e}\x1b[0m\r\n"
        )
        # Use 4010 (transient/retry) for most spawn failures;
        # 4003 only for permanent issues (container not found, auth)
        await consumer.close(code=4010)


async def spawn_direct(consumer):
    """Spawn PTY directly via pty.fork() (fallback, deprecated).

    Args:
        consumer: TerminalConsumer instance.
    """
    username = consumer.project.owner.username
    project_slug = consumer.project.slug
    user_data_dir = USER_DATA_ROOT / username
    project_dir = user_data_dir / "proj" / project_slug

    await ensure_workspace(user_data_dir, username, project_slug)

    # Auto-generate AI tool configs (user-home defaults + project-level)
    await asyncio.to_thread(
        consumer._setup_ai_configs,
        user_data_dir,
        project_dir,
        consumer.project.name,
        username,
    )

    try:
        container_path = await asyncio.to_thread(
            select_container, user_data_dir, project_dir
        )
    except Exception as e:
        from .execution import ContainerNotFoundError

        if isinstance(e, ContainerNotFoundError):
            await consumer.send(text_data=f"\x1b[1;31m❌ {e}\x1b[0m\r\n")
            await consumer.close(code=4003)
            return
        raise

    slurm_available, slurm_status = await asyncio.to_thread(check_slurm_status)
    if not slurm_available:
        logger.error(f"SLURM unavailable ({slurm_status})")
        await consumer.close(code=4003)
        return

    # Block signals during PTY fork to prevent "Interrupted system call"
    old_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK,
        {signal.SIGCHLD, signal.SIGWINCH, signal.SIGINT, signal.SIGTERM},
    )

    try:
        consumer.pid, consumer.fd = pty.fork()

        if consumer.pid == 0:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            try:
                exec_slurm_shell(
                    username,
                    user_data_dir,
                    project_dir,
                    container_path,
                    project_slug,
                    screen_session=consumer.screen_session,
                )
            except Exception as e:
                import sys

                sys.stderr.write(
                    f"\x1b[1;31m❌ Failed to start terminal: {e}\x1b[0m\r\n"
                )
                sys.stderr.flush()
            os._exit(1)
    finally:
        if consumer.pid != 0:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

    if consumer.pid != 0:
        consumer.reader_task = asyncio.create_task(_read_pty_direct(consumer))


async def _read_pty_direct(consumer):
    """Read from PTY and send to WebSocket (direct mode)."""
    try:
        while True:
            r, _, _ = await asyncio.to_thread(select.select, [consumer.fd], [], [], 0.1)
            if r:
                try:
                    data = await asyncio.to_thread(os.read, consumer.fd, 4096)
                    if data:
                        await consumer.send(
                            text_data=data.decode("utf-8", errors="replace")
                        )
                    else:
                        break
                except OSError:
                    break
    except Exception as e:
        logger.error(f"PTY read error: {e}")
    finally:
        await consumer.close()


# EOF
