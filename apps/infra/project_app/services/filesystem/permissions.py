"""
Permission checks for project filesystem operations.

This module handles all permission-related validation.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from ...models import Project


def get_user_data_root(user: User) -> Path:
    """Return the root data directory for a user (their filesystem jail)."""
    return Path(settings.BASE_DIR) / "data" / "users" / str(user.username)


def can_access_project(user: User, project: Project) -> bool:
    """Check if user has access to a project."""
    return project.owner == user or user in project.collaborators.all()


def can_modify_project(user: User, project: Project) -> bool:
    """Check if user can modify a project."""
    return project.owner == user


def can_delete_project(user: User, project: Project) -> bool:
    """Check if user can delete a project."""
    return project.owner == user


def validate_path_in_project(project_path: Path, target_path: Path) -> bool:
    """
    Validate that a path is within the project directory.

    This prevents path traversal attacks.
    """
    try:
        target_path.resolve().relative_to(project_path.resolve())
        return True
    except ValueError:
        return False


def validate_remote_path_in_root(remote_root: str, full_path: str) -> bool:
    """
    Validate that a REMOTE (SSH/SFTP) path is contained within remote_root.

    Component-wise containment on POSIX path *syntax*, mirroring
    validate_path_in_project's contract (returns False only on ValueError).

    Deliberately does NOT call Path.resolve(): the path lives on a remote
    host, so resolving it against the local container filesystem would be
    meaningless and actively wrong.

    LIMITATION: posixpath.normpath cannot collapse symlinks on the remote
    host, so this confines path syntax only -- a symlink planted inside
    remote_root that points elsewhere still escapes. Fully closing that
    requires an SFTP-side realpath() per access (a round trip). Recorded as
    an operator decision.
    """
    import posixpath
    from pathlib import PurePosixPath

    try:
        PurePosixPath(posixpath.normpath(full_path)).relative_to(
            PurePosixPath(posixpath.normpath(remote_root))
        )
        return True
    except ValueError:
        return False


def validate_path_in_user_jail(user: User, target_path: Path) -> bool:
    """
    Validate that a path stays within the user's own data directory.

    Use this wherever a user-supplied or derived path must not escape their jail.
    """
    return validate_path_in_project(get_user_data_root(user), target_path)
