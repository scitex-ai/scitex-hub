#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An unreadable workspace must say so, not raise a bare EACCES from Path.exists().

``Path.exists()`` swallows ENOENT/ENOTDIR/EBADF/ELOOP but lets EACCES through.
``get_project_filesystem_manager`` called it unguarded, so a data directory the
web process may not traverse produced an uncaught PermissionError three frames
below the view — an HTTP 500 whose body said nothing about ownership or modes.

Measured on production 2026-08-17: one account whose data dir had been chowned
to uid 100000+pk and chmodded 700 returned 500 on Writer, the file tree and git
status, while the other 89 accounts worked. The exception carried only
"[Errno 13] Permission denied: '/app/data/users/demo-reviewer/proj'".

These tests pin the contract that replaced it: a NAMED error carrying the path,
the process uid and the reason. No mocks — a real directory is really made
unreadable, and the tests skip rather than lying if the runner is root, since
root ignores permission bits and the scenario cannot exist there.
"""

import os

import pytest

from apps.infra.project_app.services.project_filesystem.manager import (
    WorkspaceNotAccessibleError,
    get_project_filesystem_manager,
)


@pytest.fixture
def locked_out_user(tmp_path, settings, django_user_model):
    """A real user whose data dir exists but cannot be traversed."""
    # Arrange
    if os.getuid() == 0:
        pytest.skip("running as root — permission bits are not enforced")
    settings.BASE_DIR = str(tmp_path)
    user = django_user_model.objects.create_user(
        username="locked-out", email="locked@example.com", password="x"
    )
    data_root = tmp_path / "data" / "users" / user.username
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "proj").mkdir(exist_ok=True)
    data_root.chmod(0o000)
    # Act
    yield user
    # Assert
    data_root.chmod(0o755)


@pytest.fixture
def raised(locked_out_user):
    """The exception raised when resolving that user's workspace."""
    # Arrange
    user = locked_out_user
    # Act
    with pytest.raises(WorkspaceNotAccessibleError) as caught:
        get_project_filesystem_manager(user)
    # Assert
    return caught.value


class TestUnreadableWorkspaceIsNamed:
    """The failure must identify itself well enough to act on."""

    def test_raises_the_named_error_rather_than_a_bare_permissionerror(
        self, locked_out_user
    ):
        # Arrange
        user = locked_out_user
        # Act
        # Assert
        with pytest.raises(WorkspaceNotAccessibleError):
            get_project_filesystem_manager(user)

    def test_message_names_the_user_whose_workspace_is_unreachable(self, raised):
        """Without it the operator cannot tell WHICH directory to fix."""
        # Arrange
        expected = "locked-out"
        # Act
        message = str(raised)
        # Assert
        assert expected in message

    def test_message_names_the_process_uid(self, raised):
        """The uid mismatch IS the bug, so our uid has to be in the message."""
        # Arrange
        expected = f"uid {os.getuid()}"
        # Act
        message = str(raised)
        # Assert
        assert expected in message

    def test_message_points_at_the_function_that_sets_the_ownership(self, raised):
        """Name the cause, so the reader does not have to hunt for it."""
        # Arrange
        expected = "enforce_data_dir_ownership"
        # Act
        message = str(raised)
        # Assert
        assert expected in message

    def test_error_is_an_oserror_so_existing_handlers_still_catch_it(self, raised):
        """Narrowing the type must not slip past callers catching OSError."""
        # Arrange
        expected_base = OSError
        # Act
        actual = raised
        # Assert
        assert isinstance(actual, expected_base)


# EOF
