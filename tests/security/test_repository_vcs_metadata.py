"""Repository readers must never expose version-control internals."""

from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.infra.project_app.services.filesystem.permissions import (
    resolve_repository_path,
)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text("public\n")
    git = tmp_path / ".git"
    (git / "objects" / "pack").mkdir(parents=True)
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "info").mkdir()
    for relative in ("HEAD", "config", "index", "info/exclude", "objects/pack/secret", "refs/heads/main"):
        target = git / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SECRET\n")
    return tmp_path


def test_normal_repository_file_resolves(repository: Path):
    assert resolve_repository_path(repository, "README.md") == repository / "README.md"


@pytest.mark.parametrize(
    "path",
    [
        ".git/HEAD",
        ".git/config",
        ".git/index",
        ".git/objects/pack/secret",
        ".git/refs/heads/main",
        ".git/info/exclude",
        "nested/.git/HEAD",
        "%2egit/HEAD",
        "%252egit/HEAD",
        ".GiT/HEAD",
        "safe/../.git/HEAD",
        ".hg/store/data",
        ".svn/wc.db",
        ".bzr/branch/format",
        "_darcs/inventory",
        "CVS/Root",
    ],
)
def test_vcs_metadata_paths_are_denied(repository: Path, path: str):
    assert resolve_repository_path(repository, path) is None


def test_symlink_into_git_metadata_is_denied(repository: Path):
    (repository / "innocent").symlink_to(repository / ".git", target_is_directory=True)
    assert resolve_repository_path(repository, "innocent/HEAD") is None


def test_symlink_outside_repository_is_denied(repository: Path, tmp_path: Path):
    outside = tmp_path.parent / "outside-secret"
    outside.write_text("SECRET")
    (repository / "outside").symlink_to(outside)
    assert resolve_repository_path(repository, "outside") is None


def test_file_tree_never_contains_vcs_metadata(repository: Path, monkeypatch):
    from apps.infra.project_app.services import file_tree_builder, project_filesystem

    project = SimpleNamespace(project_type="local", owner=SimpleNamespace())
    filesystem = SimpleNamespace(get_project_root_path=lambda _project: repository)
    monkeypatch.setattr(
        project_filesystem, "get_project_filesystem_manager", lambda _owner: filesystem
    )
    monkeypatch.setattr(file_tree_builder, "get_git_status", lambda _root: {})

    result = file_tree_builder.build_project_file_tree(project)
    names = {entry["name"].casefold() for entry in result["treeData"]}
    assert names.isdisjoint({".git", ".hg", ".svn", ".bzr", "_darcs", "cvs"})


@pytest.mark.skipif(find_spec("paramiko") is None, reason="paramiko is optional")
def test_trip_backend_denies_encoded_vcs_path():
    from apps.infra.project_app.services.trip_backend import TripFileBackend

    backend = TripFileBackend.__new__(TripFileBackend)
    backend.remote_path = "/srv/repository"
    with pytest.raises(ValueError, match="not available"):
        backend._full_path("%2egit/HEAD")


@pytest.mark.skipif(find_spec("paramiko") is None, reason="paramiko is optional")
def test_trip_backend_denies_remote_symlink_escape():
    from apps.infra.project_app.services.trip_backend import TripFileBackend

    backend = TripFileBackend.__new__(TripFileBackend)
    backend.remote_path = "/srv/repository"
    sftp = SimpleNamespace(
        normalize=lambda path: "/etc/passwd" if path.endswith("link") else path
    )
    assert backend._safe_realpath(sftp, "/srv/repository/link") is None


class TestRepositoryVcsRoutes(TestCase):
    def setUp(self):
        from apps.infra.project_app.models import Project
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        self.owner = User.objects.create_user(username="vcs-owner")
        self.public = Project.objects.create(
            owner=self.owner, slug="public-repo", name="public", visibility="public"
        )
        self.private = Project.objects.create(
            owner=self.owner, slug="private-repo", name="private", visibility="private"
        )
        self.roots = {}
        for project in (self.public, self.private):
            root = get_project_filesystem_manager(self.owner).get_project_root_path(project)
            root.mkdir(parents=True, exist_ok=True)
            (root / "README.md").write_text("NORMAL")
            (root / ".git" / "objects" / "pack").mkdir(parents=True)
            (root / ".git" / "HEAD").write_text("SECRET")
            self.roots[project.pk] = root

    def test_public_normal_blob_is_positive_control(self):
        response = self.client.get("/vcs-owner/public-repo/blob/README.md?mode=raw")
        assert response.status_code == 200

    def test_blob_tree_raw_and_archive_shapes_hide_git(self):
        paths = (
            "/vcs-owner/public-repo/blob/.git/HEAD?mode=raw",
            "/vcs-owner/public-repo/tree/main/.git/HEAD",
            "/vcs-owner/public-repo/raw/.git/HEAD/",
            "/vcs-owner/public-repo/archive/.git/HEAD/",
        )
        assert {self.client.get(path).status_code for path in paths} == {404}

    def test_workspace_reader_hides_git_for_public_anonymous_and_private_owner(self):
        from apps.infra.workspace_api.views.file_content import api_get_file_content

        statuses = []
        for project, user in ((self.public, AnonymousUser()), (self.private, self.owner)):
            request = RequestFactory().get("/", {"project_id": project.pk})
            request.user = user
            statuses.append(api_get_file_content(request, ".git/HEAD").status_code)
        assert statuses == [404, 404]
