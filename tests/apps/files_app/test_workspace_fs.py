"""Files app filesystem rules: every path stays inside the user's root."""

from django.contrib.auth.models import User
from django.test import override_settings

from apps.workspace.files_app.services import workspace_fs as fs


def _refusal(call):
    try:
        call()
    except fs.WorkspacePathError as exc:
        return exc
    return None


def test_parent_traversal_is_rejected(tmp_path):
    # Arrange
    root = tmp_path / "data" / "users" / "alice"
    root.mkdir(parents=True)
    # Act
    error = _refusal(lambda: fs.resolve_path(root, "Downloads/../../bob"))
    # Assert
    assert isinstance(error, fs.WorkspacePathError)


def test_absolute_path_is_rejected(tmp_path):
    # Arrange
    root = tmp_path / "alice"
    root.mkdir()
    # Act
    error = _refusal(lambda: fs.resolve_path(root, "/etc/passwd"))
    # Assert
    assert isinstance(error, fs.WorkspacePathError)


def test_symlink_pointing_outside_the_root_is_rejected(tmp_path):
    # Arrange
    outside = tmp_path / "bob"
    outside.mkdir()
    (outside / "secret.txt").write_text("bob's")
    root = tmp_path / "alice"
    root.mkdir()
    (root / "escape").symlink_to(outside)
    # Act
    error = _refusal(lambda: fs.resolve_path(root, "escape/secret.txt"))
    # Assert
    assert isinstance(error, fs.WorkspacePathError)


def test_dot_directories_are_not_reachable(tmp_path):
    # Arrange
    root = tmp_path / "alice"
    (root / ".ssh").mkdir(parents=True)
    # Act
    error = _refusal(lambda: fs.resolve_path(root, ".ssh/id_rsa"))
    # Assert
    assert isinstance(error, fs.WorkspacePathError)


def test_projects_folder_cannot_be_deleted(tmp_path):
    # Arrange
    root = tmp_path / "alice"
    (root / "proj" / "paper").mkdir(parents=True)
    # Act
    error = _refusal(lambda: fs.delete(root, "proj"))
    # Assert
    assert isinstance(error, fs.WorkspacePathError)


def test_standard_folders_are_created(tmp_path):
    # Arrange
    user = User(username="alice")
    # Act
    with override_settings(BASE_DIR=tmp_path):
        root = fs.user_root(user)
    # Assert
    assert sorted(p.name for p in root.iterdir()) == ["Downloads", "Recordings"]


def test_save_to_downloads_deduplicates_names(tmp_path):
    # Arrange
    user = User(username="alice")
    with override_settings(BASE_DIR=tmp_path):
        fs.save_to_downloads(user, "figure.png", b"first")
        # Act
        second = fs.save_to_downloads(user, "figure.png", b"second")
    # Assert
    assert second.name == "figure (1).png"


def test_save_to_downloads_copies_from_a_path(tmp_path):
    # Arrange
    user = User(username="alice")
    source = tmp_path / "export.pdf"
    source.write_bytes(b"%PDF-1.7")
    # Act
    with override_settings(BASE_DIR=tmp_path / "hub"):
        saved = fs.save_to_downloads(user, source.name, source)
    # Assert
    assert saved.read_bytes() == b"%PDF-1.7"
