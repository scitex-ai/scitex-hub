"""SLURM node health checks and proactive recovery.

Provides:
- NodeHealthDaemon: background thread that proactively detects and fixes stuck nodes
- ensure_node_ready(): fast non-blocking check (no recovery) for spawn path
- wait_for_node_ready(): blocks until node is healthy or timeout
- cleanup_stale_jobs(): startup cleanup
- find_existing_jobs(): query existing user jobs
"""

import enum
import logging
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

# Job name prefix for terminal allocations
JOB_NAME_PREFIX = "scitex-hub-terminal"

# Healthy SLURM node states
_HEALTHY_STATES = frozenset(("idle", "mixed", "allocated", "alloc"))
# Recoverable SLURM node states
_RECOVERABLE_STATES = frozenset(("completing", "comp", "drained", "drain", "draining"))
# Permanently down states
_DOWN_STATES = frozenset(("down", "down*", "error"))


class NodeState(enum.Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    RECOVERING = "recovering"
    DOWN = "down"


class NodeHealthDaemon:
    """Background thread that proactively monitors and recovers SLURM nodes.

    Spawn path calls wait_for_ready() instead of doing synchronous recovery.
    """

    # How often to check node health
    CHECK_INTERVAL = 10  # seconds
    # How long to try recovering a node before giving up
    RECOVERY_TIMEOUT = 30  # seconds
    # After giving up, wait before retrying recovery
    RETRY_COOLDOWN = 15  # seconds

    def __init__(self):
        self.state = NodeState.UNKNOWN
        self.node_ready = threading.Event()
        self.last_error = ""
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        """Start the daemon thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("NodeHealthDaemon started")

    def stop(self):
        """Stop the daemon thread."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("NodeHealthDaemon stopped")

    def wait_for_ready(self, timeout: float = 60.0) -> tuple[bool, str]:
        """Block until node is healthy or timeout.

        Returns (ready, error_message).
        Used by spawn path instead of synchronous recovery.
        """
        if self.node_ready.is_set():
            return True, ""

        logger.info(f"Waiting up to {timeout}s for node to become ready")
        if self.node_ready.wait(timeout=timeout):
            return True, ""

        with self._lock:
            return False, self.last_error or "Node did not become ready in time"

    def _run(self):
        """Main daemon loop."""
        # Initial check immediately
        self._check_and_recover()

        while not self._stop.is_set():
            self._stop.wait(self.CHECK_INTERVAL)
            if self._stop.is_set():
                break
            self._check_and_recover()

    def _check_and_recover(self):
        """Check node state and recover if needed."""
        try:
            node_name, raw_state = _get_node_state()
        except Exception as e:
            with self._lock:
                self.state = NodeState.DOWN
                self.last_error = str(e)
            self.node_ready.clear()
            return

        if node_name is None:
            with self._lock:
                self.state = NodeState.DOWN
                self.last_error = raw_state  # error message
            self.node_ready.clear()
            return

        if raw_state in _HEALTHY_STATES:
            with self._lock:
                self.state = NodeState.HEALTHY
                self.last_error = ""
            self.node_ready.set()
            return

        if raw_state in _DOWN_STATES:
            with self._lock:
                self.state = NodeState.DOWN
                self.last_error = (
                    f"SLURM node {node_name} is {raw_state} — compute unavailable"
                )
            self.node_ready.clear()
            return

        if raw_state in _RECOVERABLE_STATES:
            with self._lock:
                self.state = NodeState.RECOVERING
                self.last_error = ""
            self.node_ready.clear()

            logger.warning(
                f"SLURM node {node_name} stuck in {raw_state}, recovering..."
            )
            recovered = self._do_recovery(node_name)
            if recovered:
                with self._lock:
                    self.state = NodeState.HEALTHY
                    self.last_error = ""
                self.node_ready.set()
                logger.info(f"SLURM node {node_name} recovered successfully")
            else:
                with self._lock:
                    self.state = NodeState.DOWN
                    # Keep last_error from _do_recovery
                logger.error(
                    f"SLURM node {node_name} recovery failed: {self.last_error}"
                )

    def _do_recovery(self, node_name: str) -> bool:
        """Attempt to recover a stuck node. Returns True on success."""
        try:
            # 1. Cancel all COMPLETING jobs
            subprocess.run(
                ["scancel", "--state=COMPLETING"],
                capture_output=True,
                timeout=5,
            )

            # 2. Cancel all stale terminal jobs
            try:
                result = subprocess.run(
                    ["squeue", "--noheader", "--format=%i %j"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split(None, 1)
                    if len(parts) >= 2 and (
                        parts[1].startswith(JOB_NAME_PREFIX) or parts[1] == "true"
                    ):
                        subprocess.run(
                            ["scancel", parts[0]], capture_output=True, timeout=5
                        )
            except Exception:
                pass

            # 3. Wait 2s for SLURM to process cancellations
            time.sleep(2)

            # 4. Reset node state
            subprocess.run(
                ["scontrol", "update", f"NodeName={node_name}", "State=resume"],
                capture_output=True,
                timeout=5,
            )

            # 5. Poll until healthy or timeout
            deadline = time.time() + self.RECOVERY_TIMEOUT
            while time.time() < deadline:
                if self._stop.is_set():
                    return False
                try:
                    result = subprocess.run(
                        ["sinfo", "-h", "-N", "-o", "%T", f"--nodes={node_name}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    state = result.stdout.strip().lower()
                    if state in _HEALTHY_STATES:
                        return True
                except Exception:
                    pass
                time.sleep(1)

            with self._lock:
                self.last_error = (
                    f"Computing environment on {node_name} is still recovering "
                    f"(waited {self.RECOVERY_TIMEOUT}s)"
                )
            return False

        except Exception as e:
            with self._lock:
                self.last_error = f"Recovery failed: {e}"
            return False


# Module-level singleton (created by broker/monitor, used by spawn handlers)
_daemon: NodeHealthDaemon | None = None


def get_daemon() -> NodeHealthDaemon | None:
    """Get the running NodeHealthDaemon singleton."""
    return _daemon


def set_daemon(daemon: NodeHealthDaemon):
    """Set the module-level daemon singleton."""
    global _daemon
    _daemon = daemon


def ensure_node_ready() -> tuple[bool, str]:
    """Fast, non-blocking check of SLURM node state.

    Returns:
        (True, "") — node is healthy
        (False, "recovering") — node is being recovered by daemon
        (False, "<error>") — permanent failure (down, not installed, etc.)
    """
    # If daemon is running, use its cached state
    daemon = get_daemon()
    if daemon is not None:
        with daemon._lock:
            if daemon.state == NodeState.HEALTHY:
                return True, ""
            if daemon.state == NodeState.RECOVERING:
                return False, "recovering"
            if daemon.state == NodeState.DOWN:
                return False, daemon.last_error or "Node unavailable"
            # UNKNOWN — fall through to direct check
    # Fallback: direct check (no daemon running)
    return _direct_node_check()


def _direct_node_check() -> tuple[bool, str]:
    """Direct SLURM node check without daemon (fallback)."""
    try:
        node_name, raw_state = _get_node_state()
    except Exception as e:
        return False, str(e)

    if node_name is None:
        return False, raw_state

    if raw_state in _HEALTHY_STATES:
        return True, ""
    if raw_state in _RECOVERABLE_STATES:
        return False, "recovering"
    if raw_state in _DOWN_STATES:
        return False, f"SLURM node {node_name} is {raw_state} — compute unavailable"

    return False, f"SLURM node {node_name} in unexpected state: {raw_state}"


def _get_node_state() -> tuple[str | None, str]:
    """Query sinfo for node name and state.

    Returns (node_name, state_string) or (None, error_message).
    """
    try:
        result = subprocess.run(
            ["sinfo", "-h", "-o", "%N %T"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None, f"sinfo failed: {result.stderr.strip()}"

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                return parts[0], parts[1].lower()

        return None, "No SLURM nodes available"

    except subprocess.TimeoutExpired:
        return None, "SLURM not responding (sinfo timeout)"
    except FileNotFoundError:
        return None, "SLURM not installed (sinfo not found)"
    except Exception as e:
        return None, f"SLURM health check failed: {e}"


def recover_node_state():
    """Cancel stuck COMPLETING jobs and reset node state.

    Called on broker startup.
    """
    try:
        subprocess.run(
            ["scancel", "--state=COMPLETING"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["sinfo", "-h", "-o", "%N %T"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                node_name, state = parts[0], parts[1].lower()
                if state in _RECOVERABLE_STATES:
                    subprocess.run(
                        [
                            "scontrol",
                            "update",
                            f"NodeName={node_name}",
                            "State=resume",
                        ],
                        capture_output=True,
                        timeout=5,
                    )
    except Exception as e:
        logger.error(f"Node state recovery failed: {e}")


def cleanup_stale_jobs() -> int:
    """Cancel stale terminal jobs and recover stuck nodes.

    Called on broker startup. Returns count of jobs cancelled.
    """
    try:
        result = subprocess.run(
            ["squeue", "--noheader", "--format=%i %j %T"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        cancelled = 0
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            jid, jname = parts[0], parts[1]
            state = parts[2] if len(parts) >= 3 else ""

            should_cancel = (
                jname.startswith(JOB_NAME_PREFIX)
                or jname == "true"
                or state == "COMPLETING"
            )
            if should_cancel:
                try:
                    subprocess.run(["scancel", jid], capture_output=True, timeout=5)
                    cancelled += 1
                    logger.info(f"Cleaned up SLURM job {jid} ({jname}, {state})")
                except Exception:
                    pass
        recover_node_state()
        return cancelled
    except Exception as e:
        logger.error(f"Failed to cleanup stale jobs: {e}")
        return 0


def find_existing_jobs(username: str) -> list[str]:
    """Query squeue for existing terminal jobs for this user.

    Returns list of SLURM job IDs (RUNNING or PENDING).
    """
    job_name_for_user = f"{JOB_NAME_PREFIX}-{username}"
    try:
        result = subprocess.run(
            ["squeue", "--noheader", "--format=%i %j"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        job_ids = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(None, 1)
            if len(parts) >= 2 and parts[1] == job_name_for_user:
                job_ids.append(parts[0])
        return job_ids
    except Exception as e:
        logger.error(f"Failed to query squeue for {job_name_for_user}: {e}")
        return []


# EOF
