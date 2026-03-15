"""SLURM node health checks and recovery.

Provides pre-flight validation and auto-recovery for stuck nodes
(e.g., COMPLETING state blocking new job scheduling).
"""

import logging
import subprocess
import time

logger = logging.getLogger(__name__)

# How long to wait for node recovery before giving up
_NODE_RECOVERY_TIMEOUT = 10  # seconds


def ensure_node_ready() -> tuple[bool, str]:
    """Check SLURM node state and auto-recover if stuck.

    Returns (ready, error_message). If ready is True, error_message is empty.
    """
    try:
        result = subprocess.run(
            ["sinfo", "-h", "-o", "%N %T"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, f"sinfo failed: {result.stderr.strip()}"

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            node_name, state = parts[0], parts[1].lower()

            if state in ("idle", "mixed", "allocated", "alloc"):
                return True, ""

            if state in ("completing", "comp"):
                logger.warning(
                    f"SLURM node {node_name} stuck in {state}, auto-recovering"
                )
                recovered, err = _recover_node(node_name)
                if recovered:
                    return True, ""
                return False, err

            if state in ("drained", "drain", "draining"):
                logger.warning(f"SLURM node {node_name} is {state}, attempting resume")
                recovered, err = _recover_node(node_name)
                if recovered:
                    return True, ""
                return False, f"SLURM node {node_name} is {state}: {err}"

            if state in ("down", "down*", "error"):
                return (
                    False,
                    f"SLURM node {node_name} is {state} — compute unavailable",
                )

        # No nodes found
        return False, "No SLURM nodes available"

    except subprocess.TimeoutExpired:
        return False, "SLURM not responding (sinfo timeout)"
    except FileNotFoundError:
        return False, "SLURM not installed (sinfo not found)"
    except Exception as e:
        return False, f"SLURM health check failed: {e}"


def recover_node_state():
    """Cancel stuck COMPLETING jobs and reset node state.

    Called on broker startup and by the periodic health monitor.
    """
    try:
        # Cancel all COMPLETING jobs
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
                if state in ("completing", "comp", "drained", "drain"):
                    _recover_node(node_name)
    except Exception as e:
        logger.error(f"Node state recovery failed: {e}")


# Job name prefix for terminal allocations
JOB_NAME_PREFIX = "scitex-cloud-terminal"


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
        # Recover node state
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


def _recover_node(node_name: str) -> tuple[bool, str]:
    """Attempt to recover a stuck node. Returns (success, error)."""
    try:
        # Cancel all COMPLETING jobs first
        subprocess.run(
            ["scancel", "--state=COMPLETING"],
            capture_output=True,
            timeout=5,
        )

        # Reset node state
        subprocess.run(
            ["scontrol", "update", f"NodeName={node_name}", "State=resume"],
            capture_output=True,
            timeout=5,
        )

        # Wait for node to become available
        deadline = time.time() + _NODE_RECOVERY_TIMEOUT
        while time.time() < deadline:
            result = subprocess.run(
                ["sinfo", "-h", "-N", "-o", "%T", f"--nodes={node_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            state = result.stdout.strip().lower()
            if state in ("idle", "mixed", "allocated", "alloc"):
                logger.info(f"SLURM node {node_name} recovered to {state}")
                return True, ""
            time.sleep(1)

        return (
            False,
            f"Node {node_name} did not recover within {_NODE_RECOVERY_TIMEOUT}s",
        )

    except Exception as e:
        return False, f"Node recovery failed: {e}"


# EOF
