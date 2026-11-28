"""Real HTTP -> isolated Clew -> PostgreSQL, using synthetic users only.

Run with SCITEX_CLEW_TEST_ADMIN_DSN pointing at a disposable local cluster.
The integration fixture refuses the fleet's managed store ports. These tests
must not be run against a deployment database or existing research projects.
"""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, override_settings
from psycopg import sql
from scitex_clew._claim._store import _CLAIMS_SCHEMA
from scitex_clew._db._schema import (
    FILE_HASHES_SCHEMA,
)
from scitex_clew._django.models import HashRegistration
from scitex_clew._django.services.project_store import execute, project_context
from scitex_dev.store import (
    NEW_RECORD,
    WriterPolicy,
    open_tenant_store,
)

from apps.infra.project_app.models import Project, ProjectMembership

from ._clew_store_fixture import READ_ROUTES, SCHEMAS, ClewStoreFixture


class ClewTenantIntegrationTest(ClewStoreFixture):
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
        with override_settings(SCITEX_STORE_TENANT_SECRETS={}):
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
        with override_settings(SCITEX_STORE_TENANT_SECRETS=altered):
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

    def test_project_permission_matrix_over_http(self):
        """scitex-hub#1225: members read the project's records; editors write.

        Bob owns a same-named project in his own tenant, so a member read that
        used the caller's credentials instead of the project's would show
        ``bob-evidence`` here.
        """
        carol = User.objects.create_user(username="clew-carol")
        for user, role, permission in (
            (self.bob, "viewer", "read"),
            (carol, "admin", "admin"),
        ):
            ProjectMembership.objects.create(
                project=self.paper, user=user, role=role, permission_level=permission
            )
        outsider = User.objects.create_user(username="clew-outsider")
        queries = {
            "verify-run/": {"session_id": "same-session"},
            "verify-chain/": {"target": "output.csv"},
            "dag/json/": {"session_id": "same-session"},
            "dag/mermaid/": {"session_id": "same-session"},
        }
        # The write gate is what Hub decides; ALLOWED means "passed the gate"
        # (the leaf's example copy itself may still fail, e.g. when the wheel
        # ships no bundled examples).
        allowed = "passes the write gate"
        cases = (
            ("owner", self.alice, 200, allowed),
            ("maintainer", carol, 200, allowed),
            ("viewer", self.bob, 200, 403),
            ("non-member", outsider, 404, 404),
            ("anonymous", None, 401, 401),
        )
        for label, user, read_status, write_status in cases:
            client = Client()
            if user is not None:
                client.force_login(user)
            for route in READ_ROUTES:
                with self.subTest(who=label, route=route):
                    response = client.get(
                        "/apps/clew/api/" + route,
                        {
                            "project": "clew-alice/paper-scitex-clew",
                            **queries.get(route, {}),
                        },
                    )
                    self.assertEqual(
                        response.status_code, read_status, response.content
                    )
                    self.assertNotIn("bob-evidence", response.content.decode())
                    if read_status == 200:
                        self.assertTrue(response.json()["success"])
            if read_status == 200:
                with self.subTest(who=label, route="runs/ content"):
                    runs = client.get(
                        "/apps/clew/api/runs/",
                        {"project": "clew-alice/paper-scitex-clew"},
                    )
                    self.assertIn("alice-evidence", runs.content.decode())
            with self.subTest(who=label, route="add-examples/"):
                response = client.post(
                    "/apps/clew/api/add-examples/?project=clew-alice/paper-scitex-clew"
                )
                if write_status == allowed:
                    self.assertNotIn(response.status_code, (401, 403, 404))
                else:
                    self.assertEqual(
                        response.status_code, write_status, response.content
                    )
        # A member's own project still resolves to their own tenant.
        self.client.force_login(self.bob)
        own = self.get("runs/", project="clew-bob/paper-scitex-clew")
        self.assertIn("bob-evidence", own.content.decode())
        self.assertNotIn("alice-evidence", own.content.decode())

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
        migration = import_module(
            "scitex_clew._django.migrations.0001_initial"
        ).Migration
        self.assertEqual(migration.dependencies, [("auth", "__first__")])
        with override_settings(
            MIGRATION_MODULES={"clew_app": "scitex_clew._django.migrations"}
        ):
            loader = MigrationLoader(connection, load=False)
            loader.load_disk()
            self.assertIn(("clew_app", "0001_initial"), loader.disk_migrations)

    def test_file_preview_enforces_project_access_and_containment(self):
        self.assertContains(
            self.get("file/", path="input.csv"), "alice-evidence", status_code=200
        )
        self.assertEqual(
            self.get(
                "file/", path=str(self.roots[self.bob.pk] / "input.csv")
            ).status_code,
            400,
        )
        self.assertEqual(
            self.get(
                "file/", path="input.csv", project="clew-bob/paper-scitex-clew"
            ).status_code,
            404,
        )
        self.assertEqual(
            Client()
            .get(
                "/apps/clew/api/file/",
                {"project": "clew-alice/paper-scitex-clew", "path": "input.csv"},
            )
            .status_code,
            401,
        )

    def test_session_registry_write_requires_csrf_and_badge_cannot_claim_rerun(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        response = client.post(
            "/apps/clew/api/register/",
            json.dumps({"hash": "a" * 64}),
            content_type="application/json",
        )
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
        self.assertEqual(
            module.context_builder, "scitex_clew._django.views.build_context"
        )
        root = self.roots[self.alice.pk]
        entry = self.entries[str(self.alice.pk)]
        local_entry = {
            "tenant_id": entry["tenant_id"],
            "dsn": entry["dsn"],
            "project_scope": entry["projects"][str(self.paper.pk)],
            "owner_role": self.owner_role,
        }
        session = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.route(
                    "**/*",
                    lambda route: (
                        route.continue_()
                        if urlparse(route.request.url).hostname
                        in {"localhost", "127.0.0.1"}
                        else route.abort()
                    ),
                )
                page.context.add_cookies(
                    [
                        {
                            "name": settings.SESSION_COOKIE_NAME,
                            "value": session,
                            "url": self.live_server_url,
                        }
                    ]
                )
                page.goto(
                    self.live_server_url
                    + "/apps/clew/?project=clew-alice/paper-scitex-clew"
                )
                page.locator(".dag-visualization-area svg").first.wait_for()
                page.locator("[data-stx-project-picker]").get_by_role(
                    "button", name="Living paper", exact=True
                ).wait_for()
                artifacts = os.environ.get("SCITEX_GUI_TEST_ARTIFACT_DIR")
                if artifacts:
                    Path(artifacts).mkdir(mode=0o700, parents=True, exist_ok=True)
                    page.screenshot(
                        path=str(Path(artifacts) / "clew-plugin-desktop.png")
                    )
                page.locator('button[data-mode="claims"]').click()
                page.locator(".claim-item").first.wait_for()
                self.assertNotIn(
                    "bob-evidence", page.locator(".dag-visualization-area").inner_text()
                )
                page.set_viewport_size({"width": 390, "height": 844})
                self.assertTrue(
                    page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    )
                )
                self.assertFalse(errors, errors)
                if artifacts:
                    page.screenshot(
                        path=str(Path(artifacts) / "clew-plugin-mobile.png")
                    )
                page.context.clear_cookies()
                with override_settings(
                    SCITEX_APP_MODE="standalone",
                    ROOT_URLCONF="scitex_clew._django.standalone_urls",
                    SCITEX_PROJECT_PROVIDER="scitex_sdk.local.LocalProjectProvider",
                    SCITEX_PROJECT_STORAGE="scitex_sdk.local.LocalProjectStorage",
                    SCITEX_PROJECT_STORE="scitex_sdk.local.LocalProjectStore",
                    SCITEX_LOCAL_PROJECT_ROOT=str(root.parent),
                    SCITEX_LOCAL_PROJECT_STORES={root.name: local_entry},
                ):
                    page.goto(self.live_server_url + "/?project=" + root.name)
                    page.locator(".dag-visualization-area svg").first.wait_for()
                    page.locator("[data-stx-project-picker]").get_by_role(
                        "button", name=root.name, exact=True
                    ).wait_for()
                    page.locator('button[data-mode="claims"]').click()
                    page.locator(".claim-item").first.wait_for()
                    self.assertNotIn(
                        "bob-evidence",
                        page.locator(".dag-visualization-area").inner_text(),
                    )
                    self.assertTrue(
                        page.evaluate(
                            "document.documentElement.scrollWidth <= window.innerWidth"
                        )
                    )
                    page.set_viewport_size({"width": 1280, "height": 900})
                    if artifacts:
                        page.screenshot(
                            path=str(Path(artifacts) / "clew-standalone-desktop.png")
                        )
                    page.set_viewport_size({"width": 390, "height": 844})
                    if artifacts:
                        page.screenshot(
                            path=str(Path(artifacts) / "clew-standalone-mobile.png")
                        )
                    with override_settings(SCITEX_LOCAL_PROJECT_STORES={}):
                        page.reload()
                        page.get_by_text(
                            "Private store is not configured for this project"
                        ).wait_for()
                        self.assertNotIn(
                            "No Runs Yet",
                            page.locator(".dag-visualization-area").inner_text(),
                        )
                self.assertFalse(errors, errors)
            finally:
                browser.close()
