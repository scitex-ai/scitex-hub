"""Diagnostic helpers for SLURM/Apptainer allocation failures.

These functions are called when an allocation times out, to collect
useful context (job state, pending reason, srun stderr) that is then
stored in ``Allocation.last_error`` for surfacing to the user.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)

_FAILURE_MESSAGES = {
    "TIMEOUT": "Session time limit reached — restarting automatically",
    "CANCELLED": "Session was stopped",
    "FAILED": "Session encountered an error — restarting automatically",
    "NODE_FAIL": "Server issue — restarting automatically",
    "PREEMPTED": "Resources needed elsewhere — restarting automatically",
    "OUT_OF_MEMORY": "Memory limit reached — please reduce memory usage",
}


def format_failure_reason(state: str, reason: str) -> str:
    """Map SLURM job state/reason to a human-readable message."""
    return _FAILURE_MESSAGES.get(state, "Session ended — restarting automatically")


def sacct_failure_reason(job_id) -> str:
    """Query sacct for the failure reason of a job."""
    if not job_id:
        return "No SLURM job ID"
    try:
        result = subprocess.run(
            ["sacct", "-j", job_id, "-o", "State,Reason", "--noheader", "--parsable2"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            parts = result.stdout.strip().split("\n")[0].split("|")
            state = parts[0] if parts else "UNKNOWN"
            reason = parts[1] if len(parts) > 1 else ""
            return format_failure_reason(state, reason)
    except Exception:
        pass
    return "Allocation ended (reason unknown)"


def collect_pending_reason(job_id: str, alloc_id_prefix: str = "") -> str:
    """Query squeue for the reason a job is stuck in PENDING state.

    Parameters
    ----------
    job_id:
        SLURM job ID to query.
    alloc_id_prefix:
        Short allocation ID for log context (e.g. first 8 chars of UUID).

    Returns
    -------
    str
        Human-readable reason string, or a fallback message.
    """
    if not job_id:
        return "no job ID"
    try:
        result = subprocess.run(
            ["squeue", "--job", job_id, "--noheader", "--format=%R"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        reason = result.stdout.strip()
        if reason:
            logger.info(
                "Allocation %s: PENDING reason for job %s: %s",
                alloc_id_prefix,
                job_id,
                reason,
            )
            return reason
    except Exception as exc:
        logger.debug(
            "Allocation %s: could not query squeue reason: %s",
            alloc_id_prefix,
            exc,
        )
    return "resources unavailable (squeue reason unknown)"


def collect_instance_timeout_diagnostics(
    job_id: str,
    last_srun_stderr: str = "",
    alloc_id_prefix: str = "",
) -> str:
    """Gather diagnostics when apptainer instance fails to appear in time.

    Tries, in order:
    1. ``scontrol show job`` — for job state and reason
    2. Last captured stderr from ``srun apptainer instance list``
    3. Generic fallback message

    Parameters
    ----------
    job_id:
        SLURM job ID to inspect.
    last_srun_stderr:
        stderr captured from the most recent ``srun apptainer instance list``
        call during the polling loop.
    alloc_id_prefix:
        Short allocation ID for log context.

    Returns
    -------
    str
        Human-readable diagnostic string.
    """
    if not job_id:
        return "no job ID"

    # Try scontrol show job for job-level details
    try:
        result = subprocess.run(
            ["scontrol", "show", "job", str(job_id)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            details = result.stdout.strip()
            logger.info(
                "Allocation %s: scontrol show job %s:\n%s",
                alloc_id_prefix,
                job_id,
                details,
            )
            job_state = ""
            reason = ""
            for token in details.split():
                if token.startswith("JobState="):
                    job_state = token.split("=", 1)[1]
                elif token.startswith("Reason="):
                    reason = token.split("=", 1)[1]
            if job_state or reason:
                parts = []
                if job_state:
                    parts.append(f"job state={job_state}")
                if reason and reason != "None":
                    parts.append(f"reason={reason}")
                return "; ".join(parts) if parts else "see logs"
    except Exception as exc:
        logger.debug(
            "Allocation %s: scontrol show job failed: %s",
            alloc_id_prefix,
            exc,
        )

    # Fall back to last captured srun stderr
    if last_srun_stderr:
        snippet = last_srun_stderr[:200].replace("\n", " ")
        return f"srun stderr: {snippet}"

    return "apptainer instance did not appear (check compute node logs)"


# EOF
