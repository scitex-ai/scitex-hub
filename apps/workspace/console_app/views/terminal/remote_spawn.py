"""
Remote Terminal Spawn — SSH directly into remote machine for SSHFS projects.

Extracted from consumer.py to keep file sizes within limits.
Used by TerminalConsumer for project_type="remote" projects.

Same pattern as trip_spawn.py but fetches RemoteProjectConfig
instead of TripProjectConfig.
"""

import asyncio
import logging
import os
import pty
import signal

from apps.infra.project_app.ssh_safety import (
    minimal_ssh_env,
    ssh_login_argv,
    validate_remote_path,
)

logger = logging.getLogger(__name__)


async def spawn_remote_ssh(consumer):
    """
    Spawn SSH session to remote machine for SSHFS remote projects.

    Uses pty.fork() + os.execvp("ssh") to give the user a direct
    SSH shell on the remote machine, landed in the project's remote_path.

    Args:
        consumer: TerminalConsumer instance (has self.project, self.send, etc.)
    """
    try:
        remote_config = await asyncio.to_thread(lambda: consumer.project.remote_config)
        credential = await asyncio.to_thread(lambda: remote_config.remote_credential)
    except Exception:
        await consumer.send(
            text_data="\x1b[1;31m❌ Remote configuration not found\x1b[0m\r\n"
        )
        await consumer.close(code=4003)
        return

    ssh_key = credential.private_key_path
    ssh_user = credential.ssh_username
    ssh_host = credential.ssh_host
    ssh_port = str(credential.ssh_port)
    remote_path = remote_config.remote_path

    # SECURITY: remote_path is interpolated UNQUOTED into the remote
    # command below ("cd {remote_path} ..."). Reject shell metacharacters
    # before the fork, and fail CLOSED — never spawn a degraded session.
    try:
        validate_remote_path(remote_path)
    except Exception as exc:
        await consumer.send(
            text_data=f"\x1b[1;31m❌ Invalid remote path: {exc}\x1b[0m\r\n"
        )
        await consumer.close(code=4003)
        return

    logger.info(
        f"Remote SSH: {ssh_user}@{ssh_host}:{remote_path} "
        f"for {consumer.project.owner.username}/{consumer.project.slug}"
    )

    # Block signals during PTY fork
    old_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK,
        {signal.SIGCHLD, signal.SIGWINCH, signal.SIGINT, signal.SIGTERM},
    )

    try:
        consumer.pid, consumer.fd = pty.fork()

        if consumer.pid == 0:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            try:
                # SECURITY: ssh_login_argv inserts a "--" end-of-options
                # terminator before the destination so a leading-dash
                # username/host can never be parsed as an ssh option
                # (arg-injection → host RCE). execvpe with minimal_ssh_env()
                # denies a stray ProxyCommand access to Django secrets.
                os.execvpe(
                    "ssh",
                    ssh_login_argv(
                        ssh_port=ssh_port,
                        ssh_key=ssh_key,
                        ssh_user=ssh_user,
                        ssh_host=ssh_host,
                        remote_command=f"cd {remote_path} 2>/dev/null; exec bash -l",
                    ),
                    minimal_ssh_env(),
                )
            except Exception as e:
                import sys

                sys.stderr.write(f"\x1b[1;31m❌ Remote SSH failed: {e}\x1b[0m\r\n")
                sys.stderr.flush()
            os._exit(1)
    finally:
        if consumer.pid != 0:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

    if consumer.pid != 0:
        consumer.use_broker = False
        consumer.reader_task = asyncio.create_task(consumer._read_pty_direct())


# EOF
