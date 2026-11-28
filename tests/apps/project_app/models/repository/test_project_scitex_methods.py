#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/project_app/models/repository/project_scitex_methods.py"""

from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from apps.infra.organizations_app.models import Organization
from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)


@pytest.mark.django_db
def test_org_owned_project_resolves_where_its_files_are_served(tmp_path):
    # Arrange
    owner = User.objects.create_user("org-paper-author")
    org = Organization.objects.create(name="Example Lab", slug="example-lab")
    project = Project(owner=owner, org_owner=org, name="Paper", slug="paper")
    # Act
    with override_settings(BASE_DIR=tmp_path):
        local = project.get_local_path()
        served = get_project_filesystem_manager(owner)._get_effective_base_path(project)
    # Assert
    assert (local, local.parent) == (
        tmp_path / "data" / "organizations" / "example-lab" / "proj" / "paper",
        served,
    )


@pytest.mark.django_db
def test_user_owned_project_resolves_under_the_owner(tmp_path):
    # Arrange
    owner = User.objects.create_user("user-paper-author")
    project = Project(owner=owner, name="Paper", slug="paper")
    # Act
    with override_settings(BASE_DIR=tmp_path):
        local = project.get_local_path()
    # Assert
    assert local == Path(tmp_path) / "data/users/user-paper-author/proj/paper"


def test_explicit_local_path_wins():
    # Arrange
    project = Project(name="Paper", slug="paper", local_path="/srv/papers/paper")
    # Act
    local = project.get_local_path()
    # Assert
    assert local == Path("/srv/papers/paper")


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
