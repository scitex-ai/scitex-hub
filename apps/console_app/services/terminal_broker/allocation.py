"""Shared SLURM allocation — one sbatch job per (user, project).

Multiple terminal shells attach via ``srun --overlap --jobid=X``.
"""

import enum
import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# How long to wait for sbatch job to start running
SBATCH_STARTUP_TIMEOUT = 60  # seconds
SQUEUE_POLL_INTERVAL = 1.0  # seconds
# After job is RUNNING, poll for apptainer instance readiness
INSTANCE_VERIFY_TIMEOUT = 30  # seconds
INSTANCE_VERIFY_INTERVAL = 2.0  # seconds

# Shared script directory: Docker writes here, SLURM reads from host path
# Docker path: /app/data/.cache/alloc-scripts/
# Host path: derived from SLURM_USER_DATA_ROOT (e.g., .../data/users -> .../data/.cache/...)
_DOCKER_SCRIPT_DIR = Path("/app/data/.cache/alloc-scripts")
_HOST_SCRIPT_DIR: Optional[Path] = None


def _get_host_script_dir() -> Path:
    """Get host-side script directory, derived from SLURM_USER_DATA_ROOT."""
    global _HOST_SCRIPT_DIR
    if _HOST_SCRIPT_DIR is None:
        from apps.console_app.views.terminal.config import SLURM_USER_DATA_ROOT

        # SLURM_USER_DATA_ROOT is e.g. /home/.../scitex-cloud/data/users
        # We want /home/.../scitex-cloud/data/.cache/alloc-scripts
        _HOST_SCRIPT_DIR = SLURM_USER_DATA_ROOT.parent / ".cache" / "alloc-scripts"
    return _HOST_SCRIPT_DIR


class AllocationState(enum.Enum):
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    DEAD = "dead"


class Allocation:
    """Manages one sbatch allocation (SLURM job + apptainer instance).

    Lifecycle:
        1. start() — writes instance start script, submits via sbatch,
           polls squeue until RUNNING, verifies instance is ready.
        2. get_shell_command() — returns srun --overlap command for new shells.
        3. stop() — stops instance, cancels job.
    """

    def __init__(
        self,
        username: str,
        project_slug: str,
        container_path: str,
        host_user_dir: Path,
        host_project_dir: Path,
        time_limit_seconds: int = 14400,
    ):
        self.allocation_id = str(uuid.uuid4())
        self.username = username
        self.project_slug = project_slug
        self.container_path = container_path
        self.host_user_dir = host_user_dir
        self.host_project_dir = host_project_dir
        self.time_limit_seconds = time_limit_seconds
        self.instance_name = f"scitex-{username}"
        self.job_id: Optional[str] = None
        self.state = AllocationState.DEAD
        self.shell_count: int = 0
        self._script_path: Optional[str] = None
        self.started_at: Optional[float] = None

    def start(self) -> bool:
        """Submit sbatch job and wait for allocation + instance to be ready.

        Returns True on success, False on failure.
        """
        self.state = AllocationState.STARTING
        try:
            # 1. Generate instance start script
            from apps.console_app.views.terminal._command_builder import (
                build_instance_start_script_cmd,
                build_sbatch_cmd,
            )

            script_content = build_instance_start_script_cmd(
                container_path=self.container_path,
                username=self.username,
                host_user_dir=self.host_user_dir,
                host_project_dir=self.host_project_dir,
                project_slug=self.project_slug,
                instance_name=self.instance_name,
            )

            # 2. Write script to shared volume (accessible by both Docker and host)
            # Docker writes here; sbatch reads from here (Docker path).
            # Script CONTENT uses host paths (for apptainer on compute node).
            _DOCKER_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
            script_name = f"scitex-alloc-{self.allocation_id[:8]}.sh"
            docker_script_path = _DOCKER_SCRIPT_DIR / script_name
            docker_script_path.write_text(script_content)
            docker_script_path.chmod(0o755)
            self._script_path = str(docker_script_path)

            # 3. Submit via sbatch with Docker path (sbatch reads file locally)
            sbatch_cmd = build_sbatch_cmd(
                instance_name=self.instance_name,
                script_path=str(docker_script_path),
                username=self.username,
                project_slug=self.project_slug,
            )
            logger.info(
                f"Allocation {self.allocation_id[:8]}: submitting sbatch "
                f"for {self.username}/{self.project_slug} "
                f"(script: {docker_script_path})"
            )
            result = subprocess.run(
                sbatch_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                logger.error(
                    f"Allocation {self.allocation_id[:8]}: sbatch failed: "
                    f"rc={result.returncode} "
                    f"stdout={result.stdout.strip()!r} "
                    f"stderr={result.stderr.strip()!r}"
                )
                self.state = AllocationState.DEAD
                return False

            self.job_id = result.stdout.strip()
            logger.info(
                f"Allocation {self.allocation_id[:8]}: sbatch submitted, "
                f"job_id={self.job_id}"
            )

            # 4. Poll squeue until RUNNING
            if not self._wait_for_running():
                logger.error(
                    f"Allocation {self.allocation_id[:8]}: "
                    f"job {self.job_id} did not start within timeout"
                )
                self._cancel_job()
                self.state = AllocationState.DEAD
                return False

            # 5. Verify apptainer instance is ready via srun --overlap
            if not self._wait_for_instance():
                logger.error(
                    f"Allocation {self.allocation_id[:8]}: "
                    f"instance {self.instance_name} not ready within timeout"
                )
                self._cancel_job()
                self.state = AllocationState.DEAD
                return False

            self.state = AllocationState.READY
            self.started_at = time.time()
            logger.info(
                f"Allocation {self.allocation_id[:8]}: READY "
                f"(job={self.job_id}, instance={self.instance_name})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Allocation {self.allocation_id[:8]}: start failed: {e}",
                exc_info=True,
            )
            self.state = AllocationState.DEAD
            return False

    def stop(self):
        """Stop the allocation by cancelling the SLURM job.

        Cancelling the job kills the sbatch script, which stops the
        apptainer instance keep-alive loop, causing the instance to exit.
        """
        self.state = AllocationState.STOPPING
        try:
            self._cancel_job()
        finally:
            self.state = AllocationState.DEAD
            self._cleanup_script()
            logger.info(f"Allocation {self.allocation_id[:8]}: stopped")

    def get_shell_command(self, project_slug: str = "") -> list[str]:
        """Return srun --overlap command for attaching a new shell."""
        from apps.console_app.views.terminal._command_builder import (
            build_shell_in_allocation_cmd,
        )

        return build_shell_in_allocation_cmd(
            job_id=self.job_id,
            instance_name=self.instance_name,
            username=self.username,
            project_slug=project_slug or self.project_slug,
        )

    def check_alive(self) -> bool:
        """Check if the SLURM job is still running."""
        if not self.job_id:
            return False
        try:
            result = subprocess.run(
                ["squeue", "--job", self.job_id, "--noheader", "--format=%T"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            state = result.stdout.strip()
            return state in ("RUNNING", "PENDING")
        except Exception:
            return False

    def increment_shells(self):
        self.shell_count += 1

    def decrement_shells(self):
        self.shell_count = max(0, self.shell_count - 1)

    def get_remaining_seconds(self) -> Optional[int]:
        """Return seconds remaining in this allocation, or None if unknown."""
        if self.started_at is None or self.state != AllocationState.READY:
            return None
        elapsed = time.time() - self.started_at
        remaining = self.time_limit_seconds - int(elapsed)
        return max(0, remaining)

    def get_failure_reason(self) -> str:
        """Query sacct for the failure reason of this job."""
        if not self.job_id:
            return "No SLURM job ID"
        try:
            result = subprocess.run(
                [
                    "sacct",
                    "-j",
                    self.job_id,
                    "-o",
                    "State,Reason",
                    "--noheader",
                    "--parsable2",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                line = result.stdout.strip().split("\n")[0]
                parts = line.split("|")
                state = parts[0] if parts else "UNKNOWN"
                reason = parts[1] if len(parts) > 1 else ""
                return self._format_failure_reason(state, reason)
        except Exception:
            pass
        return "Allocation ended (reason unknown)"

    @staticmethod
    def _format_failure_reason(state: str, reason: str) -> str:
        """Map SLURM job state/reason to a human-readable message."""
        messages = {
            "TIMEOUT": "Job exceeded time limit",
            "CANCELLED": "Job was cancelled",
            "FAILED": f"Job failed ({reason})" if reason else "Job failed",
            "NODE_FAIL": "Compute node failure",
            "PREEMPTED": "Job was preempted by higher-priority job",
            "OUT_OF_MEMORY": "Job exceeded memory limit",
        }
        return messages.get(state, f"{state}: {reason}" if reason else state)

    def _wait_for_instance(self) -> bool:
        """Poll via srun --overlap until the apptainer instance is ready."""
        deadline = time.time() + INSTANCE_VERIFY_TIMEOUT
        logger.info(
            f"Allocation {self.allocation_id[:8]}: "
            f"verifying instance {self.instance_name} (timeout={INSTANCE_VERIFY_TIMEOUT}s)"
        )
        while time.time() < deadline:
            try:
                result = subprocess.run(
                    [
                        "srun",
                        "--overlap",
                        f"--jobid={self.job_id}",
                        "apptainer",
                        "instance",
                        "list",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if self.instance_name in result.stdout:
                    logger.info(
                        f"Allocation {self.allocation_id[:8]}: "
                        f"instance {self.instance_name} verified ready"
                    )
                    return True
            except Exception:
                pass
            if not self.check_alive():
                return False
            time.sleep(INSTANCE_VERIFY_INTERVAL)
        return False

    def _wait_for_running(self) -> bool:
        """Poll squeue until job state is RUNNING."""
        deadline = time.time() + SBATCH_STARTUP_TIMEOUT
        while time.time() < deadline:
            try:
                result = subprocess.run(
                    [
                        "squeue",
                        "--job",
                        self.job_id,
                        "--noheader",
                        "--format=%T",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                state = result.stdout.strip()
                if state == "RUNNING":
                    return True
                if not state or state in ("FAILED", "CANCELLED", "TIMEOUT"):
                    return False
            except Exception:
                pass
            time.sleep(SQUEUE_POLL_INTERVAL)
        return False

    def _cancel_job(self):
        """Cancel the SLURM job."""
        if self.job_id:
            try:
                subprocess.run(
                    ["scancel", self.job_id],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

    def _cleanup_script(self):
        """Remove the temporary script file."""
        if self._script_path and os.path.exists(self._script_path):
            try:
                os.unlink(self._script_path)
            except OSError:
                pass


# EOF
