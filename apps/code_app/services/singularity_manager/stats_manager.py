#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/stats_manager.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/stats_manager.py"
# ----------------------------------------

"""
Singularity Statistics Manager

Job execution statistics tracking and reporting.
"""

import logging
from typing import Dict, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


class StatsManager:
    """
    Manage execution statistics

    Handles:
    - Job execution tracking
    - Success/failure counting
    - Execution time tracking
    - User statistics
    """

    def __init__(self, config):
        """
        Initialize statistics manager

        Args:
            config: SingularityConfig instance
        """
        self.config = config

    def update_stats(self, user_id: int, execution_time: float, success: bool):
        """
        Update execution statistics

        Args:
            user_id: User ID
            execution_time: Job execution time in seconds
            success: Whether the job succeeded
        """
        try:
            stats = cache.get(self.config.cache_key_stats, {})

            user_key = f"user_{user_id}"
            if user_key not in stats:
                stats[user_key] = {
                    'total_jobs': 0,
                    'successful_jobs': 0,
                    'failed_jobs': 0,
                    'total_time': 0.0,
                }

            stats[user_key]['total_jobs'] += 1
            if success:
                stats[user_key]['successful_jobs'] += 1
            else:
                stats[user_key]['failed_jobs'] += 1
            stats[user_key]['total_time'] += execution_time

            cache.set(self.config.cache_key_stats, stats, 3600 * 24)  # 24 hours

        except Exception as e:
            logger.error(f"Failed to update stats: {e}")

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get execution statistics for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary with job statistics
        """
        stats = cache.get(self.config.cache_key_stats, {})
        user_key = f"user_{user_id}"
        return stats.get(user_key, {
            'total_jobs': 0,
            'successful_jobs': 0,
            'failed_jobs': 0,
            'total_time': 0.0,
        })


# EOF
