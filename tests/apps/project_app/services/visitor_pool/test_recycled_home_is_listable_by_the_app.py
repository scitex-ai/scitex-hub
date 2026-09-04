#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A recycled visitor home must be LISTABLE by the app, not merely owned by it.

THE DEFECT, MEASURED ON PRODUCTION 2026-08-16
---------------------------------------------
A wiped visitor slot came back mode 0700 and the app (uid 1000) could not list
it::

    drwx------ 2 100001 100001  /app/data/users/visitor-001   <- 0700, EMPTY
    drwxr-xr-x 5 100002 100002  /app/data/users/visitor-002   <- 0755, populated
    drwxr-xr-x 5 100004 100004  /app/data/users/visitor-003   <- 0755, populated

Note what the three rows do NOT differ on: all three are owned by a foreign
uid, and two of them worked. Ownership was never the discriminator — the
``o+rx`` bits were. So the property to hold is "the app's identity can list
it", and mode 0755 is one mechanism for it, not the property itself. These
tests therefore assert through :func:`dir_is_traversable_by`, which resolves
the POSIX owner/group/other class the app would actually land in.

WHY IT WAS A P2 AND NOT A ONE-SLOT ANNOYANCE. ``check_user_data_permissions``
walks every directory under ``data/users`` and marks the WHOLE check unhealthy
on a single ``PermissionError``; the aggregate turns that into a site-wide
warning, which the header renders as "Server: partial" for every visitor,
anonymous ones included. One slot in a bad mode degraded a site-wide badge for
days, with nothing connecting the two.

THE TRAP THIS SUITE IS BUILT AROUND
-----------------------------------
ROOT CAN LIST A 0700 DIRECTORY. The card's author probed production with
``docker exec`` — which lands as uid 0 — and got BROKEN=[] while the API kept
reporting 1. Any check that consults the CALLER's privilege (``os.access``,
``Path.iterdir`` in a root worker) reports clean over a live fault, and the
reset itself runs as root in ``celery_worker_vis``. That is why the assertions
below go through a DAC-only predicate with no root bypass rather than through
"can this process list it", and why
``TestThePredicateItselfDiscriminates`` exists: a predicate that answered True
for everything would make every other test here green.

The end-to-end RED must be CONSTRUCTED, not provoked. Reproducing the
production path needs root: ``enforce_data_dir_ownership`` chowns to
``100000 + pk`` with ``check=True`` before it chmods, and that chown fails for
an unprivileged test (``chown: changing ownership: Invalid argument``,
measured), so line never reaches the chmod. Constructing mode 0700 directly is
the honest form of the same state.
"""

import os
import stat
from pathlib import Path

import pytest
from django.test import override_settings

from apps.infra.project_app.services.visitor_pool.home_access import (
    APP_TRAVERSABLE_DIR_MODE,
    dir_is_traversable_by,
    enforce_app_ownership,
    leave_home_root_listable,
    verify_app_can_write,
)
from apps.infra.project_app.services.visitor_pool.home_state import HomeStateError
from apps.infra.project_app.services.visitor_pool.workspace_wipe import (
    _add_owner_rwx,
    wipe_directory_contents,
)

DEFECT = (
    "a wiped visitor home root came back mode 0700, so the app uid could not "
    "list it and the site-wide health badge read 'partial' for every visitor"
)

APP_IDENTITY = f"{os.getuid()}:{os.getgid()}"

# An identity that owns nothing this test creates. Unprivileged tests cannot
# make the DIRECTORY foreign-owned — ``chown 100001`` fails with "Invalid
# argument" — so the OBSERVER is made foreign instead. Same POSIX class
# ("other"), same predicate, and it is exactly the class the app landed in on
# production, where the home root was owned by 100001 and the app is uid 1000.
FOREIGN_UID = os.getuid() + 54321
FOREIGN_GID = os.getgid() + 54321


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _app_can_list(path: Path) -> bool:
    """THE ORACLE, and the one place this file can go quietly useless.

    It must NOT be ``dir_is_traversable_by(path, os.getuid(), os.getgid())``.
    A test process OWNS the directories it creates, and 0700 grants the owner
    r-x, so that spelling answers True for the exact production state
    (``drwx------``) and every assertion below turns green over a live fault.
    Measured while writing this file: with that spelling, two tests passed
    against deliberately un-fixed code, one of which was hiding a fix I had
    not actually applied to ``force_rmtree``.

    It is the same shape as the trap the card records — ``docker exec`` lands
    as uid 0, root ignores DAC, and the probe reports clean. Whoever the
    checker is must not be privileged with respect to what it checks.
    """
    return dir_is_traversable_by(path, FOREIGN_UID, FOREIGN_GID)


@pytest.fixture
def visitor_home(tmp_path):
    """A visitor home root holding the entries a real one holds.

    The dotfile SYMLINKS matter: they are what makes ``force_rmtree``'s
    file branch — the branch that chmods the wiped directory's PARENT —
    run against real entries of the home root during a wipe.
    """
    # Arrange
    root = tmp_path / "data" / "users" / "visitor-001"
    (root / "proj" / "dotfiles").mkdir(parents=True)
    (root / ".singularity").mkdir()
    (root / "proj" / "dotfiles" / "bashrc").write_text("# bashrc\n")
    (root / ".bashrc").symlink_to("proj/dotfiles/bashrc")
    os.chmod(root, APP_TRAVERSABLE_DIR_MODE)
    # Act
    yield root
    # Assert
    # Restore a removable mode. Tests here deliberately leave the tree at 0700
    # / 0555 / 0055, and pytest's tmp_path cleaner cannot rmtree those — it
    # warns and leaks the directory into /uvwork/tmp for every run.
    if root.exists():
        os.chmod(root, APP_TRAVERSABLE_DIR_MODE)
        for entry in root.iterdir():
            if entry.is_dir() and not entry.is_symlink():
                os.chmod(entry, APP_TRAVERSABLE_DIR_MODE)


@pytest.fixture
def unlistable_visitor_home(visitor_home):
    """THE CONSTRUCTED RED: the exact mode production came back at."""
    # Arrange
    visitor_home.chmod(0o700)
    # Act
    assert _mode(visitor_home) == 0o700
    # Assert
    return visitor_home


@pytest.fixture
def read_only_visitor_home(visitor_home):
    """A home root whose entries cannot be unlinked without a chmod first.

    This is what sends ``force_rmtree`` down the branch that chmods the
    entry's PARENT — the home root itself.
    """
    # Arrange
    visitor_home.chmod(0o555)
    # Act
    return visitor_home
    # Assert


class TestThePredicateItselfDiscriminates:
    """POSITIVE + NEGATIVE control for the oracle every other test leans on.

    Without these, a predicate stuck at True would make this whole file green
    while asserting nothing — the failure mode the repo's guards marker exists
    to catch.
    """

    @pytest.mark.guards(defect=DEFECT)
    def test_a_0755_directory_is_listable_by_a_foreign_identity(self, visitor_home):
        """visitor-003 on production: foreign owner, o+rx, and it worked."""
        # Arrange
        target = visitor_home
        # Act
        listable = dir_is_traversable_by(target, FOREIGN_UID, FOREIGN_GID)
        # Assert
        assert listable is True

    @pytest.mark.guards(defect=DEFECT)
    def test_a_0700_directory_is_not_listable_by_a_foreign_identity(
        self, unlistable_visitor_home
    ):
        """visitor-001 on production: drwx------ owned by 100001, app is 1000."""
        # Arrange
        target = unlistable_visitor_home
        # Act
        listable = dir_is_traversable_by(target, FOREIGN_UID, FOREIGN_GID)
        # Assert
        assert listable is False

    @pytest.mark.guards(defect=DEFECT)
    def test_a_0700_directory_is_still_listable_by_its_own_owner(
        self, unlistable_visitor_home
    ):
        """Pins the reason ``_app_can_list`` uses a FOREIGN identity.

        This is the true statement that makes the naive oracle useless: the
        same 0700 directory that locked production out is perfectly listable
        by the uid that owns it. A test process owns everything it creates,
        so an owner-keyed predicate can never see the defect.
        """
        # Arrange
        target = unlistable_visitor_home
        # Act
        listable = dir_is_traversable_by(target, os.getuid(), os.getgid())
        # Assert
        assert listable is True

    @pytest.mark.guards(defect=DEFECT)
    def test_owner_bits_win_over_wider_other_bits(self, visitor_home):
        """POSIX matches the FIRST class, so o+rx cannot rescue the owner.

        Mode 0055 grants everyone but the owner. A predicate written as a
        mask over the whole mode would call this listable for the owner; the
        real one must not, or the gate would pass a slot the app owns and
        cannot read.
        """
        # Arrange
        visitor_home.chmod(0o055)
        # Act
        listable = dir_is_traversable_by(visitor_home, os.getuid(), os.getgid())
        # Assert
        assert listable is False


class TestTheWipeDoesNotNarrowTheHomeRoot:
    """``force_rmtree``'s permission recovery used to ASSIGN 0700 to the
    wiped directory's parent — which, for every direct entry of a visitor
    home, IS the home root — and nothing ever restored it."""

    @pytest.mark.guards(defect=DEFECT)
    def test_home_root_is_still_listable_after_a_wipe(self, visitor_home):
        # Arrange
        target = visitor_home
        # Act
        wipe_directory_contents(target)
        # Assert
        assert _app_can_list(target) is True

    @pytest.mark.guards(defect=DEFECT)
    def test_a_wipe_that_hits_the_parent_chmod_recovery_leaves_it_listable(
        self, read_only_visitor_home
    ):
        """THE PRODUCTION MECHANISM, driven end to end.

        ``force_rmtree``'s file branch retries a failed ``unlink`` by chmodding
        ``path.parent`` — and for every DIRECT entry of a visitor home, the
        parent IS the home root. A home root that is not writable makes the
        first ``unlink`` fail, so the branch fires on the ``.bashrc`` symlink
        and the old code assigned the home root 0700 with nothing to restore
        it. The wipe then reports success and the slot is left unreadable.
        """
        # Arrange
        target = read_only_visitor_home
        # Act
        wipe_directory_contents(target)
        # Assert
        assert _app_can_list(target) is True

    @pytest.mark.guards(defect=DEFECT)
    def test_a_directory_entry_is_removable_when_it_is_iterated_first(self, tmp_path):
        """THE ORDER-DEPENDENT FAILURE, made deterministic.

        ``wipe_directory_contents`` iterates the home root in the filesystem's
        own order. When a DIRECTORY entry comes before any file entry, nothing
        has widened the read-only root yet, and rmdir needs write on the
        parent just as unlink does. ``force_rmtree``'s directory branch used to
        widen only the tree below the directory, so its retry hit the same
        EACCES and the wipe failed — but only on filesystems (and tmp names)
        whose hash order put the directory first. CI flickered per leg for
        two days and then went red on every leg. A home root holding ONLY a
        directory removes the order from the equation: this test is red on the
        old code on every filesystem.
        """
        # Arrange
        root = tmp_path / "data" / "users" / "visitor-001"
        (root / "proj" / "dotfiles").mkdir(parents=True)
        (root / "proj" / "dotfiles" / "bashrc").write_text("# bashrc\n")
        os.chmod(root, 0o555)
        try:
            # Act
            wipe_directory_contents(root)
            # Assert
            assert list(root.iterdir()) == []
            assert _app_can_list(root) is True
        finally:
            os.chmod(root, APP_TRAVERSABLE_DIR_MODE)

    @pytest.mark.guards(defect=DEFECT)
    def test_that_wipe_still_empties_the_directory(self, read_only_visitor_home):
        """The widening must not have been bought by skipping the removal."""
        # Arrange
        target = read_only_visitor_home
        # Act
        wipe_directory_contents(target)
        # Assert
        assert list(target.iterdir()) == []

    @pytest.mark.guards(defect=DEFECT)
    def test_the_recovery_helper_adds_owner_write_without_dropping_other_bits(
        self, visitor_home
    ):
        """The shared helper both recovery branches now go through.

        Asserted directly because it is the whole contract: the old form
        (``os.chmod(path, stat.S_IRWXU)``) granted u+rwx AND silently stripped
        ``go``, and nothing downstream put those bits back.
        """
        # Arrange
        visitor_home.chmod(0o555)
        # Act
        _add_owner_rwx(visitor_home)
        # Assert
        assert _mode(visitor_home) == 0o755

    @pytest.mark.guards(defect=DEFECT)
    def test_a_read_only_subtree_is_still_removed(self, visitor_home):
        """The recovery must still do its job: a read-only file inside a
        read-only directory is the failure mode it was written for
        (production's ``revision.tex``)."""
        # Arrange
        locked = visitor_home / "locked"
        locked.mkdir()
        (locked / "revision.tex").write_text("% read only\n")
        (locked / "revision.tex").chmod(0o444)
        locked.chmod(0o500)
        # Act
        wipe_directory_contents(visitor_home)
        # Assert
        assert locked.exists() is False


class TestTheHandBackPinsTheModeExplicitly:
    """``enforce_app_ownership`` chowned and left the mode to chance."""

    @pytest.mark.guards(defect=DEFECT)
    def test_a_0700_home_root_is_listable_after_the_hand_back(
        self, unlistable_visitor_home
    ):
        # Arrange
        target = unlistable_visitor_home
        # Act
        with override_settings(APP_UNIX_OWNER=APP_IDENTITY):
            enforce_app_ownership(target)
        # Assert
        assert _app_can_list(target) is True

    @pytest.mark.guards(defect=DEFECT)
    def test_the_hand_back_does_not_depend_on_the_callers_umask(
        self, unlistable_visitor_home
    ):
        """``os.makedirs(mode=)`` is masked by umask; ``os.chmod`` is not.

        Measured on this interpreter: ``makedirs(mode=0o755)`` yields 0700
        under umask 0077 — the card's exact mode. A umask this hostile is what
        would defeat a mode= argument, so the hand-back is run under it.
        """
        # Arrange
        previous = os.umask(0o077)
        # Act
        try:
            with override_settings(APP_UNIX_OWNER=APP_IDENTITY):
                enforce_app_ownership(unlistable_visitor_home)
        finally:
            os.umask(previous)
        # Assert
        assert _mode(unlistable_visitor_home) == APP_TRAVERSABLE_DIR_MODE


@pytest.fixture
def gate_error_for_unlistable_root(unlistable_visitor_home):
    """The gate's refusal of a 0700 home root, as seen by a foreign app uid."""
    # Arrange
    foreign_owner = f"{os.getuid() + 54321}:{os.getgid() + 54321}"
    # Act
    with override_settings(APP_UNIX_OWNER=foreign_owner):
        with pytest.raises(HomeStateError) as caught:
            verify_app_can_write(unlistable_visitor_home)
    # Assert
    return caught.value


@pytest.fixture
def gate_error_for_unlistable_subdir(visitor_home):
    """The gate's refusal when only ``proj/`` is unlistable."""
    # Arrange
    (visitor_home / "proj").chmod(0o700)
    foreign_owner = f"{os.getuid() + 54321}:{os.getgid() + 54321}"
    # Act
    with override_settings(APP_UNIX_OWNER=foreign_owner):
        with pytest.raises(HomeStateError) as caught:
            verify_app_can_write(visitor_home)
    # Assert
    return caught.value


class TestTheGateRefusesAnUnlistableSlot:
    """The final gate read ``st_uid`` only and never looked at the mode, so
    the broken slot passed as verified-clean and was served."""

    @pytest.mark.guards(defect=DEFECT)
    def test_an_unlistable_home_root_fails_the_gate(self, unlistable_visitor_home):
        # Arrange
        foreign_owner = f"{os.getuid() + 54321}:{os.getgid() + 54321}"
        # Act
        # Assert
        with override_settings(APP_UNIX_OWNER=foreign_owner):
            with pytest.raises(HomeStateError):
                verify_app_can_write(unlistable_visitor_home)

    @pytest.mark.guards(defect=DEFECT)
    def test_the_gate_error_says_the_slot_is_not_listable(
        self, gate_error_for_unlistable_root
    ):
        # Arrange
        expected = "not listable"
        # Act
        message = str(gate_error_for_unlistable_root)
        # Assert
        assert expected in message

    @pytest.mark.guards(defect=DEFECT)
    def test_the_gate_error_names_the_offending_mode(
        self, gate_error_for_unlistable_root
    ):
        # Arrange
        expected = "0700"
        # Act
        message = str(gate_error_for_unlistable_root)
        # Assert
        assert expected in message

    @pytest.mark.guards(defect=DEFECT)
    def test_an_unlistable_subdirectory_also_fails_the_gate(
        self, gate_error_for_unlistable_subdir
    ):
        """The health check walks one level down too, so proj/ counts."""
        # Arrange
        expected = "proj"
        # Act
        message = str(gate_error_for_unlistable_subdir)
        # Assert
        assert expected in message

    @pytest.mark.guards(defect=DEFECT)
    def test_a_listable_slot_still_passes(self, visitor_home):
        """POSITIVE CONTROL: the gate must not reject everything."""
        # Arrange
        target = visitor_home
        # Act
        with override_settings(APP_UNIX_OWNER=APP_IDENTITY):
            result = verify_app_can_write(target)
        # Assert
        assert result is None


class TestAQuarantinedSlotDoesNotDegradeTheWholeSite:
    """One broken slot should cost one slot, not the site-wide badge."""

    @pytest.mark.guards(defect=DEFECT)
    def test_a_failed_reset_leaves_the_home_root_listable(
        self, unlistable_visitor_home
    ):
        # Arrange
        target = unlistable_visitor_home
        # Act
        leave_home_root_listable(target)
        # Assert
        assert _app_can_list(target) is True

    @pytest.mark.guards(defect=DEFECT)
    def test_the_repair_reports_that_it_succeeded(self, unlistable_visitor_home):
        # Arrange
        target = unlistable_visitor_home
        # Act
        repaired = leave_home_root_listable(target)
        # Assert
        assert repaired is True

    @pytest.mark.guards(defect=DEFECT)
    def test_it_widens_rather_than_replaces_the_mode(self, visitor_home):
        """Group-write must survive: a repair that narrows is the bug again."""
        # Arrange
        visitor_home.chmod(0o770)
        # Act
        leave_home_root_listable(visitor_home)
        # Assert
        assert _mode(visitor_home) == 0o775

    @pytest.mark.guards(defect=DEFECT)
    def test_a_missing_home_root_is_reported_not_crashed_on(self, tmp_path):
        """This runs on a path already reporting an error; it must not raise
        a second one over the first and hide the real cause."""
        # Arrange
        absent = tmp_path / "no-such-visitor"
        # Act
        repaired = leave_home_root_listable(absent)
        # Assert
        assert repaired is False


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])

# EOF
