#!/usr/bin/env python3
"""SDK project scope in the hub: explicit project beats last visited; listing is access-scoped."""

import json

import pytest
from django.contrib.auth.models import User
from django.template import Context
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project, ProjectMembership
from apps.infra.project_app.services.project_scope import (
    HubProjectProvider,
    project_for_scope_app,
    project_key,
    resolve_scoped_project,
)
from apps.infra.project_app.services.project_utils import (
    get_current_project,
    get_requested_project,
    remember_current_project,
)
from apps.infra.project_app.templatetags.project_scope_tags import (
    hub_project_provider_meta,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class ProjectScopeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username="scope-me", password=PASSWORD)
        cls.other = User.objects.create_user(username="scope-other", password=PASSWORD)
        cls.notes = Project.objects.create(
            slug="notes", owner=cls.me, name="notes", visibility="private"
        )
        cls.paper = Project.objects.create(
            slug="paper", owner=cls.me, name="paper", visibility="private"
        )
        Project.objects.create(
            slug="secret", owner=cls.other, name="secret", visibility="private"
        )
        Project.objects.create(
            slug="open", owner=cls.other, name="open", visibility="public"
        )
        cls.shared = Project.objects.create(
            slug="shared", owner=cls.other, name="shared", visibility="private"
        )
        ProjectMembership.objects.create(project=cls.shared, user=cls.me)

    def setUp(self):
        profile = User.objects.get(pk=self.me.pk).profile
        profile.last_active_repository = self.notes
        profile.save(update_fields=["last_active_repository"])

    def _request(self, query=""):
        request = RequestFactory().get("/apps/figrecipe/" + query)
        request.user = User.objects.get(pk=self.me.pk)
        return request

    def _listed_ids(self):
        return {e.id for e in HubProjectProvider().list_projects(self._request())}

    def _owned_plus_shared_ids(self):
        owned = {project_key(p) for p in Project.objects.filter(owner=self.me)}
        return owned | {project_key(self.shared)}

    def test_explicit_url_project_beats_last_visited(self):
        # Arrange
        request = self._request("?project=scope-me/paper")
        # Act
        project = resolve_scoped_project(request)
        # Assert
        assert project == self.paper

    def test_explicit_url_project_becomes_last_visited(self):
        # Arrange
        request = self._request("?project=scope-me/paper")
        # Act
        resolve_scoped_project(request)
        # Assert
        assert (
            User.objects.get(pk=self.me.pk).profile.last_active_repository == self.paper
        )

    def test_last_visited_is_used_when_url_has_no_project(self):
        # Arrange
        request = self._request()
        # Act
        project = resolve_scoped_project(request)
        # Assert
        assert project == self.notes

    def test_inaccessible_explicit_project_does_not_fall_back_to_last_visited(self):
        # Arrange
        request = self._request("?project=scope-other/secret")
        # Act
        project = resolve_scoped_project(request)
        # Assert
        assert project is None

    def test_listing_excludes_other_users_private_projects(self):
        # Arrange
        forbidden = "scope-other/secret"
        # Act
        listed = self._listed_ids()
        # Assert
        assert forbidden not in listed

    def test_listing_excludes_other_users_public_projects(self):
        # Arrange
        unrelated = "scope-other/open"
        # Act
        listed = self._listed_ids()
        # Assert
        assert unrelated not in listed

    def test_listing_is_owned_plus_shared(self):
        # Arrange
        expected = self._owned_plus_shared_ids()
        # Act
        listed = self._listed_ids()
        # Assert
        assert listed == expected

    def test_hub_current_project_preserves_authorized_shared_last_visited(self):
        # Arrange
        profile = User.objects.get(pk=self.me.pk).profile
        profile.last_active_repository = self.shared
        profile.save(update_fields=["last_active_repository"])
        request = self._request()
        request.session = {}
        # Act
        project = get_current_project(request)
        # Assert
        assert project == self.shared

    def test_explicit_shared_project_is_a_valid_hub_request_project(self):
        # Arrange
        request = self._request("?project=scope-other/shared")
        # Act
        project = get_requested_project(request)
        # Assert
        assert project == self.shared

    def test_remembered_shared_project_session_key_includes_owner(self):
        # Arrange
        request = self._request()
        request.session = {}
        # Act
        remember_current_project(request, self.shared)
        # Assert
        assert request.session["current_project_key"] == "scope-other/shared"
        assert request.session["current_project_slug"] == "shared"

    def test_scope_api_lists_only_accessible_projects(self):
        # Arrange
        self.client.login(username="scope-me", password=PASSWORD)
        # Act
        body = self.client.get("/api/project/scope/").json()
        # Assert
        assert {p["id"] for p in body["projects"]} == self._owned_plus_shared_ids()

    def test_scope_api_refuses_to_remember_a_foreign_project(self):
        # Arrange
        self.client.login(username="scope-me", password=PASSWORD)
        # Act
        response = self.client.post(
            "/api/project/scope/",
            data=json.dumps({"id": "scope-other/secret"}),
            content_type="application/json",
        )
        # Assert
        assert response.status_code == 403

    def test_figrecipe_opens_the_url_project_over_last_visited(self):
        # Arrange
        self.client.login(username="scope-me", password=PASSWORD)
        # Act
        response = self.client.get("/apps/figrecipe/?project=scope-me/paper")
        # Assert
        assert b'data-project-slug="paper"' in response.content

    def test_figrecipe_opens_last_visited_without_url_project(self):
        # Arrange
        self.client.login(username="scope-me", password=PASSWORD)
        # Act
        response = self.client.get("/apps/figrecipe/")
        # Assert
        assert b'data-project-slug="notes"' in response.content

    def test_figrecipe_page_advertises_the_hub_project_provider(self):
        # Arrange
        _require_sdk_host_service()
        self.client.login(username="scope-me", password=PASSWORD)
        # Act
        response = self.client.get("/apps/figrecipe/?project=scope-me/paper")
        # Assert
        assert (
            b'<meta name="stx-project-provider" content="/api/project/scope/">'
            in response.content
        )

    def test_figrecipe_default_project_becomes_last_visited(self):
        # Arrange
        profile = User.objects.get(pk=self.me.pk).profile
        profile.last_active_repository = None
        profile.save(update_fields=["last_active_repository"])
        request = self._request()
        request.session = {}
        # Act
        opened = project_for_scope_app(request)
        # Assert
        assert HubProjectProvider().last_visited(request) == project_key(opened)

    def test_writer_leaf_picker_maps_the_hub_project(self):
        # Arrange
        _require_sdk_host_service()
        from django.template.loader import render_to_string

        # Act
        html = render_to_string(
            "writer/_project_picker.html",
            {"request": self._request(), "current_project": self.paper},
        )
        # Assert
        assert 'data-current="scope-me/paper"' in html

    def test_anonymous_visitor_gets_no_provider_meta(self):
        # Arrange
        _require_sdk_host_service()
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        # Act
        html = hub_project_provider_meta(Context({"request": request}))
        # Assert
        assert html == ""


def _require_sdk_host_service():
    module = pytest.importorskip("scitex_ui.templatetags.scitex_project_picker")
    if not hasattr(module, "scitex_project_provider_meta"):
        pytest.skip("scitex-ui predates the project provider host service")
