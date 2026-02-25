"""
Terminal Configuration
Centralized configuration for terminal sessions, SLURM, and Apptainer
"""

import os
from pathlib import Path

from django.conf import settings

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
# Support both new (SCITEX_CLOUD_*) and legacy (SCITEX_CLOUD_QUOTA_*) names
SLURM_PARTITION = os.environ.get(
    "SCITEX_CLOUD_SLURM_INTERACTIVE_PARTITION"
) or os.environ.get("SCITEX_CLOUD_QUOTA_SLURM_INTERACTIVE_PARTITION", "express")
SLURM_TIME_LIMIT = os.environ.get(
    "SCITEX_CLOUD_SLURM_INTERACTIVE_TIME_LIMIT"
) or os.environ.get("SCITEX_CLOUD_QUOTA_SLURM_INTERACTIVE_TIME_LIMIT", "04:00:00")
SLURM_CPUS = int(
    os.environ.get("SCITEX_CLOUD_SLURM_INTERACTIVE_CPUS")
    or os.environ.get("SCITEX_CLOUD_QUOTA_SLURM_INTERACTIVE_CPUS", 2)
)
SLURM_MEMORY_GB = int(
    os.environ.get("SCITEX_CLOUD_SLURM_INTERACTIVE_MEMORY_GB")
    or os.environ.get("SCITEX_CLOUD_QUOTA_SLURM_INTERACTIVE_MEMORY_GB", 4)
)

# SLURM host paths - jobs run on compute nodes, not inside Docker
# These paths must be accessible from the SLURM compute nodes
# Using /opt/scitex to avoid NAS ACL issues with home directories
SLURM_CONTAINER_PATH = os.environ.get(
    "SCITEX_CLOUD_SLURM_CONTAINER_PATH"
) or os.environ.get(
    "SCITEX_SLURM_CONTAINER_PATH",
    "/opt/scitex/singularity/current-sandbox",
)
SLURM_USER_DATA_ROOT = Path(
    os.environ.get("SCITEX_CLOUD_SLURM_USER_DATA_ROOT")
    or os.environ.get("SCITEX_SLURM_USER_DATA_ROOT", "/opt/scitex/data/users")
)

# =============================================================================
# Dev Mode: Editable repo mounts
# =============================================================================
# In dev, bind-mount full repos into the container for editable install.
# Paths are HOST paths (for SLURM --bind), not Docker-internal paths.
#
# Comma-separated entries: name:host_path:extras
# Example: scitex-python:/home/user/proj/scitex-python:all,figrecipe:...
DEV_REPOS_RAW = os.environ.get("SCITEX_CLOUD_DEV_REPOS", "")

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
SCITEX_DEV_SRC = os.environ.get("SCITEX_CLOUD_DEV_SCITEX_SRC", "")
FIGRECIPE_DEV_SRC = os.environ.get("SCITEX_CLOUD_DEV_FIGRECIPE_SRC", "")


# =============================================================================
# Host Package Bind Mounts (shared between Apptainer and Docker)
# =============================================================================
# Generic host mounts: host_path:container_path:mode (comma-separated)
HOST_MOUNTS_RAW = os.environ.get("SCITEX_CLOUD_HOST_MOUNTS", "")

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
HOST_TEXLIVE_PREFIX = os.environ.get("SCITEX_CLOUD_HOST_TEXLIVE_PREFIX", "")


# EOF
