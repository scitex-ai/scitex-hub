#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path-containment tests for the console workspace file API.

Targets:
- ``apps/workspace/console_app/workspace_api/file_write.py`` -> ``api_save_file``
  (sink: ``open(file_full_path, "w")``)
- ``apps/workspace/console_app/workspace_api/file_create_delete.py`` ->
  ``api_create_file`` (sink: ``open(..., "w")``) and ``api_delete_file``
  (DESTRUCTIVE sinks: ``shutil.rmtree`` / ``Path.unlink``)
- ``apps/workspace/console_app/workspace_api/execution.py`` ->
  ``api_execute_script`` (sink: ``subprocess.run(["python", file_full_path])``
  -- a path escape here is arbitrary-code execution). This view was MISSED by
  the original containment sweep: its three siblings above were converted to
  ``validate_path_in_project`` while ``api_execute_script`` kept the prefix
  guard AND resolved from the (often-empty) ``git_clone_path``.

Each view builds ``file_full_path = project_path / file_path`` from an
untrusted ``path`` and gates the sink on
``validate_path_in_project(project_path, file_full_path)``. The pre-sweep guard
was ``str(file_full_path.resolve()).startswith(str(project_path.resolve()))`` --
a *string prefix* that admits a sibling tenant ``.../proj-secret`` when the root
is ``.../proj``, so an editor authorized for project A could DELETE or overwrite
another tenant's files. The current guard is component-wise
``validate_path_in_project``.

Two layers:

1. ``TestWorkspaceGuardRejectsEscapes`` drives the REAL
   ``validate_path_in_project`` exactly the way the views build its arguments
   (``project_path / path``), against REAL ``tmp_path`` dirs -- no DB, no
   mocks. Sibling-prefix / traversal / absolute paths must return ``False``; a
   legitimate in-project path must return ``True``. On the old prefix-match
   code the sibling-prefix case returns ``True``, so those tests FAIL on the
   vulnerable code and PASS on the patched code.

2. ``TestDeleteSinkDoesNotRun`` drives the REAL ``api_delete_file`` /
   ``api_create_file`` / ``api_save_file`` views with a REAL ``Project`` +
   owner and a REAL sibling-tenant directory on disk, and asserts the victim
   file is STILL PRESENT (the destructive sink never ran) and the response is a
   400 rejection.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from apps.infra.project_app.services.filesystem.permissions import (
    validate_path_in_project,
)


# =============================================================================
# Layer 1 -- real guard, real on-disk dirs, no DB
# =============================================================================
@pytest.fixture
def project_root(tmp_path):
    """A real project root plus a sibling-PREFIX tenant holding a victim file."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "keep.txt").write_text("IN-PROJECT")

    sibling = tmp_path / "proj-secret"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("TENANT-B-SECRET")
    return root


class TestWorkspaceGuardRejectsEscapes:
    """``validate_path_in_project`` rejects every cross-boundary target the
    workspace views could build from an untrusted ``path``."""

    def test_sibling_prefix_target_is_rejected(self, project_root):
        # Arrange: reproduce the view's ``project_path / file_path``.
        target = project_root / "../proj-secret/secret.txt"
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is False

    def test_parent_traversal_target_is_rejected(self, project_root):
        # Arrange
        target = project_root / "../../../../etc/passwd"
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is False

    def test_absolute_target_is_rejected(self, project_root):
        # Arrange
        target = project_root / "/etc/passwd"
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is False

    def test_legitimate_in_project_target_is_allowed(self, project_root):
        # Arrange: a real nested path must pass (not a blanket deny).
        target = project_root / "sub/dir/file.txt"
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is True


# =============================================================================
# Layer 2 -- real workspace views, real Project + on-disk tenant dirs
# =============================================================================
def _json_post(view, user, payload):
    """Invoke a workspace API view with a real authenticated JSON POST."""
    from django.test import RequestFactory

    request = RequestFactory().post(
        "/code/api/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    request.user = user
    return view(request)


@pytest.fixture
def owner_project_with_sibling(db):
    """Real owner + local Project, real on-disk project dir, real sibling-PREFIX
    tenant dir with a victim file. Yields
    ``(user, project, project_dir, sibling_dir, victim_file)``; removes the
    on-disk user tree on teardown.
    """
    from django.conf import settings
    from django.contrib.auth.models import User
    from apps.infra.project_app.models import Project

    suffix = uuid.uuid4().hex[:8]
    username = f"ws_owner_{suffix}"
    slug = f"proj-{suffix}"

    user = User.objects.create_user(username=username, password="x")
    project = Project.objects.create(slug=slug, owner=user, name="WS Project")

    base = Path(settings.BASE_DIR) / "data" / "users" / username / "proj"
    project_dir = base / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "keep.txt").write_text("IN-PROJECT")

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
class TestDeleteSinkDoesNotRun:
    """The real workspace views refuse cross-tenant paths before the sink."""

    def test_delete_does_not_unlink_sibling_victim_file(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.workspace.console_app.workspace_api.file_create_delete import (
            api_delete_file,
        )

        user, project, _, _, victim_file = owner_project_with_sibling
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret/secret.txt",
        }
        # Act
        _json_post(api_delete_file, user, payload)
        # Assert: the victim file must survive (unlink never ran).
        assert victim_file.exists()

    def test_delete_of_sibling_returns_invalid_path(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.workspace.console_app.workspace_api.file_create_delete import (
            api_delete_file,
        )

        user, project, _, _, _ = owner_project_with_sibling
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret/secret.txt",
        }
        # Act
        response = _json_post(api_delete_file, user, payload)
        # Assert
        assert response.status_code == 400

    def test_delete_does_not_rmtree_sibling_tenant_dir(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.workspace.console_app.workspace_api.file_create_delete import (
            api_delete_file,
        )

        user, project, _, sibling_dir, _ = owner_project_with_sibling
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret",
        }
        # Act
        _json_post(api_delete_file, user, payload)
        # Assert: the sibling tenant directory must survive (rmtree never ran).
        assert sibling_dir.exists()

    def test_create_does_not_write_outside_project(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.workspace.console_app.workspace_api.file_create_delete import (
            api_create_file,
        )

        user, project, _, sibling_dir, _ = owner_project_with_sibling
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret/planted.txt",
            "content": "x",
        }
        # Act
        _json_post(api_create_file, user, payload)
        # Assert
        assert not (sibling_dir / "planted.txt").exists()

    def test_save_does_not_overwrite_sibling_victim_file(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.workspace.console_app.workspace_api.file_write import (
            api_save_file,
        )

        user, project, _, _, victim_file = owner_project_with_sibling
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret/secret.txt",
            "content": "OVERWRITTEN-BY-ATTACKER",
        }
        # Act
        _json_post(api_save_file, user, payload)
        # Assert: the victim's content must be untouched (open("w") never ran).
        assert victim_file.read_text() == "TENANT-B-SECRET"

    def test_execute_does_not_run_sibling_py_file(
        self, owner_project_with_sibling
    ):
        # Arrange: a runnable .py in the sibling tenant dir that, IF executed,
        # would write a marker -- so a passing guard is proven by its ABSENCE.
        from apps.workspace.console_app.workspace_api.execution import (
            api_execute_script,
        )

        user, project, _, sibling_dir, _ = owner_project_with_sibling
        marker = sibling_dir / "pwned.txt"
        (sibling_dir / "evil.py").write_text(
            f"open({str(marker)!r}, 'w').write('RAN')\n"
        )
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret/evil.py",
        }
        # Act
        _json_post(api_execute_script, user, payload)
        # Assert: the sibling script must NOT have run (no marker written).
        assert not marker.exists()

    def test_execute_of_sibling_returns_invalid_path(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.workspace.console_app.workspace_api.execution import (
            api_execute_script,
        )

        user, project, _, sibling_dir, _ = owner_project_with_sibling
        (sibling_dir / "evil.py").write_text("print('x')\n")
        payload = {
            "project_id": project.id,
            "path": f"../{project.slug}-secret/evil.py",
        }
        # Act
        response = _json_post(api_execute_script, user, payload)
        # Assert
        assert response.status_code == 400


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
