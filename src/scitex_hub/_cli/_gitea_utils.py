#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/cli/_gitea_utils.py
"""Gitea CLI utilities - Helper functions for tea wrapper."""

import fcntl
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import click
from scitex_config._ecosystem import local_state

# Default Gitea port for SciTeX Hub
_DEFAULT_GITEA_PORT = 3000


def get_gitea_url():
    """Return the Gitea base URL from env or .env file.

    Resolution order:
    1. SCITEX_CLOUD_GITEA_URL_DEV env var
    2. SCITEX_CLOUD_GITEA_HTTP_PORT_DEV env var (builds http://localhost:{port})
    3. SECRET/.env.dev file (parsed for the above keys)
    4. Fallback: http://localhost:3000
    """
    url = os.environ.get("SCITEX_CLOUD_GITEA_URL_DEV")
    if url:
        return url.rstrip("/")

    port = os.environ.get("SCITEX_CLOUD_GITEA_HTTP_PORT_DEV")
    if port:
        return f"http://localhost:{port}"

    # Try reading from .env file
    for env_path in _find_env_files():
        parsed = _parse_env_file(env_path)
        if "SCITEX_CLOUD_GITEA_URL_DEV" in parsed:
            return parsed["SCITEX_CLOUD_GITEA_URL_DEV"].rstrip("/")
        if "SCITEX_CLOUD_GITEA_HTTP_PORT_DEV" in parsed:
            return f"http://localhost:{parsed['SCITEX_CLOUD_GITEA_HTTP_PORT_DEV']}"

    return f"http://localhost:{_DEFAULT_GITEA_PORT}"


def _find_env_files():
    """Yield paths to .env files (SECRET/.env.dev, .env) from project root."""
    # Walk up from cwd to find the project root (has SECRET/ or .env)
    cwd = Path(os.getcwd())
    for parent in [cwd] + list(cwd.parents):
        secret_env = parent / "SECRET" / ".env.dev"
        if secret_env.exists():
            yield secret_env
        dot_env = parent / ".env"
        if dot_env.exists():
            yield dot_env
        if (parent / "manage.py").exists():
            break


def _parse_env_file(path):
    """Parse a .env file into a dict (simple KEY=VALUE format)."""
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    result[key.strip()] = value.strip().strip("'\"")
    except Exception:
        pass
    return result


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


def get_tea_config(login_name="scitex-dev"):
    """Read tea config and return the named login entry (url, token, user)."""
    import yaml

    config_path = Path.home() / ".config" / "tea" / "config.yml"
    if not config_path.exists():
        click.echo(
            "Error: Tea configuration not found. Run 'scitex-hub gitea login' first.",
            err=True,
        )
        sys.exit(1)
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        for entry in config.get("logins", []):
            if entry["name"] == login_name:
                return entry
        click.echo(f"Error: Login '{login_name}' not found in tea config.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading tea config: {e}", err=True)
        sys.exit(1)


def get_gitea_http_url(owner, repo, login_name="scitex-dev"):
    """Return an HTTP URL with embedded token for git operations."""
    cfg = get_tea_config(login_name)
    host = cfg["url"].rstrip("/")
    # Strip scheme and re-add with token embedded
    if "://" in host:
        scheme, rest = host.split("://", 1)
    else:
        scheme, rest = "http", host
    token = cfg["token"]
    return f"{scheme}://{token}@{rest}/{owner}/{repo}.git"


def ensure_gitea_remote(remote_name="scitex", login_name="scitex-dev", repo=None):
    """Ensure a Gitea remote exists on the current git repo.

    If the remote is missing, infer owner/repo from tea config and cwd,
    create it with a token-authenticated URL, and return the remote name.
    """
    # Check if remote already exists
    result = subprocess.run(
        ["git", "remote", "get-url", remote_name],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return remote_name

    # Remote does not exist — build URL from tea config + cwd
    cfg = get_tea_config(login_name)
    owner = cfg.get("user", "")
    if not owner:
        click.echo(
            "Error: Could not determine Gitea username from tea config.", err=True
        )
        sys.exit(1)

    if repo is None:
        repo = Path(os.getcwd()).name

    url = get_gitea_http_url(owner, repo, login_name)
    click.echo(f"Adding remote '{remote_name}' -> {cfg['url']}/{owner}/{repo}.git")
    try:
        subprocess.run(["git", "remote", "add", remote_name, url], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error adding remote: {e}", err=True)
        sys.exit(1)
    return remote_name


class SyncLock:
    """File-based lock for preventing concurrent sync operations."""

    def __init__(self, lock_path=None, timeout=30):
        if lock_path is None:
            # local_state.runtime_path() auto-creates runtime/ + seeds.
            lock_path = str(local_state.runtime_path("cloud", "workspace-sync.lock"))
        else:
            Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
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
