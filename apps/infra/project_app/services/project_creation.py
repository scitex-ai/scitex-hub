"""Make creating a project all-or-nothing on disk.

A creation touches three places: the Project row, its Gitea repository (made
and cloned by the post_save signal) and the working tree under
``data/users/<owner>/proj/<slug>``. Failure paths used to delete the row --
which removes the repository through post_delete -- and leave the working tree
behind. The next attempt with the same name then found "the directory already
exists as a git repo", skipped the clone of the NEW repository and failed in
1.5 s without a word to the user (hub#1274).

Two rules close that:

* before a creation, a folder at the target path that no project owns is a
  leftover: it is moved aside (never deleted -- it might hold someone's work)
  so the new project starts from an empty path;
* after a failed creation, everything it made is removed: the row, therefore
  the repository, and the working tree. Because the path was empty when the
  creation began, everything under it belongs to that creation.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from django.conf import settings

from ..models import Project

logger = logging.getLogger(__name__)

LEFTOVERS_DIRNAME = ".project-leftovers"


def user_project_path(user, slug: str) -> Path:
    """Where a user-owned project's working tree lives (see paths.py)."""
    return Path(settings.BASE_DIR) / "data" / "users" / user.username / "proj" / slug


def find_leftover(user, slug: str) -> Optional[Path]:
    """The folder at ``slug``'s path if it exists and no project owns it."""
    path = user_project_path(user, slug)
    if not (path.exists() or path.is_symlink()):
        return None
    owned = (
        Project.objects.filter(owner=user, slug=slug).exists()
        or Project.objects.filter(git_clone_path=str(path)).exists()
    )
    return None if owned else path


def move_leftover_aside(user, path: Path) -> Path:
    """Move an unowned project folder to ``data/users/<owner>/.project-leftovers``.

    Kept, not deleted: a folder no row points at is most likely an earlier
    failed creation, but it may also be the only copy of work whose row was
    lost. Returns the new location; raises OSError if it cannot be moved.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = path.parent.parent / LEFTOVERS_DIRNAME / f"{path.name}-{stamp}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(target))
    logger.warning(
        "Moved unowned project folder %s to %s before creating a project there",
        path,
        target,
    )
    return target


def discard_failed_creation(project: Optional[Project], path: Path) -> None:
    """Undo a failed creation: the row (and with it the repository) and the tree.

    Never raises: it runs on the failure path, where the user must still get
    the form back with an explanation. Anything it cannot remove is logged
    with the path, because a leftover is exactly what breaks the next try.
    """
    if project is not None and project.pk is not None:
        try:
            project.delete()  # post_delete removes the Gitea repository
        except Exception:
            logger.exception("Could not delete the row of failed project %s", path)
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path, ignore_errors=True)
    if path.exists() or path.is_symlink():
        logger.error("Failed creation left %s on disk; remove it by hand", path)
