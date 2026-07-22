#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-prefix path escape in the docs and writer file-serving views.

FINDING (2026-07-22) — same class as PR #437 / #441
    Three sites guarded a directory boundary with a STRING PREFIX instead of
    path containment::

        apps/workspace/docs_app/_sphinx.py::sphinx_raw
            if not str(doc_file).startswith(str(doc_base_resolved)):
        apps/workspace/docs_app/_sphinx.py::serve_sphinx_docs
            if not str(doc_file).startswith(str(doc_base)):
        apps/workspace/writer_app/views/editor/api/content.py::read_tex_file_view
            if not str(full_path).startswith(str(workspace_resolved)):

    ``str.startswith`` is not path containment. A SIBLING directory whose name
    merely EXTENDS the root satisfies it, so a ``../`` segment that lands in
    that sibling passes the guard:

        root  ".../_build/html"  admits ".../_build/html-other/secret.html"
        root  ".../projects/proj" admits ".../projects/proj-other/secret.tex"

    The Sphinx views take ``page`` straight from the URL and the writer view
    takes ``path`` straight from the query string, so the escape is reachable
    by request.

FIX
    ``validate_path_in_project()`` — component-wise containment via
    ``Path.resolve().relative_to()``.

DESIGN NOTES
- The exploit runs against a real tmp filesystem layout, and each escape test
  asserts the VICTIM BYTES never reach the response — not merely that a status
  code changed.
- The writer view is exercised through its real ``@api_login_optional``
  decorator with UNSAVED model instances and a fake manager, so the suite
  never touches the test database.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, override_settings

from apps.workspace.docs_app import _sphinx as sphinx_mod
from apps.workspace.writer_app.views.editor.api import content as content_mod

pytestmark = pytest.mark.security

SECRET = "sibling-directory-secret-must-not-leak"


@pytest.fixture
def rf():
    return RequestFactory()


# ---------------------------------------------------------------- docs_app
# resolve_sphinx_path("scitex-hub") -> BASE_DIR/docs/sphinx/_build/html


@pytest.fixture
def sphinx_tree(tmp_path):
    """Doc root ".../_build/html" plus a sibling ".../_build/html-other"."""
    build = tmp_path / "docs" / "sphinx" / "_build"
    html = build / "html"
    html.mkdir(parents=True)
    (html / "index.html").write_text("<h1>public docs</h1>", encoding="utf-8")
    (html / "style.css").write_text("body{color:red}", encoding="utf-8")

    sibling = build / "html-other"
    sibling.mkdir()
    (sibling / "secret.html").write_text(SECRET, encoding="utf-8")
    (sibling / "secret.css").write_text(SECRET, encoding="utf-8")
    return tmp_path


def _call_sphinx(view, rf, base_dir, page):
    """Return the response body, or None when the view refuses with 404."""
    req = rf.get(f"/apps/docs/sphinx/scitex-hub/{page}")
    with override_settings(BASE_DIR=str(base_dir)):
        try:
            resp = view(req, "scitex-hub", page)
        except Http404:
            return None
    return resp.content.decode("utf-8", "replace")


@pytest.fixture
def raw_escape_body(rf, sphinx_tree):
    return _call_sphinx(
        sphinx_mod.sphinx_raw, rf, sphinx_tree, "../html-other/secret.html"
    )


def test_sphinx_raw_rejects_sibling_prefix_escape(raw_escape_body):
    # Arrange
    body = raw_escape_body
    # Act
    served = body is not None
    # Assert
    assert served is False, f"sibling file served: {body!r}"


def test_sphinx_raw_never_leaks_sibling_bytes(raw_escape_body):
    # Arrange
    body = raw_escape_body or ""
    # Act
    leaked = SECRET in body
    # Assert
    assert leaked is False


@pytest.fixture
def serve_escape_body(rf, sphinx_tree):
    return _call_sphinx(
        sphinx_mod.serve_sphinx_docs, rf, sphinx_tree, "../html-other/secret.css"
    )


def test_serve_sphinx_docs_rejects_sibling_prefix_escape(serve_escape_body):
    # Arrange
    body = serve_escape_body
    # Act
    served = body is not None
    # Assert
    assert served is False, f"sibling file served: {body!r}"


def test_serve_sphinx_docs_never_leaks_sibling_bytes(serve_escape_body):
    # Arrange
    body = serve_escape_body or ""
    # Act
    leaked = SECRET in body
    # Assert
    assert leaked is False


def test_sphinx_raw_still_serves_a_real_page(rf, sphinx_tree):
    """Anti-regression: an in-root page must still be served."""
    # Arrange
    body = _call_sphinx(sphinx_mod.sphinx_raw, rf, sphinx_tree, "index.html")
    # Act
    ok = body is not None and "public docs" in body
    # Assert
    assert ok is True, f"legitimate page rejected: {body!r}"


def test_serve_sphinx_docs_still_serves_a_real_asset(rf, sphinx_tree):
    """Anti-regression: an in-root asset must still be served."""
    # Arrange
    body = _call_sphinx(sphinx_mod.serve_sphinx_docs, rf, sphinx_tree, "style.css")
    # Act
    ok = body is not None and "color:red" in body
    # Assert
    assert ok is True, f"legitimate asset rejected: {body!r}"


# -------------------------------------------------------------- writer_app


class _SingleProjectManager:
    """Hand-rolled stand-in for ``Project.objects``.

    The view's only database need is "fetch project N"; substituting a real
    unsaved ``Project`` for that one lookup keeps the REAL model class, the
    REAL decorator and the REAL view in the path while avoiding the test
    database. Nothing else about production is rewritten.
    """

    def __init__(self, project):
        self._project = project

    def get(self, *args, **kwargs):
        return self._project


@pytest.fixture
def read_tex():
    """Yield a caller for the real view; restore ``Project.objects`` on teardown."""
    from apps.infra.project_app.models import Project

    original_descriptor = Project.__dict__["objects"]

    def call(rf_, workspace, path):
        User = get_user_model()
        user = User(pk=1, username="alice")

        project = Project(id=1)
        project.owner = user
        project.get_local_path = lambda: workspace
        setattr(Project, "objects", _SingleProjectManager(project))

        req = rf_.get("/apps/writer/api/1/read-tex-file/", {"path": path})
        req.user = user
        # Call the REAL decorated view so @api_login_optional is exercised.
        resp = content_mod.read_tex_file_view(req, 1)
        return resp.status_code, json.loads(resp.content)

    yield call

    setattr(Project, "objects", original_descriptor)


@pytest.fixture
def writer_tree(tmp_path):
    """Workspace ".../proj" plus a sibling ".../proj-other"."""
    projects = tmp_path / "data" / "projects"
    workspace = projects / "proj"
    workspace.mkdir(parents=True)
    (workspace / "mine.tex").write_text("\\section{mine}", encoding="utf-8")

    sibling = projects / "proj-other"
    sibling.mkdir()
    (sibling / "secret.tex").write_text(SECRET, encoding="utf-8")
    return workspace


@pytest.fixture
def writer_escape(rf, read_tex, writer_tree):
    return read_tex(rf, writer_tree, "../proj-other/secret.tex")


def test_read_tex_rejects_sibling_prefix_escape(writer_escape):
    # Arrange
    status, payload = writer_escape
    # Act
    allowed = status == 200
    # Assert
    assert allowed is False, payload


def test_read_tex_never_leaks_sibling_bytes(writer_escape):
    # Arrange
    _, payload = writer_escape
    # Act
    leaked = SECRET in json.dumps(payload)
    # Assert
    assert leaked is False


def test_read_tex_still_reads_an_in_workspace_file(rf, read_tex, writer_tree):
    """Anti-regression: the project's own file must still be readable."""
    # Arrange
    status, payload = read_tex(rf, writer_tree, "mine.tex")
    # Act
    ok = status == 200 and payload.get("content") == "\\section{mine}"
    # Assert
    assert ok is True, payload

# EOF
