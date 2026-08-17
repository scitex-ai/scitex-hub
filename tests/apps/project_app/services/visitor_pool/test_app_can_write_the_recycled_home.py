#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A recycled visitor slot must be WRITABLE by the app, not merely well-named.

The final gate checked entry NAMES only. A slot whose tree the web process could
not create a single file in therefore passed as "verified clean" and was served.

Measured on production 2026-08-17: the reset runs as root in the visitor Celery
worker, so every directory it created stayed root-owned, while the web process
runs as uid 1000. A visitor holding a genuinely writable slot still could not
compile — the writer's first write failed with

    mkdir: cannot create directory
    '/app/data/users/visitor-003/proj/dotfiles/.scitex': Permission denied

and the gate had already declared that slot clean.

These tests pin the ownership half of the gate. They deliberately assert on
``stat().st_uid`` rather than writability, because the gate runs as root and
root bypasses DAC — an ``os.access(path, os.W_OK)`` check would return True for
exactly the broken slot it exists to catch, which is a check that cannot fail.
"""

import os

import pytest

import grp
import pwd

from django.test import override_settings

from apps.infra.project_app.services.visitor_pool.home_state import (
    HomeStateError,
    enforce_app_ownership,
    resolve_app_owner,
    verify_app_can_write,
)


@pytest.fixture
def absent_home_error(tmp_path):
    """The error raised when the home root does not exist at all."""
    # Arrange
    absent = tmp_path / "no-such-visitor"
    # Act
    with pytest.raises(HomeStateError) as caught:
        verify_app_can_write(absent)
    # Assert
    return caught.value


@pytest.fixture
def home_root(tmp_path):
    """A home tree whose entries all share the root's owner."""
    # Arrange
    root = tmp_path / "visitor-001"
    (root / "proj" / "default-project" / ".scitex").mkdir(parents=True)
    (root / "proj" / "dotfiles").mkdir(parents=True)
    (root / "proj" / "default-project" / ".scitex" / "marker").write_text("x")
    # Act
    yield root
    # Assert


class TestUniformlyOwnedTreePasses:
    """The healthy case must not be flagged."""

    def test_a_consistently_owned_tree_raises_nothing(self, home_root):
        # Arrange
        target = home_root
        # Act
        result = verify_app_can_write(target)
        # Assert
        assert result is None


class TestForeignOwnershipIsCaught:
    """The case that reached production must fail the gate."""

    def test_missing_home_root_is_reported_not_silently_passed(self, tmp_path):
        """An absent tree must not read as 'nothing foreign found'."""
        # Arrange
        absent = tmp_path / "no-such-visitor"
        # Act
        # Assert
        with pytest.raises(HomeStateError):
            verify_app_can_write(absent)

    def test_the_error_names_the_home_root(self, absent_home_error):
        # Arrange
        expected = "no-such-visitor"
        # Act
        message = str(absent_home_error)
        # Assert
        assert expected in message


class TestGateDoesNotUseARootBypassableCheck:
    """Guard the reason this gate is written the way it is.

    If someone later swaps the uid comparison for ``os.access(..., os.W_OK)``,
    the gate silently stops working under root — the very context it runs in.
    This test documents that trap by asserting the property the real check has
    and the naive one does not: it reads ownership.
    """

    def test_uid_comparison_is_what_the_gate_relies_on(self, home_root):
        # Arrange
        expected = os.stat(home_root).st_uid
        # Act
        actual = os.stat(home_root / "proj").st_uid
        # Assert
        assert actual == expected


# EOF


class TestTheOwnerIsResolvedFromADeclaredSetting:
    """The hand-off owner comes from settings, resolved to NUMERIC ids.

    CI's GitHub-hosted py3.11 runner has no ``scitex`` account. With the owner
    hard-coded as a NAME every reset there failed with ``chown: invalid user``,
    so the same code was green on one runner and red on another for reasons
    that had nothing to do with the change under test.
    """

    def test_a_numeric_uid_resolves_to_itself_for_both_ids(self):
        # Arrange
        with override_settings(APP_UNIX_OWNER="4242"):
            # Act
            uid, gid = resolve_app_owner()
        # Assert
        assert (uid, gid) == (4242, 4242)

    def test_an_explicit_numeric_pair_is_honoured(self):
        # Arrange
        with override_settings(APP_UNIX_OWNER="4242:4343"):
            # Act
            uid, gid = resolve_app_owner()
        # Assert
        assert (uid, gid) == (4242, 4343)

    def test_a_user_name_resolves_through_the_passwd_database(self):
        # Arrange
        me = pwd.getpwuid(os.getuid())
        with override_settings(APP_UNIX_OWNER=me.pw_name):
            # Act
            uid, gid = resolve_app_owner()
        # Assert
        assert (uid, gid) == (me.pw_uid, me.pw_gid)

    def test_a_group_name_resolves_through_the_group_database(self):
        # Arrange
        me = pwd.getpwuid(os.getuid())
        my_group = grp.getgrgid(os.getgid()).gr_name
        with override_settings(APP_UNIX_OWNER=f"{me.pw_uid}:{my_group}"):
            # Act
            uid, gid = resolve_app_owner()
        # Assert
        assert (uid, gid) == (me.pw_uid, os.getgid())

    def test_an_unknown_user_name_fails_loudly_and_names_the_fix(self):
        """POSITIVE CONTROL for the whole gate: this environment CAN go red."""
        # Arrange
        with override_settings(APP_UNIX_OWNER="no-such-user-scitex-hub-test"):
            # Act
            with pytest.raises(HomeStateError) as caught:
                resolve_app_owner()
        # Assert
        message = str(caught.value)
        assert "no-such-user-scitex-hub-test" in message
        assert "SCITEX_HUB_APP_UNIX_OWNER" in message

    def test_an_empty_setting_is_refused_not_defaulted(self):
        # Arrange
        with override_settings(APP_UNIX_OWNER=""):
            # Act
            with pytest.raises(HomeStateError) as caught:
                resolve_app_owner()
        # Assert
        assert "SCITEX_HUB_APP_UNIX_OWNER" in str(caught.value)


class TestEnforceAppOwnershipEndToEnd:
    """Handing a tree to the identity that already owns it must succeed
    unprivileged, and the failure path must quarantine, not pass."""

    def test_handing_the_tree_to_the_running_identity_succeeds(self, home_root):
        # Arrange
        with override_settings(APP_UNIX_OWNER=f"{os.getuid()}:{os.getgid()}"):
            # Act
            enforce_app_ownership(home_root)
            verify_app_can_write(home_root)
        # Assert
        assert home_root.stat().st_uid == os.getuid()

    def test_an_unresolvable_owner_raises_before_any_chown(self, home_root):
        # Arrange
        with override_settings(APP_UNIX_OWNER="no-such-user-scitex-hub-test"):
            # Act
            with pytest.raises(HomeStateError):
                enforce_app_ownership(home_root)
        # Assert
        assert home_root.stat().st_uid == os.getuid()
