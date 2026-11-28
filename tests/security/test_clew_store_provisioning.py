"""A new owner's project opens in Clew with no hand-written store entry.

scitex-hub#1231: Clew answered 503 for every project whose owner was not
hand-listed in SCITEX_HUB_STORE_TENANT_SECRETS. With an administration
connection configured, the first authorized request now provisions the
owner's tenant and the project's scope, and later requests reuse them.

Real HTTP -> Clew worker -> PostgreSQL on an explicitly supplied disposable
local cluster (SCITEX_CLEW_TEST_ADMIN_DSN), synthetic users only:

python -m django test tests.security.test_clew_store_provisioning \
    --settings=tests.security.clew_store_settings --noinput
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest import SkipTest
from uuid import uuid4

import psycopg
from django.contrib.auth.models import User
from django.test import RequestFactory, TransactionTestCase, override_settings
from psycopg import sql
from scitex_dev.store import TenantScope

from apps.infra.project_app.models import (
    Project,
    ProjectStoreScope,
    ProjectStoreTenant,
)
from apps.infra.project_app.services.project_store import HubProjectStore


class ClewStoreProvisioningTest(TransactionTestCase):
    def setUp(self):
        admin_dsn = os.environ.get("SCITEX_CLEW_TEST_ADMIN_DSN")
        if not admin_dsn:
            raise SkipTest(
                "A disposable PostgreSQL cluster must be explicitly configured"
            )
        self.admin = psycopg.connect(admin_dsn, autocommit=True)
        self.addCleanup(self.admin.close)
        if int(self.admin.info.port) in {55432, 55433}:
            self.fail("Synthetic integration refuses the managed store ports")
        self.owner_role = "clew_test_owner_" + uuid4().hex[:12]
        self.admin.execute(
            sql.SQL("CREATE ROLE {} NOLOGIN NOBYPASSRLS").format(
                sql.Identifier(self.owner_role)
            )
        )
        self.addCleanup(self._drop_tenants)
        self.temporary = tempfile.TemporaryDirectory(prefix="clew-provision-test-")
        self.addCleanup(self.temporary.cleanup)
        self.owner = User.objects.create_user(username="clew-new-owner")
        self.other = User.objects.create_user(username="clew-stranger")
        (self.project,) = Project.objects.bulk_create(
            [Project(owner=self.owner, name="Fresh study", slug="fresh-study")]
        )
        self.root = (
            Path(self.temporary.name)
            / "data/users"
            / self.owner.username
            / "proj"
            / self.project.slug
        )
        self.root.mkdir(parents=True)
        override = override_settings(
            BASE_DIR=Path(self.temporary.name),
            SCITEX_STORE_TENANT_SECRETS="",
            SCITEX_STORE_OWNER=self.owner_role,
            SCITEX_STORE_PROVISIONER_SECRET=admin_dsn,
        )
        override.enable()
        self.addCleanup(override.disable)
        self.client.force_login(self.owner)

    def _drop_tenants(self):
        for tenant in ProjectStoreTenant.objects.all():
            scope = TenantScope(tenant.tenant_id)
            self.admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(scope.namespace)
                )
            )
            self.admin.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(
                    sql.Identifier(scope.principal)
                )
            )
        self.admin.execute(
            sql.SQL("DROP ROLE {}").format(sql.Identifier(self.owner_role))
        )

    def stats(self):
        return self.client.get(
            "/apps/clew/api/stats/",
            {"project": f"{self.owner.username}/{self.project.slug}"},
        )

    def test_first_request_of_an_unconfigured_owner_succeeds(self):
        # Arrange
        # (an owner nobody configured; a provisioner is configured)
        # Act
        response = self.stats()
        # Assert
        assert response.status_code == 200, response.content

    def test_first_request_provisions_one_tenant_and_one_scope(self):
        # Arrange
        # (nothing provisioned yet)
        # Act
        self.stats()
        # Assert
        assert (
            ProjectStoreTenant.objects.filter(owner=self.owner).count(),
            ProjectStoreScope.objects.filter(project=self.project).count(),
        ) == (1, 1)

    def test_the_scope_is_the_projects_own_clew_id(self):
        # Arrange
        id_file = self.root / ".scitex/clew/project-id"
        # Act
        self.stats()
        # Assert
        assert (
            ProjectStoreScope.objects.get(project=self.project).scope
            == id_file.read_text().strip()
        )

    def test_repeat_requests_reuse_the_tenant(self):
        # Arrange
        self.stats()
        first = ProjectStoreTenant.objects.get(owner=self.owner).tenant_id
        # Act
        response = self.stats()
        # Assert
        assert (response.status_code, ProjectStoreTenant.objects.get().tenant_id) == (
            200,
            first,
        )

    def test_the_tenant_login_is_unprivileged(self):
        # Arrange
        self.stats()
        scope = TenantScope(ProjectStoreTenant.objects.get().tenant_id)
        # Act
        flags = self.admin.execute(
            "SELECT rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolcanlogin "
            "FROM pg_roles WHERE rolname=%s",
            (scope.principal,),
        ).fetchone()
        # Assert
        assert flags == (False, False, False, False, True)

    def test_the_stored_login_credential_is_encrypted(self):
        # Arrange
        self.stats()
        # Act
        tenant = ProjectStoreTenant.objects.get()
        # Assert
        assert TenantScope(tenant.tenant_id).principal not in tenant.dsn

    def test_provisioning_never_logs_the_credential(self):
        # Arrange
        logger = logging.getLogger()
        # Act
        with self.assertLogs(logger, level=logging.INFO) as captured:
            self.stats()
        # Assert
        password = psycopg.conninfo.conninfo_to_dict(
            ProjectStoreTenant.objects.get().get_dsn()
        )["password"]
        assert password not in "\n".join(captured.output)

    def test_a_stranger_provisions_nothing(self):
        # Arrange
        self.client.force_login(self.other)
        # Act
        response = self.stats()
        # Assert
        assert (response.status_code, ProjectStoreTenant.objects.count()) == (404, 0)

    def test_without_a_provisioner_an_unconfigured_owner_stays_unavailable(self):
        # Arrange
        unconfigured = override_settings(SCITEX_STORE_PROVISIONER_SECRET="")
        # Act
        with unconfigured:
            response = self.stats()
        # Assert
        assert response.status_code == 503

    def test_a_hand_configured_mapping_still_wins(self):
        # Arrange
        self.stats()
        provisioned = ProjectStoreTenant.objects.get()
        entry = {
            str(self.owner.pk): {
                "tenant_id": str(provisioned.tenant_id),
                "dsn": provisioned.get_dsn(),
                "projects": {str(self.project.pk): "hand-configured-scope"},
            }
        }
        request = RequestFactory().get("/")
        request.user = self.owner
        # Act
        with override_settings(SCITEX_STORE_TENANT_SECRETS=json.dumps(entry)):
            access = HubProjectStore().store_access(
                f"{self.owner.username}/{self.project.slug}", request
            )
        # Assert
        assert access.project_scope == "hand-configured-scope"
