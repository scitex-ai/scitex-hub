"""
API Key Models

APIKey - API keys for programmatic access to SciTeX Cloud
"""

import hashlib
import secrets

from django.contrib.auth.models import User
from django.db import models


class APIKey(models.Model):
    """API keys for programmatic access to SciTeX Cloud"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(
        max_length=100, help_text="Descriptive name for this API key"
    )
    key_prefix = models.CharField(
        max_length=8,
        unique=True,
        help_text="First 8 characters of the key (for display)",
    )
    key_hash = models.CharField(
        max_length=64, unique=True, help_text="SHA256 hash of the full key"
    )

    # Permissions
    scopes = models.JSONField(
        default=list, help_text="List of allowed scopes/permissions"
    )

    # Usage tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="When this key expires (optional)"
    )

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "profile_app_apikey"

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    @classmethod
    def generate_key(cls):
        """
        Generate a new API key.

        Returns:
            str: The full API key (scitex_xxxxx...)
        """
        # Generate 32 bytes = 64 hex characters
        random_bytes = secrets.token_bytes(32)
        key = random_bytes.hex()
        return f"scitex_{key}"

    @classmethod
    def hash_key(cls, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def create_key(cls, user, name, scopes=None, expires_at=None):
        """
        Create a new API key for a user.

        Args:
            user: User instance
            name: Name/description for the key
            scopes: List of permission scopes
            expires_at: Optional expiration datetime

        Returns:
            tuple: (APIKey instance, full_key_string)
        """
        full_key = cls.generate_key()
        key_hash = cls.hash_key(full_key)
        key_prefix = full_key[:8]  # "scitex_x"

        api_key = cls.objects.create(
            user=user,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes or [],
            expires_at=expires_at,
        )

        return api_key, full_key

    def verify_key(self, key: str) -> bool:
        """Verify if a provided key matches this API key."""
        return self.key_hash == self.hash_key(key)

    def is_valid(self):
        """Check if key is active and not expired."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < models.DateTimeField().now():
            return False
        return True

    def has_scope(self, scope: str) -> bool:
        """Check if key has a specific scope/permission."""
        return scope in self.scopes or "*" in self.scopes
