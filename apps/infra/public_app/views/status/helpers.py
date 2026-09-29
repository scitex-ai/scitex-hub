#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/helpers.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/status/helpers.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Status View Helper Functions

Utility functions for GPU info, GPU utilization, and user counts.
"""

import logging
import subprocess

logger = logging.getLogger("scitex")


def get_gpu_utilization():
    """Get GPU utilization percentage."""
    gpu_percent = None
    try:
        # Try NVIDIA nvidia-smi
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu_percent = float(result.stdout.strip().split("\n")[0])
        except:
            pass

        # Try AMD rocm-smi
        if gpu_percent is None:
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showuse"], capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0 and result.stdout:
                    import re

                    for line in result.stdout.split("\n"):
                        if "GPU use" in line or "%" in line:
                            match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                            if match:
                                gpu_percent = float(match.group(1))
                                break
            except:
                pass
    except:
        pass

    return gpu_percent


def check_registered_users_count(status_data):
    """Count total registered users (excluding visitors)."""
    try:
        from django.contrib.auth.models import User

        # Count users excluding visitor accounts (visitor-001, visitor-002, etc.)
        total_registered = User.objects.exclude(username__startswith="visitor-").count()

        status_data["registered_users"] = {
            "total": total_registered,
        }
    except Exception as e:
        logger.warning(f"Could not get registered users count: {e}")
        status_data["registered_users"] = {"total": 0, "error": str(e)}
# EOF
