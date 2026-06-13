"""Shared allocation handlers for the terminal broker.

These functions implement the sbatch + srun --overlap spawn pattern.
They receive the broker instance as the first argument to access
shared state (allocations, shells, indexes).
"""

import base64
import logging
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

from apps.workspace.console_app.views.terminal.config import SLURM_TIME_LIMIT_SECONDS

from ._handler_utils import respawn_pty, send_state
from .allocation import Allocation, AllocationState
from .session import SessionState
from .shell import MAX_RESPAWNS as SHELL_MAX_RESPAWNS
from .shell import Shell

logger = logging.getLogger(__name__)

# Cooldown: don't retry allocation after hard failures (node DOWN, not installed)
# Escalates: 30s -> 60s -> 120s -> 240s (capped at 4 min)
_HARD_FAIL_COOLDOWN_BASE = 30  # seconds
_HARD_FAIL_COOLDOWN_MAX = 240  # seconds
# alloc_key -> (timestamp, reason, fail_count)
_hard_fail_info: dict[tuple, tuple[float, str, int]] = {}


def _get_cooldown(fail_count: int) -> int:
    """Return escalating cooldown in seconds based on consecutive failure count."""
    return min(_HARD_FAIL_COOLDOWN_BASE * (2**fail_count), _HARD_FAIL_COOLDOWN_MAX)


def _wait_for_node_or_fail(broker, client, alloc_key) -> tuple[bool, str]:
    """Wait for node to be ready, using daemon if available.

    Returns (ready, error). For transient issues (RECOVERING), waits up to 60s.
    For hard failures (DOWN, not installed), returns immediately.
    """
    from .slurm_health import ensure_node_ready, get_daemon

    ready, err = ensure_node_ready()
    if ready:
        return True, ""

    if err == "recovering":
        # Node is being recovered by daemon — wait for it
        send_state(broker, client, "", "allocation_starting")
        daemon = get_daemon()
        if daemon:
            logger.info("Node recovering — waiting for daemon to fix it")
            ready, err = daemon.wait_for_ready(timeout=60.0)
            if ready:
                return True, ""
        return False, err or "Computing environment did not become ready in time"

    # Hard failure — apply escalating cooldown
    existing = _hard_fail_info.get(alloc_key)
    fail_count = (existing[2] + 1) if existing else 0
    _hard_fail_info[alloc_key] = (time.time(), err, fail_count)
    return False, err


def handle_spawn_shared(broker, msg: dict, client: socket.socket) -> dict:
    """Shared spawn: one sbatch per (user, project), shells via srun --overlap."""
    username = msg["username"]
    project_slug = msg["project_slug"]
    screen_session = msg.get("screen_session", "scitex-0")
    shell_key = (username, screen_session)
    alloc_key = (username,)  # 1 allocation per user, not per project

    # 1. Check for existing shell to reattach
    with broker.lock:
        existing_shell_id = broker.shell_index.get(shell_key)
        existing_shell = (
            broker.shells.get(existing_shell_id) if existing_shell_id else None
        )
        if (
            existing_shell
            and existing_shell.state == SessionState.RUNNING
            and existing_shell.fd is not None
        ):
            # Replay scrollback before starting live output
            scrollback = existing_shell.get_scrollback()
            if scrollback:
                broker._send_message(
                    client,
                    {
                        "action": "output",
                        "session_id": existing_shell_id,
                        "data": base64.b64encode(scrollback).decode("ascii"),
                    },
                )
            existing_shell.client_socket = client
            existing_shell.on_exit_callback = _make_shell_exit_cb(broker, client)
            existing_shell.start_reader(broker._make_output_callback(client))
            # cd to project dir if project changed
            if existing_shell.last_project_slug != project_slug:
                from scitex_hub._utils._project_nav import build_switch_command

                cd_cmd = build_switch_command(username, project_slug)
                existing_shell.write(f"{cd_cmd}\n".encode())
                existing_shell.last_project_slug = project_slug
            logger.info(f"Shell {existing_shell_id[:8]}: reattaching")
            return {"status": "ok", "session_id": existing_shell_id}

    # 2. Get or create allocation
    with broker.lock:
        alloc_id = broker.alloc_index.get(alloc_key)
        alloc = broker.allocations.get(alloc_id) if alloc_id else None

    if not alloc or alloc.state == AllocationState.DEAD:
        # Cooldown: only for hard failures (node DOWN, SLURM not installed)
        last_info = _hard_fail_info.get(alloc_key)
        if last_info:
            last_fail, last_reason, fail_count = last_info
            cooldown = _get_cooldown(fail_count)
            elapsed = time.time() - last_fail
            if elapsed < cooldown:
                wait = int(cooldown - elapsed)
                return {
                    "status": "error",
                    "error": f"{last_reason} (retrying in {wait}s)",
                }

        # Wait for node to be ready (waits for daemon recovery if needed)
        node_ready, node_err = _wait_for_node_or_fail(broker, client, alloc_key)
        if not node_ready:
            return {
                "status": "error",
                "error": node_err,
                "transient": True,
            }

        alloc = Allocation(
            username=username,
            project_slug=project_slug,
            container_path=msg["container_path"],
            host_user_dir=Path(msg["user_data_dir"]),
            host_project_dir=Path(msg["project_dir"]),
            time_limit_seconds=SLURM_TIME_LIMIT_SECONDS,
        )
        send_state(broker, client, "", "allocation_starting")

        # Check squeue for existing jobs before submitting new sbatch
        existing_jobs = Allocation.find_existing_jobs(username)
        if len(existing_jobs) > 1:
            logger.error(
                f"Multiple SLURM terminal jobs for {username}: {existing_jobs}. "
                f"This should not happen — cancelling extras."
            )
            # Cancel all but the first, then attach to the first
            for extra_jid in existing_jobs[1:]:
                try:
                    subprocess.run(
                        ["scancel", extra_jid], capture_output=True, timeout=5
                    )
                except Exception:
                    pass

        if existing_jobs:
            # Attach to existing job instead of creating duplicate
            logger.info(
                f"Found existing SLURM job {existing_jobs[0]} for {username}, attaching"
            )
            if not alloc.attach_to_existing(existing_jobs[0]):
                reason = alloc.last_error or "Failed to attach to existing environment"
                existing = _hard_fail_info.get(alloc_key)
                fail_count = (existing[2] + 1) if existing else 0
                _hard_fail_info[alloc_key] = (time.time(), reason, fail_count)
                return {"status": "error", "error": reason}
        elif not alloc.start():
            reason = alloc.last_error or "Failed to start computing environment"
            existing = _hard_fail_info.get(alloc_key)
            fail_count = (existing[2] + 1) if existing else 0
            _hard_fail_info[alloc_key] = (time.time(), reason, fail_count)
            return {"status": "error", "error": reason}

        with broker.lock:
            broker.allocations[alloc.allocation_id] = alloc
            broker.alloc_index[alloc_key] = alloc.allocation_id
            _hard_fail_info.pop(alloc_key, None)  # clear cooldown on success

    elif alloc.state == AllocationState.STARTING:
        # Another tab is already starting this allocation — wait
        deadline = time.time() + 60
        while time.time() < deadline and alloc.state == AllocationState.STARTING:
            time.sleep(1)
        if alloc.state != AllocationState.READY:
            return {
                "status": "error",
                "error": "Environment startup timed out, please retry",
            }

    # 3. Spawn shell inside allocation. Resolve broker-visible project_dir so
    # BasePTY chdirs to the project root before fork (falls back to HOME → /tmp
    # if the path is missing, e.g. first-time user — no silent swallow).
    from apps.workspace.console_app.views.terminal.config import USER_DATA_ROOT

    broker_project_dir = USER_DATA_ROOT / username / "proj" / project_slug
    shell_id = str(uuid.uuid4())
    shell = Shell(
        shell_id=shell_id,
        allocation_id=alloc.allocation_id,
        username=username,
        screen_session=screen_session,
        command=alloc.get_shell_command(project_slug=project_slug),
        project_dir=broker_project_dir,
    )

    if not shell.spawn():
        detail = getattr(shell, "last_error", "")
        error_msg = (
            f"Failed to open terminal: {detail}"
            if detail
            else "Failed to open terminal"
        )
        logger.error(f"Shell {shell_id[:8]}: spawn failed — {detail!r}")
        return {"status": "error", "error": error_msg}

    shell.client_socket = client
    shell.last_project_slug = project_slug
    shell.on_exit_callback = _make_shell_exit_cb(broker, client)
    shell.start_reader(broker._make_output_callback(client))
    alloc.increment_shells()

    # Dismiss the "Starting computing environment..." spinner on the frontend
    send_state(broker, client, shell_id, "running")

    # Inject cd and MOTD after shell initializes
    container_dir = f"/home/{username}/proj/{project_slug}"

    from apps.workspace.console_app.views.terminal.config import SHOW_MOTD

    def _inject_init():
        time.sleep(0.5)
        # cd is handled by _build_shell_command via SCITEX_PROJECT env var;
        # only clear the screen here for clean initial appearance
        shell.write(b"clear\n")
        if not SHOW_MOTD:
            return
        time.sleep(0.8)
        # Send MOTD directly to client (not through shell)
        motd = (
            "\r\n"
            "\x1b[1;36m  Welcome to SciTeX Hub\x1b[0m\r\n"
            "\r\n"
            "\x1b[0;36m  1. Type \x1b[1mclaude\x1b[0;36m, "
            "\x1b[1mcodex\x1b[0;36m, or "
            "\x1b[1mgemini\x1b[0;36m and hit Enter\x1b[0m\r\n"
            "\x1b[0;36m  2. Subscribe to and sign in to "
            "their services\x1b[0m\r\n"
            "\x1b[0;36m  3. Ask agents anything about research, "
            "including SciTeX usage and app creation\x1b[0m\r\n"
            "\r\n"
            "\x1b[0;90m  To hide this message: "
            "set SCITEX_HUB_SHOW_MOTD=false in config\x1b[0m"
            "\r\n\r\n"
        ).encode()
        broker._send_message(
            client,
            {
                "action": "output",
                "session_id": shell_id,
                "data": base64.b64encode(motd).decode("ascii"),
            },
        )

    init_thread = threading.Thread(target=_inject_init, daemon=True)
    init_thread.start()

    with broker.lock:
        broker.shells[shell_id] = shell
        broker.shell_index[shell_key] = shell_id

    return {"status": "ok", "session_id": shell_id}


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


def handle_stop_allocation(broker, msg: dict) -> dict:
    """Stop a shared allocation and all its shells."""
    username = msg.get("username", "")
    project_slug = msg.get("project_slug", "")
    alloc_key = (username,)  # matches per-user key in handle_spawn_shared

    with broker.lock:
        alloc_id = broker.alloc_index.pop(alloc_key, None)
        alloc = broker.allocations.pop(alloc_id, None) if alloc_id else None
        if alloc:
            dead_shells = [
                sid
                for sid, s in broker.shells.items()
                if s.allocation_id == alloc.allocation_id
            ]
            for sid in dead_shells:
                shell = broker.shells.pop(sid, None)
                if shell:
                    shell.close()
            broker.shell_index = {
                k: v for k, v in broker.shell_index.items() if v not in dead_shells
            }

    if alloc:
        alloc.stop()
        return {"status": "ok"}
    return {"status": "error", "error": "No active session found"}


def stop_all_allocations(broker):
    """Stop all allocations and shells during broker shutdown."""
    with broker.lock:
        for shell in list(broker.shells.values()):
            shell.close()
        broker.shells.clear()
        broker.shell_index.clear()
        allocs = list(broker.allocations.values())
        broker.allocations.clear()
        broker.alloc_index.clear()

    for alloc in allocs:
        alloc.stop()


# EOF
