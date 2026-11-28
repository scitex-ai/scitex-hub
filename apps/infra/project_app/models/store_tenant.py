"""Which private store holds a project's Clew records.

Every project owner gets one tenant in the Clew store (a PostgreSQL namespace
reached through an unprivileged login, ``scitex_dev.store.TenantScope``), and
every project one scope inside it. Both are provisioned by the Hub
(``services.project_store_provisioning``) instead of being hand-listed in the
deployment configuration, so a new account's first project opens in Clew
without an operator step.
"""

from __future__ import annotations

import uuid

from django.contrib.auth.models import User
from django.db import models

from apps import field_encryption

from .repository import Project


class ProjectStoreTenant(models.Model):
    """The project owner's tenant in the Clew store."""

    owner = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="project_store_tenant"
    )
    tenant_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # field_encryption ciphertext of the tenant login's DSN (it carries the
    # login password). Never logged, never sent to a browser.
    dsn = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Columns holding field_encryption ciphertext (reencrypt_encrypted_fields).
    ENCRYPTED_FIELDS = ("dsn",)

    class Meta:
        verbose_name = "Project store tenant"

    def __str__(self):
        return f"store tenant of {self.owner_id}"

    def set_dsn(self, value: str) -> None:
        self.dsn = field_encryption.encrypt(value)

    def get_dsn(self) -> str:
        return field_encryption.decrypt(self.dsn)


class ProjectStoreScope(models.Model):
    """The Clew project scope of one project inside its owner's tenant."""

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="store_scope"
    )
    scope = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Project store scope"

    def __str__(self):
        return f"{self.project_id}: {self.scope}"
