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
    'SINGULARITY_IMAGE_PATH',
    '/app/singularity/scitex-user-workspace.sif'
)

# User data directory (inside Docker container)
USER_DATA_ROOT = Path(getattr(settings, 'USER_DATA_ROOT', '/app/data/users'))


# =============================================================================
# SLURM Configuration
# =============================================================================

# SLURM settings for interactive sessions (from env vars)
SLURM_PARTITION = os.environ.get('SCITEX_QUOTA_SLURM_INTERACTIVE_PARTITION', 'express')
SLURM_TIME_LIMIT = os.environ.get('SCITEX_QUOTA_SLURM_INTERACTIVE_TIME_LIMIT', '04:00:00')
SLURM_CPUS = int(os.environ.get('SCITEX_QUOTA_SLURM_INTERACTIVE_CPUS', 2))
SLURM_MEMORY_GB = int(os.environ.get('SCITEX_QUOTA_SLURM_INTERACTIVE_MEMORY_GB', 4))

# SLURM host paths - jobs run on compute nodes, not inside Docker
# These paths must be accessible from the SLURM compute nodes
# Using /opt/scitex to avoid NAS ACL issues with home directories
SLURM_CONTAINER_PATH = os.environ.get(
    'SCITEX_SLURM_CONTAINER_PATH',
    '/opt/scitex/singularity/scitex-user-workspace.sif'
)
SLURM_USER_DATA_ROOT = Path(os.environ.get(
    'SCITEX_SLURM_USER_DATA_ROOT',
    '/opt/scitex/data/users'
))


# EOF
