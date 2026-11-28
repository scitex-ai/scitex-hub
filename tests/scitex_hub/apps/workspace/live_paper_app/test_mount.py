"""Actual Hub authorization remains attached to every leaf evidence resource."""

import json
from urllib.parse import urlencode

from django.test import Client, override_settings
from django.urls import include, path
from scitex_sdk.ui import project_scope

from apps.infra.accounts_app.models.profile import UserProfile
from apps.infra.project_app.models import Project
from apps.workspace.apps_app.services.plugin_apps import _wrap_login
from apps.workspace.live_paper_app.mount import app_namespace, urlpatterns
from tests.security._clew_store_fixture import ClewStoreFixture


def projects(request):
    return project_scope.scoped_project_listing_view(
        project_scope.host_project_provider()
    )(request)


class LivePaperTestURLs:
    urlpatterns = [
        path("apps/live-paper/", include(([_wrap_login(p) for p in urlpatterns], app_namespace))),
        path("project-list/", projects, name="project-list"),
    ]


@override_settings(ROOT_URLCONF=LivePaperTestURLs)
class LivePaperMountTest(ClewStoreFixture):
    def setUp(self):
        super().setUp()
        for user, marker in ((self.alice, "alice"), (self.bob, "bob")):
            root = self.roots[user.pk]
            (root / "manuscript.tex").write_text(r"\vclaim{value} " + marker + " private text")
            claim = {
                "claim_id": "value", "location": {"file": "manuscript.tex", "line": 1},
                "state": "not_supported", "reason": "Recorded source differs",
                "stated_value": 20, "source": {"file": "output.csv", "value": 21},
            }
            legacy = {
                "claim_id": "value", "file_path": "manuscript.tex", "line_number": 1,
                "claim_type": "value", "claim_value": 20, "status": "suspect",
            }
            (root / "claims.json").write_text(json.dumps({"claims": [legacy]}))
            report = {
                "schema": "scitex-live-paper.evidence-report", "schema_version": "1.2.0",
                "provider": {"name": "recorded-integration-fixture"},
                "project_root": str(self.roots[self.bob.pk]), "claims": [claim],
            }
            (root / "evidence-report.json").write_text(json.dumps(report))

    def resource(self, endpoint, **query):
        return self.client.get(
            "/apps/live-paper/" + endpoint,
            {"project": "clew-alice/paper-scitex-clew", **query},
        )

    def test_owned_pages_use_installed_leaf_and_preserve_navigation(self):
        second = Project.objects.bulk_create([
            Project(owner=self.alice, name="Navigation", slug="navigation")
        ])[0]
        profile = UserProfile.objects.create(user=self.alice, last_active_repository=second)
        before = (self.roots[self.alice.pk] / "manuscript.tex").read_bytes()
        for endpoint in ("", "paper.html", "graph.html", "review.json", "review.txt", "assets"):
            with self.subTest(endpoint=endpoint):
                response = self.resource(endpoint, claim_id="value", name="assets/paper.js")
                self.assertEqual(response.status_code, 200, response.content[:400])
                self.assertNotIn(b"bob private text", response.content)
                profile.refresh_from_db()
                self.assertEqual(profile.last_active_repository_id, second.pk)
        html = self.resource("paper.html").content
        self.assertIn(b"alice private text", html)
        self.assertIn(b">20<", html)
        self.assertIn(b'"value": 21', html)
        self.assertEqual((self.roots[self.alice.pk] / "manuscript.tex").read_bytes(), before)

    def test_every_resource_refuses_another_users_project(self):
        self.client.force_login(self.bob)
        for endpoint in ("paper.html", "graph.html", "review.json", "review.txt", "assets"):
            with self.subTest(endpoint=endpoint):
                response = self.resource(endpoint, claim_id="value", name="assets/paper.js")
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b"alice private text", response.content)

    def test_explicit_working_directory_cannot_cross_the_user_jail(self):
        for endpoint in ("paper.html", "assets"):
            with self.subTest(endpoint=endpoint):
                response = self.resource(endpoint, working_dir=str(self.roots[self.bob.pk]), name="assets/paper.js")
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(b"bob private text", response.content)

    def test_report_and_manuscript_symlinks_cannot_read_another_user(self):
        root = self.roots[self.alice.pk]
        for name in ("evidence-report.json", "manuscript.tex"):
            with self.subTest(name=name):
                member = root / name
                before = member.read_bytes()
                member.unlink()
                member.symlink_to(self.roots[self.bob.pk] / name)
                try:
                    response = self.resource("paper.html")
                finally:
                    member.unlink()
                    member.write_bytes(before)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(b"bob private text", response.content)

    def test_anonymous_asset_requests_pass_through_host_login(self):
        query = urlencode({"project": "clew-alice/paper-scitex-clew", "name": "assets/paper.js"})
        response = Client().get("/apps/live-paper/assets?" + query)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(b"alice private text", response.content)
