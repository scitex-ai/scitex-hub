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

import logging
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
