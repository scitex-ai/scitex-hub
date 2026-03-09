"""
DataStore permission checker.

Enforces access control modes for AppData records:
  - owner_only: only the record owner may read/write
  - owner_and_collaborators: owner + project collaborators may read/write
  - project_read: any project member may read; only owner may write
  - public_read: anyone may read; only owner may write
"""

from typing import Literal

from apps.infra.platform_app.models.app_data import AppData

AccessMode = Literal[
    "owner_only",
    "owner_and_collaborators",
    "project_read",
    "public_read",
]

VALID_MODES = {"owner_only", "owner_and_collaborators", "project_read", "public_read"}


class PermissionDeniedError(PermissionError):
    """Raised when an operation is not permitted under the configured access mode."""


def check_read(record: AppData, user, mode: AccessMode) -> None:
    """
    Assert that *user* may read *record* under *mode*.

    Raises:
        PermissionDeniedError: if access is denied.
        ValueError: if *mode* is not a recognised access mode.
    """
    _validate_mode(mode)

    if mode == "public_read":
        return  # Everyone may read

    if mode == "project_read":
        if _is_project_member(record, user):
            return
        raise PermissionDeniedError(
            f"User '{user}' is not a member of the project and cannot read this record."
        )

    if mode in ("owner_only", "owner_and_collaborators"):
        if _is_owner(record, user):
            return
        if mode == "owner_and_collaborators" and _is_collaborator(record, user):
            return
        raise PermissionDeniedError(
            f"User '{user}' does not have read access to this record."
        )


def check_write(record: AppData, user, mode: AccessMode) -> None:
    """
    Assert that *user* may write (update/delete) *record* under *mode*.

    Raises:
        PermissionDeniedError: if access is denied.
        ValueError: if *mode* is not a recognised access mode.
    """
    _validate_mode(mode)

    # Write is always restricted to owner regardless of mode
    if not _is_owner(record, user):
        if mode == "owner_and_collaborators" and _is_collaborator(record, user):
            return
        raise PermissionDeniedError(
            f"User '{user}' does not have write access to this record."
        )


def check_create(project, owner, user, mode: AccessMode) -> None:
    """
    Assert that *user* may create a new record in *project* under *mode*.

    Args:
        project: The Project instance the record will belong to.
        owner: The intended owner of the new record.
        user: The requesting user.
        mode: The access mode from the schema manifest.

    Raises:
        PermissionDeniedError: if access is denied.
    """
    _validate_mode(mode)

    if user != owner:
        raise PermissionDeniedError(
            f"User '{user}' cannot create records on behalf of '{owner}'."
        )

    if mode == "owner_only":
        # Only project members who are the owner; ownership is enforced above
        return

    if not _is_project_member_by_project(project, user):
        raise PermissionDeniedError(
            f"User '{user}' is not a member of the project and cannot create records."
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_mode(mode: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError(
            f"Unknown access mode '{mode}'. Valid modes: {sorted(VALID_MODES)}."
        )


def _is_owner(record: AppData, user) -> bool:
    return record.owner_id == user.pk


def _is_project_member(record: AppData, user) -> bool:
    return _is_project_member_by_project(record.project, user)


def _is_project_member_by_project(project, user) -> bool:
    """Return True if user is the project owner or a collaborator."""
    if project.owner_id == user.pk:
        return True
    # Project model uses a ManyToMany collaborators field (standard pattern)
    return project.collaborators.filter(pk=user.pk).exists()


def _is_collaborator(record: AppData, user) -> bool:
    return _is_project_member_by_project(record.project, user) and not _is_owner(
        record, user
    )
