#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 14:46:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/code_app/services/singularity_manager/exceptions.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/code_app/services/singularity_manager/exceptions.py"
# ----------------------------------------

"""
Singularity Manager Exceptions

Custom exceptions for Singularity container operations.
"""


class SingularityError(Exception):
    """Raised when Singularity operations fail."""
    pass


# EOF
