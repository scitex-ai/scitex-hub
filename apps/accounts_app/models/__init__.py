"""
Accounts App Models - User Profiles and Authentication

Exports all models for backward compatibility:
    from apps.accounts_app.models import UserProfile, APIKey, ...
"""

from .api_key import APIKey
from .profile import (
    JAPANESE_ACADEMIC_DOMAINS,
    UserProfile,
    is_japanese_academic_email,
)
from .ssh import WorkspaceSSHKey

__all__ = [
    # profile.py
    "UserProfile",
    "JAPANESE_ACADEMIC_DOMAINS",
    "is_japanese_academic_email",
    # ssh.py
    "WorkspaceSSHKey",
    # api_key.py
    "APIKey",
]
