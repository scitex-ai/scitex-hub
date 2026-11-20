"""Resource reads preserve the user's separate remembered navigation project."""

from apps.infra.accounts_app.models.profile import UserProfile
from apps.infra.project_app.models import Project
from django.test import override_settings

from ._clew_store_fixture import ClewStoreFixture


class ClewStoreSelectionTest(ClewStoreFixture):
    @override_settings(
        SCITEX_PROJECT_PROVIDER=(
            "apps.infra.project_app.services.project_scope.AppAwareHubProjectProvider"
        )
    )
    def test_leaf_page_declares_project_scope_to_the_actual_hub_provider(self):
        response = self.client.get(
            "/apps/clew/", {"project": "clew-alice/paper-scitex-clew"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'data-project-ref="clew-alice/paper-scitex-clew"'
        )
        self.assertNotContains(response, "Project provider is unavailable")

    def test_api_and_file_reads_do_not_change_the_remembered_project(self):
        second = Project.objects.bulk_create(
            [
                Project(
                    owner=self.alice,
                    name="Navigation project",
                    slug="navigation-project",
                )
            ]
        )[0]
        profile = UserProfile.objects.create(
            user=self.alice, last_active_repository=second
        )
        for route in ("stats/", "file/"):
            with self.subTest(route=route):
                response = self.get(route, path="input.csv")
                self.assertEqual(response.status_code, 200, response.content)
                profile.refresh_from_db()
                self.assertEqual(profile.last_active_repository_id, second.pk)
