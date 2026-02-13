#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/services/slurm_manager.py"""

import pytest

# from apps.console_app.services.slurm_manager import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/console_app/services/slurm_manager.py
# --------------------------------------------------------------------------------
# # -*- coding: utf-8 -*-
# # Timestamp: 2025-11-25 23:15:00
# # Author: ywatanabe
# # File: apps/console_app/services/slurm_manager.py
# 
# """
# SLURM job management for SciTeX Cloud.
# 
# This module provides a Python interface to SLURM for submitting and managing
# computational jobs in Apptainer containers.
# """
# 
# import logging
# import subprocess
# from collections import Counter
# from pathlib import Path
# from typing import Dict, Optional
# 
# logger = logging.getLogger(__name__)
# 
# 
# class SlurmManager:
#     """
#     Manage SLURM job submissions for SciTeX Cloud.
# 
#     Handles job submission, status monitoring, and cancellation through
#     SLURM's command-line interface.
#     """
# 
#     def __init__(self, job_scripts_dir: Optional[Path] = None):
#         """
#         Initialize SLURM manager.
# 
#         Args:
#             job_scripts_dir: Directory to store generated batch scripts.
#                            Defaults to /app/data/slurm/scripts in production,
#                            or /tmp/slurm/scripts in development.
#         """
#         if job_scripts_dir is None:
#             # Use /tmp for development, /app for production
#             if Path("/app").exists():
#                 job_scripts_dir = Path("/app/data/slurm/scripts")
#             else:
#                 job_scripts_dir = Path("/tmp/slurm/scripts")
# 
#         self.job_scripts_dir = Path(job_scripts_dir)
#         self.job_scripts_dir.mkdir(parents=True, exist_ok=True)
#         logger.info(f"SlurmManager initialized with scripts dir: {self.job_scripts_dir}")
# 
#     def submit_job(
#         self,
#         user_id: str,
#         script_path: Path,
#         container_path: Path,
#         workspace: Path,
#         job_name: str = "scitex_job",
#         partition: str = "normal",
#         cpus: int = 1,
#         memory_gb: int = 4,
#         time_limit: str = "01:00:00",
#         env_vars: Optional[Dict[str, str]] = None
#     ) -> Dict:
#         """
#         Submit a job to SLURM.
# 
#         Args:
#             user_id: User identifier for accounting
#             script_path: Path to Python script inside container
#             container_path: Path to Apptainer .sif file
#             workspace: User workspace directory (will be bound to /workspace)
#             job_name: Name for the SLURM job
#             partition: SLURM partition (normal/express/long)
#             cpus: Number of CPUs to allocate
#             memory_gb: Memory in GB
#             time_limit: Time limit in HH:MM:SS format
#             env_vars: Environment variables to export
# 
#         Returns:
#             Dict with keys:
#                 - success (bool): Whether submission succeeded
#                 - job_id (int): SLURM job ID if successful
#                 - partition (str): Partition used
#                 - message (str): Status or error message
#         """
#         # Create batch script
#         batch_script = self._create_batch_script(
#             user_id=user_id,
#             script_path=script_path,
#             container_path=container_path,
#             workspace=workspace,
#             job_name=job_name,
#             partition=partition,
#             cpus=cpus,
#             memory_gb=memory_gb,
#             time_limit=time_limit,
#             env_vars=env_vars or {}
#         )
# 
#         # Save batch file
#         batch_file = self.job_scripts_dir / f"job_{user_id}_{job_name}.sh"
#         batch_file.write_text(batch_script)
#         batch_file.chmod(0o755)
# 
#         logger.info(f"Created batch script: {batch_file}")
# 
#         # Submit to SLURM
#         cmd = ["sbatch", str(batch_file)]
# 
#         try:
#             result = subprocess.run(
#                 cmd,
#                 capture_output=True,
#                 text=True,
#                 check=True
#             )
# 
#             # Parse output: "Submitted batch job 12345"
#             job_id = int(result.stdout.strip().split()[-1])
# 
#             logger.info(f"Job {job_id} submitted for user {user_id}")
# 
#             return {
#                 'success': True,
#                 'job_id': job_id,
#                 'partition': partition,
#                 'message': f'Job {job_id} submitted successfully'
#             }
# 
#         except subprocess.CalledProcessError as e:
#             error_msg = e.stderr.strip()
#             logger.error(f"Job submission failed for user {user_id}: {error_msg}")
#             return {
#                 'success': False,
#                 'message': error_msg
#             }
# 
#     def _create_batch_script(
#         self,
#         user_id: str,
#         script_path: Path,
#         container_path: Path,
#         workspace: Path,
#         job_name: str,
#         partition: str,
#         cpus: int,
#         memory_gb: int,
#         time_limit: str,
#         env_vars: Dict[str, str]
#     ) -> str:
#         """
#         Generate SLURM batch script content.
# 
#         Creates a bash script with SBATCH directives and Apptainer execution.
#         """
#         # Ensure output directory exists
#         output_dir = workspace / "slurm_outputs"
#         output_dir.mkdir(parents=True, exist_ok=True)
# 
#         # Format environment variables
#         env_exports = "\n".join([
#             f"export {k}={v}" for k, v in env_vars.items()
#         ])
# 
#         return f"""#!/bin/bash
# #SBATCH --job-name={job_name}
# #SBATCH --partition={partition}
# #SBATCH --cpus-per-task={cpus}
# #SBATCH --mem={memory_gb}G
# #SBATCH --time={time_limit}
# #SBATCH --chdir={workspace}
# #SBATCH --output={output_dir}/slurm-%j.out
# #SBATCH --error={output_dir}/slurm-%j.err
# #SBATCH --account=user_{user_id}
# 
# # Environment variables
# {env_exports}
# 
# # Job information
# echo "=========================================="
# echo "SLURM Job Information"
# echo "=========================================="
# echo "Job ID: $SLURM_JOB_ID"
# echo "Job Name: {job_name}"
# echo "User: {user_id}"
# echo "Node: $(hostname)"
# echo "Start Time: $(date)"
# echo "CPUs: {cpus}"
# echo "Memory: {memory_gb}G"
# echo "=========================================="
# echo ""
# 
# # Execute in Apptainer container
# apptainer exec \\
#     --contain \\
#     --cleanenv \\
#     --bind {workspace}:/workspace \\
#     --pwd /workspace \\
#     {container_path} \\
#     python {script_path}
# 
# # Capture exit code
# EXIT_CODE=$?
# 
# echo ""
# echo "=========================================="
# echo "Job finished: $(date)"
# echo "Exit console: $EXIT_CODE"
# echo "=========================================="
# 
# exit $EXIT_CODE
# """
# 
#     def get_job_status(self, job_id: int) -> Dict:
#         """
#         Get status of a SLURM job.
# 
#         Args:
#             job_id: SLURM job ID
# 
#         Returns:
#             Dict with job status information. Keys depend on job state:
#                 - job_id (int): Job ID
#                 - state (str): Job state (PENDING/RUNNING/COMPLETED/FAILED/etc.)
#                 - is_running (bool): True if currently running
#                 - is_pending (bool): True if pending
#                 - is_completed (bool): True if finished
#                 - success (bool): True if completed successfully (only for completed jobs)
#                 - time_used/elapsed (str): Time used
#                 - reason (str): Reason for pending state (if pending)
#                 - exit_code (str): Exit code (if completed)
#         """
#         # Check active queue first (running/pending jobs)
#         cmd = ["squeue", "-j", str(job_id), "-o", "%T %M %r", "--noheader"]
#         result = subprocess.run(cmd, capture_output=True, text=True)
# 
#         if result.stdout.strip():
#             parts = result.stdout.strip().split()
#             state = parts[0]
#             time_used = parts[1] if len(parts) > 1 else "0:00"
#             reason = parts[2] if len(parts) > 2 else "None"
# 
#             return {
#                 'job_id': job_id,
#                 'state': state,
#                 'time_used': time_used,
#                 'reason': reason,
#                 'is_running': state == "RUNNING",
#                 'is_pending': state == "PENDING",
#                 'is_completed': False
#             }
# 
#         # Check completed jobs (sacct)
#         cmd = ["sacct", "-j", str(job_id), "-o", "State,ExitCode,Elapsed",
#                "--noheader", "--parsable2"]
#         result = subprocess.run(cmd, capture_output=True, text=True)
# 
#         if result.stdout.strip():
#             line = result.stdout.strip().split('\n')[0]
#             parts = line.split('|')
#             state = parts[0] if len(parts) > 0 else "UNKNOWN"
#             exit_code = parts[1] if len(parts) > 1 else "1:0"
#             elapsed = parts[2] if len(parts) > 2 else "0:00"
# 
#             return {
#                 'job_id': job_id,
#                 'state': state,
#                 'exit_code': exit_code,
#                 'elapsed': elapsed,
#                 'is_completed': True,
#                 'is_running': False,
#                 'is_pending': False,
#                 'success': state == "COMPLETED" and exit_code == "0:0"
#             }
# 
#         # Job not found
#         return {
#             'job_id': job_id,
#             'state': 'NOT_FOUND',
#             'is_completed': False,
#             'is_running': False,
#             'is_pending': False
#         }
# 
#     def cancel_job(self, job_id: int) -> Dict:
#         """
#         Cancel a SLURM job.
# 
#         Args:
#             job_id: SLURM job ID to cancel
# 
#         Returns:
#             Dict with keys:
#                 - success (bool): Whether cancellation succeeded
#                 - message (str): Error message if failed
#         """
#         cmd = ["scancel", str(job_id)]
# 
#         try:
#             subprocess.run(cmd, check=True, capture_output=True, text=True)
#             logger.info(f"Job {job_id} cancelled")
#             return {'success': True, 'message': f'Job {job_id} cancelled'}
#         except subprocess.CalledProcessError as e:
#             error_msg = e.stderr.strip()
#             logger.error(f"Failed to cancel job {job_id}: {error_msg}")
#             return {'success': False, 'message': error_msg}
# 
#     def get_queue_status(self) -> Dict:
#         """
#         Get overall cluster/queue status.
# 
#         Returns:
#             Dict with keys:
#                 - running (int): Number of running jobs
#                 - pending (int): Number of pending jobs
#                 - total (int): Total jobs in queue
#                 - cpu_allocation (str): CPU allocation info (allocated/idle/other/total)
#         """
#         # Job counts by state
#         cmd = ["squeue", "-o", "%T", "--noheader"]
#         result = subprocess.run(cmd, capture_output=True, text=True)
#         states = result.stdout.strip().split('\n') if result.stdout.strip() else []
# 
#         counts = Counter(states) if states and states[0] else Counter()
# 
#         # CPU allocation info
#         cmd = ["sinfo", "-o", "%C", "--noheader"]
#         result = subprocess.run(cmd, capture_output=True, text=True)
#         cpu_info = result.stdout.strip()  # Format: allocated/idle/other/total
# 
#         return {
#             'running': counts.get('RUNNING', 0),
#             'pending': counts.get('PENDING', 0),
#             'total': len([s for s in states if s]),
#             'cpu_allocation': cpu_info
#         }
# 
#     def list_jobs(self, user: str = None, state: str = None) -> Dict:
#         """
#         List SLURM jobs with detailed information.
# 
#         Args:
#             user: Filter by username (None for all users)
#             state: Filter by state ('running', 'pending', 'all')
# 
#         Returns:
#             Dict with keys:
#                 - jobs (list): List of job dicts
#                 - running (int): Count of running jobs
#                 - pending (int): Count of pending jobs
#                 - total (int): Total job count
#         """
#         # Build squeue command with detailed output
#         # Format: JobID|Name|User|State|TimeUsed|TimeLimit|CPUs|Memory|Partition|NodeList|Reason
#         fmt = "%i|%j|%u|%T|%M|%l|%C|%m|%P|%N|%r"
#         cmd = ["squeue", "-o", fmt, "--noheader"]
# 
#         if user:
#             cmd.extend(["-u", user])
# 
#         if state == "running":
#             cmd.extend(["-t", "RUNNING"])
#         elif state == "pending":
#             cmd.extend(["-t", "PENDING"])
# 
#         try:
#             result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
#             lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
# 
#             jobs = []
#             running_count = 0
#             pending_count = 0
# 
#             for line in lines:
#                 if not line.strip():
#                     continue
# 
#                 parts = line.split('|')
#                 if len(parts) < 11:
#                     continue
# 
#                 job = {
#                     'job_id': int(parts[0]),
#                     'name': parts[1],
#                     'user': parts[2],
#                     'state': parts[3],
#                     'time_used': parts[4],
#                     'time_limit': parts[5],
#                     'cpus': parts[6],
#                     'memory': parts[7],
#                     'partition': parts[8],
#                     'node': parts[9] if parts[9] else None,
#                     'reason': parts[10] if parts[10] != 'None' else None,
#                 }
# 
#                 jobs.append(job)
# 
#                 if job['state'] == 'RUNNING':
#                     running_count += 1
#                 elif job['state'] == 'PENDING':
#                     pending_count += 1
# 
#             return {
#                 'success': True,
#                 'jobs': jobs,
#                 'running': running_count,
#                 'pending': pending_count,
#                 'total': len(jobs)
#             }
# 
#         except subprocess.TimeoutExpired:
#             logger.error("SLURM squeue command timed out")
#             return {
#                 'success': False,
#                 'jobs': [],
#                 'running': 0,
#                 'pending': 0,
#                 'total': 0,
#                 'message': 'SLURM command timed out'
#             }
#         except Exception as e:
#             logger.error(f"Error listing jobs: {str(e)}")
#             return {
#                 'success': False,
#                 'jobs': [],
#                 'running': 0,
#                 'pending': 0,
#                 'total': 0,
#                 'message': str(e)
#             }
# 
#     def is_available(self) -> bool:
#         """
#         Check if SLURM is available on this system.
# 
#         Returns:
#             bool: True if SLURM commands are available
#         """
#         try:
#             result = subprocess.run(
#                 ["squeue", "--version"],
#                 capture_output=True,
#                 timeout=5
#             )
#             return result.returncode == 0
#         except (FileNotFoundError, subprocess.TimeoutExpired):
#             return False
# 
#     def get_job_output(self, job_id: int, workspace: Path, tail_lines: int = 100) -> Dict:
#         """
#         Get job output logs.
# 
#         Args:
#             job_id: SLURM job ID
#             workspace: User workspace directory
#             tail_lines: Number of lines to return from end of file
# 
#         Returns:
#             Dict with keys:
#                 - stdout (str): Standard output content
#                 - stderr (str): Standard error content
#                 - found (bool): Whether log files were found
#         """
#         output_dir = workspace / "slurm_outputs"
#         stdout_file = output_dir / f"slurm-{job_id}.out"
#         stderr_file = output_dir / f"slurm-{job_id}.err"
# 
#         result = {'found': False, 'stdout': '', 'stderr': ''}
# 
#         if stdout_file.exists():
#             result['found'] = True
#             lines = stdout_file.read_text().split('\n')
#             result['stdout'] = '\n'.join(lines[-tail_lines:]) if tail_lines else '\n'.join(lines)
# 
#         if stderr_file.exists():
#             result['found'] = True
#             lines = stderr_file.read_text().split('\n')
#             result['stderr'] = '\n'.join(lines[-tail_lines:]) if tail_lines else '\n'.join(lines)
# 
#         return result
# 
# 
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/console_app/services/slurm_manager.py
# --------------------------------------------------------------------------------
