"""
Guarded, verified filesystem wipe for visitor workspaces.

Security-critical (visitor-slot isolation audit 2026-07-07, gap #1):
the previous unguarded ``shutil.rmtree`` aborted mid-wipe on a
read-only file (``PermissionError('revision.tex')``) and the caller
carried on, handing the next visitor a workspace with the previous
visitor's files still in it.

This module provides:

* :class:`WorkspaceWipeError` — raised on ANY wipe/verify failure so
  callers must handle it (fail loud, quarantine the slot; never serve).
* :func:`force_rmtree` — rmtree with chmod+retry recovery for
  permission-denied entries.
* :func:`wipe_directory_contents` — remove every entry under a
  directory, then VERIFY it is empty.
"""

import logging
import os
import shutil
import stat
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceWipeError(Exception):
    """A visitor workspace could not be wiped and verified empty."""


def _chmod_tree_writable(path: Path) -> None:
    """Best-effort chmod u+rwx on ``path`` and everything below it.

    Recovery step for rmtree failures caused by read-only files or
    directories (the exact failure mode observed in production:
    ``PermissionError`` on a read-only ``revision.tex``).
    """
    try:
        os.chmod(path, stat.S_IRWXU)
    except OSError:
        pass
    if not path.is_dir() or path.is_symlink():
        return
    for root, dirs, files in os.walk(path, topdown=True):
        for name in dirs + files:
            try:
                os.chmod(os.path.join(root, name), stat.S_IRWXU)
            except OSError:
                pass


def force_rmtree(path: Path) -> None:
    """Remove a file/dir tree, recovering from permission errors.

    First tries a plain removal; on failure chmods the whole tree
    user-writable and retries once. If the retry also fails, raises
    :class:`WorkspaceWipeError` — callers must NOT continue as if the
    wipe succeeded.
    """
    if path.is_symlink() or path.is_file():
        try:
            path.unlink()
        except OSError:
            try:
                os.chmod(path.parent, stat.S_IRWXU)
                path.unlink()
            except OSError as exc:
                raise WorkspaceWipeError(f"Could not remove {path}: {exc}") from exc
        return

    try:
        shutil.rmtree(path)
    except OSError:
        _chmod_tree_writable(path)
        try:
            shutil.rmtree(path)
        except OSError as exc:
            raise WorkspaceWipeError(f"Could not remove {path}: {exc}") from exc


def wipe_directory_contents(path: Path) -> None:
    """Remove every entry under ``path`` and VERIFY it ended up empty.

    ``path`` itself is kept (it is the visitor's base dir, recreated
    content goes back into it). Missing ``path`` is fine — nothing to
    leak. Raises :class:`WorkspaceWipeError` on any failure, including
    a non-empty directory after the wipe (verification step).
    """
    if not path.exists():
        return
    if not path.is_dir():
        raise WorkspaceWipeError(f"Wipe target is not a directory: {path}")

    errors = []
    for entry in list(path.iterdir()):
        try:
            force_rmtree(entry)
        except WorkspaceWipeError as exc:
            errors.append(str(exc))

    # VERIFY: the directory must be empty now. This is the guarantee
    # allocation relies on — a partially-wiped workspace is a leak.
    residue = [p.name for p in path.iterdir()]
    if residue or errors:
        raise WorkspaceWipeError(
            f"Wipe of {path} left residue {residue!r}; errors: {errors!r}"
        )

    logger.info(f"[VisitorPool] Wiped and verified empty: {path}")


# EOF
