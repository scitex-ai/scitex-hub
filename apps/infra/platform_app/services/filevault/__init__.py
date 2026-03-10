"""
FileVault — per-app namespaced file storage within a project.

Public API:
    FileVault(app_name, project, user)  — see storage.py for methods
"""

from .storage import FileVault

__all__ = ["FileVault"]
