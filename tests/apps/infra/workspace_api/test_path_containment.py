#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-tenant path-containment tests for the LIVE workspace_api file
endpoints — the two highest-value sites in the sweep.

Security class: the old guard was ``str(full.resolve()).startswith(
str(project_path.resolve()))``. A string prefix is NOT containment: a
sibling project directory whose name merely EXTENDS the victim's slug
(``.../proj/demo`` vs ``.../proj/demo-secret``) string-prefix-matches the
victim root, so an authorized-for-project-A caller escapes into sibling
project B on disk.

  * api_get_file_content (GET, NO @login_required) — anonymous cross-tenant
    arbitrary-file READ, sink is FileResponse / file read.
  * api_save_file      (POST, @login_required) — cross-tenant WRITE, sink is
    mkdir + open(..., "w").

The sibling-PREFIX vector (not plain ``..``) is the one that distinguishes
containment from a prefix match: a differently-named sibling would be caught
by both guards, but ``demo`` vs ``demo-secret`` passes the OLD guard and is
rejected only by the NEW one. So these tests FAIL on the pre-patch code
(200 + leaked bytes / file written) and PASS after the fix (400, nothing
leaked / written) — a genuine red/green proof.

Views are invoked directly via RequestFactory (the real, routed view
functions) to deliver the raw ``..`` path bytes; the Django test client
would normalise the URL and mask the attack an HTTP client can still send.
No mocks (project rule). One assertion per test (STX-TQ007).
"""

import json
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project
from apps.infra.workspace_api.views.file_content import api_get_file_content
from apps.infra.workspace_api.views.file_save import api_save_file

SENTINEL = "TENANT-B-SECRET-a1b2c3d4"
ESCAPE_PATH = "../demo-secret/SECRET.txt"
WRITE_ESCAPE_PATH = "../demo-secret/PWNED.txt"


def _proj_base(username: str) -> Path:
    return Path(settings.BASE_DIR) / "data" / "users" / username / "proj"


class WorkspaceApiContainmentTest(TestCase):
    """Two real tenants; the victim project's slug is a string PREFIX of a
    sibling directory, exercising the exact hole the prefix guard left open.
    """

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="wsc-alice")
        # Victim project slug "demo"; a sibling on-disk dir "demo-secret"
        # extends that slug so the old startswith guard admits it.
        cls.project = Project.objects.create(
            owner=cls.alice, name="Demo", slug="demo", visibility="public"
        )

    def setUp(self):
        self.rf = RequestFactory()
        base = _proj_base("wsc-alice")
        self.victim_root = base / "demo"
        self.sibling = base / "demo-secret"
        self.victim_root.mkdir(parents=True, exist_ok=True)
        self.sibling.mkdir(parents=True, exist_ok=True)
        (self.victim_root / "README.md").write_text("legit in-project file")
        (self.sibling / "SECRET.txt").write_text(SENTINEL)
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)

    # -- helpers ----------------------------------------------------------

    def _read(self, file_path, user=None):
        request = self.rf.get(
            f"/api/workspace/file-content/{file_path}",
            {"project_id": str(self.project.id)},
        )
        request.user = user or AnonymousUser()
        return api_get_file_content(request, file_path=file_path)

    def _save(self, path, content="owned"):
        payload = {
            "project_id": str(self.project.id),
            "path": path,
            "content": content,
        }
        request = self.rf.post(
            "/api/workspace/save-file/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.alice
        request.session = {}
        return api_save_file(request)

    # -- READ: api_get_file_content ---------------------------------------

    def test_anonymous_sibling_prefix_escape_read_returns_400(self):
        # Arrange
        # Act
        response = self._read(ESCAPE_PATH)
        # Assert
        assert response.status_code == 400

    def test_anonymous_sibling_prefix_escape_read_leaks_no_bytes(self):
        # Arrange
        # Act
        response = self._read(ESCAPE_PATH)
        # Assert
        assert SENTINEL not in response.content.decode("utf-8", "replace")

    def test_anonymous_read_of_own_public_file_returns_200(self):
        # Arrange — the public-sharing feature must not regress.
        # Act
        response = self._read("README.md")
        # Assert
        assert response.status_code == 200

    def test_anonymous_read_of_own_public_file_returns_its_content(self):
        # Arrange
        # Act
        response = self._read("README.md")
        # Assert
        assert "legit in-project file" in response.content.decode(
            "utf-8", "replace"
        )

    # -- WRITE: api_save_file ---------------------------------------------

    def test_sibling_prefix_escape_write_returns_400(self):
        # Arrange
        # Act
        response = self._save(WRITE_ESCAPE_PATH)
        # Assert
        assert response.status_code == 400

    def test_sibling_prefix_escape_write_creates_no_file(self):
        # Arrange
        # Act
        self._save(WRITE_ESCAPE_PATH)
        # Assert — the write must never land in the sibling project on disk.
        assert not (self.sibling / "PWNED.txt").exists()

    def test_legitimate_in_project_write_returns_200(self):
        # Arrange
        # Act
        response = self._save("notes/todo.txt", content="hello")
        # Assert
        assert response.status_code == 200

    def test_legitimate_in_project_write_persists_content(self):
        # Arrange
        # Act
        self._save("notes/todo.txt", content="hello")
        # Assert
        assert (self.victim_root / "notes" / "todo.txt").read_text() == "hello"


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
