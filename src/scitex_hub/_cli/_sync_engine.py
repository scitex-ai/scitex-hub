#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conflict-aware file sync engine (Dropbox-style).

Syncs files between local and remote (workspace), detecting conflicts
when both sides have changes since the last sync.

Conflict resolution:
    - Only one side changed → overwrite the stale copy (normal sync)
    - Both sides changed → keep both: original + .conflict-<timestamp> copy
    - Report all conflicts at the end

State tracking:
    .scitex-sync-state.json stores checksums from last successful sync.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SYNC_STATE_FILE = ".scitex-sync-state.json"
EXCLUDES = {".git", "__pycache__", "node_modules", ".venv", SYNC_STATE_FILE}


@dataclass
class SyncResult:
    """Result of a sync operation."""

    synced: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def _checksum(path: Path) -> str:
    """SHA-256 of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except (OSError, PermissionError):
        return ""
    return h.hexdigest()


def _should_exclude(rel: str) -> bool:
    """Check if a relative path should be excluded from sync."""
    parts = Path(rel).parts
    return any(p in EXCLUDES or p.startswith(".conflict-") for p in parts)


def _list_files(root: Path) -> dict[str, str]:
    """List all files under root with their checksums. Returns {rel_path: checksum}."""
    files: dict[str, str] = {}
    if not root.is_dir():
        return files
    for path in root.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(root))
            if not _should_exclude(rel):
                files[rel] = _checksum(path)
    return files


def _list_remote_files(ssh_cmd: list[str], remote_path: str) -> dict[str, str]:
    """List files on remote with checksums via SSH."""
    # Use find + sha256sum on remote
    script = (
        f"cd {remote_path} 2>/dev/null && "
        f"find . -type f "
        f"-not -path './.git/*' "
        f"-not -path './__pycache__/*' "
        f"-not -path './node_modules/*' "
        f"-not -path './.venv/*' "
        f"-not -name '{SYNC_STATE_FILE}' "
        f"-exec sha256sum {{}} \\;"
    )
    try:
        result = subprocess.run(
            ssh_cmd + [script],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return {}

    files: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            checksum, path = parts
            # Remove leading ./
            rel = path.lstrip("./")
            if rel and not _should_exclude(rel):
                files[rel] = checksum
    return files


def _load_sync_state(local_root: Path) -> dict[str, str]:
    """Load last-sync checksums from state file."""
    state_file = local_root / SYNC_STATE_FILE
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_sync_state(local_root: Path, checksums: dict[str, str]) -> None:
    """Save current checksums as sync state."""
    state_file = local_root / SYNC_STATE_FILE
    state_file.write_text(json.dumps(checksums, indent=2, sort_keys=True))


def _conflict_name(rel: str) -> str:
    """Generate a conflict filename: file.txt → file.conflict-20260324T120000.txt"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    p = Path(rel)
    return str(p.with_stem(f"{p.stem}.conflict-{ts}"))


def sync_files(
    local_root: Path,
    ssh_cmd: list[str],
    remote_path: str,
    direction: str,  # "to" or "from"
    dry_run: bool = False,
) -> SyncResult:
    """Sync files with conflict detection.

    Args:
        local_root: Local directory root.
        ssh_cmd: SSH command prefix (e.g. ["ssh", "-p", "2200", "scitex@host"]).
        remote_path: Remote workspace path.
        direction: "to" (local → remote) or "from" (remote → local).
        dry_run: If True, only report what would happen.

    Returns:
        SyncResult with synced files, conflicts, and errors.
    """
    result = SyncResult()

    # 1. Gather checksums from both sides
    local_files = _list_files(local_root)
    remote_files = _list_remote_files(ssh_cmd, remote_path)
    last_sync = _load_sync_state(local_root)

    # 2. Determine changes since last sync
    all_files = set(local_files) | set(remote_files)

    to_copy: list[str] = []  # files to copy in sync direction
    conflicts: list[str] = []  # files changed on both sides

    for rel in sorted(all_files):
        local_cs = local_files.get(rel, "")
        remote_cs = remote_files.get(rel, "")
        last_cs = last_sync.get(rel, "")

        if local_cs == remote_cs:
            # Already in sync
            continue

        local_changed = local_cs != last_cs
        remote_changed = remote_cs != last_cs

        if local_changed and remote_changed:
            # Both sides changed → conflict
            conflicts.append(rel)
        elif direction == "to" and local_changed:
            to_copy.append(rel)
        elif direction == "from" and remote_changed:
            to_copy.append(rel)
        elif direction == "to" and not local_changed and remote_changed:
            # Remote changed but we're pushing — skip (would overwrite remote changes)
            pass
        elif direction == "from" and not remote_changed and local_changed:
            # Local changed but we're pulling — skip (would overwrite local changes)
            pass

    # 3. Handle conflicts: copy the "other" version with .conflict- suffix
    for rel in conflicts:
        if dry_run:
            result.conflicts.append(rel)
            continue

        conflict_path = _conflict_name(rel)
        try:
            if direction == "to":
                # We're pushing local → remote. Save remote version as conflict.
                _scp_from_remote(
                    ssh_cmd, f"{remote_path}/{rel}", local_root / conflict_path
                )
            else:
                # We're pulling remote → local. Save local version as conflict.
                conflict_dest = local_root / conflict_path
                conflict_dest.parent.mkdir(parents=True, exist_ok=True)
                import shutil

                shutil.copy2(local_root / rel, conflict_dest)
            result.conflicts.append(rel)
        except Exception as e:
            result.errors.append(f"Conflict save failed for {rel}: {e}")

    # 4. Copy non-conflicting changed files
    for rel in to_copy:
        if dry_run:
            result.synced.append(rel)
            continue

        try:
            if direction == "to":
                _scp_to_remote(ssh_cmd, local_root / rel, f"{remote_path}/{rel}")
            else:
                _scp_from_remote(ssh_cmd, f"{remote_path}/{rel}", local_root / rel)
            result.synced.append(rel)
        except Exception as e:
            result.errors.append(f"Copy failed for {rel}: {e}")

    # 5. Also copy conflicting files (the "winning" direction still syncs)
    for rel in conflicts:
        if dry_run:
            continue
        try:
            if direction == "to":
                _scp_to_remote(ssh_cmd, local_root / rel, f"{remote_path}/{rel}")
            else:
                _scp_from_remote(ssh_cmd, f"{remote_path}/{rel}", local_root / rel)
        except Exception as e:
            result.errors.append(f"Conflict sync failed for {rel}: {e}")

    # 6. Update sync state with current checksums (merged)
    if not dry_run and result.ok:
        merged = {}
        for rel in all_files:
            # After sync, both sides should match — use the "winner"
            if direction == "to":
                merged[rel] = local_files.get(rel, remote_files.get(rel, ""))
            else:
                merged[rel] = remote_files.get(rel, local_files.get(rel, ""))
        _save_sync_state(local_root, merged)

    return result


def _scp_to_remote(ssh_cmd: list[str], local_path: Path, remote_rel: str) -> None:
    """Copy a single file to remote via SSH."""
    # Ensure remote directory exists
    remote_dir = str(Path(remote_rel).parent)
    subprocess.run(
        ssh_cmd + [f"mkdir -p {remote_dir}"],
        check=True,
        capture_output=True,
    )
    # Build scp command from ssh command
    host = ssh_cmd[-1]  # e.g. "scitex@host"
    port_idx = ssh_cmd.index("-p") + 1 if "-p" in ssh_cmd else None
    port = ssh_cmd[port_idx] if port_idx else "22"
    subprocess.run(
        ["scp", "-P", port, str(local_path), f"{host}:{remote_rel}"],
        check=True,
        capture_output=True,
    )


def _scp_from_remote(ssh_cmd: list[str], remote_rel: str, local_path: Path) -> None:
    """Copy a single file from remote via SSH."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    host = ssh_cmd[-1]
    port_idx = ssh_cmd.index("-p") + 1 if "-p" in ssh_cmd else None
    port = ssh_cmd[port_idx] if port_idx else "22"
    subprocess.run(
        ["scp", "-P", port, f"{host}:{remote_rel}", str(local_path)],
        check=True,
        capture_output=True,
    )


# EOF
