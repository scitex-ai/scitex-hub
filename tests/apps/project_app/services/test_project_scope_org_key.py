#!/usr/bin/env python3
"""``find_accessible_project`` accepts the organization slug of an org-owned project.

An organization-owned project's page is ``/<org>/<slug>/``, so a project-scope app
opened with ``?project=<org>/<slug>`` must find it. The organization name only
selects among projects the caller can already access, so it grants nothing.
"""

import pytest
from django.contrib.auth.models import User

from apps.infra.organizations_app.models import Organization
from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_scope import find_accessible_project


@pytest.fixture
def org_project(db):
    owner = User.objects.create_user("org-scope-owner")
    org = Organization.objects.create(name="Scope Lab", slug="scope-lab")
    project = Project.objects.create(
        owner=owner, org_owner=org, name="Paper", slug="paper"
    )
    return owner, project


@pytest.mark.django_db
def test_org_slug_key_finds_the_owners_org_project(org_project):
    # Arrange
    owner, project = org_project
    # Act
    found = find_accessible_project(owner, "scope-lab/paper")
    # Assert
    assert found == project


@pytest.mark.django_db
def test_owner_username_key_still_finds_the_org_project(org_project):
    # Arrange
    owner, project = org_project
    # Act
    found = find_accessible_project(owner, "org-scope-owner/paper")
    # Assert
    assert found == project


@pytest.mark.django_db
def test_org_slug_key_grants_nothing_to_an_outsider(org_project):
    # Arrange
    outsider = User.objects.create_user("org-scope-outsider")
    # Act
    found = find_accessible_project(outsider, "scope-lab/paper")
    # Assert
    assert found is None
