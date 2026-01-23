#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/resource_manager.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/resource_manager.py"
# ----------------------------------------

"""
Singularity Resource Manager

Job counting and concurrency control for Singularity containers.
"""

from typing import Tuple
from django.core.cache import cache


class ResourceManager:
    """
    Manage resource allocation and job concurrency

    Handles:
    - Active job counting
    - Concurrency limits
    - Resource availability checks
    """

    def __init__(self, config):
        """
        Initialize resource manager

        Args:
            config: SingularityConfig instance
        """
        self.config = config

    def get_active_job_count(self) -> int:
        """Get current number of active Singularity jobs"""
        return cache.get(self.config.cache_key_active, 0)

    def _increment_job_count(self):
        """Increment active job counter"""
        count = self.get_active_job_count()
        cache.set(self.config.cache_key_active, count + 1, self.config.cache_ttl)

    def _decrement_job_count(self):
        """Decrement active job counter"""
        count = self.get_active_job_count()
        cache.set(self.config.cache_key_active, max(0, count - 1), self.config.cache_ttl)

    def can_execute(self) -> Tuple[bool, str]:
        """
        Check if resources are available for execution

        Returns:
            (can_execute, reason)
        """
        active = self.get_active_job_count()

        if active >= self.config.max_concurrent:
            return False, f"Maximum concurrent jobs reached ({self.config.max_concurrent})"

        return True, "Resources available"


# EOF
