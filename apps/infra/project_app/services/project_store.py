"""Authorized project-store credentials; schemas and operations belong to leaves."""

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
        if project.owner_id != user.pk or project.is_org_owned:
            raise CapabilityUnavailable(
                "Shared project stores require project-level access control"
            )
        # SECRET is deliberate: Django's technical error reporter must redact
        # this configuration, which contains credentials for multiple owners.
        configuration = getattr(settings, "SCITEX_STORE_TENANT_SECRETS", {})
        if isinstance(configuration, str):
            try:
                configuration = json.loads(configuration)
            except ValueError:
                raise CapabilityUnavailable(
                    "Private store configuration is invalid"
                ) from None
        if not isinstance(configuration, Mapping):
            raise CapabilityUnavailable("Private store configuration is invalid")
        entry = configuration.get(str(user.pk))
        if entry is None:
            raise CapabilityUnavailable("Private store is not configured for this user")
        try:
            if not isinstance(entry, Mapping):
                raise ValueError
            projects = entry.get("projects")
            if not isinstance(projects, Mapping):
                raise ValueError
            tenant_id = UUID(str(entry["tenant_id"]))
            scope, dsn = projects.get(str(project.pk)), entry.get("dsn")
            owner_role = getattr(settings, "SCITEX_STORE_OWNER", "scitex_cloud_owner")
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


def api_key_user(request):
    """Use the existing active API-key authority and its api/* permission."""
    from apps.infra.accounts_app.auth import authenticate_api_key

    key = authenticate_api_key(request)
    return key.user if key and key.has_scope("api") else None
