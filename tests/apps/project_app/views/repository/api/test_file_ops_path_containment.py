#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path-containment tests for the file_ops CRUD/transfer destructive sinks.

Target: ``apps/infra/project_app/views/repository/api/file_ops_utils.py``
``validate_path()`` -- the SOLE containment validator gating the 9 callers in
``file_ops_crud.py`` / ``file_ops_transfer.py``. Its downstream sinks are
DESTRUCTIVE: ``Path.unlink``, ``shutil.move``, ``shutil.rmtree`` and
``open(dest, "wb")``.

Security class: a *string prefix* is not *containment*. The pre-sweep guard
used ``str(full_path).startswith(str(project_resolved))``, so a sibling
directory that merely shares a string prefix (project root ``.../proj`` vs
``.../proj-secret``) slipped through -- an authorized-for-project-A caller
could ``rmtree`` / ``move`` / overwrite another tenant's tree. The current
guard delegates to component-wise ``validate_path_in_project``.

Two layers:

1. ``TestValidatePathRejectsEscapes`` drives the REAL ``validate_path``
   directly against REAL on-disk ``tmp_path`` dirs -- no DB, no mocks. Each
   escaping case asserts ``validate_path(...) is None``; on the OLD
   prefix-match code the sibling-prefix case returns a Path instead, so the
   test FAILS on the vulnerable code and PASSES on the patched code (a genuine
   red/green proof, not a tautology).

2. ``TestDestructiveSinkDoesNotRun`` drives the REAL routed views
   (``api_file_delete`` -> rmtree/unlink, ``api_file_move`` -> shutil.move)
   with a REAL ``Project`` + owner and a REAL sibling-tenant directory on
   disk, and asserts the victim file/dir is STILL PRESENT after the request
   (the sink never ran) and the response is a 400 rejection.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from apps.infra.project_app.views.repository.api.file_ops_utils import validate_path


# =============================================================================
# Layer 1 -- direct validator, real on-disk dirs, no DB
# =============================================================================
@pytest.fixture
def project_root(tmp_path):
    """A real project root with an in-project file and a sibling-PREFIX tenant.

    Layout under ``tmp_path``::

        proj/            <- the caller's authorized project root
          keep.txt
        proj-secret/     <- a DIFFERENT tenant; shares the string prefix
          secret.txt        ".../proj" but is NOT contained in it
    """
    root = tmp_path / "proj"
    root.mkdir()
    (root / "keep.txt").write_text("IN-PROJECT")

    sibling = tmp_path / "proj-secret"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("TENANT-B-SECRET")
    return root


class TestValidatePathRejectsEscapes:
    """The real ``validate_path`` returns None for every out-of-project path."""

    def test_sibling_prefix_escape_returns_none(self, project_root):
        # Arrange: ".../proj-secret" string-prefix-matches ".../proj".
        rel = "../proj-secret/secret.txt"
        # Act
        result = validate_path(project_root, rel)
        # Assert
        assert result is None

    def test_parent_traversal_to_etc_passwd_returns_none(self, project_root):
        # Arrange
        rel = "../../../../etc/passwd"
        # Act
        result = validate_path(project_root, rel)
        # Assert
        assert result is None

    def test_absolute_path_escape_returns_none(self, project_root):
        # Arrange: a leading "/" makes pathlib discard the project root.
        rel = "/etc/passwd"
        # Act
        result = validate_path(project_root, rel)
        # Assert
        assert result is None

    def test_legitimate_nested_path_is_accepted(self, project_root):
        # Arrange: a genuine in-project path must still resolve (proves the
        # guard is real containment, not a blanket deny).
        rel = "sub/dir/file.txt"
        # Act
        result = validate_path(project_root, rel)
        # Assert
        assert result == (project_root / "sub" / "dir" / "file.txt").resolve()


# =============================================================================
# Layer 2 -- real routed views, real Project + on-disk tenant dirs
# =============================================================================
def _json_post(view, user, username, slug, payload):
    """Invoke a file_ops view function with a real authenticated POST."""
    from django.test import RequestFactory

    request = RequestFactory().post(
        f"/{username}/{slug}/api/file/op/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    request.user = user
    return view(request, username, slug)


@pytest.fixture
def owner_project_with_sibling(db):
    """Create a real owner + local Project, a real on-disk project dir, and a
    real sibling-PREFIX tenant dir holding a victim file.

    Yields ``(user, project, project_dir, sibling_dir, victim_file)`` and
    removes the on-disk user tree on teardown.
    """
    from django.conf import settings
    from django.contrib.auth.models import User
    from apps.infra.project_app.models import Project

    suffix = uuid.uuid4().hex[:8]
    username = f"pc_owner_{suffix}"
    slug = f"proj-{suffix}"

    user = User.objects.create_user(username=username, password="x")
    project = Project.objects.create(slug=slug, owner=user, name="PC Project")

    base = Path(settings.BASE_DIR) / "data" / "users" / username / "proj"
    project_dir = base / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "keep.txt").write_text("IN-PROJECT")

    # Sibling tenant: same base dir, slug shares the string prefix.
    sibling_dir = base / f"{slug}-secret"
    sibling_dir.mkdir(parents=True, exist_ok=True)
    victim_file = sibling_dir / "secret.txt"
    victim_file.write_text("TENANT-B-SECRET")

    try:
        yield user, project, project_dir, sibling_dir, victim_file
    finally:
        user_root = Path(settings.BASE_DIR) / "data" / "users" / username
        shutil.rmtree(user_root, ignore_errors=True)


@pytest.mark.django_db
class TestDestructiveSinkDoesNotRun:
    """The real views refuse cross-tenant paths BEFORE the destructive sink."""

    def test_delete_does_not_rmtree_sibling_tenant_dir(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.repository.api.file_ops_crud import (
            api_file_delete,
        )

        user, project, _, sibling_dir, _ = owner_project_with_sibling
        payload = {"path": f"../{project.slug}-secret"}
        # Act
        _json_post(api_file_delete, user, user.username, project.slug, payload)
        # Assert: the sibling tenant directory must survive (rmtree never ran).
        assert sibling_dir.exists()

    def test_delete_of_sibling_returns_invalid_path(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.repository.api.file_ops_crud import (
            api_file_delete,
        )

        user, project, _, _, victim_file = owner_project_with_sibling
        payload = {"path": f"../{project.slug}-secret/secret.txt"}
        # Act
        response = _json_post(
            api_file_delete, user, user.username, project.slug, payload
        )
        # Assert
        assert response.status_code == 400

    def test_delete_does_not_unlink_sibling_victim_file(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.repository.api.file_ops_crud import (
            api_file_delete,
        )

        user, project, _, _, victim_file = owner_project_with_sibling
        payload = {"path": f"../{project.slug}-secret/secret.txt"}
        # Act
        _json_post(api_file_delete, user, user.username, project.slug, payload)
        # Assert: the victim file must survive (unlink never ran).
        assert victim_file.exists()

    def test_move_does_not_relocate_across_tenant_boundary(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.repository.api.file_ops_transfer import (
            api_file_move,
        )

        user, project, _, _, victim_file = owner_project_with_sibling
        payload = {
            "source_path": "keep.txt",
            "dest_path": f"../{project.slug}-secret/stolen.txt",
        }
        # Act
        _json_post(api_file_move, user, user.username, project.slug, payload)
        # Assert: nothing must be written into the sibling tenant dir.
        assert not (victim_file.parent / "stolen.txt").exists()

    def test_create_does_not_write_outside_project(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.repository.api.file_ops_crud import (
            api_file_create,
        )

        user, project, _, sibling_dir, _ = owner_project_with_sibling
        payload = {"path": f"../{project.slug}-secret/planted.txt", "type": "file"}
        # Act
        _json_post(api_file_create, user, user.username, project.slug, payload)
        # Assert: no attacker-controlled file may appear in the sibling tenant.
        assert not (sibling_dir / "planted.txt").exists()


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
