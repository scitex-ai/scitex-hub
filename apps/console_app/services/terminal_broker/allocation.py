"""Shared SLURM allocation — one sbatch job per (user, project).

Multiple terminal shells attach via ``srun --overlap --jobid=X``.
"""

import enum
import logging
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# How long to wait for sbatch job to start running
SBATCH_STARTUP_TIMEOUT = 60  # seconds
SQUEUE_POLL_INTERVAL = 1.0  # seconds
INSTANCE_VERIFY_TIMEOUT = 30  # seconds
INSTANCE_VERIFY_INTERVAL = 2.0  # seconds


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
    ):
        self.allocation_id = str(uuid.uuid4())
        self.username = username
        self.project_slug = project_slug
        self.container_path = container_path
        self.host_user_dir = host_user_dir
        self.host_project_dir = host_project_dir
        self.instance_name = f"scitex-{username}-{project_slug}"
        self.job_id: Optional[str] = None
        self.state = AllocationState.DEAD
        self.shell_count: int = 0
        self._script_path: Optional[str] = None

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

            # 2. Write script to temp file
            fd, self._script_path = tempfile.mkstemp(
                prefix=f"scitex-alloc-{self.allocation_id[:8]}-",
                suffix=".sh",
            )
            with os.fdopen(fd, "w") as f:
                f.write(script_content)
            os.chmod(self._script_path, 0o755)

            # 3. Submit via sbatch
            sbatch_cmd = build_sbatch_cmd(
                instance_name=self.instance_name,
                script_path=self._script_path,
                username=self.username,
                project_slug=self.project_slug,
            )
            logger.info(
                f"Allocation {self.allocation_id[:8]}: submitting sbatch "
                f"for {self.username}/{self.project_slug}"
            )
            result = subprocess.run(
                sbatch_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(
                    f"Allocation {self.allocation_id[:8]}: sbatch failed: "
                    f"{result.stderr.strip()}"
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

            # 5. Poll until instance is ready (apptainer startup takes a few seconds)
            if not self._wait_for_instance():
                logger.error(
                    f"Allocation {self.allocation_id[:8]}: "
                    f"instance {self.instance_name} not ready"
                )
                self._cancel_job()
                self.state = AllocationState.DEAD
                return False

            self.state = AllocationState.READY
            logger.info(
                f"Allocation {self.allocation_id[:8]}: READY "
                f"(job={self.job_id}, instance={self.instance_name})"
            )
            return True

        except Exception as e:
            logger.error(f"Allocation {self.allocation_id[:8]}: start failed: {e}")
            self.state = AllocationState.DEAD
            return False

    def stop(self):
        """Stop the instance and cancel the SLURM job."""
        self.state = AllocationState.STOPPING
        try:
            # Stop apptainer instance via srun --overlap
            if self.job_id:
                try:
                    subprocess.run(
                        [
                            "srun",
                            "--overlap",
                            f"--jobid={self.job_id}",
                            "apptainer",
                            "instance",
                            "stop",
                            self.instance_name,
                        ],
                        capture_output=True,
                        timeout=10,
                    )
                except Exception as e:
                    logger.debug(
                        f"Allocation {self.allocation_id[:8]}: "
                        f"instance stop error (non-fatal): {e}"
                    )

            self._cancel_job()
        finally:
            self.state = AllocationState.DEAD
            self._cleanup_script()
            logger.info(f"Allocation {self.allocation_id[:8]}: stopped")

    def get_shell_command(self) -> list[str]:
        """Return srun --overlap command for attaching a new shell."""
        from apps.console_app.views.terminal._command_builder import (
            build_shell_in_allocation_cmd,
        )

        return build_shell_in_allocation_cmd(
            job_id=self.job_id,
            instance_name=self.instance_name,
            username=self.username,
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

    def _wait_for_instance(self) -> bool:
        """Poll until apptainer instance appears inside the allocation."""
        deadline = time.time() + INSTANCE_VERIFY_TIMEOUT
        while time.time() < deadline:
            if self._verify_instance():
                return True
            time.sleep(INSTANCE_VERIFY_INTERVAL)
        return False

    def _verify_instance(self) -> bool:
        """Verify apptainer instance is running inside the allocation."""
        if not self.job_id:
            return False
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
                timeout=15,
            )
            return self.instance_name in result.stdout
        except Exception:
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
