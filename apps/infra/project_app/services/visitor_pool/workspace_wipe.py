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


def _add_owner_rwx(path) -> None:
    """Best-effort ``u+rwx`` on ``path``, ADDING bits and clearing none.

    The recovery chmods below used to assign ``stat.S_IRWXU`` (0700)
    outright, which does two things at once: it grants the owner write
    (what the recovery needs) and it strips ``go`` (what nothing here
    asked for, and what nothing here restores).

    That second half reached production. ``force_rmtree``'s file branch
    chmods ``path.parent``, and for every direct entry of a visitor's
    home root the parent IS the home root — so a single read-only
    dotfile during a wipe left ``data/users/<visitor>`` at mode 0700
    permanently. Measured 2026-08-16: ``drwx------ 100001 visitor-001``,
    empty, which the app (uid 1000) could not list. ``/api/server-health/``
    walks every directory under ``data/users`` and marks the WHOLE check
    unhealthy on one ``PermissionError``, so that one slot rendered
    "Server: partial" in the header for every visitor, anonymous ones
    included, for days.

    Widening-only is the property that removes the class: a recovery
    step must never narrow a permission it did not need to narrow.
    """
    try:
        current = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return
    if current & stat.S_IRWXU == stat.S_IRWXU:
        return
    try:
        os.chmod(path, current | stat.S_IRWXU)
    except OSError:
        pass


def _chmod_tree_writable(path: Path) -> None:
    """Best-effort chmod u+rwx on ``path`` and everything below it.

    Recovery step for rmtree failures caused by read-only files or
    directories (the exact failure mode observed in production:
    ``PermissionError`` on a read-only ``revision.tex``).

    Adds ``u+rwx`` without clearing any other bit — see
    :func:`_add_owner_rwx` for why the widening-only form matters.
    """
    _add_owner_rwx(path)
    if not path.is_dir() or path.is_symlink():
        return
    for root, dirs, files in os.walk(path, topdown=True):
        for name in dirs + files:
            _add_owner_rwx(os.path.join(root, name))


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
                # ADDS u+rwx to the parent; never assigns 0700 to it. For a
                # direct entry of a visitor home the parent IS the home root,
                # and assigning here is what left production unlistable — see
                # :func:`_add_owner_rwx`.
                _add_owner_rwx(path.parent)
                path.unlink()
            except OSError as exc:
                raise WorkspaceWipeError(f"Could not remove {path}: {exc}") from exc
        return

    try:
        shutil.rmtree(path)
    except OSError:
        # Removing a directory needs WRITE on its PARENT (rmdir unlinks the
        # entry from the parent), exactly as unlinking a file does — and for
        # a direct entry of a visitor home the parent IS the home root, which
        # a reset finds at 0555. The file branch above widens the parent; this
        # branch used to widen only the tree BELOW the directory, so the retry
        # failed with the same EACCES whenever the directory entry was
        # iterated before a file entry had already widened the root. That
        # order is the filesystem's hash order, not ours: the same wipe passed
        # or failed depending on the tmp dir's name, which is why CI flickered
        # per leg and then went red on every leg (2026-09-03/04). Widen the
        # parent too, widening-only as always (see _add_owner_rwx).
        _add_owner_rwx(path.parent)
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
