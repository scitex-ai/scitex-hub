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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import SkipTest
from uuid import uuid4

import psycopg
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, RequestFactory, override_settings
from psycopg import sql
from scitex_clew._claim._store import _CLAIMS_SCHEMA
from scitex_clew._db._schema import (
    FILE_HASHES_SCHEMA,
    RUNS_SCHEMA,
    SESSION_PARENTS_SCHEMA,
    VERIFICATION_RESULTS_SCHEMA,
)
from scitex_clew._django.models import HashRegistration
from scitex_clew._django.services.project_store import execute, project_context
from scitex_dev.store import (
    NEW_RECORD,
    StoreTarget,
    TenantScope,
    WriterPolicy,
    open_tenant_store,
    provision_tenant_store,
)

from apps.infra.project_app.models import Project, ProjectMembership

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


class ClewTenantIntegrationTest(StaticLiveServerTestCase):
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
            dsn = f"postgresql://{scope.principal}:{password}@127.0.0.1:{port}/{self.admin.info.dbname}"
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
            SCITEX_STORE_TENANTS=self.entries,
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

    def test_anonymous_cannot_read_any_project_endpoint(self):
        client = Client()
        for route in READ_ROUTES:
            with self.subTest(route=route):
                response = client.get("/apps/clew/api/" + route)
                self.assertEqual(response.status_code, 401)
                self.assertNotIn("evidence", response.content.decode())

    def test_foreign_project_never_falls_back_to_owned_project(self):
        self.client.force_login(self.bob)
        for route in READ_ROUTES:
            with self.subTest(route=route):
                response = self.get(route)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("alice-evidence", response.content.decode())

    def test_current_package_runs_stats_claims_and_graph_work(self):
        queries = {
            "verify-run/": {"session_id": "same-session"},
            "verify-chain/": {"target": "output.csv"},
            "dag/json/": {"session_id": "same-session"},
            "dag/mermaid/": {"session_id": "same-session"},
        }
        for route in READ_ROUTES:
            with self.subTest(route=route):
                response = self.get(route, **queries.get(route, {}))
                self.assertEqual(response.status_code, 200, response.content)
                self.assertTrue(response.json()["success"])
                self.assertNotIn("bob-evidence", response.content.decode())
        self.assertIn("alice-evidence", self.get("runs/").content.decode())
        self.assertEqual(self.get("stats/").json()["data"]["total_runs"], 1)
        self.assertTrue(
            self.get("verify-run/", session_id="same-session").json()["data"][
                "is_verified"
            ]
        )

    def test_no_config_returns_unavailable_instead_of_empty_success(self):
        with override_settings(SCITEX_STORE_TENANTS={}):
            response = self.get("stats/")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])
        self.assertNotIn("total_runs", response.json())

    def test_forged_identity_and_project_files_cannot_redirect_worker(self):
        root = self.roots[self.alice.pk]
        (root / "scitex_clew.py").write_text(
            'raise RuntimeError("PROJECT CODE EXECUTED")\n'
        )
        (root / "sitecustomize.py").write_text(
            'raise RuntimeError("PROJECT CODE EXECUTED")\n'
        )
        response = self.get(
            "runs/",
            tenant_id=self.entries[str(self.bob.pk)]["tenant_id"],
            dsn=self.entries[str(self.bob.pk)]["dsn"],
            actor="clew-bob",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("alice-evidence", response.content.decode())
        self.assertNotIn("bob-evidence", response.content.decode())

    def test_wrong_authenticated_login_and_missing_policy_fail_closed(self):
        altered = {key: dict(value) for key, value in self.entries.items()}
        altered[str(self.alice.pk)]["dsn"] = self.entries[str(self.bob.pk)]["dsn"]
        with override_settings(SCITEX_STORE_TENANTS=altered):
            response = self.get("runs/")
        self.assertEqual(response.status_code, 503)
        scope = self.targets[self.alice.pk][1]
        self.admin.execute(
            sql.SQL("DROP POLICY tenant_boundary ON {}").format(
                sql.Identifier(scope.namespace, "claims_oplog")
            )
        )
        self.assertEqual(self.get("runs/").status_code, 503)

    def test_read_api_does_not_execute_scripts_or_modify_claims(self):
        root = self.roots[self.alice.pk]
        before = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.iterdir()
            if path.is_file()
        }
        target, scope = self.targets[self.alice.pk]
        with open_tenant_store(
            target,
            _CLAIMS_SCHEMA,
            scope,
            node="synthetic_check",
            writer_policy=WriterPolicy.MULTI_WRITER,
            owner_role=self.owner_role,
        ) as store:
            claims_before = [dict(row.values) for row in store.rows()]
        self.assertEqual(
            self.get(
                "verify-run/", session_id="same-session", from_scratch="true"
            ).status_code,
            405,
        )
        self.assertEqual(self.get("dag/mermaid/", claims="true").status_code, 200)
        self.assertFalse((self.roots[self.alice.pk] / "EXECUTED").exists())
        self.assertEqual(
            self.get("claims/").json()["data"]["claims"][0]["status"], "registered"
        )
        after = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.iterdir()
            if path.is_file()
        }
        self.assertEqual(before, after)
        with open_tenant_store(
            target,
            _CLAIMS_SCHEMA,
            scope,
            node="synthetic_check",
            writer_policy=WriterPolicy.MULTI_WRITER,
            owner_role=self.owner_role,
        ) as store:
            self.assertEqual(claims_before, [dict(row.values) for row in store.rows()])

    def test_recorded_foreign_paths_are_not_hashed(self):
        target, scope = self.targets[self.alice.pk]
        with open_tenant_store(
            target,
            FILE_HASHES_SCHEMA,
            scope,
            node="synthetic_seed",
            writer_policy=WriterPolicy.MULTI_WRITER,
            owner_role=self.owner_role,
        ) as store:
            store.put(
                {
                    "project": self.entries[str(self.alice.pk)]["projects"][
                        str(self.paper.pk)
                    ],
                    "session_id": "same-session",
                    "file_path": str(self.roots[self.bob.pk] / "input.csv"),
                    "role": "input",
                    "hash": "0" * 64,
                    "recorded_at": "2026-10-01T00:00:00",
                },
                expected_revision=NEW_RECORD,
            )
        response = self.get("status/")
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("bob-evidence", response.content.decode())

    def test_projects_with_same_session_id_stay_separate_within_one_tenant(self):
        second = Project.objects.bulk_create(
            [Project(owner=self.alice, name="Second paper", slug="second-paper")]
        )[0]
        second_scope = "clew-" + uuid4().hex
        self.entries[str(self.alice.pk)]["projects"][str(second.pk)] = second_scope
        first_root = self.roots[self.alice.pk]
        second_root = first_root.parent / second.slug
        second_root.mkdir()
        target, scope = self.targets[self.alice.pk]
        for schema in SCHEMAS:
            with open_tenant_store(
                target,
                schema,
                scope,
                node="synthetic_seed",
                writer_policy=WriterPolicy.MULTI_WRITER,
                owner_role=self.owner_role,
            ) as store:
                for row in store.rows():
                    values = dict(row.values)
                    values["project"] = second_scope
                    for key, value in values.items():
                        if isinstance(value, str):
                            values[key] = value.replace(
                                str(first_root), str(second_root)
                            ).replace("alice-evidence", "second-paper-evidence")
                    store.put(values, expected_revision=NEW_RECORD)
        first = self.get("runs/")
        second_response = self.get("runs/", project="clew-alice/second-paper")
        self.assertIn("alice-evidence", first.content.decode())
        self.assertNotIn("second-paper-evidence", first.content.decode())
        self.assertIn("second-paper-evidence", second_response.content.decode())
        self.assertNotIn("alice-evidence", second_response.content.decode())

    def test_path_escape_and_symlink_are_rejected(self):
        self.assertEqual(
            self.get("verify-chain/", target="../../other/input.csv").status_code, 400
        )
        (self.roots[self.alice.pk] / "escape").symlink_to(
            self.roots[self.bob.pk], target_is_directory=True
        )
        self.assertEqual(
            self.get("verify-chain/", target="escape/input.csv").status_code, 400
        )

    def test_collaborator_does_not_borrow_the_owner_login(self):
        ProjectMembership.objects.create(
            project=self.paper, user=self.bob, permission_level="read"
        )
        self.client.force_login(self.bob)
        self.assertEqual(self.get("runs/").status_code, 503)

    def test_concurrent_requests_keep_tenant_and_project_separate(self):
        contexts = []
        for user in (self.alice, self.bob):
            request = RequestFactory().get(
                "/", {"project": f"{user.username}/paper-scitex-clew"}
            )
            request.user, request.session = user, {}
            contexts.append(project_context(request))
        parameters = {"limit": 50, "offset": 0, "status": None}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(execute, contexts[index % 2], "runs", parameters)
                for index in range(12)
            ]
            results = [future.result() for future in futures]
        for index, result in enumerate(results):
            self.assertIn(
                "alice-evidence" if index % 2 == 0 else "bob-evidence",
                json.dumps(result),
            )
            self.assertNotIn(
                "bob-evidence" if index % 2 == 0 else "alice-evidence",
                json.dumps(result),
            )

    def test_public_hash_proof_stays_anonymous_and_accessible(self):
        digest = "a" * 64
        HashRegistration.objects.create(
            user=self.alice, hash=digest, metadata={"secret": "alice-evidence"}
        )
        response = Client().get("/apps/clew/api/verify/" + digest + "/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("clew-alice", response.content.decode())
        self.assertNotIn("alice-evidence", response.content.decode())


    def test_leaf_model_preserves_existing_table_and_migration_identity(self):
        from importlib import import_module

        from django.apps import apps
        from django.db import connection
        from django.db.migrations.loader import MigrationLoader

        self.assertEqual(apps.get_app_config("clew_app").name, "scitex_clew._django")
        self.assertEqual(HashRegistration._meta.db_table, "clew_app_hashregistration")
        migration = import_module("scitex_clew._django.migrations.0001_initial").Migration
        self.assertEqual(migration.dependencies, [("auth", "__first__")])
        with override_settings(MIGRATION_MODULES={"clew_app": "scitex_clew._django.migrations"}):
            loader = MigrationLoader(connection, load=False)
            loader.load_disk()
            self.assertIn(("clew_app", "0001_initial"), loader.disk_migrations)

    def test_file_preview_enforces_project_access_and_containment(self):
        self.assertContains(self.get("file/", path="input.csv"), "alice-evidence", status_code=200)
        self.assertEqual(self.get("file/", path=str(self.roots[self.bob.pk] / "input.csv")).status_code, 400)
        self.assertEqual(self.get("file/", path="input.csv", project="clew-bob/paper-scitex-clew").status_code, 404)
        self.assertEqual(Client().get("/apps/clew/api/file/", {"project": "clew-alice/paper-scitex-clew", "path": "input.csv"}).status_code, 401)

    def test_session_registry_write_requires_csrf_and_badge_cannot_claim_rerun(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        response = client.post("/apps/clew/api/register/", json.dumps({"hash": "a" * 64}), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        response = Client().get("/apps/clew/badge/" + "a" * 64 + "/?level=L2")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("reproducible", response.content.decode())

    def test_browser_plugin_and_standalone_share_leaf_assets_and_behavior(self):
        from urllib.parse import urlparse

        from django.apps import apps
        from django.conf import settings
        from playwright.sync_api import sync_playwright

        from apps.workspace.apps_app.services.plugin_apps import plugin_module_config

        config = apps.get_app_config("clew_app")
        module = plugin_module_config(config)
        self.assertEqual(module.partial_template, "clew_app/index_partial.html")
        self.assertEqual(module.context_builder, "scitex_clew._django.views.build_context")
        root = self.roots[self.alice.pk]
        entry = self.entries[str(self.alice.pk)]
        local_entry = {"tenant_id": entry["tenant_id"], "dsn": entry["dsn"], "project_scope": entry["projects"][str(self.paper.pk)], "owner_role": self.owner_role}
        session = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).hostname in {"localhost", "127.0.0.1"} else route.abort())
                page.context.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": session, "url": self.live_server_url}])
                page.goto(self.live_server_url + "/apps/clew/?project=clew-alice/paper-scitex-clew")
                page.locator(".dag-visualization-area svg").first.wait_for()
                artifacts = os.environ.get("SCITEX_GUI_TEST_ARTIFACT_DIR")
                if artifacts:
                    Path(artifacts).mkdir(mode=0o700, parents=True, exist_ok=True)
                    page.screenshot(path=str(Path(artifacts) / "clew-plugin-desktop.png"))
                page.locator('button[data-mode="claims"]').click()
                page.locator(".claim-item").first.wait_for()
                self.assertNotIn("bob-evidence", page.locator(".dag-visualization-area").inner_text())
                page.set_viewport_size({"width": 390, "height": 844})
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
                self.assertFalse(errors, errors)
                if artifacts:
                    page.screenshot(path=str(Path(artifacts) / "clew-plugin-mobile.png"))
                page.context.clear_cookies()
                with override_settings(SCITEX_APP_MODE="standalone", ROOT_URLCONF="scitex_clew._django.standalone_urls", SCITEX_PROJECT_PROVIDER="scitex_sdk.local.LocalProjectProvider", SCITEX_PROJECT_STORAGE="scitex_sdk.local.LocalProjectStorage", SCITEX_PROJECT_STORE="scitex_sdk.local.LocalProjectStore", SCITEX_LOCAL_PROJECT_ROOT=str(root.parent), SCITEX_LOCAL_PROJECT_STORES={root.name: local_entry}):
                    page.goto(self.live_server_url + "/?project=" + root.name)
                    page.locator(".dag-visualization-area svg").first.wait_for()
                    page.locator('button[data-mode="claims"]').click()
                    page.locator(".claim-item").first.wait_for()
                    self.assertNotIn("bob-evidence", page.locator(".dag-visualization-area").inner_text())
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
                    if artifacts:
                        page.screenshot(path=str(Path(artifacts) / "clew-standalone-mobile.png"))
                    with override_settings(SCITEX_LOCAL_PROJECT_STORES={}):
                        page.reload()
                        page.get_by_text("Private store is not configured for this project").wait_for()
                        self.assertNotIn("No Runs Yet", page.locator(".dag-visualization-area").inner_text())
                self.assertFalse(errors, errors)
            finally:
                browser.close()
