#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/accounts_app/models.py"""

import pytest

# from apps.infra.accounts_app.models import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/accounts_app/models.py
# --------------------------------------------------------------------------------
# from django.db import models
# from django.contrib.auth.models import User
# import secrets
# import hashlib
#
#
# # Japanese Academic domains to recognize
# JAPANESE_ACADEMIC_DOMAINS = [
#     # Japanese Academic (.ac.jp) - All academic institutions
#     ".ac.jp",
#     ".u-tokyo.ac.jp",
#     ".kyoto-u.ac.jp",
#     ".osaka-u.ac.jp",
#     ".tohoku.ac.jp",
#     ".nagoya-u.ac.jp",
#     ".kyushu-u.ac.jp",
#     ".hokudai.ac.jp",
#     ".tsukuba.ac.jp",
#     ".hiroshima-u.ac.jp",
#     ".kobe-u.ac.jp",
#     ".waseda.jp",
#     ".keio.ac.jp",
#     # Government Research Institutions (.go.jp)
#     ".go.jp",  # Broader government research support
#     ".riken.jp",
#     ".aist.go.jp",
#     ".nict.go.jp",
#     ".jaxa.jp",
#     ".jst.go.jp",
#     ".nims.go.jp",
#     ".nies.go.jp",
# ]
#
#
# def is_japanese_academic_email(email):
#     """Check if email belongs to Japanese academic institution"""
#     if not email:
#         return False
#     try:
#         domain = email.lower().split("@")[1]
#         # Check if domain matches exactly or ends with the academic domain
#         for academic_domain in JAPANESE_ACADEMIC_DOMAINS:
#             # Remove leading dot for exact matching
#             clean_domain = academic_domain.lstrip(".")
#             if domain == clean_domain or domain.endswith(academic_domain):
#                 return True
#         return False
#     except (IndexError, AttributeError):
#         return False
#
#
# class UserProfile(models.Model):
#     """Extended user profile for researchers"""
#
#     VISIBILITY_CHOICES = [
#         ("public", "Public"),
#         ("restricted", "Restricted"),
#         ("private", "Private"),
#     ]
#
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
#     avatar = models.ImageField(
#         upload_to="avatars/", blank=True, null=True, help_text="Profile picture"
#     )
#     bio = models.TextField(
#         max_length=500,
#         blank=True,
#         help_text="Brief description of your research background",
#     )
#     location = models.CharField(
#         max_length=200,
#         blank=True,
#         help_text="Your current location (e.g., 'Tokyo, Japan')",
#     )
#     timezone = models.CharField(
#         max_length=100,
#         blank=True,
#         default="UTC",
#         help_text="Your timezone (e.g., 'Asia/Tokyo')",
#     )
#     institution = models.CharField(
#         max_length=200, blank=True, help_text="Your current institution"
#     )
#     research_interests = models.TextField(
#         max_length=500, blank=True, help_text="Your research areas and interests"
#     )
#     website = models.URLField(
#         blank=True, help_text="Your personal or professional website"
#     )
#
#     # Academic information
#     orcid = models.CharField(
#         max_length=19,
#         blank=True,
#         help_text="Your ORCID identifier (e.g., 0000-0000-0000-0000)",
#     )
#     academic_title = models.CharField(
#         max_length=100,
#         blank=True,
#         help_text="Your academic title (e.g., PhD, Professor)",
#     )
#     department = models.CharField(
#         max_length=200, blank=True, help_text="Your department or faculty"
#     )
#
#     # Professional links
#     google_scholar = models.URLField(
#         blank=True, help_text="Your Google Scholar profile"
#     )
#     linkedin = models.URLField(blank=True, help_text="Your LinkedIn profile")
#     researchgate = models.URLField(blank=True, help_text="Your ResearchGate profile")
#     twitter = models.CharField(
#         max_length=50, blank=True, help_text="Your Twitter handle (without @)"
#     )
#
#     # Git hosting profiles (for public bio display)
#     github_profile = models.CharField(
#         max_length=100, blank=True, help_text="Your GitHub username"
#     )
#     gitlab_profile = models.CharField(
#         max_length=100, blank=True, help_text="Your GitLab username"
#     )
#     bitbucket_profile = models.CharField(
#         max_length=100, blank=True, help_text="Your Bitbucket username"
#     )
#
#     # Privacy settings
#     profile_visibility = models.CharField(
#         max_length=20,
#         choices=VISIBILITY_CHOICES,
#         default="public",
#         help_text="Who can view your profile",
#     )
#     is_public = models.BooleanField(default=True, help_text="Make profile public")
#     show_email = models.BooleanField(
#         default=False, help_text="Show email in public profile"
#     )
#     allow_collaboration = models.BooleanField(
#         default=True, help_text="Allow collaboration requests"
#     )
#     allow_messages = models.BooleanField(
#         default=True, help_text="Allow messages from other users"
#     )
#
#     # Academic institution recognition
#     is_academic_ja = models.BooleanField(
#         default=False,
#         help_text="Automatically detected: User belongs to Japanese academic institution",
#     )
#
#     # Last active repository tracking
#     last_active_repository = models.ForeignKey(
#         "project_app.Project",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="last_active_for_users",
#         help_text="Last repository the user was working on",
#     )
#
#     # SSH Key Management
#     ssh_public_key = models.TextField(
#         blank=True, help_text="User's SSH public key for Git operations"
#     )
#     ssh_key_fingerprint = models.CharField(
#         max_length=100, blank=True, help_text="SSH key fingerprint (SHA256)"
#     )
#     ssh_key_created_at = models.DateTimeField(
#         null=True, blank=True, help_text="When SSH key was generated"
#     )
#     ssh_key_last_used_at = models.DateTimeField(
#         null=True, blank=True, help_text="Last time SSH key was used"
#     )
#
#     # Git Platform Integration Tokens
#     github_token = models.CharField(
#         max_length=255,
#         blank=True,
#         help_text="GitHub Personal Access Token for importing private repos",
#     )
#     gitlab_token = models.CharField(
#         max_length=255,
#         blank=True,
#         help_text="GitLab Personal Access Token for importing private repos",
#     )
#     bitbucket_token = models.CharField(
#         max_length=255,
#         blank=True,
#         help_text="Bitbucket App Password for importing private repos",
#     )
#
#     # Account deletion
#     deletion_scheduled_at = models.DateTimeField(
#         null=True, blank=True, help_text="When account deletion was scheduled"
#     )
#
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         ordering = ["user__last_name", "user__first_name"]
#         db_table = (
#             "core_app_userprofile"  # Keep the same table name for smooth migration
#         )
#
#     def __str__(self):
#         return f"Profile for {self.user.get_full_name() or self.user.username}"
#
#     def get_display_name(self):
#         """Get the best display name for the user"""
#         if self.user.first_name and self.user.last_name:
#             return f"{self.user.first_name} {self.user.last_name}"
#         return self.user.username
#
#     def get_ssh_manager(self):
#         """Get SSH key manager for this user"""
#         from apps.api.v1.auth.ssh_key_manager import SSHKeyManager
#
#         return SSHKeyManager(self.user)
#
#     def get_full_title(self):
#         """Get full academic title and name"""
#         name = self.get_display_name()
#         if self.academic_title:
#             return f"{self.academic_title} {name}"
#         return name
#
#     def is_complete(self):
#         """Check if profile has essential information"""
#         return bool(self.bio and self.institution and self.research_interests)
#
#     @property
#     def total_documents(self):
#         """Get total number of documents created by the user"""
#         return self.user.documents.count()
#
#     @property
#     def total_projects(self):
#         """Get total number of projects owned by the user"""
#         return self.user.owned_projects.count()
#
#     def get_user_projects(self):
#         """Get all projects owned by the user, ordered by last activity"""
#         from apps.infra.project_app.models import Project
#
#         return Project.objects.filter(owner=self.user).order_by("-updated_at")
#
#     @property
#     def total_collaborations(self):
#         """Get total number of collaborations"""
#         # Import here to avoid circular dependency
#         from apps.infra.project_app.models import ProjectPermission
#
#         return ProjectPermission.objects.filter(user=self.user).count()
#
#     def get_social_links(self):
#         """Get available social/professional links"""
#         links = []
#         if self.website:
#             links.append(("Website", self.website))
#         if self.google_scholar:
#             links.append(("Google Scholar", self.google_scholar))
#         if self.linkedin:
#             links.append(("LinkedIn", self.linkedin))
#         if self.researchgate:
#             links.append(("ResearchGate", self.researchgate))
#         if self.twitter:
#             links.append(("Twitter", f"https://twitter.com/{self.twitter}"))
#         return links
#
#     def update_academic_status(self):
#         """Update is_academic_ja flag based on user's email"""
#         self.is_academic_ja = is_japanese_academic_email(self.user.email)
#         return self.is_academic_ja
#
#     def get_academic_status_display(self):
#         """Get display text for academic status"""
#         if self.is_academic_ja:
#             return "Japanese Academic Institution"
#         return "General User"
#
#     def save(self, *args, **kwargs):
#         """Override save to automatically update academic status"""
#         # Update academic status before saving
#         self.update_academic_status()
#         super().save(*args, **kwargs)
#
#
# class WorkspaceSSHKey(models.Model):
#     """
#     SSH public keys for workspace access via SSH gateway.
#
#     These are user-uploaded public keys used to authenticate
#     when SSHing into their workspace containers.
#
#     Different from UserProfile.ssh_public_key which is server-generated
#     and used for Git operations to external services.
#     """
#
#     user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name="workspace_ssh_keys"
#     )
#     title = models.CharField(
#         max_length=100,
#         help_text="Descriptive name for this key (e.g., 'Work Laptop', 'Home PC')",
#     )
#     public_key = models.TextField(help_text="SSH public key content")
#     fingerprint = models.CharField(
#         max_length=100, help_text="SSH key fingerprint (SHA256)"
#     )
#     key_type = models.CharField(
#         max_length=20,
#         help_text="Key algorithm (rsa, ed25519, ecdsa, etc.)",
#         default="rsa",
#     )
#
#     # Usage tracking
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_used_at = models.DateTimeField(
#         null=True, blank=True, help_text="Last time this key was used for authentication"
#     )
#
#     class Meta:
#         ordering = ["-created_at"]
#         db_table = "accounts_app_workspacesshkey"
#         unique_together = [["user", "fingerprint"]]
#
#     def __str__(self):
#         return f"{self.title} ({self.fingerprint[:16]}...)"
#
#
# class APIKey(models.Model):
#     """API keys for programmatic access to SciTeX Cloud"""
#
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
#     name = models.CharField(
#         max_length=100, help_text="Descriptive name for this API key"
#     )
#     key_prefix = models.CharField(
#         max_length=8,
#         unique=True,
#         help_text="First 8 characters of the key (for display)",
#     )
#     key_hash = models.CharField(
#         max_length=64, unique=True, help_text="SHA256 hash of the full key"
#     )
#
#     # Permissions
#     scopes = models.JSONField(
#         default=list, help_text="List of allowed scopes/permissions"
#     )
#
#     # Usage tracking
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_used_at = models.DateTimeField(null=True, blank=True)
#     expires_at = models.DateTimeField(
#         null=True, blank=True, help_text="When this key expires (optional)"
#     )
#
#     # Status
#     is_active = models.BooleanField(default=True)
#
#     class Meta:
#         ordering = ["-created_at"]
#         db_table = "profile_app_apikey"
#
#     def __str__(self):
#         return f"{self.name} ({self.key_prefix}...)"
#
#     @classmethod
#     def generate_key(cls):
#         """
#         Generate a new API key.
#
#         Returns:
#             str: The full API key (scitex_xxxxx...)
#         """
#         # Generate 32 bytes = 64 hex characters
#         random_bytes = secrets.token_bytes(32)
#         key = random_bytes.hex()
#         return f"scitex_{key}"
#
#     @classmethod
#     def hash_key(cls, key: str) -> str:
#         """Hash an API key for storage."""
#         return hashlib.sha256(key.encode()).hexdigest()
#
#     @classmethod
#     def create_key(cls, user, name, scopes=None, expires_at=None):
#         """
#         Create a new API key for a user.
#
#         Args:
#             user: User instance
#             name: Name/description for the key
#             scopes: List of permission scopes
#             expires_at: Optional expiration datetime
#
#         Returns:
#             tuple: (APIKey instance, full_key_string)
#         """
#         full_key = cls.generate_key()
#         key_hash = cls.hash_key(full_key)
#         key_prefix = full_key[:8]  # "scitex_x"
#
#         api_key = cls.objects.create(
#             user=user,
#             name=name,
#             key_prefix=key_prefix,
#             key_hash=key_hash,
#             scopes=scopes or [],
#             expires_at=expires_at,
#         )
#
#         return api_key, full_key
#
#     def verify_key(self, key: str) -> bool:
#         """Verify if a provided key matches this API key."""
#         return self.key_hash == self.hash_key(key)
#
#     def is_valid(self):
#         """Check if key is active and not expired."""
#         if not self.is_active:
#             return False
#         if self.expires_at and self.expires_at < models.DateTimeField().now():
#             return False
#         return True
#
#     def has_scope(self, scope: str) -> bool:
#         """Check if key has a specific scope/permission."""
#         return scope in self.scopes or "*" in self.scopes

# --------------------------------------------------------------------------------
# End of Source Code from: apps/accounts_app/models.py
# --------------------------------------------------------------------------------
