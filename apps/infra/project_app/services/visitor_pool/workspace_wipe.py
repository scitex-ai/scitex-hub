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
  directory, then VERIFY it is empty. Entries that survive the
  chmod+retry (files owned by apptainer ``--fakeroot`` sub-UIDs, which
  the Django uid cannot chmod at all) are retried once through
  :func:`_fakeroot_rm` before the wipe is declared failed.
"""

import logging
import os
import shutil
import stat
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

FAKEROOT_RM_TIMEOUT = 120  # seconds


class WorkspaceWipeError(Exception):
    """A visitor workspace could not be wiped and verified empty."""


def _default_run_cmd(argv: list, timeout: float):
    """The real subprocess boundary (injectable seam for tests)."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


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


def _fakeroot_rm(path: Path, *, run_cmd=None) -> None:
    """Remove ``path`` via ``apptainer exec --fakeroot ... rm -rf``.

    Last resort for entries owned by apptainer ``--fakeroot`` sub-UIDs
    (e.g. from a visitor's container build), which the Django uid can
    neither chmod nor unlink. Inside a ``--fakeroot`` namespace those
    sub-UIDs map back to the invoking user, so ``rm -rf`` succeeds.

    Mirrors the flag discipline of ``scripts/deploy/rebuild.sh``:
    ``--contain --no-home --no-mount home,tmp,cwd`` so the namespace
    can only touch the single explicit ``--bind`` we pass.

    Raises :class:`WorkspaceWipeError` on any failure — including no
    configured apptainer image, a nonzero exit, or ``path`` surviving.
    """
    from django.conf import settings

    run_cmd = run_cmd or _default_run_cmd
    image = getattr(settings, "SINGULARITY_IMAGE_PATH", "") or ""
    if not image or not Path(image).exists():
        raise WorkspaceWipeError(
            f"fakeroot rm unavailable for {path}: no apptainer image at "
            f"SINGULARITY_IMAGE_PATH={image!r}"
        )

    argv = [
        "apptainer",
        "exec",
        "--fakeroot",
        "--contain",
        "--no-home",
        "--no-mount",
        "home,tmp,cwd",
        "--bind",
        f"{path.parent}:/wipe",
        str(image),
        "rm",
        "-rf",
        f"/wipe/{path.name}",
    ]
    try:
        result = run_cmd(argv, FAKEROOT_RM_TIMEOUT)
    except WorkspaceWipeError:
        raise
    except Exception as exc:
        raise WorkspaceWipeError(f"fakeroot rm failed for {path}: {exc}") from exc
    if result.returncode != 0:
        raise WorkspaceWipeError(
            f"fakeroot rm exited {result.returncode} for {path}: "
            f"{(result.stderr or '').strip()}"
        )
    if path.exists() or path.is_symlink():
        raise WorkspaceWipeError(f"fakeroot rm left {path} in place")


def wipe_directory_contents(path: Path, *, run_cmd=None) -> None:
    """Remove every entry under ``path`` and VERIFY it ended up empty.

    ``path`` itself is kept (it is the visitor's base dir, recreated
    content goes back into it). Missing ``path`` is fine — nothing to
    leak. Raises :class:`WorkspaceWipeError` on any failure, including
    a non-empty directory after the wipe (verification step).

    Entries that survive :func:`force_rmtree`'s chmod+retry are retried
    once through :func:`_fakeroot_rm` (loud, never silent) — the only
    way to delete ``--fakeroot`` sub-UID-owned files without root.
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
            logger.warning(
                f"[VisitorPool] {entry} survived chmod+retry ({exc}); "
                f"retrying via apptainer --fakeroot rm"
            )
            try:
                _fakeroot_rm(entry, run_cmd=run_cmd)
                logger.warning(f"[VisitorPool] Removed via fakeroot rm: {entry}")
            except WorkspaceWipeError as fallback_exc:
                errors.append(f"{exc}; fakeroot retry: {fallback_exc}")

    # VERIFY: the directory must be empty now. This is the guarantee
    # allocation relies on — a partially-wiped workspace is a leak.
    residue = [p.name for p in path.iterdir()]
    if residue or errors:
        raise WorkspaceWipeError(
            f"Wipe of {path} left residue {residue!r}; errors: {errors!r}"
        )

    logger.info(f"[VisitorPool] Wiped and verified empty: {path}")


# EOF
