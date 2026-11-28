"""Authorized project-store credentials; schemas and operations belong to leaves.

Access follows the Hub's project permission model:

* **read** — anyone who can open the project in the Hub (its owner and every
  ``ProjectMembership``, whatever the permission level) reads that project's
  records. ``find_accessible_project`` is the same lookup the project picker
  and ``HubProjectStorage`` use, so the store can never be wider or narrower
  than the project itself.
* **write** — decided by ``HubProjectStorage.can_write`` (``Project.can_edit``:
  the owner, or a member with ``write``/``admin`` permission). Leaves request
  writes through ``scitex_sdk.host.project_access(write=True)``; this provider
  only selects the store.

The store belongs to the project, not to whoever is asking: credentials are the
project owner's tenant, and the project maps to one Clew project scope in it.
An operator may still configure an owner by hand
(``SCITEX_STORE_TENANT_SECRETS``, which wins for the projects it maps); every
other project gets a Hub-provisioned tenant and scope on its first use
(``project_store_provisioning``). A collaborator therefore reads the project's
records and nothing else of the owner's, and never their own same-named
project. Credentials never leave the server process.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from uuid import UUID

from django.conf import settings
from django.views.decorators.debug import sensitive_variables
from scitex_sdk.host import CapabilityUnavailable, StoreAccess

from .project_scope import find_accessible_project


class HubProjectStore:
    @sensitive_variables()
    def store_access(self, project_id, request):
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            raise CapabilityUnavailable("Authentication required")
        project = find_accessible_project(user, project_id)
        if project is None:
            raise CapabilityUnavailable("Project not available")
        # SECRET is deliberate: Django's technical error reporter must redact
        # this configuration, which contains credentials for multiple owners.
        configuration = getattr(settings, "SCITEX_STORE_TENANT_SECRETS", {})
        if isinstance(configuration, str):
            try:
                # Unset (empty) means no tenant is configured, not invalid.
                configuration = (
                    json.loads(configuration) if configuration.strip() else {}
                )
            except ValueError:
                raise CapabilityUnavailable(
                    "Private store configuration is invalid"
                ) from None
        if not isinstance(configuration, Mapping):
            raise CapabilityUnavailable("Private store configuration is invalid")
        owner_role = getattr(settings, "SCITEX_STORE_OWNER", "scitex_cloud_owner")
        entry = configuration.get(str(project.owner_id))
        if entry is not None:
            configured = self._configured_access(entry, project, owner_role)
            if configured is not None:
                return configured
        return self._provisioned_access(project, owner_role)

    @staticmethod
    @sensitive_variables()
    def _configured_access(entry, project, owner_role):
        """The operator's hand-configured entry for this project, if it maps it."""
        try:
            if not isinstance(entry, Mapping):
                raise ValueError
            projects = entry.get("projects")
            if not isinstance(projects, Mapping):
                raise ValueError
            tenant_id = UUID(str(entry["tenant_id"]))
            scope, dsn = projects.get(str(project.pk)), entry.get("dsn")
            if scope is None:
                return None
            if not tenant_id.int or any(
                not isinstance(value, str) or not value.strip()
                for value in (scope, dsn, owner_role)
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise CapabilityUnavailable(
                "Private store configuration is invalid"
            ) from None
        return StoreAccess(
            tenant_id=tenant_id, dsn=dsn, project_scope=scope, owner_role=owner_role
        )

    @staticmethod
    @sensitive_variables()
    def _provisioned_access(project, owner_role):
        """The Hub-provisioned store; provisioned now if this is its first use.

        This is what makes Clew work for an owner nobody configured by hand
        (scitex-hub#1231): the first authorized request for a project without
        a store provisions the owner's tenant and the project's scope through
        the separate administration connection, then reads with the tenant
        login like every later request.
        """
        from cryptography.fernet import InvalidToken

        from apps.infra.project_app.models import ProjectStoreScope, ProjectStoreTenant

        from .project_store_provisioning import (
            ProvisioningUnavailable,
            provision_project_store,
            provisioning_configured,
        )

        not_yet = "Clew records are not configured for this project yet"
        scope = ProjectStoreScope.objects.filter(project=project).first()
        tenant = ProjectStoreTenant.objects.filter(owner_id=project.owner_id).first()
        try:
            dsn = tenant.get_dsn() if tenant is not None else ""
        except InvalidToken:
            raise CapabilityUnavailable(
                "Private store configuration is invalid"
            ) from None
        if scope is None or not dsn:
            if not provisioning_configured():
                raise CapabilityUnavailable(not_yet)
            try:
                scope = provision_project_store(project)
            except ProvisioningUnavailable:
                raise CapabilityUnavailable(not_yet) from None
            tenant = ProjectStoreTenant.objects.get(owner_id=project.owner_id)
            dsn = tenant.get_dsn()
        return StoreAccess(
            tenant_id=tenant.tenant_id,
            dsn=dsn,
            project_scope=scope.scope,
            owner_role=owner_role,
        )


def api_key_user(request):
    """Use the existing active API-key authority and its api/* permission."""
    from apps.infra.accounts_app.auth import authenticate_api_key

    key = authenticate_api_key(request)
    return key.user if key and key.has_scope("api") else None
