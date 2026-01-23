#!/usr/bin/env python3
"""
Environment Management for SciTeX-Code
Provides reproducible Python environments with package management.

This module maintains backward compatibility by re-exporting all classes.
"""

from .exceptions import EnvironmentError
from .models import PackageRequirement, Environment
from .manager import EnvironmentManager
from .workflow_manager import WorkflowManager

__all__ = [
    "EnvironmentError",
    "PackageRequirement",
    "Environment",
    "EnvironmentManager",
    "WorkflowManager",
]
