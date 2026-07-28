#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path-containment tests for the live routed directory browse / file view.

Targets:
- ``apps/infra/project_app/views/directory_views/browse.py`` ->
  ``project_directory_dynamic`` (lists ``full_directory_path.iterdir()``)
- ``apps/infra/project_app/views/directory_views/file_view_utils.py`` ->
  ``get_file_context`` (gates ``open(full_file_path)`` in the file view)

Both build a path from an untrusted URL segment
(``project_path / directory_path`` / ``project_path / file_path``), resolve it,
and gate the read on ``validate_path_in_project``. A *string prefix* guard would
admit a sibling tenant ``.../proj-secret`` when the root is ``.../proj``,
leaking another tenant's directory listing / file contents to a viewer
authorized only for the caller's own (even public) project. The current guard
is component-wise ``validate_path_in_project``.

Two layers:

1. ``TestBrowseGuardRejectsEscapes`` drives the REAL
   ``validate_path_in_project`` exactly as the views build its argument
   (``(project_path / segment).resolve()``), against REAL ``tmp_path`` dirs --
   no DB, no mocks. Sibling-prefix / traversal / absolute paths must return
   ``False``; a legitimate in-project path must return ``True``. On the old
   prefix-match code the sibling-prefix case returns ``True``, so those tests
   FAIL on the vulnerable code and PASS on the patched code.

2. ``TestRoutedReadDoesNotEscape`` drives the REAL routed views
   (``get_file_context`` and ``project_directory_dynamic``) with a REAL
   ``Project`` + owner and a REAL sibling-tenant directory on disk, and asserts
   the out-of-project read is refused (``get_file_context`` returns ``None``;
   the browse view returns a redirect instead of a 200 listing).
"""

from __future__ import annotations

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


class TestBrowseGuardRejectsEscapes:
    """``validate_path_in_project`` rejects every out-of-project read target the
    browse / file view could build from an untrusted URL segment."""

    def test_sibling_prefix_directory_is_rejected(self, project_root):
        # Arrange: reproduce the view's ``(project_path / segment).resolve()``.
        target = (project_root / "../proj-secret").resolve()
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is False

    def test_sibling_prefix_file_is_rejected(self, project_root):
        # Arrange
        target = (project_root / "../proj-secret/secret.txt").resolve()
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is False

    def test_parent_traversal_is_rejected(self, project_root):
        # Arrange
        target = (project_root / "../../../../etc").resolve()
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is False

    def test_legitimate_in_project_path_is_allowed(self, project_root):
        # Arrange: a real in-project file must pass (not a blanket deny).
        target = (project_root / "keep.txt").resolve()
        # Act
        allowed = validate_path_in_project(project_root, target)
        # Assert
        assert allowed is True


# =============================================================================
# Layer 2 -- real routed views, real Project + on-disk tenant dirs
# =============================================================================
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
    username = f"dv_owner_{suffix}"
    slug = f"proj-{suffix}"

    user = User.objects.create_user(username=username, password="x")
    project = Project.objects.create(slug=slug, owner=user, name="DV Project")

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


def _authed_get(user, path="/browse/"):
    """A real authenticated GET request with session + messages attached."""
    from django.test import RequestFactory
    from django.contrib.messages.storage.fallback import FallbackStorage

    request = RequestFactory().get(path)
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


@pytest.mark.django_db
class TestRoutedReadDoesNotEscape:
    """The real routed views refuse out-of-project reads."""

    def test_get_file_context_rejects_sibling_prefix_file(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.directory_views.file_view_utils import (
            get_file_context,
        )

        user, project, _, _, _ = owner_project_with_sibling
        request = _authed_get(user)
        file_path = f"../{project.slug}-secret/secret.txt"
        # Act
        result = get_file_context(request, user.username, project.slug, file_path)
        # Assert: out-of-project file read is refused.
        assert result is None

    def test_get_file_context_allows_in_project_file(
        self, owner_project_with_sibling
    ):
        # Arrange: a genuine in-project file must resolve (not a blanket deny).
        from apps.infra.project_app.views.directory_views.file_view_utils import (
            get_file_context,
        )

        user, project, _, _, _ = owner_project_with_sibling
        request = _authed_get(user)
        # Act
        result = get_file_context(request, user.username, project.slug, "keep.txt")
        # Assert
        assert result is not None

    def test_browse_rejects_sibling_prefix_directory_with_redirect(
        self, owner_project_with_sibling
    ):
        # Arrange
        from apps.infra.project_app.views.directory_views.browse import (
            project_directory_dynamic,
        )

        user, project, _, _, _ = owner_project_with_sibling
        request = _authed_get(user)
        directory_path = f"../{project.slug}-secret"
        # Act
        response = project_directory_dynamic(
            request, user.username, project.slug, directory_path
        )
        # Assert: rejection is a redirect, never a 200 listing of the sibling.
        assert response.status_code == 302


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
