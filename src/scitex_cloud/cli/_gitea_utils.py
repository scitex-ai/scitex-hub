#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/cli/_gitea_utils.py
"""Gitea CLI utilities - Helper functions for tea wrapper."""

import fcntl
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import click


def run_tea(*args):
    """Execute tea command and return result."""
    tea_path = Path.home() / ".local" / "bin" / "tea"
    if not tea_path.exists():
        click.echo("Error: tea CLI not found", err=True)
        click.echo(
            "Install: wget https://dl.gitea.com/tea/0.9.2/tea-0.9.2-linux-amd64 "
            "-O ~/.local/bin/tea && chmod +x ~/.local/bin/tea",
            err=True,
        )
        sys.exit(1)
    try:
        return subprocess.run(
            [str(tea_path)] + list(args), capture_output=False, text=True
        )
    except Exception as e:
        click.echo(f"Error running tea: {e}", err=True)
        sys.exit(1)


def is_in_workspace():
    """Check if running in SciTeX workspace container."""
    if os.environ.get("SCITEX_WORKSPACE"):
        return True
    if socket.gethostname().startswith("scitex-workspace-"):
        return True
    if Path("/.scitex-workspace").exists():
        return True
    return False


def ensure_not_in_workspace():
    """Ensure user is NOT in workspace container."""
    if is_in_workspace():
        click.echo("", err=True)
        click.echo("Error: You are inside a SciTeX workspace!", err=True)
        click.echo("The 'scitex cloud' commands are for LOCAL machines.", err=True)
        click.echo("Inside workspace, use regular git commands.", err=True)
        sys.exit(1)


def check_workspace_sync_status():
    """Check if workspace has uncommitted or unpushed changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )
        if result.stdout.strip():
            return True, "Uncommitted changes"
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )
        if result.returncode == 0 and int(result.stdout.strip()) > 0:
            return True, "Unpushed commits"
        return False, "Synced"
    except Exception:
        return False, "Cannot determine status"


def check_large_files(threshold_mb=100):
    """Check for files larger than threshold."""
    large_files = []
    threshold_bytes = threshold_mb * 1024 * 1024
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )
        untracked = result.stdout.strip().split("\n") if result.stdout.strip() else []
        for filepath in untracked:
            full_path = Path(os.getcwd()) / filepath
            if full_path.exists() and full_path.is_file():
                size = full_path.stat().st_size
                if size > threshold_bytes:
                    large_files.append((filepath, size / (1024 * 1024)))
    except Exception as e:
        click.echo(f"Warning: Could not check file sizes: {e}", err=True)
    return large_files


class SyncLock:
    """File-based lock for preventing concurrent sync operations."""

    def __init__(self, lock_path="/tmp/scitex-workspace-sync.lock", timeout=30):
        self.lock_path = lock_path
        self.timeout = timeout
        self.lock_file = None

    def __enter__(self):
        self.lock_file = open(self.lock_path, "w")
        start_time = time.time()
        while True:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
                return self
            except IOError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError("Could not acquire sync lock")
                click.echo("Waiting for ongoing sync...", err=True)
                time.sleep(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except Exception:
                pass


# EOF
