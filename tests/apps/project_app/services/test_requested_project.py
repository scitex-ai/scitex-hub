#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An app opened from a project must open THAT project, not the last-used one.

Writer used to answer "which project" from ``profile.last_active_repository``
alone, so a user who clicked Writer on project B landed in project A (the one
they had used before). ``get_requested_project`` reads the explicit hint — the
``?project=`` query, then the Referer — and Writer persists it.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_utils import (
    get_requested_project,
    remember_current_project,
)

User = get_user_model()


@pytest.fixture
def owner(db):
    # Arrange
    return User.objects.create_user(
        username="hinted", email="hinted@example.com", password="x"
    )


@pytest.fixture
def last_used(db, owner):
    # Arrange
    project = Project.objects.create(name="Older", slug="older-work", owner=owner)
    owner.profile.last_active_repository = project
    owner.profile.save()
    return project


@pytest.fixture
def came_from(db, owner):
    # Arrange
    return Project.objects.create(name="Sleep", slug="sleep-study", owner=owner)


@pytest.fixture
def stranger_project(db):
    # Arrange
    other = User.objects.create_user(
        username="stranger", email="stranger@example.com", password="x"
    )
    return Project.objects.create(name="Theirs", slug="theirs", owner=other)


def _request(owner, path="/apps/writer/", **extra):
    request = RequestFactory().get(path, **extra)
    request.user = owner
    request.session = SessionStore()
    return request


class TestGetRequestedProject:
    def test_query_slug_wins(self, owner, last_used, came_from):
        # Arrange
        request = _request(owner, "/apps/writer/?project=sleep-study")
        # Act
        project = get_requested_project(request)
        # Assert
        assert project == came_from

    def test_query_owner_slug_form(self, owner, last_used, came_from):
        # Arrange
        request = _request(owner, "/apps/writer/?project=hinted/sleep-study")
        # Act
        project = get_requested_project(request)
        # Assert
        assert project == came_from

    def test_referer_project_page(self, owner, last_used, came_from):
        # Arrange
        request = _request(
            owner, HTTP_REFERER="http://testserver/hinted/sleep-study/blob/main/a.py"
        )
        # Act
        project = get_requested_project(request)
        # Assert
        assert project == came_from

    def test_query_beats_referer(self, owner, last_used, came_from):
        # Arrange
        request = _request(
            owner,
            "/apps/writer/?project=older-work",
            HTTP_REFERER="http://testserver/hinted/sleep-study/",
        )
        # Act
        project = get_requested_project(request)
        # Assert
        assert project == last_used

    def test_foreign_site_referer_ignored(self, owner, last_used, came_from):
        # Arrange
        request = _request(owner, HTTP_REFERER="https://evil.example/hinted/sleep-study/")
        # Act
        project = get_requested_project(request)
        # Assert
        assert project is None

    def test_other_users_project_ignored(self, owner, stranger_project):
        # Arrange
        request = _request(owner, HTTP_REFERER="http://testserver/stranger/theirs/")
        # Act
        project = get_requested_project(request)
        # Assert
        assert project is None

    def test_no_hint_returns_none(self, owner, last_used):
        # Arrange
        request = _request(owner, HTTP_REFERER="http://testserver/apps/")
        # Act
        project = get_requested_project(request)
        # Assert
        assert project is None


class TestRememberCurrentProject:
    def test_remember_project_updates_profile_selection(self, owner, last_used, came_from):
        # Arrange
        request = _request(owner)
        # Act
        remember_current_project(request, came_from)
        # Assert
        owner.profile.refresh_from_db()
        assert owner.profile.last_active_repository_id == came_from.id

    def test_remember_project_updates_session_slug(self, owner, last_used, came_from):
        # Arrange
        request = _request(owner)
        # Act
        remember_current_project(request, came_from)
        # Assert
        assert request.session["current_project_slug"] == came_from.slug


class TestWriterOpensTheProjectYouCameFrom:
    def test_writer_page_uses_referer_project(self, client, owner, last_used, came_from):
        # Arrange
        client.force_login(owner)
        # Act
        response = client.get(
            "/apps/writer/", HTTP_REFERER="http://testserver/hinted/sleep-study/"
        )
        # Assert
        assert response.context["current_project"] == came_from
