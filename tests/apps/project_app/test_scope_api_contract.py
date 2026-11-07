"""Exercise the real tagged-scope HTTP adapter using only owned test records."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory

from apps.infra.project_app.models import Project
from apps.infra.project_app.views.projects.scope_api import api_project_scope


@pytest.mark.django_db
def test_scope_contract():
    user = User.objects.create_user(username="scope-contract-user")
    project = Project.objects.create(owner=user, slug="paper", name="Paper")
    identifier = f"{user.username}/{project.slug}"
    factory = RequestFactory()

    def request(method, payload=None):
        if method == "GET":
            value = factory.get("/api/project/scope/")
        else:
            value = factory.post(
                "/api/project/scope/", json.dumps(payload), content_type="application/json"
            )
        value.user = User.objects.get(pk=user.pk)
        value.session = {}
        return api_project_scope(value)

    def get():
        response = request("GET")
        assert response.status_code == 200
        return json.loads(response.content)

    def post(payload, want):
        response = request("POST", payload)
        body = json.loads(response.content)
        assert response.status_code == want, (payload, response.status_code, body)
        return body

    body = get()
    assert body["allow_user_scope"] is True
    assert set(body) >= {"projects", "current", "allow_user_scope"}
    assert identifier in {entry["id"] for entry in body["projects"]}

    body = post({"scope": "user", "id": None}, 200)
    assert body == {"current": None, "current_scope": "user"}

    body = post({"scope": "project", "id": identifier}, 200)
    assert body["current_scope"] == "project"
    assert get()["current_scope"] == "project"

    body = post({"id": identifier}, 200)
    assert body["current"] == identifier
    user.profile.refresh_from_db()
    assert user.profile.last_active_repository_id == project.pk

    post({"scope": "org", "id": "x"}, 403)
    post({"scope": "project", "id": "nobody/ghost"}, 403)
    post({"scope": "user"}, 403)
    post({"scope": "user", "id": 5}, 403)
