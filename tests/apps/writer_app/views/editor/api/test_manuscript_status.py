#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GET /apps/writer/api/project/<id>/manuscript-status/ answers instead of 404-probing."""

import pytest
from django.urls import reverse

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.writer_workspace_layout import (
    get_manuscript_path,
)

pytestmark = pytest.mark.django_db


def _status_for(client, project):
    url = reverse("writer_app:api_manuscript_status", args=[project.id])
    return client.get(url).json()


@pytest.fixture
def owned_project(client, django_user_model, settings, tmp_path):
    settings.BASE_DIR = tmp_path
    owner = django_user_model.objects.create_user(username="status-owner", password="x")
    project = Project.objects.create(
        slug="status-study", owner=owner, name="status-study", visibility="private"
    )
    manager = get_project_filesystem_manager(owner)
    (manager.base_path / project.slug).mkdir(parents=True, exist_ok=True)
    client.force_login(owner)
    return project


@pytest.fixture
def project_with_manuscript(owned_project):
    manager = get_project_filesystem_manager(owned_project.owner)
    project_root = manager.get_project_root_path(owned_project)
    get_manuscript_path(project_root).mkdir(parents=True)
    return owned_project


def test_status_without_a_manuscript_says_it_does_not_exist(client, owned_project):
    # Arrange
    project = owned_project
    # Act
    status = _status_for(client, project)
    # Assert
    assert status["exists"] is False


def test_status_with_a_manuscript_says_it_exists(client, project_with_manuscript):
    # Arrange
    project = project_with_manuscript
    # Act
    status = _status_for(client, project)
    # Assert
    assert status["exists"] is True
