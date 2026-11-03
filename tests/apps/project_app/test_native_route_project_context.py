"""Only the repository URL owner can bind template project context."""

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory
from django.urls import resolve

from apps.infra.project_app.context_processors import project_context
from apps.infra.project_app.models import Project


@pytest.mark.parametrize("path", ["/apps/live-paper/", "/accounts/settings/", "/landing/"])
def test_native_routes_do_not_query_repository_models(path):
    # No db fixture: an accidental ORM lookup is a failure, not a mocked result.
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    context = project_context(request)
    assert context["project"] is None
    assert context["is_guest_session"] is False


@pytest.mark.django_db
@pytest.mark.parametrize("attach_match", [False, True])
def test_actual_public_repository_url_resolves_its_owned_project(attach_match):
    owner = User.objects.create_user(username="context-route-owner")
    project = Project.objects.create(
        owner=owner, slug="public-study", name="Study", visibility="public"
    )
    request = RequestFactory().get(f"/{owner.username}/{project.slug}/")
    request.user = AnonymousUser()
    match = resolve(request.path_info)
    assert "project_app" in match.app_names
    if attach_match:
        request.resolver_match = match
    assert project_context(request)["project"] == project
