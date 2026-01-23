#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkflowSecret model for SciTeX Projects

Encrypted secrets for workflows (similar to GitHub Secrets).
Secrets can be defined at project or organization level.
"""

from django.db import models
from django.contrib.auth.models import User


class WorkflowSecret(models.Model):
    """
    Encrypted secrets for workflows (similar to GitHub Secrets)
    Secrets can be defined at project or organization level
    """

    SCOPE_CHOICES = [
        ("project", "Project"),
        ("organization", "Organization"),
    ]

    name = models.CharField(
        max_length=100, help_text="Secret name (uppercase, underscores only)"
    )
    encrypted_value = models.TextField(help_text="Encrypted secret value")

    # Scope
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default="project",
        help_text="Secret scope",
    )
    project = models.ForeignKey(
        "project_app.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_secrets",
        help_text="Associated project (for project-scoped secrets)",
    )
    organization = models.ForeignKey(
        "organizations_app.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_secrets",
        help_text="Associated organization (for org-scoped secrets)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workflow_secrets",
        help_text="User who created this secret",
    )
    last_used_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time this secret was used"
    )

    class Meta:
        app_label = "project_app"
        indexes = [
            models.Index(fields=["project", "name"]),
            models.Index(fields=["organization", "name"]),
        ]

    def __str__(self):
        scope_obj = self.project or self.organization
        return f"{scope_obj} - {self.name}"

    def encrypt_value(self, value):
        """Encrypt secret value"""
        from cryptography.fernet import Fernet
        from django.conf import settings

        # Get encryption key from settings
        key = settings.SCITEX_CLOUD_DJANGO_SECRET_KEY[:32].encode()
        f = Fernet(key)
        self.encrypted_value = f.encrypt(value.encode()).decode()

    def decrypt_value(self):
        """Decrypt and return secret value"""
        from cryptography.fernet import Fernet
        from django.conf import settings

        # Get encryption key from settings
        key = settings.SCITEX_CLOUD_DJANGO_SECRET_KEY[:32].encode()
        f = Fernet(key)
        return f.decrypt(self.encrypted_value.encode()).decode()


# EOF
