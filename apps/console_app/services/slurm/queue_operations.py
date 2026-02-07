#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLURM queue and job listing operations."""

from __future__ import annotations

import logging
import subprocess
from collections import Counter
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_queue_status() -> Dict:
    """
    Get overall cluster/queue status.

    Returns:
        Dict with running, pending, total, and cpu_allocation keys
    """
    # Job counts by state
    cmd = ["squeue", "-o", "%T", "--noheader"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    states = result.stdout.strip().split("\n") if result.stdout.strip() else []

    counts = Counter(states) if states and states[0] else Counter()

    # CPU allocation info
    cmd = ["sinfo", "-o", "%C", "--noheader"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    cpu_info = result.stdout.strip()  # Format: allocated/idle/other/total

    return {
        "running": counts.get("RUNNING", 0),
        "pending": counts.get("PENDING", 0),
        "total": len([s for s in states if s]),
        "cpu_allocation": cpu_info,
    }


def list_jobs(user: Optional[str] = None, state: Optional[str] = None) -> Dict:
    """
    List SLURM jobs with detailed information.

    Args:
        user: Filter by username (None for all users)
        state: Filter by state ('running', 'pending', 'all')

    Returns:
        Dict with jobs list and count statistics
    """
    # Build squeue command with detailed output
    fmt = "%i|%j|%u|%T|%M|%l|%C|%m|%P|%N|%r"
    cmd = ["squeue", "-o", fmt, "--noheader"]

    if user:
        cmd.extend(["-u", user])

    if state == "running":
        cmd.extend(["-t", "RUNNING"])
    elif state == "pending":
        cmd.extend(["-t", "PENDING"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        jobs = []
        running_count = 0
        pending_count = 0

        for line in lines:
            if not line.strip():
                continue

            job = _parse_job_line(line)
            if job:
                jobs.append(job)
                if job["state"] == "RUNNING":
                    running_count += 1
                elif job["state"] == "PENDING":
                    pending_count += 1

        return {
            "success": True,
            "jobs": jobs,
            "running": running_count,
            "pending": pending_count,
            "total": len(jobs),
        }

    except subprocess.TimeoutExpired:
        logger.error("SLURM squeue command timed out")
        return _error_response("SLURM command timed out")
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return _error_response(str(e))


def _parse_job_line(line: str) -> Optional[Dict]:
    """Parse a single job line from squeue output."""
    parts = line.split("|")
    if len(parts) < 11:
        return None

    return {
        "job_id": int(parts[0]),
        "name": parts[1],
        "user": parts[2],
        "state": parts[3],
        "time_used": parts[4],
        "time_limit": parts[5],
        "cpus": parts[6],
        "memory": parts[7],
        "partition": parts[8],
        "node": parts[9] if parts[9] else None,
        "reason": parts[10] if parts[10] != "None" else None,
    }


def _error_response(message: str) -> Dict:
    """Create a standard error response."""
    return {
        "success": False,
        "jobs": [],
        "running": 0,
        "pending": 0,
        "total": 0,
        "message": message,
    }


def is_slurm_available() -> bool:
    """
    Check if SLURM is available on this system.

    Returns:
        bool: True if SLURM commands are available
    """
    try:
        result = subprocess.run(["squeue", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# EOF
