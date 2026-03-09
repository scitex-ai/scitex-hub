"""
Workspace SSH Key Models

WorkspaceSSHKey - SSH public keys for workspace access via SSH gateway
"""

from django.contrib.auth.models import User
from django.db import models


class WorkspaceSSHKey(models.Model):
    """
    SSH public keys for workspace access via SSH gateway.

    These are user-uploaded public keys used to authenticate
    when SSHing into their workspace containers.

    Different from UserProfile.ssh_public_key which is server-generated
    and used for Git operations to external services.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="workspace_ssh_keys"
    )
    title = models.CharField(
        max_length=100,
        help_text="Descriptive name for this key (e.g., 'Work Laptop', 'Home PC')",
    )
    public_key = models.TextField(help_text="SSH public key content")
    fingerprint = models.CharField(
        max_length=100, help_text="SSH key fingerprint (SHA256)"
    )
    key_type = models.CharField(
        max_length=20,
        help_text="Key algorithm (rsa, ed25519, ecdsa, etc.)",
        default="rsa",
    )

    # Usage tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this key was used for authentication",
    )

    class Meta:
        ordering = ["-created_at"]
        db_table = "accounts_app_workspacesshkey"
        unique_together = [["user", "fingerprint"]]

    def __str__(self):
        return f"{self.title} ({self.fingerprint[:16]}...)"
