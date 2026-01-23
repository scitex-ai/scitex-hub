#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/config.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/config.py"
# ----------------------------------------

"""
Singularity Manager Configuration

Configuration and verification for Singularity containers.
"""

import subprocess
import logging
from pathlib import Path
from django.conf import settings

from .exceptions import SingularityError

logger = logging.getLogger(__name__)


class SingularityConfig:
    """
    Configuration manager for Singularity containers

    Handles:
    - Image path configuration
    - Timeout settings
    - Concurrency limits
    - Cache configuration
    - Singularity installation verification
    """

    def __init__(self):
        # Get configuration from Django settings
        self.image_path = Path(settings.SINGULARITY_IMAGE_PATH)
        self.max_concurrent = settings.SINGULARITY_MAX_CONCURRENT_JOBS
        self.default_timeout = settings.SINGULARITY_DEFAULT_TIMEOUT
        self.max_timeout = settings.SINGULARITY_MAX_TIMEOUT

        # Cache keys
        self.cache_key_active = 'singularity_active_jobs'
        self.cache_key_stats = 'singularity_stats'
        self.cache_ttl = 300  # 5 minutes

        # Verify Singularity is installed
        self._verify_singularity()

        # Verify image exists
        if not self.image_path.exists():
            logger.error(f"Singularity image not found: {self.image_path}")
            raise FileNotFoundError(
                f"Singularity image not found: {self.image_path}\n"
                f"Build it with: sudo singularity build {self.image_path} {self.image_path.with_suffix('.def')}"
            )

    def _verify_singularity(self):
        """Verify Singularity is installed and accessible"""
        try:
            result = subprocess.run(
                ["singularity", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Singularity version: {result.stdout.strip()}")
            else:
                raise SingularityError("Singularity not found or not working")
        except FileNotFoundError:
            raise SingularityError(
                "Singularity not installed. Install with: "
                "sudo apt-get install singularity-container"
            )
        except subprocess.TimeoutExpired:
            raise SingularityError("Singularity command timed out")


# EOF
