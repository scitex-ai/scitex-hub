"""
Terminal Configuration
Centralized configuration for terminal sessions, SLURM, and Apptainer
"""

import os
from pathlib import Path

from django.conf import settings

# =============================================================================
# Terminal MOTD (Message of the Day)
# =============================================================================
# Defined first so that a partial module (re)load — e.g. if a later
# environment-dependent assignment raises — never leaves this name undefined.
SHOW_MOTD = os.environ.get("SCITEX_HUB_SHOW_MOTD", "true").lower() != "false"


# =============================================================================
# Container Configuration
# =============================================================================

# Base Apptainer image (shared by all users)
# For direct Apptainer execution inside Docker container
BASE_CONTAINER_PATH = getattr(
    settings,
    "SINGULARITY_IMAGE_PATH",
    "/app/singularity/current-sandbox",
)

# User data directory (inside Docker container)
USER_DATA_ROOT = Path(getattr(settings, "USER_DATA_ROOT", None) or "/app/data/users")


# =============================================================================
# SLURM Configuration
# =============================================================================

# SLURM settings for interactive sessions (from env vars)
# Support both new (SCITEX_HUB_*) and legacy (SCITEX_HUB_QUOTA_*) names
SLURM_PARTITION = os.environ.get(
    "SCITEX_HUB_SLURM_INTERACTIVE_PARTITION"
) or os.environ.get("SCITEX_HUB_QUOTA_SLURM_INTERACTIVE_PARTITION", "express")
SLURM_TIME_LIMIT = os.environ.get(
    "SCITEX_HUB_SLURM_INTERACTIVE_TIME_LIMIT"
) or os.environ.get("SCITEX_HUB_QUOTA_SLURM_INTERACTIVE_TIME_LIMIT", "04:00:00")
SLURM_CPUS = int(
    os.environ.get("SCITEX_HUB_SLURM_INTERACTIVE_CPUS")
    or os.environ.get("SCITEX_HUB_QUOTA_SLURM_INTERACTIVE_CPUS", 2)
)
SLURM_MEMORY_GB = int(
    os.environ.get("SCITEX_HUB_SLURM_INTERACTIVE_MEMORY_GB")
    or os.environ.get("SCITEX_HUB_QUOTA_SLURM_INTERACTIVE_MEMORY_GB", 4)
)

# SLURM host paths - jobs run on compute nodes, not inside Docker
# These paths must be accessible from the SLURM compute nodes
# Using /opt/scitex to avoid NAS ACL issues with home directories
SLURM_CONTAINER_PATH = os.environ.get(
    "SCITEX_HUB_SLURM_CONTAINER_PATH",
    "/opt/scitex/singularity/current-sandbox",
)
SLURM_USER_DATA_ROOT = Path(
    os.environ.get("SCITEX_HUB_SLURM_USER_DATA_ROOT", "/opt/scitex/data/users")
)

# =============================================================================
# Apptainer Persistent Overlay (SIF+overlay migration — DEFAULT OFF)
# =============================================================================
# Flag-gated, reversible foundation for the SIF+overlay migration.
# When ENABLED, each user's terminal session mounts a persistent
# per-user ``--overlay`` image (with ``--fakeroot``) in place of the
# ephemeral ``--writable-tmpfs`` write layer, so their container state
# persists across sessions.
#
# DEFAULT OFF: when disabled, the emitted apptainer command is
# byte-identical to today's ``--writable-tmpfs`` behavior (see
# ``resolve_overlay_kwargs`` in ``_command_builder.py`` — disabled
# yields an empty kwargs dict, so nothing extra is passed through to
# the scitex_container builders).
#
# Do NOT enable this without also provisioning the per-user overlay
# images under ``OVERLAY_ROOT`` on the SLURM compute nodes.
APPTAINER_OVERLAY_ENABLED = (
    os.environ.get("SCITEX_HUB_APPTAINER_OVERLAY_ENABLED", "false").lower() == "true"
)

# Host directory (on the SLURM compute nodes) holding per-user overlay
# images. Sibling of ``SLURM_USER_DATA_ROOT`` (/opt/scitex/data/users).
OVERLAY_ROOT = os.environ.get(
    "SCITEX_HUB_OVERLAY_ROOT", "/opt/scitex/data/overlays"
)

# =============================================================================
# Dev Mode: Editable repo mounts
# =============================================================================
# In dev, bind-mount full repos into the container for editable install.
# Paths are HOST paths (for SLURM --bind), not Docker-internal paths.
#
# Comma-separated entries: name:host_path:extras
# Example: scitex-python:/home/user/proj/scitex-python:all,figrecipe:...
DEV_REPOS_RAW = os.environ.get("SCITEX_HUB_DEV_REPOS", "")

DEV_REPOS: list[dict] = []
if DEV_REPOS_RAW:
    for _entry in DEV_REPOS_RAW.split(","):
        _parts = _entry.strip().split(":")
        if len(_parts) >= 2:
            DEV_REPOS.append(
                {
                    "name": _parts[0],
                    "host_path": _parts[1],
                    "extras": _parts[2] if len(_parts) > 2 else "all",
                }
            )

# Legacy vars (kept for backward compat)
SCITEX_DEV_SRC = os.environ.get("SCITEX_HUB_DEV_SCITEX_SRC", "")
FIGRECIPE_DEV_SRC = os.environ.get("SCITEX_HUB_DEV_FIGRECIPE_SRC", "")


# =============================================================================
# Host Package Bind Mounts (shared between Apptainer and Docker)
# =============================================================================
# Generic host mounts: host_path:container_path:mode (comma-separated)
HOST_MOUNTS_RAW = os.environ.get("SCITEX_HUB_HOST_MOUNTS", "")

HOST_MOUNTS: list[dict] = []
if HOST_MOUNTS_RAW:
    for _entry in HOST_MOUNTS_RAW.split(","):
        _parts = _entry.strip().split(":")
        if len(_parts) >= 2:
            HOST_MOUNTS.append(
                {
                    "host_path": _parts[0],
                    "container_path": _parts[1],
                    "mode": _parts[2] if len(_parts) > 2 else "ro",
                }
            )

# Texlive prefix shortcut (e.g., "/usr" → auto-mounts /usr/share/texlive, /usr/bin/pdflatex, etc.)
HOST_TEXLIVE_PREFIX = os.environ.get("SCITEX_HUB_HOST_TEXLIVE_PREFIX", "")


# =============================================================================
# SLURM Time Limit Parsing
# =============================================================================


def parse_time_limit_seconds(time_str: str) -> int:
    """Parse SLURM time limit string (HH:MM:SS or MM:SS) to seconds."""
    parts = time_str.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0]) * 60


SLURM_TIME_LIMIT_SECONDS = parse_time_limit_seconds(SLURM_TIME_LIMIT)


# EOF
