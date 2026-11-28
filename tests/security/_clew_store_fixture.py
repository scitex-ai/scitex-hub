"""Real HTTP -> isolated Clew -> PostgreSQL, using synthetic users only.

Run with SCITEX_CLEW_TEST_ADMIN_DSN pointing at a disposable local cluster.
The integration fixture refuses the fleet's managed store ports. These tests
must not be run against a deployment database or existing research projects.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path
from unittest import SkipTest
from urllib.parse import quote, urlencode
from uuid import uuid4

import psycopg
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from scitex_clew._claim._store import _CLAIMS_SCHEMA
from scitex_clew._db._schema import (
    FILE_HASHES_SCHEMA,
    RUNS_SCHEMA,
    SESSION_PARENTS_SCHEMA,
    VERIFICATION_RESULTS_SCHEMA,
)
from scitex_dev.store import (
    NEW_RECORD,
    StoreTarget,
    TenantScope,
    WriterPolicy,
    open_tenant_store,
    provision_tenant_store,
)

from apps.infra.project_app.models import Project

SCHEMAS = (
    RUNS_SCHEMA,
    FILE_HASHES_SCHEMA,
    VERIFICATION_RESULTS_SCHEMA,
    SESSION_PARENTS_SCHEMA,
    _CLAIMS_SCHEMA,
)
READ_ROUTES = (
    "status/",
    "stats/",
    "runs/",
    "verify-run/",
    "verify-chain/",
    "dag/json/",
    "dag/mermaid/",
    "claims/",
)


class ClewStoreFixture(StaticLiveServerTestCase):
    def setUp(self):
        admin_dsn = os.environ.get("SCITEX_CLEW_TEST_ADMIN_DSN")
        if not admin_dsn:
            raise SkipTest(
                "A disposable PostgreSQL cluster must be explicitly configured"
            )
        self.admin = psycopg.connect(admin_dsn, autocommit=True)
        self.addCleanup(self.admin.close)
        port = int(self.admin.info.port)
        if port in {55432, 55433}:
            self.fail("Synthetic integration refuses the managed store ports")
        self.temporary = tempfile.TemporaryDirectory(prefix="clew-http-test-")
        self.addCleanup(self.temporary.cleanup)
        self.owner_role = "clew_test_owner_" + uuid4().hex[:12]
        self.scopes = []
        self.admin.execute(
            sql.SQL("CREATE ROLE {} NOLOGIN NOBYPASSRLS").format(
                sql.Identifier(self.owner_role)
            )
        )
        self.addCleanup(self.clean_tenants)
        self.alice = User.objects.create_user(username="clew-alice")
        self.bob = User.objects.create_user(username="clew-bob")
        # bulk_create avoids repository-provisioning signals: these are ORM
        # projects only, not requests to create a repository in live Gitea.
        self.paper, self.other = Project.objects.bulk_create(
            [
                Project(
                    owner=self.alice, name="Living paper", slug="paper-scitex-clew"
                ),
                Project(owner=self.bob, name="Other paper", slug="paper-scitex-clew"),
            ]
        )
        self.entries = {}
        self.roots = {}
        self.targets = {}
        for user, project, sentinel in (
            (self.alice, self.paper, "alice-evidence"),
            (self.bob, self.other, "bob-evidence"),
        ):
            scope = TenantScope(uuid4())
            password = secrets.token_urlsafe(32)
            self.admin.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(scope.principal), sql.Literal(password))
            )
            self.scopes.append(scope)
            migration = StoreTarget.postgres(admin_dsn, pkg="synthetic_clew")
            for schema in SCHEMAS:
                provision_tenant_store(
                    migration, schema, scope, owner_role=self.owner_role
                )
            selected = conninfo_to_dict(admin_dsn)
            selected.update(user=scope.principal, password=password)
            database = selected.pop("dbname", self.admin.info.dbname)
            dsn = f"postgresql:///{quote(database, safe='')}?{urlencode(selected)}"
            target = StoreTarget.postgres(dsn, pkg="scitex_clew")
            root = (
                Path(self.temporary.name)
                / "data/users"
                / user.username
                / "proj"
                / project.slug
            )
            root.mkdir(parents=True)
            (root / "script.py").write_text(
                'from pathlib import Path\nPath("EXECUTED").touch()\n'
            )
            (root / "input.csv").write_text(sentinel)
            (root / "output.csv").write_text(sentinel + "-result")
            (root / "manuscript.tex").write_text("Researcher-defined claim")
            project_scope = "clew-" + uuid4().hex
            common = {"project": project_scope, "session_id": "same-session"}
            data = {
                "runs": [
                    {
                        **common,
                        "script_path": str(root / "script.py"),
                        "script_hash": hashlib.sha256(
                            (root / "script.py").read_bytes()
                        ).hexdigest(),
                        "started_at": "2026-10-01T00:00:00",
                        "status": "success",
                        "metadata": json.dumps({"sentinel": sentinel}),
                    }
                ],
                "file_hashes": [
                    {
                        **common,
                        "file_path": str(root / filename),
                        "role": role,
                        "hash": hashlib.sha256(
                            (root / filename).read_bytes()
                        ).hexdigest(),
                        "recorded_at": "2026-10-01T00:00:00",
                    }
                    for filename, role in (
                        ("input.csv", "input"),
                        ("output.csv", "output"),
                    )
                ],
                "claims": [
                    {
                        "project": project_scope,
                        "claim_id": "researcher-claim",
                        "file_path": str(root / "manuscript.tex"),
                        "claim_type": "value",
                        "claim_value": sentinel,
                        "source_file": str(root / "output.csv"),
                        "source_session": "same-session",
                        "status": "registered",
                    }
                ],
            }
            for schema in SCHEMAS:
                with open_tenant_store(
                    target,
                    schema,
                    scope,
                    node="synthetic_seed",
                    writer_policy=WriterPolicy.MULTI_WRITER,
                    owner_role=self.owner_role,
                ) as store:
                    for values in data.get(schema.name, []):
                        store.put(values, expected_revision=NEW_RECORD)
            self.entries[str(user.pk)] = {
                "tenant_id": str(scope.tenant_id),
                "dsn": dsn,
                "projects": {str(project.pk): project_scope},
            }
            self.roots[user.pk] = root
            self.targets[user.pk] = (target, scope)
        override = override_settings(
            BASE_DIR=Path(self.temporary.name),
            SCITEX_STORE_TENANT_SECRETS=self.entries,
            SCITEX_STORE_OWNER=self.owner_role,
        )
        override.enable()
        self.addCleanup(override.disable)
        self.client.force_login(self.alice)

    def clean_tenants(self):
        for scope in self.scopes:
            self.admin.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(scope.namespace)
                )
            )
        for scope in self.scopes:
            self.admin.execute(
                sql.SQL("DROP ROLE {}").format(sql.Identifier(scope.principal))
            )
        self.admin.execute(
            sql.SQL("DROP ROLE {}").format(sql.Identifier(self.owner_role))
        )

    def get(self, route, **parameters):
        return self.client.get(
            "/apps/clew/api/" + route,
            {"project": "clew-alice/paper-scitex-clew", **parameters},
        )
