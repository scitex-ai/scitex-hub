"""Focused regressions for the Python findings in CodeQL check 104465980385."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.infra.public_app.views.status.api.health import _build_issues_list
from apps.workspace.writer_app.services.writer.file_operations import (
    FileOperationsMixin,
)
from apps.workspace.writer_app.views.editor.api.content import _section_target
from apps.workspace.writer_app.views.editor.api.files import writer_pdf_candidates


class _WriterService(FileOperationsMixin):
    def __init__(self, root: Path):
        self.writer_dir = root

    @property
    def writer(self):  # pragma: no cover - a rejected path must never get here
        raise AssertionError("Writer received an unvalidated path")


def test_writer_service_rejects_section_escape_before_writer(tmp_path):
    service = _WriterService(tmp_path / "writer")
    service.writer_dir.mkdir()

    with pytest.raises(ValueError, match="Invalid Writer section path"):
        service.write_section("../../outside", "secret", "manuscript")


def test_content_section_target_is_confined_to_document_directory(tmp_path):
    root = tmp_path / "writer"
    root.mkdir()
    service = SimpleNamespace(writer_dir=root)

    assert _section_target(service, "../../outside", "manuscript") is None
    assert _section_target(service, "abstract", "unknown") is None


def test_content_api_does_not_return_an_absolute_server_path():
    source = Path(
        "apps/workspace/writer_app/views/editor/api/content.py"
    ).read_text(encoding="utf-8")

    assert '"file_path": str(file_path)' not in source


def test_pdf_candidates_reject_filename_traversal(tmp_path):
    writer_dir = tmp_path / "writer"
    writer_dir.mkdir()

    assert writer_pdf_candidates(writer_dir, "../../secret.pdf") == []


def test_metadata_failure_does_not_expose_exception(monkeypatch):
    from apps.workspace.writer_app.views.editor.api.metadata import file_tree

    secret = "postgresql://user:password@db/private"

    def fail(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(file_tree, "get_object_or_404", fail)
    request = RequestFactory().get("/writer/tree/?project_id=1")
    request.user = AnonymousUser()
    request.session = {}

    response = file_tree.file_tree_view(request, project_id=1)
    body = json.loads(response.content)

    assert response.status_code == 500
    assert secret not in response.content.decode()
    assert body["error"] == "Unable to load file tree."


def test_dev_file_failure_is_generic_and_logged(monkeypatch):
    from apps.workspace.apps_app.views import dev_project_files

    class BrokenPath:
        def is_file(self):
            return True

        def stat(self):
            return SimpleNamespace(st_size=1)

        def read_text(self, **kwargs):
            raise OSError("/srv/private/credential.txt")

    monkeypatch.setattr(dev_project_files, "_get_project_dir", lambda *args: Path("/p"))
    monkeypatch.setattr(dev_project_files, "_resolve_safe_path", lambda *args: BrokenPath())
    request = RequestFactory().get("/dev/files/?path=name\nforged")
    request.user = SimpleNamespace(is_authenticated=True)

    response = dev_project_files.api_dev_file_read(
        request, "owner", "repo", "project"
    )

    assert response.status_code == 500
    assert b"credential.txt" not in response.content
    assert json.loads(response.content)["error"] == "Unable to read file."


def test_auth_log_field_cannot_add_a_physical_log_line(caplog):
    from apps.workspace.writer_app.views.editor.auth_utils import get_user_for_request

    request = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=False),
        session={},
    )
    get_user_for_request(request, "project\nFORGED")

    assert "project\\nFORGED" in caplog.text
    assert "project\nFORGED" not in caplog.text


def test_status_issues_do_not_expose_probe_exceptions():
    secret = "connection failed for postgresql://user:password@db/private"
    status = {
        "database": {"health_class": "unhealthy", "error": secret},
        "redis": {"health_class": "unhealthy", "error": secret},
        "services": [],
        "ssh_services": [],
        "api_services": [],
    }

    issues = _build_issues_list(status)

    assert secret not in repr(issues)
    assert {issue["message"] for issue in issues} == {
        "Database connection failed",
        "Redis connection failed",
    }


def test_upload_redirect_remains_local(monkeypatch, tmp_path):
    from apps.infra.project_app.views.repository import add_file

    project = SimpleNamespace()
    monkeypatch.setattr(
        add_file, "_writable_project", lambda *args: (project, tmp_path, None)
    )
    request = RequestFactory().post(
        "/alice/p/upload/",
        data={
            "directory": "//evil.example/landing",
            "files": [SimpleUploadedFile("paper.txt", b"content")],
        },
    )

    response = add_file.project_upload_files(request, "alice", "p")

    assert response.status_code == 302
    assert urlsplit(response["Location"]).netloc == ""


def test_project_tree_rejects_redirect_that_fails_local_allowlist(monkeypatch):
    from apps.infra.project_app.views.projects import detail

    request = RequestFactory().get("/alice/p/tree/main/x/?view=repository")
    request.user = AnonymousUser()
    request.project = SimpleNamespace()
    monkeypatch.setattr(detail, "wants_repository_view", lambda request: True)
    monkeypatch.setattr(detail, "url_has_allowed_host_and_scheme", lambda *a, **k: False)

    response = detail.project_tree_or_blob.__wrapped__(
        request, "alice", "p", branch="main", path="x"
    )

    assert response.status_code == 302
    assert response["Location"] == "/alice/p/"
