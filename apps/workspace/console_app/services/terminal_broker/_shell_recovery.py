"""Shell exit / respawn / allocation-recovery callbacks (shared mode).

Extracted from ``_handlers_shared.py`` (512-line cap). These functions
are mutually recursive with each other (exit callback schedules respawn
and recovery, recovery re-installs the exit callback) so they live
together; ``_handlers_shared`` re-exports them for broker.py and tests.
"""

import logging
import socket
import threading
import time

from ._alloc_cooldown import _get_cooldown, _hard_fail_info
from ._handler_utils import respawn_pty, send_state
from .allocation import Allocation
from .session import SessionState
from .shell import MAX_RESPAWNS as SHELL_MAX_RESPAWNS

logger = logging.getLogger(__name__)


def _make_shell_exit_cb(broker, client: socket.socket):
    """Create exit callback for shell auto-respawn."""

    def on_exit(pty_id):
        with broker.lock:
            shell = broker.shells.get(pty_id)
        if not shell or shell.state != SessionState.RUNNING:
            return

        shell.cleanup_fd()
        shell.state = SessionState.EXITED
        send_state(broker, client, pty_id, "exited")

        # Check if allocation is still alive
        with broker.lock:
            alloc = broker.allocations.get(shell.allocation_id)
        if alloc and not alloc.check_alive():
            reason = alloc.get_failure_reason()
            shell.state = SessionState.DEAD
            alloc.decrement_shells()
            send_state(
                broker,
                client,
                pty_id,
                "allocation_dead",
                extra={"reason": reason},
            )
            # Attempt auto-recovery after a short delay
            timer = threading.Timer(
                2.0,
                _auto_recover_allocation,
                args=(broker, pty_id, shell, alloc, client),
            )
            timer.daemon = True
            timer.start()
            return

        # Intentional exit (ran >10s): reset counter so user never gets stuck
        if shell.last_spawn_time and (time.time() - shell.last_spawn_time > 10):
            shell.spawn_count = 0

        if shell.spawn_count < SHELL_MAX_RESPAWNS:
            backoff = (
                0.5 if shell.spawn_count == 0 else min(2 ** (shell.spawn_count - 1), 4)
            )
            timer = threading.Timer(
                backoff, _respawn_shell, args=(broker, pty_id, client)
            )
            timer.daemon = True
            timer.start()
        else:
            shell.state = SessionState.DEAD
            if alloc:
                alloc.decrement_shells()

    return on_exit


def _respawn_shell(broker, pty_id: str, client: socket.socket):
    """Respawn a shell after exit."""
    with broker.lock:
        shell = broker.shells.get(pty_id)
    if not shell or shell.state == SessionState.DEAD:
        return

    def on_fail():
        with broker.lock:
            alloc = broker.allocations.get(shell.allocation_id)
        if alloc:
            alloc.decrement_shells()

    respawn_pty(broker, shell, client, _make_shell_exit_cb, on_fail=on_fail)


def _auto_recover_allocation(
    broker,
    pty_id: str,
    shell,
    old_alloc,
    client: socket.socket,
):
    """Attempt to start a new allocation and respawn the shell inside it."""
    alloc_key = (shell.username,)

    # Check cooldown (hard failures only)
    last_info = _hard_fail_info.get(alloc_key)
    if last_info and time.time() - last_info[0] < _get_cooldown(last_info[2]):
        send_state(
            broker,
            client,
            pty_id,
            "dead",
            extra={"reason": "Please wait a moment before retrying"},
        )
        return

    send_state(broker, client, pty_id, "allocation_recovering")

    new_alloc = Allocation(
        username=old_alloc.username,
        project_slug=old_alloc.project_slug,
        container_path=old_alloc.container_path,
        host_user_dir=old_alloc.host_user_dir,
        host_project_dir=old_alloc.host_project_dir,
        time_limit_seconds=old_alloc.time_limit_seconds,
    )

    # Check squeue for existing jobs before submitting new sbatch
    existing_jobs = Allocation.find_existing_jobs(old_alloc.username)
    if existing_jobs:
        started = new_alloc.attach_to_existing(existing_jobs[0])
    else:
        started = new_alloc.start()

    if not started:
        reason = new_alloc.last_error or "Could not restart environment"
        existing = _hard_fail_info.get(alloc_key)
        fail_count = (existing[2] + 1) if existing else 0
        _hard_fail_info[alloc_key] = (time.time(), reason, fail_count)
        send_state(
            broker,
            client,
            pty_id,
            "dead",
            extra={"reason": reason},
        )
        return

    with broker.lock:
        broker.allocations[new_alloc.allocation_id] = new_alloc
        broker.alloc_index[alloc_key] = new_alloc.allocation_id
        _hard_fail_info.pop(alloc_key, None)
        shell.allocation_id = new_alloc.allocation_id
        shell.command = new_alloc.get_shell_command(project_slug=old_alloc.project_slug)
        shell.spawn_count = 0

    def on_fail():
        new_alloc.decrement_shells()

    success = respawn_pty(broker, shell, client, _make_shell_exit_cb, on_fail=on_fail)
    if success:
        new_alloc.increment_shells()
        logger.info(
            f"Shell {pty_id[:8]}: auto-recovered into allocation {new_alloc.allocation_id[:8]}"
        )
    else:
        logger.error(f"Shell {pty_id[:8]}: auto-recovery respawn failed")


def handle_restart_shared(broker, msg: dict, client: socket.socket) -> dict:
    """Restart a shell: respawn if allocation alive, recover if dead."""
    session_id = msg.get("session_id", "")
    with broker.lock:
        shell = broker.shells.get(session_id)

    if not shell:
        return {"status": "error", "error": "Shell not found"}

    with broker.lock:
        alloc = broker.allocations.get(shell.allocation_id)

    if alloc and alloc.check_alive():
        # Allocation is alive — just respawn the shell
        def on_fail():
            if alloc:
                alloc.decrement_shells()

        respawn_pty(broker, shell, client, _make_shell_exit_cb, on_fail=on_fail)
        return {"status": "ok", "session_id": session_id}

    # Allocation is dead — trigger recovery
    if alloc:
        threading.Timer(
            0,
            _auto_recover_allocation,
            args=(broker, session_id, shell, alloc, client),
        ).start()
    return {"status": "ok", "session_id": session_id}


# EOF
