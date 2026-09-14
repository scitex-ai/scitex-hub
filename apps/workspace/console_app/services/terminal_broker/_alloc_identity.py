"""Run an allocation as its hub user instead of root (see services/compute_user)."""

from __future__ import annotations

import logging

from ..compute_user import (
    broker_is_root,
    compute_home,
    foreign_user_data_binds,
    job_scratch_dir,
)

logger = logging.getLogger(__name__)


def adopt_compute_identity(alloc) -> None:
    """Give a root broker's allocation the user's uid/gid, home and scratch.

    A non-root broker cannot submit as another user, so it keeps the
    legacy paths it was handed.
    """
    if alloc.uid is None:
        if not broker_is_root():
            return
        from ..compute_identity import compute_identity_for_username

        identity = compute_identity_for_username(alloc.username)
        alloc.uid, alloc.gid = identity.uid, identity.gid
    home = compute_home(alloc.username)
    alloc.host_user_dir = home
    alloc.host_project_dir = home / "proj" / alloc.project_slug
    alloc.scratch_dir = job_scratch_dir(alloc.username, alloc.allocation_id)


def foreign_bind_error(alloc, script: str) -> str:
    if alloc.uid is None:
        return ""
    foreign = foreign_user_data_binds(script, alloc.username)
    if not foreign:
        return ""
    return f"Refusing to start: binds outside {alloc.username}'s home: {foreign}"
