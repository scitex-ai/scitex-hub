"""
Container-state teardown for visitor slots (isolation audit gap #6).

Visitor usernames are permanent per slot (``visitor-001..N``), so any
container resource keyed on the username outlives the visitor session:

* The terminal broker runs ONE apptainer instance per user, named
  ``scitex-<username>`` (terminal_broker/allocation.py), inside ONE
  SLURM job. The visitor session is 1 h but the SLURM job limit is
  4 h, releasing a slot never cancelled the job, and a reconnect
  ATTACHES to a still-running job — so visitor N+1 could land inside
  visitor N's live instance (its ``--writable-tmpfs`` overlay, ``/tmp``,
  running processes and exported environment).

This module stops the instance, cancels the job(s), and VERIFIES both
are gone, through an injectable ``run_cmd`` seam (the same
fake-at-the-subprocess-boundary pattern the reset pipeline uses for
Gitea and the template clone).

Failure policy (no silent fallbacks):

* squeue/scancel present but failing, jobs surviving scancel, or an
  instance surviving teardown ⇒ :class:`ContainerTeardownError` — the
  caller (workspace_manager) quarantines the slot.
* SLURM/apptainer binaries MISSING (``FileNotFoundError``) is a
  decidable environment state, not a swallowed error: deployments
  without the SLURM/apptainer toolchain (dev SQLite, plain CI) cannot
  have broker-created jobs or instances, so there is nothing to tear
  down. Logged, then treated as clean.
"""

import logging
import subprocess
import time

from apps.workspace.console_app.services.terminal_broker.slurm_health import (
    instance_name_for,
    terminal_job_name,
)

logger = logging.getLogger(__name__)

SQUEUE_TIMEOUT = 15
SCANCEL_TIMEOUT = 15
INSTANCE_STOP_TIMEOUT = 60
INSTANCE_LIST_TIMEOUT = 15
# scancel is asynchronous — cancelled jobs linger in COMPLETING before
# leaving squeue. Poll up to this long before declaring teardown failed.
JOB_GONE_TIMEOUT = 30.0
JOB_GONE_POLL_INTERVAL = 1.0


class ContainerTeardownError(Exception):
    """Visitor container state could not be torn down and verified gone."""


def default_run_cmd(argv: list, timeout: float):
    """The real subprocess boundary (injectable seam for tests)."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def _is_visitor_job(job_name: str, username: str) -> bool:
    """True if a SLURM job name belongs to this visitor.

    Union of the two job-name conventions that exist in this codebase
    (mirrors ``console_app.job_api_views._is_user_job``):

    * ``scitex-hub-terminal-<username>`` — the broker-side constant
      (terminal_broker/slurm_health.JOB_NAME_PREFIX), exact match.
    * ``scitex_<username>_<project>`` — what the installed
      ``scitex_container.apptainer.build_sbatch_command`` actually
      passes to ``sbatch --job-name`` (also the compute-job naming),
      prefix match. The trailing underscore keeps ``visitor-001`` from
      matching ``visitor-0011``.

    Matching both families makes teardown robust to the library/broker
    naming drift and also reaps any compute jobs the visitor left
    running (which would keep writing into the workspace after the
    wipe).
    """
    return job_name == terminal_job_name(username) or job_name.startswith(
        f"scitex_{username}_"
    )


def _visitor_job_ids(username: str, run_cmd) -> "list[str] | None":
    """SLURM job ids belonging to ``username``.

    Returns ``None`` when the squeue binary is absent (no SLURM in this
    deployment). Raises :class:`ContainerTeardownError` when squeue is
    present but fails — an unreadable queue must never pass the gate.
    """
    try:
        result = run_cmd(["squeue", "--noheader", "--format=%i %j"], SQUEUE_TIMEOUT)
    except FileNotFoundError:
        logger.info(
            "[VisitorPool] squeue not installed — no SLURM jobs to manage "
            f"for {username}"
        )
        return None
    except ContainerTeardownError:
        raise
    except Exception as exc:
        raise ContainerTeardownError(f"squeue query failed for {username}: {exc}") from exc

    if result.returncode != 0:
        raise ContainerTeardownError(
            f"squeue exited {result.returncode} for {username}: "
            f"{result.stderr.strip()}"
        )

    job_ids = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) >= 2 and _is_visitor_job(parts[1].strip(), username):
            job_ids.append(parts[0])
    return job_ids


def _instance_visible(username: str, run_cmd) -> bool:
    """True if ``scitex-<username>`` shows in ``apptainer instance list``.

    A missing apptainer binary means no instance can run on this host —
    logged, treated as not visible. A failing apptainer call raises:
    "cannot check" must never verify as "clean".
    """
    instance = instance_name_for(username)
    try:
        result = run_cmd(["apptainer", "instance", "list"], INSTANCE_LIST_TIMEOUT)
    except FileNotFoundError:
        logger.info(
            "[VisitorPool] apptainer not installed — no local instance "
            f"check possible for {username}"
        )
        return False
    except ContainerTeardownError:
        raise
    except Exception as exc:
        raise ContainerTeardownError(
            f"apptainer instance list failed for {username}: {exc}"
        ) from exc

    if result.returncode != 0:
        raise ContainerTeardownError(
            f"apptainer instance list exited {result.returncode} for "
            f"{username}: {result.stderr.strip()}"
        )

    for line in result.stdout.strip().split("\n"):
        tokens = line.split()
        # Exact first-token match (never substring: scitex-visitor-001
        # must not match scitex-visitor-0011).
        if tokens and tokens[0] == instance:
            return True
    return False


def _stop_instance_in_job(job_id: str, instance: str, username: str, run_cmd) -> None:
    """Gracefully stop the apptainer instance INSIDE its SLURM job.

    Best-effort by design: the job is scancel'ed right after, which
    kills the instance's processes via SLURM's proctrack anyway, and
    :func:`verify_container_state_gone` is the actual gate. Failures
    are logged loudly, never swallowed into a fake success.
    """
    argv = [
        "srun",
        "--overlap",
        f"--jobid={job_id}",
        "apptainer",
        "instance",
        "stop",
        instance,
    ]
    try:
        result = run_cmd(argv, INSTANCE_STOP_TIMEOUT)
    except Exception as exc:
        logger.warning(
            f"[VisitorPool] instance stop inside job {job_id} failed for "
            f"{username}: {exc} — continuing to scancel; the final gate "
            f"catches survivors"
        )
        return
    if result.returncode != 0:
        logger.warning(
            f"[VisitorPool] instance stop inside job {job_id} exited "
            f"{result.returncode} for {username}: {result.stderr.strip()} — "
            f"continuing to scancel; the final gate catches survivors"
        )


def _scancel(job_id: str, username: str, run_cmd) -> None:
    """Cancel one SLURM job; raise on any failure."""
    try:
        result = run_cmd(["scancel", job_id], SCANCEL_TIMEOUT)
    except ContainerTeardownError:
        raise
    except Exception as exc:
        raise ContainerTeardownError(
            f"scancel {job_id} failed for {username}: {exc}"
        ) from exc
    if result.returncode != 0:
        raise ContainerTeardownError(
            f"scancel {job_id} exited {result.returncode} for {username}: "
            f"{result.stderr.strip()}"
        )


def _wait_jobs_gone(username: str, run_cmd) -> None:
    """Poll squeue until no visitor job remains (scancel is async)."""
    deadline = time.monotonic() + JOB_GONE_TIMEOUT
    while True:
        job_ids = _visitor_job_ids(username, run_cmd)
        if not job_ids:  # [] or None (binary vanished mid-flight)
            return
        if time.monotonic() >= deadline:
            raise ContainerTeardownError(
                f"SLURM jobs for {username} survived scancel after "
                f"{JOB_GONE_TIMEOUT:.0f}s: {job_ids!r}"
            )
        time.sleep(JOB_GONE_POLL_INTERVAL)


def teardown_container_state(username: str, *, run_cmd=None) -> None:
    """Stop the visitor's container instance(s) + SLURM job(s); verify gone.

    Sequencing is load-bearing: this runs BEFORE the filesystem wipe —
    a live instance holds the ``--home`` bind of the visitor home open
    and its processes keep writing, defeating rmtree + re-clone.

    Raises :class:`ContainerTeardownError` on any failure; the caller
    must quarantine the slot.
    """
    run_cmd = run_cmd or default_run_cmd
    job_ids = _visitor_job_ids(username, run_cmd)
    if job_ids:
        instance = instance_name_for(username)
        logger.info(
            f"[VisitorPool] Tearing down container state for {username}: "
            f"jobs={job_ids!r}, instance={instance}"
        )
        for job_id in job_ids:
            _stop_instance_in_job(job_id, instance, username, run_cmd)
            _scancel(job_id, username, run_cmd)
        _wait_jobs_gone(username, run_cmd)
    verify_container_state_gone(username, run_cmd=run_cmd)


def verify_container_state_gone(username: str, *, run_cmd=None) -> None:
    """The container half of the final gate: no job, no instance.

    Raises :class:`ContainerTeardownError` if any SLURM job or a
    ``scitex-<username>`` apptainer instance is still present.
    """
    run_cmd = run_cmd or default_run_cmd
    job_ids = _visitor_job_ids(username, run_cmd)
    if job_ids:
        raise ContainerTeardownError(
            f"SLURM jobs still present for {username}: {job_ids!r}"
        )
    if _instance_visible(username, run_cmd):
        raise ContainerTeardownError(
            f"apptainer instance {instance_name_for(username)} still running"
        )


# EOF
