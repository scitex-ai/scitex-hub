#!/usr/bin/env python3
"""
Statistics and quota management for User Container Manager
"""

from typing import Dict, Any
from django.contrib.auth.models import User
from django.core.cache import cache


class StatsManager:
    """Manage container statistics and quotas"""

    def __init__(self, config, path_utils):
        self.config = config
        self.path_utils = path_utils

    def get_container_stats(self, user: User) -> Dict[str, Any]:
        """Get user's container statistics"""
        user_dir = self.path_utils.get_user_dir(user)
        container_path = self.path_utils.get_user_container_path(user)
        sandbox_path = self.path_utils.get_sandbox_path(user)

        stats = {
            'has_custom': container_path.exists(),
            'has_sandbox': sandbox_path.exists(),
            'container_size_mb': 0,
            'sandbox_size_mb': 0,
            'total_size_mb': 0,
            'quota_used_percentage': 0,
        }

        # Container size
        if container_path.exists():
            stats['container_size_mb'] = container_path.stat().st_size / 1024**2

        # Sandbox size
        if sandbox_path.exists():
            total = sum(
                f.stat().st_size
                for f in sandbox_path.rglob('*')
                if f.is_file()
            )
            stats['sandbox_size_mb'] = total / 1024**2

        # Total
        stats['total_size_mb'] = stats['container_size_mb'] + stats['sandbox_size_mb']
        stats['total_size_gb'] = stats['total_size_mb'] / 1024

        # Quota
        quota_gb = self.config.max_container_size / 1024**3
        stats['quota_gb'] = quota_gb
        stats['quota_used_percentage'] = (stats['total_size_gb'] / quota_gb) * 100

        return stats

    def check_build_rate_limit(self, user: User) -> tuple[bool, str]:
        """Check if user has exceeded build rate limit"""
        cache_key = f"{self.config.cache_prefix}builds_{user.id}"
        builds_today = cache.get(cache_key, 0)

        if builds_today >= self.config.max_builds_per_day:
            return False, f"Build limit reached ({self.config.max_builds_per_day}/day)"

        return True, "OK"

    def increment_build_count(self, user: User):
        """Increment user's build count for today"""
        cache_key = f"{self.config.cache_prefix}builds_{user.id}"
        builds = cache.get(cache_key, 0)
        # Cache for 24 hours
        cache.set(cache_key, builds + 1, 86400)

# EOF
