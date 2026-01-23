"""
User Style Presets for SCITEX_STYLE Customization
"""

import uuid

from django.contrib.auth.models import User
from django.db import models


class UserStylePreset(models.Model):
    """User-defined style presets for SCITEX_STYLE customization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="style_presets"
    )

    # Preset identification
    name = models.CharField(
        max_length=100, help_text="Preset name (e.g., 'Nature Style', 'My Thesis')"
    )
    description = models.TextField(
        blank=True, help_text="Optional description of this style preset"
    )

    # Style configuration stored as YAML-compatible JSON
    style_config = models.JSONField(
        default=dict, help_text="SCITEX_STYLE overrides in YAML-compatible format"
    )

    # Active status
    is_active = models.BooleanField(
        default=False, help_text="Whether this is the currently active preset"
    )

    # Built-in presets cannot be deleted
    is_builtin = models.BooleanField(
        default=False, help_text="Built-in preset (e.g., SciTeX Default)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-is_builtin", "name"]
        unique_together = ["user", "name"]

    def __str__(self):
        active_marker = " (Active)" if self.is_active else ""
        builtin_marker = " [Built-in]" if self.is_builtin else ""
        return f"{self.name}{active_marker}{builtin_marker}"

    def activate(self):
        """Set this preset as active and deactivate others"""
        UserStylePreset.objects.filter(user=self.user, is_active=True).update(
            is_active=False
        )
        self.is_active = True
        self.save()
