#!/usr/bin/env python3
"""
User Container Manager for SciTeX-Code
Enables users to customize their Apptainer/Singularity environments using fakeroot.

Features:
- Two-tier system: Base container + user customization
- Fakeroot support for rootless container building
- Web-based package installation
- Definition file upload
- Storage quotas

Modular structure:
- exceptions: Exception classes
- config: Configuration and initialization
- path_utils: Path management utilities
- stats: Statistics and quota management
- container_ops: Container build and management operations
- package_ops: Package installation operations
- manager: Main orchestrator class
"""

from .exceptions import UserContainerError
from .manager import UserContainerManager

# Global instance for backward compatibility
user_container_manager = UserContainerManager()

# Public API
__all__ = [
    'UserContainerError',
    'UserContainerManager',
    'user_container_manager',
]

# EOF
