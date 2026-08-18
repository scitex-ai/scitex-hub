"""
Permission checks for project filesystem operations.

This module handles all permission-related validation.
"""

from pathlib import Path, PurePosixPath

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

    Component-wise containment via ``Path.relative_to``, NOT a string prefix
    match. A prefix match is not containment: ``project_path`` ``.../proj`` is a
    string prefix of the sibling ``.../proj-secret``, so ``startswith`` would
    admit ``project_path / "../proj-secret/x"`` and leak into another project.
    ``relative_to`` compares path COMPONENTS, so the sibling is rejected.
    Returns False only on ValueError/OSError (target outside, or unresolvable).
    """
    try:
        target_path.resolve().relative_to(project_path.resolve())
        return True
    except (ValueError, OSError):
        return False


# Path components that must never be SERVED, whatever the project's
# visibility. Deliberately NOT "every dotfile": `.gitignore`, `.github/` and
# friends are ordinary repository content that a repo browser is supposed to
# show, and refusing them would be a UX regression dressed as hardening.
#
# `.git` is different in kind rather than degree. It is not content; it is the
# object store, and a reader who can walk it reconstructs every version of
# every file, including ones committed and later deleted.
_REFUSED_PATH_COMPONENTS = frozenset({".git"})

# Filenames refused wherever they appear. Same reasoning, one level down: these
# are not repository content, they are credentials that happen to live in the
# tree.
_REFUSED_FILENAMES = frozenset({".env"})


def path_is_servable(relative_path) -> bool:
    """False when a path reaches VCS metadata or a credentials file.

    This is the code-level form of two edge tourniquets added on 2026-08-18,
    and it exists because those tourniquets key on URL SHAPES while this keys
    on the PATH ITSELF. That distinction is the whole point: the first block
    covered the repo browser, an anonymous request through the workspace API
    reached the same files by a different prefix, and the second block had to
    be written for it. BLOCKING A PATH SHAPE ONLY BLOCKS THE ROUTES THAT USE
    IT. A rule at the filesystem chokepoint covers every route, including ones
    nobody has enumerated -- and the route enumeration is known to be
    incomplete.

    Why the containment check next door is not enough: it answers "is this
    inside the project?", and `.git/HEAD` IS inside the project. The jail is
    sound; it simply has no opinion about which components are admissible
    within it. `file_view_utils` says so itself -- "CONTAINMENT ONLY".

    Measured on live production before this existed, anonymously, on two
    public projects: `.git/HEAD` and `.git/config` both returned 200 with real
    contents, with `README.md` (200) and a nonexistent `.env` (404) as the
    controls proving the route worked and the 200s were not a catch-all.

    Accepts str or Path, absolute or relative. Comparison is component-wise,
    so `foo.git` and `env` are unaffected and only a real `.git` component or
    a real `.env` filename is refused.
    """
    parts = PurePosixPath(str(relative_path).replace("\\", "/")).parts
    if any(part in _REFUSED_PATH_COMPONENTS for part in parts):
        return False
    return not (parts and parts[-1] in _REFUSED_FILENAMES)


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
