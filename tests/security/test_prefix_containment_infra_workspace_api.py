#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-prefix path escape in the shared workspace file APIs.

FINDING (2026-07-22)
    Both ``apps/infra/workspace_api/views/file_content.py::api_get_file_content``
    and ``apps/infra/workspace_api/views/file_save.py::api_save_file`` guarded
    the project directory with a STRING PREFIX::

        file_full_path = project_path / file_path
        if not str(file_full_path.resolve()).startswith(str(project_path.resolve())):
            return JsonResponse({"error": "Invalid file path"}, status=400)

    ``str.startswith`` is not path containment. A SIBLING directory whose name
    merely EXTENDS the project root satisfies it: for root ``<base>/alpha`` the
    resolved path ``<base>/alpha-other/secret.txt`` — reached with the request
    path ``../alpha-other/secret.txt`` — does start with ``<base>/alpha``.

    Consequence: the read endpoint serves another project's files, and the save
    endpoint WRITES into another project's tree, while the caller was only ever
    authorised against the project they named. Sibling projects live in exactly
    that layout (``data/users/<user>/proj/<slug>``), and a project slug is
    attacker-chosen, so the prerequisite is trivially engineered.

FIX
    ``validate_path_in_project()`` — component-wise containment via
    ``Path.resolve().relative_to()``.

DESIGN NOTES
- Everything downstream of the lookup is REAL: a real ``Project`` instance, the
  real ``ProjectServiceManager`` path resolution, and a real on-disk tree under
  ``tmp_path`` (``BASE_DIR`` is redirected there). The exploit therefore runs
  against production path logic, not a mock of it.
- The model instances are UNSAVED (``pk`` set by hand) and the single
  ``Project.objects.get`` lookup is swapped for an in-memory stand-in by an
  explicit set/restore fixture, so the suite never touches the test database.
- Arrange+act live in the fixtures so each test carries a single assertion.
"""

import json
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings

from apps.infra.project_app.models import Project as RealProject
from apps.infra.workspace_api.views import file_content as file_content_mod
from apps.infra.workspace_api.views import file_save as file_save_mod

pytestmark = pytest.mark.security

USERNAME = "alice"
SLUG = "alpha"
# The sibling project's slug EXTENDS this project's slug — the whole point of
# the finding. A plain "../elsewhere" traversal was already blocked.
SIBLING_SLUG = "alpha-other"
SECRET = "other-project-private-data-must-not-leak\n"
OWN_TEXT = "my own notes\n"


class _FakeQuerySet:
    def __init__(self, project):
        self._project = project

    def get(self, **kwargs):
        return self._project


class _FakeManager:
    def __init__(self, project):
        self._project = project

    def select_related(self, *args, **kwargs):
        return _FakeQuerySet(self._project)


class _ProjectLookup:
    """Stand-in for the ``Project`` model class inside a view module.

    Only the ``.objects.select_related(...).get(...)`` lookup is replaced; the
    object it hands back is a REAL ``Project`` instance, so every attribute the
    view touches afterwards is production behaviour.
    """

    DoesNotExist = RealProject.DoesNotExist

    def __init__(self, project):
        self.objects = _FakeManager(project)


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def env(tmp_path):
    """A real two-project tree: <base>/alpha next to <base>/alpha-other."""
    base = tmp_path.resolve()
    proj_base = base / "data" / "users" / USERNAME / "proj"

    root = proj_base / SLUG
    root.mkdir(parents=True)
    (root / "notes.txt").write_text(OWN_TEXT)

    sibling = proj_base / SIBLING_SLUG
    sibling.mkdir(parents=True)
    (sibling / "secret.txt").write_text(SECRET)

    User = get_user_model()
    user = User(pk=1, username=USERNAME)
    project = RealProject(
        id=1,
        name=SLUG,
        slug=SLUG,
        owner=user,
        project_type="local",
        visibility="private",
    )
    return SimpleNamespace(
        base=base, root=root, sibling=sibling, user=user, project=project
    )


@pytest.fixture
def views(env):
    """Point both views' Project lookup at the in-memory project, then restore."""
    lookup = _ProjectLookup(env.project)
    originals = {
        file_content_mod: file_content_mod.Project,
        file_save_mod: file_save_mod.Project,
    }
    for module in originals:
        module.Project = lookup
    try:
        yield env
    finally:
        for module, original in originals.items():
            module.Project = original


# ---------------------------------------------------------------------------
# api_get_file_content — cross-project READ
# ---------------------------------------------------------------------------


def _get_content(rf, env, file_path):
    request = rf.get("/api/workspace/file-content/", {"project_id": "1"})
    request.user = env.user
    with override_settings(BASE_DIR=str(env.base)):
        return file_content_mod.api_get_file_content(request, file_path)


@pytest.fixture
def read_escape(rf, views):
    return _get_content(rf, views, f"../{SIBLING_SLUG}/secret.txt")


def test_read_escape_is_rejected(read_escape):
    # Arrange
    response = read_escape
    # Act
    status = response.status_code
    # Assert
    assert status == 400, getattr(response, "content", b"")


def test_read_escape_does_not_return_the_sibling_secret(read_escape):
    # Arrange
    response = read_escape
    # Act
    body = response.content.decode()
    # Assert
    assert SECRET.strip() not in body


@pytest.fixture
def read_own(rf, views):
    return _get_content(rf, views, "notes.txt")


def test_read_own_file_still_works(read_own):
    # Arrange
    response = read_own
    # Act
    payload = json.loads(response.content)
    # Assert
    assert payload.get("content") == OWN_TEXT, payload


# ---------------------------------------------------------------------------
# api_save_file — cross-project WRITE
# ---------------------------------------------------------------------------


def _save(rf, env, file_path, content):
    request = rf.post(
        "/api/workspace/save-file/",
        data=json.dumps({"project_id": 1, "path": file_path, "content": content}),
        content_type="application/json",
    )
    request.user = env.user
    with override_settings(BASE_DIR=str(env.base)):
        return file_save_mod.api_save_file(request)


@pytest.fixture
def save_escape(rf, views):
    response = _save(rf, views, f"../{SIBLING_SLUG}/pwned.txt", "pwned\n")
    return SimpleNamespace(
        response=response, victim=views.sibling / "pwned.txt"
    )


def test_save_escape_is_rejected(save_escape):
    # Arrange
    response = save_escape.response
    # Act
    status = response.status_code
    # Assert
    assert status == 400, getattr(response, "content", b"")


def test_save_escape_writes_nothing_into_the_sibling_project(save_escape):
    # Arrange
    victim = save_escape.victim
    # Act
    landed = victim.exists()
    # Assert
    assert landed is False, f"wrote outside the project root: {victim}"


@pytest.fixture
def save_own(rf, views):
    response = _save(rf, views, "sub/mine.txt", "my own content\n")
    return SimpleNamespace(
        response=response, target=views.root / "sub" / "mine.txt"
    )


def test_save_own_file_still_succeeds(save_own):
    # Arrange
    response = save_own.response
    # Act
    status = response.status_code
    # Assert
    assert status == 200, getattr(response, "content", b"")


def test_save_own_file_lands_on_disk(save_own):
    # Arrange
    target = save_own.target
    # Act
    written = target.read_text() if target.exists() else None
    # Assert
    assert written == "my own content\n"


# EOF
