"""
TRIP Terminal Spawn — SSH directly into remote machine.

Extracted from consumer.py to keep file sizes within limits.
Used by TerminalConsumer for project_type="trip" projects.
"""

import asyncio
import logging
import os
import pty
import signal

logger = logging.getLogger(__name__)


async def spawn_trip_ssh(consumer):
    """
    Spawn SSH session to remote machine for TRIP projects.

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
            text_data="\x1b[1;31mRemote configuration not found\x1b[0m\r\n"
        )
        await consumer.close(code=4003)
        return

    ssh_key = credential.private_key_path
    ssh_user = credential.ssh_username
    ssh_host = credential.ssh_host
    ssh_port = str(credential.ssh_port)
    remote_path = remote_config.remote_path

    logger.info(
        f"TRIP SSH: {ssh_user}@{ssh_host}:{remote_path} "
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
                os.execvp(
                    "ssh",
                    [
                        "ssh",
                        "-t",
                        "-p",
                        ssh_port,
                        "-i",
                        ssh_key,
                        "-o",
                        "StrictHostKeyChecking=accept-new",
                        "-o",
                        "ServerAliveInterval=30",
                        f"{ssh_user}@{ssh_host}",
                        f"cd {remote_path} 2>/dev/null; exec bash -l",
                    ],
                )
            except Exception as e:
                import sys

                sys.stderr.write(f"\x1b[1;31m❌ TRIP SSH failed: {e}\x1b[0m\r\n")
                sys.stderr.flush()
            os._exit(1)
    finally:
        if consumer.pid != 0:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

    if consumer.pid != 0:
        consumer.use_broker = False
        consumer.reader_task = asyncio.create_task(consumer._read_pty_direct())


# EOF
