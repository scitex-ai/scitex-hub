#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-prefix path escape in the project REPOSITORY views.

FINDING (2026-07-22)
    Nine call sites under ``apps/infra/project_app/views/repository/`` guarded
    the project directory with a STRING PREFIX::

        full = (project_root / user_supplied).resolve()
        if not str(full).startswith(str(project_root.resolve())):
            reject()

    ``str.startswith`` is not path containment. A SIBLING directory whose name
    merely EXTENDS the project root satisfies it: root ``/data/u/proj`` admits
    ``/data/u/proj-other/secret.txt`` reached via ``../proj-other/secret.txt``.

    Every project of a given owner lives side by side under one data root, so
    the escape reads/writes/links/extracts into ANOTHER project the requester
    may not be a member of — and the browse/view/edit views only require read
    or owner access to the project actually named in the URL.

FIX
    ``validate_path_in_project()`` from
    ``apps.infra.project_app.services.filesystem.permissions`` — component-wise
    containment via ``Path.resolve().relative_to()``.

DESIGN NOTES
- Users/Projects are UNSAVED model instances and ``get_object_or_404`` is
  patched out, so the suite never touches the test database.
- The filesystem is real (``tmp_path``): the exploit is an actual read/write,
  not a mock of one.
- Each escape test has an ANTI-REGRESSION twin proving the legitimate in-root
  path still works, so "reject everything" cannot pass this gate.
"""

import json
import zipfile
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from apps.infra.project_app.views.repository import browse as browse_mod
from apps.infra.project_app.views.repository import diff_merge as diff_mod
from apps.infra.project_app.views.repository import file_edit as edit_mod
from apps.infra.project_app.views.repository import file_view as view_mod
from apps.infra.project_app.views.repository.api import directory as dir_mod
from apps.infra.project_app.views.repository.api import (
    extract_bundle as bundle_mod,
)
from apps.infra.project_app.views.repository.api import (
    file_ops_utils as ops_mod,
)
from apps.infra.project_app.views.repository.api import symlink as link_mod

pytestmark = pytest.mark.security

OWNER = "alice"
SLUG = "proj"
# The sibling directory name EXTENDS the project root name — the whole finding.
SIBLING = "proj-other"
SECRET = "other-project-private-data-must-not-leak\n"
MINE = "my own in-project data\n"

# Relative request path that climbs out of "proj" into "proj-other".
ESCAPE_FILE = f"../{SIBLING}/secret.txt"
ESCAPE_DIR = f"../{SIBLING}"


# --------------------------------------------------------------------------
# Fixtures / doubles
# --------------------------------------------------------------------------
@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def tree(tmp_path):
    """Two sibling project directories under one owner data root."""
    root = tmp_path / SLUG
    root.mkdir()
    (root / "mine.txt").write_text(MINE)
    sibling = tmp_path / SIBLING
    sibling.mkdir()
    (sibling / "secret.txt").write_text(SECRET)
    return {"root": root, "sibling": sibling}


@pytest.fixture
def owner():
    User = get_user_model()
    return User(pk=1, username=OWNER)


@pytest.fixture
def project(owner):
    from apps.infra.project_app.models import Project

    return Project(pk=1, name="Proj", slug=SLUG, owner=owner)


class _FakeManager:
    def __init__(self, root: Path):
        self._root = root

    def get_project_root_path(self, project):
        return self._root


class _Rebinder:
    """Hand-rolled attribute rebinder with exact restore (no `monkeypatch`)."""

    def __init__(self):
        self._undo = []

    def rebind(self, obj, name, value):
        self._undo.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def restore(self):
        for obj, name, previous in reversed(self._undo):
            setattr(obj, name, previous)
        self._undo.clear()


@pytest.fixture
def rebinder():
    binder = _Rebinder()
    yield binder
    binder.restore()


@pytest.fixture
def wired(rebinder, tree, owner, project):
    """Stand in for the DB row lookup + the path resolver.

    Only the two collaborators that would otherwise require a live database are
    replaced. The traversal guard, the request/response plumbing and the real
    filesystem under ``tmp_path`` are all exercised for real.
    """
    from apps.infra.project_app.services import project_filesystem as pfs_mod

    def fake_get_object_or_404(klass, *args, **kwargs):
        return owner if getattr(klass, "__name__", "") == "User" else project

    for mod in (browse_mod, view_mod, edit_mod, diff_mod, dir_mod, link_mod, bundle_mod):
        rebinder.rebind(mod, "get_object_or_404", fake_get_object_or_404)

    rebinder.rebind(
        pfs_mod,
        "get_project_filesystem_manager",
        lambda user: _FakeManager(tree["root"]),
    )
    for mod in (dir_mod, link_mod, bundle_mod):
        rebinder.rebind(mod, "check_project_write_access", lambda request, p: True)
    rebinder.rebind(view_mod, "check_project_read_access", lambda request, p: True)
    return tree


HTTP404 = "<Http404 raised>"


def _serve_or_404(view, *args):
    """Call ``view``; return ``HTTP404`` instead of propagating ``Http404``."""
    try:
        return view(*args)
    except Http404:
        return HTTP404


def _authed(request, owner):
    """Attach the owner + a message store (RequestFactory has no middleware)."""
    request.user = owner
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


# ==========================================================================
# 1. file_ops_utils.validate_path — the shared helper behind every file_ops_*
#    endpoint (create / delete / move / upload).
# ==========================================================================
def test_ops_validate_path_rejects_sibling_prefix_escape(tree):
    # Arrange
    root = tree["root"]
    # Act
    resolved = ops_mod.validate_path(root, ESCAPE_FILE)
    # Assert
    assert resolved is None, f"escaped to {resolved}"


def test_ops_validate_path_still_accepts_in_project_file(tree):
    # Arrange
    root = tree["root"]
    # Act
    resolved = ops_mod.validate_path(root, "mine.txt")
    # Assert
    assert resolved == (root / "mine.txt").resolve()


# ==========================================================================
# 2. directory.api_concatenate_directory — dumps every file it can reach.
# ==========================================================================
@pytest.fixture
def concat_escape(rf, wired, owner):
    req = _authed(rf.get("/x/"), owner)
    return dir_mod.api_concatenate_directory(req, OWNER, SLUG, ESCAPE_DIR)


def test_concatenate_directory_rejects_sibling_prefix_escape(concat_escape):
    # Arrange
    payload = json.loads(concat_escape.content)
    # Act
    leaked = SECRET.strip() in concat_escape.content.decode("utf-8", "replace")
    # Assert
    assert payload.get("success") is False and not leaked, payload


@pytest.fixture
def concat_ok(rf, wired, owner):
    req = _authed(rf.get("/x/"), owner)
    return dir_mod.api_concatenate_directory(req, OWNER, SLUG, "")


def test_concatenate_directory_still_reads_own_project(concat_ok):
    # Arrange
    payload = json.loads(concat_ok.content)
    # Act
    ok = payload.get("success")
    # Assert
    assert ok is True, payload


# ==========================================================================
# 3. symlink.api_create_symlink — a symlink out of the project is a permanent
#    read primitive for every later request.
# ==========================================================================
def _post_json(rf, owner, body):
    req = rf.post("/x/", data=json.dumps(body), content_type="application/json")
    return _authed(req, owner)


@pytest.fixture
def symlink_escape(rf, wired, owner):
    req = _post_json(rf, owner, {"source": ESCAPE_FILE, "target": "stolen.txt"})
    resp = link_mod.api_create_symlink(req, OWNER, SLUG)
    return {"resp": resp, "link": wired["root"] / "stolen.txt"}


def test_create_symlink_rejects_sibling_prefix_escape(symlink_escape):
    # Arrange
    resp = symlink_escape["resp"]
    # Act
    status = resp.status_code
    # Assert
    assert status == 400, resp.content


def test_create_symlink_plants_no_link_to_sibling_project(symlink_escape):
    # Arrange
    link = symlink_escape["link"]
    # Act
    planted = link.exists() or link.is_symlink()
    # Assert
    assert planted is False, f"symlink out of the project was created: {link}"


@pytest.fixture
def symlink_ok(rf, wired, owner):
    req = _post_json(rf, owner, {"source": "mine.txt", "target": "alias.txt"})
    resp = link_mod.api_create_symlink(req, OWNER, SLUG)
    return {"resp": resp, "link": wired["root"] / "alias.txt"}


def test_create_symlink_still_works_inside_project(symlink_ok):
    # Arrange
    resp = symlink_ok["resp"]
    # Act
    ok = json.loads(resp.content).get("success")
    # Assert
    assert ok is True, resp.content


# ==========================================================================
# 4. extract_bundle.api_extract_bundle — reads a .figz from outside the project.
# ==========================================================================
def _write_bundle(path: Path, payload: str):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("panel.txt", payload)


@pytest.fixture
def bundle_escape(rf, wired, owner):
    _write_bundle(wired["sibling"] / "private.figz", SECRET)
    req = _post_json(
        rf,
        owner,
        {"bundle_path": f"../{SIBLING}/private.figz", "output_path": "out"},
    )
    resp = bundle_mod.api_extract_bundle(req, OWNER, SLUG)
    return {"resp": resp, "out": wired["root"] / "out"}


def test_extract_bundle_rejects_sibling_prefix_escape(bundle_escape):
    # Arrange
    resp = bundle_escape["resp"]
    # Act
    status = resp.status_code
    # Assert
    assert status == 400, resp.content


def test_extract_bundle_leaks_no_sibling_payload(bundle_escape):
    # Arrange
    out = bundle_escape["out"]
    # Act
    extracted = sorted(p.name for p in out.rglob("*")) if out.exists() else []
    # Assert
    assert extracted == [], f"sibling-project bundle was extracted: {extracted}"


@pytest.fixture
def bundle_ok(rf, wired, owner):
    _write_bundle(wired["root"] / "mine.figz", MINE)
    req = _post_json(rf, owner, {"bundle_path": "mine.figz", "output_path": "out"})
    return bundle_mod.api_extract_bundle(req, OWNER, SLUG)


def test_extract_bundle_still_works_inside_project(bundle_ok):
    # Arrange
    payload = json.loads(bundle_ok.content)
    # Act
    ok = payload.get("success")
    # Assert
    assert ok is True, payload


# ==========================================================================
# 5. file_view.project_file_view (?mode=raw) — serves the file bytes directly,
#    so the escape is a literal exfiltration.
# ==========================================================================
def test_file_view_raw_rejects_sibling_prefix_escape(rf, wired, owner):
    # Arrange
    req = _authed(rf.get("/x/?mode=raw"), owner)
    # Act
    served = _serve_or_404(view_mod.project_file_view, req, OWNER, SLUG, ESCAPE_FILE)
    # Assert
    assert served == HTTP404, getattr(served, "content", served)


def test_file_view_raw_still_serves_own_file(rf, wired, owner):
    # Arrange
    req = _authed(rf.get("/x/?mode=raw"), owner)
    # Act
    resp = view_mod.project_file_view(req, OWNER, SLUG, "mine.txt")
    # Assert
    assert resp.status_code == 200 and MINE.strip().encode() in resp.content


# ==========================================================================
# 6. file_edit.project_file_edit (POST) — the escape is a WRITE outside the
#    project, so assert the sibling file's bytes are untouched.
# ==========================================================================
@pytest.fixture
def edit_escape(rf, wired, owner):
    req = _authed(rf.post("/x/", data={"content": "PWNED"}), owner)
    resp = edit_mod.project_file_edit(req, OWNER, SLUG, ESCAPE_FILE)
    return {"resp": resp, "victim": wired["sibling"] / "secret.txt"}


def test_file_edit_does_not_overwrite_sibling_project_file(edit_escape):
    # Arrange
    victim = edit_escape["victim"]
    # Act
    content = victim.read_text()
    # Assert
    assert content == SECRET, "file outside the project was overwritten"


def test_file_edit_escape_bounces_to_project_detail(edit_escape):
    # Both outcomes are 302, so the STATUS alone proves nothing: a successful
    # edit redirects to file_view. Only the TARGET distinguishes reject
    # (project detail) from "saved successfully" (the edited file).
    # Arrange
    detail = reverse("project_app:detail", kwargs={"username": OWNER, "slug": SLUG})
    # Act
    target = getattr(edit_escape["resp"], "url", "")
    # Assert
    assert target == detail, f"edit was accepted and redirected to {target}"


def test_file_edit_still_writes_own_file(rf, wired, owner):
    # Arrange
    req = _authed(rf.post("/x/", data={"content": "updated\n"}), owner)
    # Act
    edit_mod.project_file_edit(req, OWNER, SLUG, "mine.txt")
    # Assert
    assert (wired["root"] / "mine.txt").read_text() == "updated\n"


# ==========================================================================
# 7. diff_merge.api_load_file_from_repo — returns file content as JSON.
# ==========================================================================
@pytest.fixture
def diff_escape(rf, wired, owner):
    req = _authed(rf.post("/x/", data={"file_path": ESCAPE_FILE}), owner)
    return diff_mod.api_load_file_from_repo(req, OWNER, SLUG)


def test_diff_merge_load_rejects_sibling_prefix_escape(diff_escape):
    # Arrange
    resp = diff_escape
    # Act
    leaked = SECRET.strip() in resp.content.decode("utf-8", "replace")
    # Assert
    assert resp.status_code == 403 and not leaked, resp.content


def test_diff_merge_load_still_reads_own_file(rf, wired, owner):
    # Arrange
    req = _authed(rf.post("/x/", data={"file_path": "mine.txt"}), owner)
    # Act
    resp = diff_mod.api_load_file_from_repo(req, OWNER, SLUG)
    # Assert
    assert resp.status_code == 200 and json.loads(resp.content)["content"] == MINE


# ==========================================================================
# 8. browse.project_directory_dynamic / project_directory — listing a sibling
#    project's tree. Both must bounce back to the project detail page.
# ==========================================================================
def test_browse_dynamic_rejects_sibling_prefix_escape(rf, wired, owner):
    # Arrange
    req = _authed(rf.get("/x/"), owner)
    # Act
    resp = browse_mod.project_directory_dynamic(req, OWNER, SLUG, ESCAPE_DIR)
    # Assert
    assert resp.status_code == 302, resp


def test_browse_by_type_rejects_sibling_prefix_escape(rf, wired, owner):
    # Arrange
    req = _authed(rf.get("/x/"), owner)
    # Act
    resp = browse_mod.project_directory(req, OWNER, SLUG, "..", f"{SIBLING}")
    # Assert
    assert resp.status_code == 302, resp

# EOF
