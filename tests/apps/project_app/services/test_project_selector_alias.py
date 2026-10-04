"""Legacy Hub model IDs resolve through the real access-scoped SDK provider."""

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from scitex_sdk.app.project_context import STATE_DENIED, resolve_active_project
from scitex_sdk.ui.project_scope import canonical_project_selector

from apps.infra.project_app.models import Project, ProjectMembership
from apps.infra.project_app.services.project_scope import (
    HubProjectProvider,
    project_key,
)


class ProjectSelectorAliasTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="alias-owner")
        cls.other = User.objects.create_user(username="alias-other")
        cls.owned = Project.objects.create(
            owner=cls.owner, slug="paper", name="Owned paper", visibility="private"
        )
        cls.shared = Project.objects.create(
            owner=cls.other, slug="paper", name="Shared paper", visibility="private"
        )
        cls.membership = ProjectMembership.objects.create(
            project=cls.shared, user=cls.owner, permission_level="read"
        )
        cls.private = Project.objects.create(
            owner=cls.other, slug="private", name="Private", visibility="private"
        )
        cls.public = Project.objects.create(
            owner=cls.other, slug="public", name="Public", visibility="public"
        )

    def setUp(self):
        profile = User.objects.get(pk=self.owner.pk).profile
        profile.last_active_repository = self.owned
        profile.save(update_fields=["last_active_repository"])

    def _request(self):
        request = RequestFactory().get("/workspace/content/")
        request.user = User.objects.get(pk=self.owner.pk)
        return request

    def test_owned_model_id_reaches_the_genuine_sdk_canonical_selector(self):
        # Arrange
        request = self._request()
        provider = HubProjectProvider()
        listed = {entry.id for entry in provider.list_projects(request)}
        # Act
        selected = canonical_project_selector(
            request, provider, str(self.owned.pk), listed
        )
        # Assert
        assert selected == project_key(self.owned)

    def test_shared_model_id_keeps_the_other_owners_same_slug(self):
        # Arrange
        request = self._request()
        provider = HubProjectProvider()
        # Act
        result = resolve_active_project(
            request, provider, str(self.shared.pk), remember=False
        )
        # Assert
        assert result.ok and result.project.id == "alias-other/paper"

    def test_foreign_private_id_cannot_fall_back_to_the_stored_project(self):
        # Arrange
        request = self._request()
        # Act
        result = resolve_active_project(
            request, HubProjectProvider(), str(self.private.pk)
        )
        # Assert
        assert result.state == STATE_DENIED and result.project is None

    def test_foreign_public_id_is_denied_by_the_same_access_list(self):
        # Arrange
        request = self._request()
        # Act
        result = resolve_active_project(
            request, HubProjectProvider(), str(self.public.pk)
        )
        # Assert
        assert result.state == STATE_DENIED and result.project is None

    def test_revoked_membership_removes_the_numeric_alias(self):
        # Arrange
        ProjectMembership.objects.filter(pk=self.membership.pk).delete()
        request = self._request()
        # Act
        result = HubProjectProvider().canonical_project_id(request, str(self.shared.pk))
        # Assert
        assert result is None

    def test_anonymous_request_cannot_normalize_a_model_id(self):
        # Arrange
        request = RequestFactory().get("/workspace/content/")
        request.user = AnonymousUser()
        # Act
        selected = HubProjectProvider().canonical_project_id(request, str(self.owned.pk))
        # Assert
        assert selected is None

    def test_missing_request_identity_is_a_refusal(self):
        # Arrange
        request = RequestFactory().get("/workspace/content/")
        # Act
        selected = HubProjectProvider().canonical_project_id(request, str(self.owned.pk))
        # Assert
        assert selected is None

    def test_invalid_aliases_cannot_reach_any_canonical_project(self):
        # Arrange
        request = self._request()
        provider = HubProjectProvider()
        invalid = (None, False, True, self.owned.pk, [], {}, "", " 1", "01", "١")
        # Act
        selected = tuple(provider.canonical_project_id(request, value) for value in invalid)
        # Assert
        assert selected == (None,) * len(invalid)

    def test_unknown_large_numeric_input_is_denied_without_integer_coercion(self):
        # Arrange
        request = self._request()
        # Act
        selected = HubProjectProvider().canonical_project_id(request, "9" * 5000)
        # Assert
        assert selected is None

    def test_numeric_resource_resolution_does_not_rewrite_navigation(self):
        # Arrange
        request = self._request()
        provider = HubProjectProvider()
        # Act
        result = resolve_active_project(
            request, provider, str(self.shared.pk), remember=False
        )
        # Assert
        assert (result.project.id, provider.last_visited(request)) == (
            "alias-other/paper", "alias-owner/paper"
        )

    def test_existing_canonical_selection_keeps_its_identity(self):
        # Arrange
        request = self._request()
        provider = HubProjectProvider()
        listed = {entry.id for entry in provider.list_projects(request)}
        # Act
        selected = canonical_project_selector(
            request, provider, project_key(self.shared), listed
        )
        # Assert
        assert selected == "alias-other/paper"
