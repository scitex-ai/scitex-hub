"""GET /api/search/ — the header command palette's grouped, access-checked results."""

import pytest
from django.contrib.auth import get_user_model

from apps.infra.project_app.models import Project

User = get_user_model()

SEARCH_URL = "/api/search/"


def _titles(response, group_key):
    groups = {group["key"]: group for group in response.json()["groups"]}
    return [result["title"] for result in groups.get(group_key, {}).get("results", [])]


def _all_titles(response):
    return [
        result["title"]
        for group in response.json()["groups"]
        for result in group["results"]
    ]


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        username="palette-owner", email="palette-owner@example.com", password="x"
    )


@pytest.fixture
def private_project(owner):
    return Project.objects.create(
        name="Zebrafish Secret Study",
        slug="zebrafish-secret-study",
        owner=owner,
        visibility="private",
        description="",
    )


def test_anonymous_search_never_returns_a_private_project(client, private_project):
    # Arrange
    query = "zebrafish"
    # Act
    response = client.get(SEARCH_URL, {"q": query})
    # Assert
    assert private_project.name not in _all_titles(response)


def test_owner_sees_their_own_private_project(client, owner, private_project):
    # Arrange
    client.force_login(owner)
    # Act
    response = client.get(SEARCH_URL, {"q": "ZEBRAFISH"})
    # Assert
    assert private_project.name in _titles(response, "my_projects")


def test_app_registry_match_returns_the_docs_app(client, db):
    # Arrange
    query = "doc"
    # Act
    response = client.get(SEARCH_URL, {"q": query})
    # Assert
    assert "Docs" in _titles(response, "apps")


def test_endpoint_returns_200_json(client, db):
    # Arrange
    query = "settings"
    # Act
    response = client.get(SEARCH_URL, {"q": query})
    # Assert
    assert (response.status_code, response["Content-Type"]) == (200, "application/json")
