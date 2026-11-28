#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Issue lifecycle views record IssueEvent rows without crashing.

Regression (2026-11-19 acceptance walk on the dev server): every view-level
``IssueEvent.objects.create`` passed ``actor=``, but the model field is
``user``. Creating an issue saved the Issue row and then answered HTTP 500
(``IssueEvent() got unexpected keyword arguments: 'actor'``); close, reopen,
assign, label and milestone failed the same way.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client


@pytest.fixture
def owned_project(db):
    from django.contrib.auth.models import User

    from apps.infra.project_app.models import Project

    suffix = uuid.uuid4().hex[:8]
    user = User.objects.create_user(username=f"issues_{suffix}", password="x")
    project = Project.objects.create(slug=f"p-{suffix}", owner=user, name="P")
    client = Client()
    client.force_login(user)
    try:
        yield client, user, project
    finally:
        # The user-creation signal provisions data/users/<username>/.
        shutil.rmtree(
            Path(settings.BASE_DIR) / "data" / "users" / user.username,
            ignore_errors=True,
        )


def _create_issue(client, user, project, title="Smoke"):
    return client.post(
        f"/{user.username}/{project.slug}/issues/new/",
        data={"title": title, "description": "body"},
    )


def _api(client, user, project, issue_number, verb, payload=None):
    return client.post(
        f"/{user.username}/{project.slug}/issues/api/{issue_number}/{verb}/",
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


def _events(project):
    from apps.infra.project_app.models import IssueEvent

    return list(
        IssueEvent.objects.filter(issue__project=project)
        .order_by("id")
        .values_list("event_type", "user")
    )


@pytest.mark.django_db
@pytest.mark.guards(
    defect="issue views passed actor= to IssueEvent, whose field is user"
)
class TestIssueEvents:
    def test_create_redirects_instead_of_500(self, owned_project):
        # Arrange
        client, user, project = owned_project
        # Act
        response = _create_issue(client, user, project)
        # Assert
        assert response.status_code == 302

    def test_create_records_created_event_by_the_author(self, owned_project):
        # Arrange
        client, user, project = owned_project
        # Act
        _create_issue(client, user, project)
        # Assert
        assert _events(project) == [("created", user.pk)]

    def test_close_then_reopen_records_one_event_each(self, owned_project):
        # Arrange
        client, user, project = owned_project
        _create_issue(client, user, project)
        # Act
        statuses = (
            _api(client, user, project, 1, "close").status_code,
            _api(client, user, project, 1, "reopen").status_code,
        )
        # Assert
        assert (statuses, _events(project)) == (
            (200, 200),
            [("created", user.pk), ("closed", user.pk), ("reopened", user.pk)],
        )

    def test_label_add_records_labeled_event(self, owned_project):
        # Arrange
        from apps.infra.project_app.models import IssueLabel

        client, user, project = owned_project
        _create_issue(client, user, project)
        label = IssueLabel.objects.create(project=project, name="bug", color="d73a4a")
        payload = {"label_id": label.pk, "action": "add"}
        # Act
        status = _api(client, user, project, 1, "label", payload).status_code
        # Assert
        assert (status, _events(project)[-1]) == (200, ("labeled", user.pk))
