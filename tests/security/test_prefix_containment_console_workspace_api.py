#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-prefix path escape in the console workspace file APIs.

FINDING (2026-07-22)
    Four endpoints under ``apps/workspace/console_app/workspace_api/`` guarded
    the project directory with a STRING PREFIX::

        project_path = ProjectServiceManager(project).get_project_path()
        file_full_path = project_path / file_path
        if not str(file_full_path.resolve()).startswith(str(project_path.resolve())):
            return JsonResponse({"error": "Invalid file path"}, status=400)

    ``str.startswith`` is not path containment. A SIBLING directory whose name
    merely EXTENDS the project root satisfies it: for root ``/…/proj`` the
    resolved path ``/…/proj-other/secret.txt`` — reached with the request path
    ``../proj-other/secret.txt`` — does start with ``/…/proj``.

    Because project roots live side by side under one parent, ``proj-other``
    is another project's checkout. The escape therefore let a caller READ
    (``api_get_file_content``), OVERWRITE (``api_save_file``), CREATE
    (``api_create_file``) and DELETE (``api_delete_file``) files belonging to a
    project they have no rights on — the permission check ran against the
    project they NAMED, not the one they actually touched.

SITES
    apps/workspace/console_app/workspace_api/file_read.py::api_get_file_content
    apps/workspace/console_app/workspace_api/file_write.py::api_save_file
    apps/workspace/console_app/workspace_api/file_create_delete.py::api_create_file
    apps/workspace/console_app/workspace_api/file_create_delete.py::api_delete_file

FIX
    ``validate_path_in_project()`` — component-wise containment via
    ``Path.resolve().relative_to()``.

DESIGN NOTES
- The code under test is the REAL view function, unmodified: the request is a
  real ``HttpRequest``, the path arithmetic is the production code's own, and
  the boundary decision is production's.
- No database and no mocking library: the two collaborators that would demand
  one — the ``Project`` row lookup and ``ProjectServiceManager`` (which only
  answers "where does this project live on disk?") — are replaced by
  HAND-ROLLED fakes installed by a ``yield`` fixture that restores the original
  attributes on teardown. The user is an UNSAVED model instance (``pk`` by
  hand), which still satisfies ``@login_required``.
- The project tree is a real ``tmp_path`` layout with real bytes on disk, so
  the exploit — and the damage it would do — is real, not simulated.
- Every escape test asserts the specific 400 / "Invalid file path" verdict AND
  the absence of the side effect, so an unrelated 500 cannot be mistaken for a
  blocked exploit.
- Each ANTI-REGRESSION test proves the legitimate in-root operation still
  succeeds — "reject everything" must not pass this gate.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.infra.project_app.services import (
    project_service_manager as psm_mod,
)
from apps.workspace.console_app.workspace_api import file_create_delete as create_mod
from apps.workspace.console_app.workspace_api import file_read as read_mod
from apps.workspace.console_app.workspace_api import file_write as write_mod

pytestmark = pytest.mark.security

PROJECT_ID = 1
SECRET = "other-project-private-data-must-not-leak\n"
# The sibling's directory name EXTENDS the root's name — the whole finding.
ROOT_NAME = "proj"
SIBLING_NAME = "proj-other"
ESCAPE = f"../{SIBLING_NAME}/secret.txt"


# ---------------------------------------------------------------- stubs


class _StubCollaborators:
    def all(self):
        return []


class _StubProject:
    """Enough of ``Project`` for these four views; never saved."""

    project_type = "local"
    visibility = "private"

    def __init__(self, owner):
        self.id = PROJECT_ID
        self.owner = owner
        self.collaborators = _StubCollaborators()

    def can_edit(self, user):
        return True


class _StubManager:
    def __init__(self, project):
        self._project = project

    def select_related(self, *args, **kwargs):
        return self

    def get(self, *args, **kwargs):
        return self._project


def _fake_project_model(project):
    class _FakeProject:
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        objects = _StubManager(project)

    return _FakeProject


# ---------------------------------------------------------------- fixtures


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def user():
    User = get_user_model()
    return User(pk=1, username="alice")


@pytest.fixture
def tree(tmp_path):
    """Two sibling project roots; the second's name extends the first's."""
    base = tmp_path.resolve()
    root = base / ROOT_NAME
    root.mkdir()
    sibling = base / SIBLING_NAME
    sibling.mkdir()
    (sibling / "secret.txt").write_text(SECRET)
    return {"root": root, "sibling": sibling}


@pytest.fixture
def wired(user, tree):
    """Install hand-rolled collaborators; restore the originals on teardown."""
    project = _StubProject(user)
    fake_model = _fake_project_model(project)
    root = tree["root"]

    class _FakeServiceManager:
        """Answers only the one question the views ask it."""

        def __init__(self, _project):
            pass

        def get_project_path(self):
            return root

    view_modules = (read_mod, write_mod, create_mod)
    saved = [(mod, mod.Project) for mod in view_modules]
    saved_psm = psm_mod.ProjectServiceManager
    for mod in view_modules:
        setattr(mod, "Project", fake_model)
    psm_mod.ProjectServiceManager = _FakeServiceManager
    try:
        yield tree
    finally:
        for mod, original in saved:
            setattr(mod, "Project", original)
        psm_mod.ProjectServiceManager = saved_psm


# ---------------------------------------------------------------- helpers


def _post(rf, user, url, body):
    req = rf.post(url, data=json.dumps(body), content_type="application/json")
    req.user = user
    return req


# ---------------------------------------------------------------- READ


@pytest.fixture
def read_escape(rf, user, wired):
    req = rf.get("/apps/workspace/api/file/", {"project_id": str(PROJECT_ID)})
    req.user = user
    resp = read_mod.api_get_file_content(req, ESCAPE)
    return {"resp": resp, "payload": json.loads(resp.content)}


def test_read_escape_is_rejected(read_escape):
    # Arrange
    resp = read_escape["resp"]
    # Act
    verdict = (resp.status_code, read_escape["payload"].get("error"))
    # Assert
    assert verdict == (400, "Invalid file path")


def test_read_escape_leaks_no_content(read_escape):
    # Arrange
    payload = read_escape["payload"]
    # Act
    body = json.dumps(payload)
    # Assert
    assert SECRET.strip() not in body


def test_read_own_file_still_works(rf, user, wired):
    # Arrange
    (wired["root"] / "notes.txt").write_text("my own notes\n")
    req = rf.get("/apps/workspace/api/file/", {"project_id": str(PROJECT_ID)})
    req.user = user
    # Act
    resp = read_mod.api_get_file_content(req, "notes.txt")
    # Assert
    assert (resp.status_code, json.loads(resp.content)["content"]) == (
        200,
        "my own notes\n",
    )


# ---------------------------------------------------------------- WRITE


@pytest.fixture
def write_escape(rf, user, wired):
    req = _post(
        rf,
        user,
        "/apps/workspace/api/save/",
        {"project_id": PROJECT_ID, "path": ESCAPE, "content": "PWNED\n"},
    )
    resp = write_mod.api_save_file(req)
    return {
        "resp": resp,
        "payload": json.loads(resp.content),
        "victim": wired["sibling"] / "secret.txt",
    }


def test_write_escape_is_rejected(write_escape):
    # Arrange
    resp = write_escape["resp"]
    # Act
    verdict = (resp.status_code, write_escape["payload"].get("error"))
    # Assert
    assert verdict == (400, "Invalid file path")


def test_write_escape_does_not_overwrite_sibling(write_escape):
    # Arrange
    victim = write_escape["victim"]
    # Act
    text = victim.read_text()
    # Assert
    assert text == SECRET


def test_write_own_file_still_works(rf, user, wired):
    # Arrange
    req = _post(
        rf,
        user,
        "/apps/workspace/api/save/",
        {"project_id": PROJECT_ID, "path": "ok.txt", "content": "saved\n"},
    )
    # Act
    resp = write_mod.api_save_file(req)
    # Assert
    assert (resp.status_code, (wired["root"] / "ok.txt").read_text()) == (200, "saved\n")


# ---------------------------------------------------------------- CREATE


@pytest.fixture
def create_escape(rf, user, wired):
    req = _post(
        rf,
        user,
        "/apps/workspace/api/create/",
        {
            "project_id": PROJECT_ID,
            "path": f"../{SIBLING_NAME}/planted.txt",
            "content": "PWNED\n",
        },
    )
    resp = create_mod.api_create_file(req)
    return {
        "resp": resp,
        "payload": json.loads(resp.content),
        "planted": wired["sibling"] / "planted.txt",
    }


def test_create_escape_is_rejected(create_escape):
    # Arrange
    resp = create_escape["resp"]
    # Act
    verdict = (resp.status_code, create_escape["payload"].get("error"))
    # Assert
    assert verdict == (400, "Invalid file path")


def test_create_escape_plants_no_file_in_sibling(create_escape):
    # Arrange
    planted = create_escape["planted"]
    # Act
    exists = planted.exists()
    # Assert
    assert exists is False


def test_create_own_file_still_works(rf, user, wired):
    # Arrange
    req = _post(
        rf,
        user,
        "/apps/workspace/api/create/",
        {"project_id": PROJECT_ID, "path": "new.txt", "content": "hello\n"},
    )
    # Act
    resp = create_mod.api_create_file(req)
    # Assert
    assert (resp.status_code, (wired["root"] / "new.txt").read_text()) == (
        200,
        "hello\n",
    )


# ---------------------------------------------------------------- DELETE


@pytest.fixture
def delete_escape(rf, user, wired):
    req = _post(
        rf,
        user,
        "/apps/workspace/api/delete/",
        {"project_id": PROJECT_ID, "path": ESCAPE},
    )
    resp = create_mod.api_delete_file(req)
    return {
        "resp": resp,
        "payload": json.loads(resp.content),
        "victim": wired["sibling"] / "secret.txt",
    }


def test_delete_escape_is_rejected(delete_escape):
    # Arrange
    resp = delete_escape["resp"]
    # Act
    verdict = (resp.status_code, delete_escape["payload"].get("error"))
    # Assert
    assert verdict == (400, "Invalid file path")


def test_delete_escape_does_not_destroy_sibling_file(delete_escape):
    # Arrange
    victim = delete_escape["victim"]
    # Act
    survived = victim.exists() and victim.read_text() == SECRET
    # Assert
    assert survived is True


def test_delete_own_file_still_works(rf, user, wired):
    # Arrange
    doomed = wired["root"] / "gone.txt"
    doomed.write_text("bye\n")
    req = _post(
        rf,
        user,
        "/apps/workspace/api/delete/",
        {"project_id": PROJECT_ID, "path": "gone.txt"},
    )
    # Act
    resp = create_mod.api_delete_file(req)
    # Assert
    assert (resp.status_code, doomed.exists()) == (200, False)


# EOF
