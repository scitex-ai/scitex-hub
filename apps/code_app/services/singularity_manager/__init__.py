#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/__init__.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/__init__.py"
# ----------------------------------------

"""
Singularity Container Manager Package

Superior security alternative to Docker for user code execution.

Security Benefits:
- No root daemon required
- No Docker socket mounting
- User runs as themselves (UID preserved)
- Designed for multi-user HPC environments
"""

import logging

from .exceptions import SingularityError
from .config import SingularityConfig
from .resource_manager import ResourceManager
from .cgroup_manager import CGroupManager
from .stats_manager import StatsManager
from .executor import SingularityExecutor
from .hpc_manager import HPCManager
from .manager import SingularityManager

logger = logging.getLogger(__name__)

# Global instance (singleton pattern)
# Initialize on first import
try:
    singularity_manager = SingularityManager()
    logger.info("SingularityManager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SingularityManager: {e}")
    singularity_manager = None

__all__ = [
    "SingularityError",
    "SingularityConfig",
    "ResourceManager",
    "CGroupManager",
    "StatsManager",
    "SingularityExecutor",
    "HPCManager",
    "SingularityManager",
    "singularity_manager",
]

# EOF
