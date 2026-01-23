#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/__init__.py

"""
SciTeX Cloud - CLI tools for SciTeX deployment and management.

Usage:
    pip install scitex-cloud
    scitex-cloud --help
"""

__version__ = "0.1.0"
__author__ = "SciTeX Team"

from .config.environments import Environment, get_environment
from .utils.docker import DockerManager

__all__ = [
    "__version__",
    "Environment",
    "get_environment",
    "DockerManager",
]

# EOF
