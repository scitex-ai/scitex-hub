"""Generic project-store capability; no leaf package schemas or operations."""

from uuid import UUID

from django.conf import settings
from scitex_sdk.host import CapabilityUnavailable, StoreAccess

from .project_scope import find_accessible_project


class HubProjectStore:
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
        entry = getattr(settings, "SCITEX_STORE_TENANTS", {}).get(str(user.pk))
        if not entry:
            raise CapabilityUnavailable("Private store is not configured for this user")
        scope = entry.get("projects", {}).get(str(project.pk))
        try:
            tenant_id = UUID(entry["tenant_id"])
            if not tenant_id.int or not scope or not entry.get("dsn"):
                raise ValueError
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise CapabilityUnavailable("Private store configuration is invalid") from exc
        return StoreAccess(
            tenant_id=tenant_id,
            dsn=entry["dsn"],
            project_scope=scope,
            owner_role=getattr(settings, "SCITEX_STORE_OWNER", "scitex_cloud_owner"),
        )


def api_key_user(request):
    """Adapt Hub's API key authority to the SDK's identity capability."""
    from apps.infra.accounts_app.auth import authenticate_api_key

    key = authenticate_api_key(request)
    return key.user if key else None
