"""
Remote Project Models
Supports TRAMP-like remote filesystem access via SSH/SSHFS
"""

from django.contrib.auth.models import User
from django.db import models


class RemoteCredential(models.Model):
    """
    SSH credentials for remote systems.

    Users can save multiple remote systems (HPC clusters, cloud instances, personal servers)
    and reuse them when creating remote projects.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="remote_credentials"
    )

    # Remote System Info
    name = models.CharField(
        max_length=100, help_text="Display name (e.g., 'Spartan HPC', 'AWS Server')"
    )
    ssh_host = models.CharField(max_length=255, help_text="Hostname or IP address")
    ssh_port = models.IntegerField(default=22)
    ssh_username = models.CharField(
        max_length=100, help_text="Username on remote system"
    )

    # SSH Key
    ssh_public_key = models.TextField(help_text="SSH public key (RSA, ED25519, etc.)")
    ssh_key_fingerprint = models.CharField(
        max_length=100, help_text="SSH key fingerprint for display"
    )
    private_key_path = models.CharField(
        max_length=500, help_text="Path to private key file on server"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [["user", "name"]]
        ordering = ["-last_used_at", "-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} → {self.name} ({self.ssh_username}@{self.ssh_host})"
        )


class RemoteProjectConfig(models.Model):
    """
    Configuration for remote filesystem access.

    Remote projects use SSHFS to mount remote directories on-demand,
    providing TRAMP-like access without local data storage.
    """

    # Back-reference to Project (OneToOne)
    project = models.OneToOneField(
        "Project",
        on_delete=models.CASCADE,
        related_name="remote_config",
        help_text="Associated project",
    )

    # SSH Connection
    ssh_host = models.CharField(max_length=255, help_text="Remote hostname")
    ssh_port = models.IntegerField(default=22)
    ssh_username = models.CharField(
        max_length=100, help_text="Username on remote system"
    )

    # SSH Key (reference to user's remote credential)
    remote_credential = models.ForeignKey(
        RemoteCredential,
        on_delete=models.CASCADE,
        help_text="SSH key for authentication",
    )

    # Remote Path
    remote_path = models.CharField(
        max_length=500,
        help_text="Absolute path on remote system (e.g., /home/username/project)",
    )

    # Connection mode: trip (on-demand SFTP) or sshfs (persistent mount)
    CONNECTION_MODES = [
        ("trip", "TRIP (on-demand SSH)"),
        ("sshfs", "SSHFS (persistent mount)"),
    ]
    connection_mode = models.CharField(
        max_length=10,
        choices=CONNECTION_MODES,
        default="trip",
        help_text="trip = on-demand SSH/SFTP (like TRAMP), sshfs = persistent fuse mount",
    )

    # Mount State (only used when connection_mode = "sshfs")
    is_mounted = models.BooleanField(default=False)
    mount_point = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Local mount point (e.g., /tmp/scitex_remote/1/project-slug/)",
    )
    mounted_at = models.DateTimeField(
        null=True, blank=True, help_text="When mount was created"
    )
    last_accessed = models.DateTimeField(
        null=True, blank=True, help_text="Last time remote filesystem was accessed"
    )

    # Connection Test
    last_test_at = models.DateTimeField(
        null=True, blank=True, help_text="Last connection test timestamp"
    )
    last_test_success = models.BooleanField(
        default=False, help_text="Whether last connection test succeeded"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "🟢 Mounted" if self.is_mounted else "⚫ Not mounted"
        return f"{self.project.name} → {self.ssh_username}@{self.ssh_host}:{self.remote_path} [{status}]"

    class Meta:
        verbose_name = "Remote Project Configuration"
        verbose_name_plural = "Remote Project Configurations"


class TripProjectConfig(models.Model):
    """
    TRIP (Transparent Remote Interaction Protocols) configuration.

    On-demand SSH access to remote filesystems — no mount, no local copy.
    Inspired by Emacs TRAMP. Terminal SSHs directly into remote machine.
    """

    project = models.OneToOneField(
        "Project",
        on_delete=models.CASCADE,
        related_name="trip_config",
        help_text="Associated project",
    )

    remote_credential = models.ForeignKey(
        RemoteCredential,
        on_delete=models.CASCADE,
        related_name="trip_projects",
        help_text="SSH credential for authentication",
    )

    remote_path = models.CharField(
        max_length=500,
        help_text="Absolute path on remote system (e.g., /home/username/project)",
    )

    # Access tracking
    last_accessed = models.DateTimeField(
        null=True, blank=True, help_text="Last time remote was accessed"
    )

    # Connection test
    last_test_at = models.DateTimeField(
        null=True, blank=True, help_text="Last connection test timestamp"
    )
    last_test_success = models.BooleanField(
        default=False, help_text="Whether last connection test succeeded"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TRIP Project Configuration"
        verbose_name_plural = "TRIP Project Configurations"

    def __str__(self):
        cred = self.remote_credential
        return f"{self.project.name} -> {cred.ssh_username}@{cred.ssh_host}:{self.remote_path}"
