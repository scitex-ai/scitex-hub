"""
Recycled-visitor HOME state: skeleton recreation + final-gate checks.

Companion of ``workspace_manager`` (extracted for the 512-line cap).
Covers the filesystem half of isolation-audit gap #6:

* The reset pipeline wipes the visitor's ENTIRE home root (apptainer
  binds the parent of ``proj/`` as the container ``--home``, so
  ``~/.bash_history``, ``~/.local``, ``~/.cache``, AI-tool configs and
  ``~/.singularity/default.sif`` all live there and previously survived
  every reset). This module recreates the fresh skeleton afterwards and
  verifies the recycled home holds EXACTLY that skeleton — nothing
  more (leaked visitor state), nothing less (skeleton silently failed).
* ``MEDIA_ROOT/user_containers/<user.id>`` — the custom-container
  builder's per-user SIF/sandbox storage — is cleared and verified
  gone as well.

Failure policy: every check raises :class:`HomeStateError`; the caller
(``workspace_manager.reset_visitor_workspace``) wraps it into
``WorkspaceResetError`` so the slot is quarantined, never served.
"""

import grp
import logging
import os
import pwd
import subprocess
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from .workspace_wipe import WorkspaceWipeError, force_rmtree

logger = logging.getLogger(__name__)


class HomeStateError(Exception):
    """A recycled home failed skeleton recreation or state verification."""


# The exact home-root layout ensure_workspace_sync + the reset pipeline
# recreate. The final gate requires the recycled home to match this set
# EXACTLY — an extra entry is potentially leaked visitor state, a
# missing entry means the skeleton step silently failed. Both quarantine.
#
# DRIFT GUARD: these two sets are hardcoded, so if the skeleton builder
# (recreate_workspace_skeleton -> ensure_workspace_sync + the dotfiles
# setup + the project_filesystem manager) ever changes what it creates,
# a stale set here would false-quarantine EVERY slot (the
# "all-16-slots-quarantined" failure mode). tests/apps/project_app/
# services/visitor_pool/test_home_skeleton_reality.py runs the REAL
# builder and asserts it still equals these sets, so drift breaks that
# TEST in CI instead of silently bricking prod. Keep them in sync there.
EXPECTED_HOME_ENTRIES = frozenset(
    {
        "proj",
        ".singularity",
        ".bashrc",
        ".bash_profile",
        ".vimrc",
        ".gitconfig",
        ".screenrc",
        ".ipython",
    }
)
# proj/ after a verified reset: the fresh clone, the dotfiles repo, and
# the workspace metadata file written by initialize_user_workspace.
EXPECTED_PROJ_ENTRIES = frozenset({"default-project", "dotfiles", "workspace_info.json"})


def user_container_dir(visitor_user: User) -> Path:
    """The visitor's container-build storage dir.

    Mirrors ``console_app.services.user_container_manager``'s
    ``PathUtils.get_user_dir`` (``MEDIA_ROOT/user_containers/<id>``)
    WITHOUT importing it: constructing its ``ContainerConfig`` probes
    for the apptainer binary and raises where none is installed, which
    would brick resets in non-container deployments.
    """
    return Path(settings.MEDIA_ROOT) / "user_containers" / str(visitor_user.id)


def wipe_user_container_dir(visitor_user: User) -> None:
    """Remove the visitor's user_containers build dir (defensive).

    The custom-container builder stores per-user SIF/sandbox output
    here and nothing ever cleared it. Wiped defensively even though no
    current view wires visitors into the builder — a stored container
    image is a code-execution channel if it is ever selected as the
    next visitor's container.
    """
    container_dir = user_container_dir(visitor_user)
    if not container_dir.exists():
        return
    try:
        force_rmtree(container_dir)
    except WorkspaceWipeError as exc:
        raise HomeStateError(
            f"user_containers wipe failed for {visitor_user.username}: {exc}"
        ) from exc
    logger.info(
        f"[VisitorPool] Removed user_containers dir for "
        f"{visitor_user.username}: {container_dir}"
    )


def recreate_workspace_skeleton(visitor_user: User, project_slug: str) -> None:
    """Recreate the wiped home root's skeleton (proj/ + dotfiles).

    Uses the SAME code paths a normal terminal spawn uses so the layout
    can never drift: ``get_project_filesystem_manager`` re-initializes
    ``proj/`` (+ ``workspace_info.json`` + OS-ownership enforcement)
    because the base dir is gone after the home wipe, and
    ``ensure_workspace_sync`` recreates ``proj/dotfiles`` plus the
    home-level dotfile symlinks and ``.singularity/``.
    """
    from apps.infra.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )
    from apps.workspace.console_app.views.terminal.workspace import (
        ensure_workspace_sync,
    )

    username = visitor_user.username
    manager = get_project_filesystem_manager(visitor_user)
    base_path = Path(manager.base_path)
    if not base_path.is_dir():
        raise HomeStateError(
            f"Workspace re-init failed for {username}: {base_path} missing"
        )
    try:
        ensure_workspace_sync(base_path.parent, username, project_slug)
    except Exception as exc:
        raise HomeStateError(
            f"Home skeleton recreation failed for {username}: {exc}"
        ) from exc


APP_UNIX_OWNER_SETTING = "APP_UNIX_OWNER"
APP_UNIX_OWNER_ENV = "SCITEX_HUB_APP_UNIX_OWNER"


def resolve_app_owner() -> tuple[int, int]:
    """Turn ``settings.APP_UNIX_OWNER`` into a numeric ``(uid, gid)`` pair.

    Accepted forms: ``scitex`` (name), ``1000`` (uid), ``scitex:scitex`` or
    ``1000:1000`` (explicit ``user:group``, either form on each side). A bare
    user resolves its group to that user's primary group; a bare numeric uid
    resolves the gid to the same number.

    Resolution happens HERE, at reset time, and any value that cannot be
    resolved raises :class:`HomeStateError` naming the setting and the env var
    to fix. There is deliberately no fallback to ``os.getuid()``: on production
    the reset runs as root, so "whoever is running" is exactly the owner that
    locks the web process out.
    """
    declared = getattr(settings, APP_UNIX_OWNER_SETTING, None)
    if not declared or not str(declared).strip():
        raise HomeStateError(
            f"settings.{APP_UNIX_OWNER_SETTING} is empty; declare the unix identity "
            f"the web process runs as (a user name, a uid, or user:group) via "
            f"{APP_UNIX_OWNER_ENV}. Nothing is chowned until it is set."
        )
    declared = str(declared).strip()
    user_part, _, group_part = declared.partition(":")

    def _uid(token: str) -> tuple[int, int | None]:
        if token.isdigit():
            return int(token), None
        try:
            entry = pwd.getpwnam(token)
        except KeyError as exc:
            raise HomeStateError(
                f"settings.{APP_UNIX_OWNER_SETTING}={declared!r}: user {token!r} does "
                f"not exist on this host. Set {APP_UNIX_OWNER_ENV} to the user name "
                f"or numeric uid the web process actually runs as (on production "
                f"that is `scitex`, uid 1000)."
            ) from exc
        return entry.pw_uid, entry.pw_gid

    def _gid(token: str) -> int:
        if token.isdigit():
            return int(token)
        try:
            return grp.getgrnam(token).gr_gid
        except KeyError as exc:
            raise HomeStateError(
                f"settings.{APP_UNIX_OWNER_SETTING}={declared!r}: group {token!r} does "
                f"not exist on this host. Set {APP_UNIX_OWNER_ENV} to an existing "
                f"user:group or to numeric ids."
            ) from exc

    uid, primary_gid = _uid(user_part)
    if group_part:
        gid = _gid(group_part)
    elif primary_gid is not None:
        gid = primary_gid
    else:
        gid = uid
    return uid, gid


def enforce_app_ownership(home_root: Path) -> None:
    """Hand the freshly materialised tree back to the process that serves it.

    The reset runs inside the visitor Celery worker, which is ROOT, while the
    web process that must later write into this tree is ``scitex`` (uid 1000)
    and compiles IN-PROCESS with no privilege change. Measured on production
    2026-08-17: ``celery_worker_vis`` PID 7 ``Uid: 0 0 0 0``; ``daphne`` PID 7
    ``Uid: 1000 1000 1000 1000``.

    Nothing between the two ever chowned the result. ``initialize_user_workspace``
    calls ``enforce_data_dir_ownership`` at the one instant the tree is nearly
    empty, so only ``proj/`` and ``workspace_info.json`` got an owner; every
    directory created afterwards — the dotfiles repo, the project dir, the whole
    template clone — stayed ``root:root`` 0755. The app could read the tree and
    could not create a single entry in it, so the writer's first write, ``mkdir
    .scitex/``, was EACCES and the demo never compiled:

        mkdir: cannot create directory
        '/app/data/users/visitor-003/proj/dotfiles/.scitex': Permission denied

    Doing this LAST is the point. A chown in the middle is undone by every
    directory created after it, which is exactly the bug being fixed here.

    The owner comes from ``settings.APP_UNIX_OWNER`` (see settings_shared) and
    is resolved to NUMERIC ids first, so the chown never depends on a user name
    existing on the host that happens to run the reset — CI's py3.11 runner had
    no ``scitex`` account and every reset there failed with
    ``chown: invalid user``.

    ``-h`` because the home root holds relative symlinks into ``proj/``; they
    stay inside the tree, so plain ``-R`` is safe today, but ``-h`` removes the
    class of bug rather than the instance.
    """
    uid, gid = resolve_app_owner()
    result = subprocess.run(
        ["chown", "-R", "-h", f"{uid}:{gid}", str(home_root)],
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise HomeStateError(
            f"could not hand {home_root} back to uid {uid}:{gid} "
            f"(settings.{APP_UNIX_OWNER_SETTING}={getattr(settings, APP_UNIX_OWNER_SETTING, None)!r}): "
            f"{result.stderr.decode(errors='replace').strip()}. The slot is "
            f"quarantined rather than served, because a slot the web process "
            f"cannot write to cannot run the demo. If the ids are wrong, set "
            f"{APP_UNIX_OWNER_ENV} to the identity the web process runs as."
        )


def verify_app_can_write(home_root: Path) -> None:
    """Final-gate half that catches an unusable slot BEFORE it is served.

    Deliberately compares ``stat().st_uid`` rather than calling ``os.access``
    or ``Path.is_dir``-style checks. This runs in the ROOT worker, and root
    bypasses DAC — ``os.access(path, os.W_OK)`` returns True for any existing
    path regardless of owner, so a writability check here would pass for
    precisely the broken slot it exists to catch. A check that cannot fail is
    not a check.
    """
    try:
        expected_uid = os.stat(home_root).st_uid
    except OSError as exc:
        raise HomeStateError(f"cannot stat home root {home_root}: {exc}") from exc

    foreign = []
    for path in home_root.rglob("*"):
        try:
            if path.lstat().st_uid != expected_uid:
                foreign.append(str(path.relative_to(home_root)))
        except OSError:
            continue
        if len(foreign) >= 5:
            break

    if foreign:
        raise HomeStateError(
            f"{home_root} still holds entries owned by another uid "
            f"(first few: {foreign!r}); the web process would get EACCES on "
            f"its first write, so this slot must not be served"
        )


def verify_recycled_home(visitor_user: User, home_root: Path) -> None:
    """Filesystem half of the FINAL GATE.

    Asserts: the home root holds EXACTLY the fresh skeleton,
    ``~/.singularity`` is empty (an inherited ``default.sif`` would
    become the next visitor's container image via ``select_container``),
    ``proj/`` holds exactly the fresh clone + dotfiles + metadata, and
    the user_containers dir is gone.
    """
    username = visitor_user.username
    home_root = Path(home_root)

    home_entries = {p.name for p in home_root.iterdir()}
    if home_entries != EXPECTED_HOME_ENTRIES:
        raise HomeStateError(
            f"unexpected home contents for {username}: "
            f"extra={sorted(home_entries - EXPECTED_HOME_ENTRIES)!r} "
            f"missing={sorted(EXPECTED_HOME_ENTRIES - home_entries)!r}"
        )

    sif_residue = [p.name for p in (home_root / ".singularity").iterdir()]
    if sif_residue:
        raise HomeStateError(
            f"~/.singularity not empty for {username}: {sif_residue!r} "
            f"(would become the next visitor's container image)"
        )

    proj_entries = {p.name for p in (home_root / "proj").iterdir()}
    if proj_entries != EXPECTED_PROJ_ENTRIES:
        raise HomeStateError(
            f"unexpected proj contents for {username}: "
            f"extra={sorted(proj_entries - EXPECTED_PROJ_ENTRIES)!r} "
            f"missing={sorted(EXPECTED_PROJ_ENTRIES - proj_entries)!r}"
        )

    container_dir = user_container_dir(visitor_user)
    if container_dir.exists():
        raise HomeStateError(
            f"user_containers dir survived for {username}: {container_dir}"
        )


# EOF
