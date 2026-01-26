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
    settings, "SINGULARITY_IMAGE_PATH", "/app/singularity/scitex-user-workspace.sif"
)

# User data directory (inside Docker container)
USER_DATA_ROOT = Path(getattr(settings, "USER_DATA_ROOT", "/app/data/users"))


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
    "SCITEX_SLURM_CONTAINER_PATH", "/opt/scitex/singularity/scitex-user-workspace.sif"
)
SLURM_USER_DATA_ROOT = Path(
    os.environ.get("SCITEX_CLOUD_SLURM_USER_DATA_ROOT")
    or os.environ.get("SCITEX_SLURM_USER_DATA_ROOT", "/opt/scitex/data/users")
)


# EOF
