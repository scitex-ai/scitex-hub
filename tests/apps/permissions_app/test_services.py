#!/usr/bin/env python3
"""PermissionService: the role hierarchy that decides who may do what.

Card hub-528-python-test-files-are-placeholder-scaffolds-...-20260811, first
burn-down unit.

WHY THIS FILE FIRST. Measured 2026-08-11: all 6 test files in permissions_app
were placeholder scaffolds — a `TestPlaceholder` class with one passing test and
the source pasted underneath as a comment. So the app whose entire job is
authorisation had ZERO executing assertions, while the operator's standing
mandate is tenant isolation. 100% placeholder was the highest ratio in the
codebase, and the app is small enough to cover properly in one pass.

WHAT A REGRESSION HERE LOOKS LIKE: not a crash. A role comparison flipped by one
step is silent privilege escalation — a Reporter who can write, a Maintainer who
can transfer ownership. Nothing fails; the wrong person is simply allowed. That
is why these assert the BOUNDARIES between adjacent roles rather than sampling
one role in the middle.

`PermissionService` is documented as "single source of truth for all
authorization decisions", so these tests are written against that claim: every
public verb, and every rung of ROLE_HIERARCHY, is exercised at the step where it
changes answer.

No mocks — real User, Project and ProjectMember rows. One assertion per test
(STX-TQ007).
"""

import pytest
from django.contrib.auth.models import User

from apps.infra.permissions_app.models import ProjectMember, Role
from apps.infra.permissions_app.services import PermissionService
from apps.infra.project_app.models import Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="perm-owner", password="x")


@pytest.fixture
def other():
    return User.objects.create_user(username="perm-other", password="x")


@pytest.fixture
def project(owner):
    return Project.objects.create(
        name="perm-proj",
        slug="perm-proj",
        description="permission service coverage",
        owner=owner,
    )


def _member(project, user, role, **kwargs):
    return ProjectMember.objects.create(
        project=project, user=user, role=role, **kwargs
    )


# ── role resolution ──────────────────────────────────────────────────────────


def test_the_owner_resolves_as_owner_without_any_member_row(owner, project):
    """POSITIVE CONTROL for the whole file, and a real rule.

    The owner is never a ProjectMember — ownership comes from `project.owner`.
    If this fails, the fixtures are wrong and every assertion below is testing
    nothing, which is the failure mode this card exists to name.
    """
    # Arrange
    user = owner
    # Act
    role = PermissionService.get_user_role(user, project)
    # Assert
    assert role == Role.OWNER


def test_a_stranger_has_no_role(other, project):
    """A user with no membership must resolve to None, not to a default role."""
    # Arrange
    user = other
    # Act
    role = PermissionService.get_user_role(user, project)
    # Assert
    assert role is None


def test_a_deactivated_member_has_no_role(other, project):
    """`is_active=False` must revoke, not merely annotate.

    Removing a collaborator sets this flag. If the lookup ignored it, a removed
    member would keep their permissions — a revocation that does not revoke.
    """
    # Arrange
    _member(project, other, Role.DEVELOPER, is_active=False)
    # Act
    role = PermissionService.get_user_role(other, project)
    # Assert
    assert role is None


# ── read: the lowest rung ────────────────────────────────────────────────────


def test_a_guest_can_read(other, project):
    """Guest is the floor: it grants read and nothing else."""
    # Arrange
    _member(project, other, Role.GUEST)
    # Act
    allowed = PermissionService.can_read(other, project)
    # Assert
    assert allowed


def test_a_stranger_cannot_read(other, project):
    """No membership means no read — the boundary of the project."""
    # Arrange
    user = other
    # Act
    allowed = PermissionService.can_read(user, project)
    # Assert
    assert not allowed


# ── write: the guest/reporter → developer boundary ───────────────────────────


def test_a_reporter_cannot_write(other, project):
    """REPORTER is the last role below the write line."""
    # Arrange
    _member(project, other, Role.REPORTER)
    # Act
    allowed = PermissionService.can_write(other, project)
    # Assert
    assert not allowed


def test_a_developer_can_write(other, project):
    """DEVELOPER is the first role above it. This pair IS the boundary."""
    # Arrange
    _member(project, other, Role.DEVELOPER)
    # Act
    allowed = PermissionService.can_write(other, project)
    # Assert
    assert allowed


def test_a_module_override_can_revoke_write_from_a_developer(other, project):
    """Per-module flags override the role, downward.

    `can_edit_<module>=False` on a member who would otherwise pass. The override
    is the reason `can_write` takes a `module` argument at all, and it is the
    part most likely to be dropped in a refactor because most callers omit it.
    """
    # Arrange
    _member(project, other, Role.DEVELOPER, can_edit_writer=False)
    # Act
    allowed = PermissionService.can_write(other, project, module="writer")
    # Assert
    assert not allowed


def test_an_unset_module_override_falls_back_to_the_role(other, project):
    """NULL means "use the role default" — three-valued, not False.

    The field is `null=True`, so None must NOT be read as a denial. Collapsing
    unknown into False here would silently strip write from every member who
    never had a per-module flag set, which is almost all of them.
    """
    # Arrange
    _member(project, other, Role.DEVELOPER)  # can_edit_writer stays NULL
    # Act
    allowed = PermissionService.can_write(other, project, module="writer")
    # Assert
    assert allowed


# ── delete / manage / invite: the developer → maintainer boundary ────────────


def test_a_developer_cannot_delete(other, project):
    """Writing is not deleting. DEVELOPER stops below destructive actions."""
    # Arrange
    _member(project, other, Role.DEVELOPER)
    # Act
    allowed = PermissionService.can_delete(other, project)
    # Assert
    assert not allowed


def test_a_maintainer_can_delete(other, project):
    """MAINTAINER is the first destructive role."""
    # Arrange
    _member(project, other, Role.MAINTAINER)
    # Act
    allowed = PermissionService.can_delete(other, project)
    # Assert
    assert allowed


def test_a_developer_cannot_invite(other, project):
    """Inviting grants access to others — it belongs above the write line."""
    # Arrange
    _member(project, other, Role.DEVELOPER)
    # Act
    allowed = PermissionService.can_invite(other, project)
    # Assert
    assert not allowed


# ── admin: owner-only, and NOT reachable by role ─────────────────────────────


def test_a_maintainer_cannot_admin(other, project):
    """THE ESCALATION BOUNDARY THAT MATTERS MOST.

    `can_admin` gates deleting the project and transferring ownership, and it is
    the one verb that ignores ROLE_HIERARCHY entirely — it compares
    `project.owner == user`. A refactor that "tidied" it into a hierarchy check
    would hand the highest non-owner role the ability to take the project.
    """
    # Arrange
    _member(project, other, Role.MAINTAINER)
    # Act
    allowed = PermissionService.can_admin(other, project)
    # Assert
    assert not allowed


def test_the_owner_can_admin(owner, project):
    """The positive half of that boundary."""
    # Arrange
    user = owner
    # Act
    allowed = PermissionService.can_admin(user, project)
    # Assert
    assert allowed


# ── compile: the guest → reporter boundary ───────────────────────────────────


def test_a_guest_cannot_compile(other, project):
    """GUEST is below the compile line — compiling consumes real resources."""
    # Arrange
    _member(project, other, Role.GUEST)
    # Act
    allowed = PermissionService.can_compile(other, project)
    # Assert
    assert not allowed


def test_a_reporter_can_compile(other, project):
    """REPORTER may compile but still may not write. Deliberately asymmetric."""
    # Arrange
    _member(project, other, Role.REPORTER)
    # Act
    allowed = PermissionService.can_compile(other, project)
    # Assert
    assert allowed


# ── the dispatcher ───────────────────────────────────────────────────────────


def test_check_permission_dispatches_to_the_named_action(other, project):
    """The universal entry point must agree with the verb it delegates to."""
    # Arrange
    _member(project, other, Role.MAINTAINER)
    # Act
    allowed = PermissionService.check_permission(other, project, "delete")
    # Assert
    assert allowed


def test_an_unknown_action_is_denied_rather_than_raising(owner, project):
    """FAIL-CLOSED, and worth pinning because it cuts both ways.

    A misspelled action denies silently — safe, but it means `check_permission(
    user, project, "wrtie")` refuses an owner and nobody hears about it. The
    behaviour is correct for a permission gate; this test exists so that if
    anyone changes it to raise (which would be defensible), they do it knowingly
    rather than by accident, and so the silent-deny is documented where a caller
    debugging a mystery refusal will find it.
    """
    # Arrange
    user = owner  # the most privileged user available
    # Act
    allowed = PermissionService.check_permission(user, project, "wrtie")
    # Assert
    assert not allowed


# EOF
