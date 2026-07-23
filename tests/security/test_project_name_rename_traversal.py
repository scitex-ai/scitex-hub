"""Regression: project RENAME must reject path-traversal names.

`project.name` becomes a filesystem path component (…/users/<user>/<name>) in
services that build workspace paths from it (e.g. gitea_auto_sync builds
Path(f"/app/data/users/{username}/{project.name}")). The CREATE paths validate
the name (Project.validate_repository_name — ^[a-zA-Z0-9._-]+$, no leading/
trailing special → blocks '/' and '..'), but the RENAME endpoints historically
did not, so an authenticated owner could rename to '../../users/victim/proj' and
escape their jail (cross-tenant path traversal). See
sec-nonclass-pathinjection-triage.

These tests assert both rename endpoints now reject such a name and leave
project.name unchanged, and that a legitimate rename still succeeds (the guard is
not over-broad).
"""
from __future__ import annotations

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

pytestmark = pytest.mark.security

TRAVERSAL_NAME = "../../users/victim/victimproj"
SAFE_NAME = "Safe Name"


def _make_owner():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="renameowner", email="ro@example.com", password="TestPassword123!"
    )


def _make_project(owner):
    from apps.infra.project_app.models import Project

    return Project.objects.create(owner=owner, name=SAFE_NAME, slug="safe-name")


def _post_request(data, user):
    request = RequestFactory().post("/rename", data)
    request.user = user
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    setattr(request, "_messages", FallbackStorage(request))
    return request


@pytest.mark.django_db
def test_settings_update_general_rejects_path_traversal_name():
    # Arrange
    from apps.infra.project_app.views.settings_views import project_settings

    owner = _make_owner()
    project = _make_project(owner)
    request = _post_request(
        {"action": "update_general", "name": TRAVERSAL_NAME, "description": "d"}, owner
    )
    # Act
    project_settings(request, username=owner.username, slug=project.slug)
    project.refresh_from_db()
    # Assert
    assert project.name == SAFE_NAME


@pytest.mark.django_db
def test_project_edit_rejects_path_traversal_name():
    # Arrange
    from apps.infra.project_app.views.projects.edit import project_edit

    owner = _make_owner()
    project = _make_project(owner)
    request = _post_request({"name": TRAVERSAL_NAME, "description": "d"}, owner)
    # Act
    project_edit(request, username=owner.username, slug=project.slug)
    project.refresh_from_db()
    # Assert
    assert project.name == SAFE_NAME


@pytest.mark.django_db
def test_settings_update_general_accepts_a_valid_rename():
    # Arrange
    from apps.infra.project_app.views.settings_views import project_settings

    owner = _make_owner()
    project = _make_project(owner)
    request = _post_request(
        {"action": "update_general", "name": "new-valid-name", "description": "d"}, owner
    )
    # Act
    project_settings(request, username=owner.username, slug=project.slug)
    project.refresh_from_db()
    # Assert
    assert project.name == "new-valid-name"


def test_validate_repository_name_rejects_parent_traversal():
    # Arrange
    from apps.infra.project_app.models import Project

    # Act
    is_valid, _error = Project.validate_repository_name(TRAVERSAL_NAME)
    # Assert
    assert is_valid is False
