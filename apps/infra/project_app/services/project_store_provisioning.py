"""Give a project its private Clew store, without an operator step.

Before this module, a project's store existed only when an operator had added
its owner, with credentials and a project mapping, to
``SCITEX_HUB_STORE_TENANT_SECRETS`` by hand; every other owner got HTTP 503
in Clew (scitex-hub#1231). Now the Hub provisions it the first time it is
needed:

* **one tenant per owner.** A random UUID becomes a ``TenantScope``; the Hub
  creates its unprivileged LOGIN with a random password (``NOSUPERUSER
  NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS``, no role memberships)
  and stores the login's DSN encrypted with the field-encryption keys.
* **Clew decides the stores.** ``scitex_clew.tenant.provision_tenant``
  creates exactly the stores the hosted worker checks, idempotently.
* **one scope per project.** ``scitex_clew.tenant.project_scope_for`` reads
  (or mints once) ``<project>/.scitex/clew/project-id``, the scope Clew runs
  inside the project use, so their records and the Hub's reads meet.

The administration connection (``SCITEX_HUB_STORE_PROVISIONER_DSN``) is used
only here. Credentials never reach logs or responses: failures are logged by
exception type and project id only. Concurrent first requests are serialised
per owner with a PostgreSQL advisory lock on that connection.
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import quote, urlencode

from django.conf import settings
from django.db import IntegrityError, transaction
from django.views.decorators.debug import sensitive_variables

from apps.infra.project_app.models import (
    Project,
    ProjectStoreScope,
    ProjectStoreTenant,
)
from apps.infra.project_app.services.filesystem.paths import get_project_root_path

logger = logging.getLogger(__name__)

__all__ = [
    "ProvisioningUnavailable",
    "provision_project_store",
    "provisioning_configured",
]


class ProvisioningUnavailable(RuntimeError):
    """The project's store could not be provisioned; carries no credential."""


def _provisioner_dsn() -> str:
    return (getattr(settings, "SCITEX_STORE_PROVISIONER_SECRET", "") or "").strip()


def provisioning_configured() -> bool:
    """True when this deployment has an administration connection for stores."""
    return bool(_provisioner_dsn())


def _owner_role() -> str:
    return getattr(settings, "SCITEX_STORE_OWNER", "scitex_cloud_owner")


@sensitive_variables("password", "admin_dsn")
def _tenant_dsn(admin_dsn: str, principal: str, password: str) -> str:
    """The tenant login's DSN: the administration endpoint, the tenant's login."""
    from psycopg.conninfo import conninfo_to_dict

    selected = conninfo_to_dict(admin_dsn)
    database = selected.pop("dbname", "postgres")
    selected.pop("user", None)
    selected.pop("password", None)
    selected.update(user=principal, password=password)
    return f"postgresql:///{quote(database, safe='')}?{urlencode(selected)}"


def _tenant_for(owner) -> ProjectStoreTenant:
    """The owner's tenant row, created once (a concurrent creator wins)."""
    existing = ProjectStoreTenant.objects.filter(owner=owner).first()
    if existing is not None:
        return existing
    tenant = ProjectStoreTenant(owner=owner)
    try:
        with transaction.atomic():
            tenant.set_dsn("")  # filled in by _ensure_login under the lock
            tenant.save()
    except IntegrityError:
        return ProjectStoreTenant.objects.get(owner=owner)
    return tenant


@sensitive_variables("password", "admin_dsn", "dsn")
def _ensure_login(connection, tenant: ProjectStoreTenant, admin_dsn: str) -> str:
    """Create (or re-key) the tenant LOGIN; return its DSN."""
    from psycopg import sql
    from scitex_dev.store import TenantScope

    principal = TenantScope(tenant.tenant_id).principal
    dsn = tenant.get_dsn()
    role = connection.execute(
        "SELECT 1 FROM pg_roles WHERE rolname=%s", (principal,)
    ).fetchone()
    if role is not None and dsn:
        return dsn
    password = secrets.token_urlsafe(32)
    verb = "ALTER" if role is not None else "CREATE"
    connection.execute(
        sql.SQL(
            "{} ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
            "NOBYPASSRLS PASSWORD {}"
        ).format(sql.SQL(verb), sql.Identifier(principal), sql.Literal(password))
    )
    dsn = _tenant_dsn(admin_dsn, principal, password)
    tenant.set_dsn(dsn)
    tenant.save(update_fields=["dsn"])
    return dsn


@sensitive_variables("admin_dsn", "dsn")
def provision_project_store(project: Project) -> ProjectStoreScope:
    """Provision ``project``'s owner tenant, its Clew stores and its scope.

    Idempotent: a provisioned project returns its existing scope after the
    (cheap) catalogue checks. Raises :class:`ProvisioningUnavailable` when the
    deployment has no administration connection, the project has no
    directory, or the store refused. The original error is logged by type
    only and not chained, because driver messages can quote a DSN.
    """
    admin_dsn = _provisioner_dsn()
    if not admin_dsn:
        raise ProvisioningUnavailable("Store provisioning is not configured")
    root = get_project_root_path(project.owner, project)
    if root is None:
        raise ProvisioningUnavailable("Project directory not found")

    import psycopg
    from scitex_clew.tenant import project_scope_for, provision_tenant
    from scitex_dev.store import StoreTarget, TenantScope

    tenant = _tenant_for(project.owner)
    scope = TenantScope(tenant.tenant_id)
    try:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_advisory_lock(hashtext(%s))", (scope.principal,)
            )
            try:
                tenant.refresh_from_db()
                dsn = _ensure_login(connection, tenant, admin_dsn)
                provision_tenant(
                    StoreTarget.postgres(admin_dsn, pkg="scitex_clew"),
                    dsn,
                    scope,
                    owner_role=_owner_role(),
                )
            finally:
                connection.execute(
                    "SELECT pg_advisory_unlock(hashtext(%s))", (scope.principal,)
                )
        project_scope = project_scope_for(root)
    except Exception as exc:  # noqa: BLE001 - sanitized at this boundary
        logger.error(
            "Clew store provisioning failed for project %s: %s",
            project.pk,
            type(exc).__name__,
        )
        raise ProvisioningUnavailable("Store provisioning failed") from None
    stored, _ = ProjectStoreScope.objects.get_or_create(
        project=project, defaults={"scope": project_scope}
    )
    logger.info(
        "Clew store provisioned for project %s (tenant %s)",
        project.pk,
        tenant.tenant_id,
    )
    return stored
