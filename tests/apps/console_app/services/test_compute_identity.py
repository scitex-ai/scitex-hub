"""A hub user's compute uid is unique, stable, in the hub range, never reused.

Real database: uniqueness is enforced by the ``uid`` constraint, which a
stub would not exercise.
"""

import pytest
from django.contrib.auth.models import User

from apps.workspace.console_app.services.compute_identity import (
    get_or_allocate_compute_identity,
)
from apps.workspace.console_app.services.compute_user import COMPUTE_UID_BASE


@pytest.mark.django_db
def test_two_users_get_different_uids():
    # Arrange
    alice = User.objects.create_user(username="alice")
    bob = User.objects.create_user(username="bob")
    # Act
    uids = {
        get_or_allocate_compute_identity(alice).uid,
        get_or_allocate_compute_identity(bob).uid,
    }
    # Assert
    assert len(uids) == 2


@pytest.mark.django_db
def test_same_user_keeps_the_same_uid():
    # Arrange
    alice = User.objects.create_user(username="alice")
    first = get_or_allocate_compute_identity(alice).uid
    # Act
    second = get_or_allocate_compute_identity(alice).uid
    # Assert
    assert second == first


@pytest.mark.django_db
def test_first_uid_starts_at_the_hub_range():
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    identity = get_or_allocate_compute_identity(alice)
    # Assert
    assert identity.uid == COMPUTE_UID_BASE


@pytest.mark.django_db
def test_gid_mirrors_uid():
    # Arrange
    alice = User.objects.create_user(username="alice")
    # Act
    identity = get_or_allocate_compute_identity(alice)
    # Assert
    assert identity.gid == identity.uid


@pytest.mark.django_db
def test_deleted_users_uid_is_not_reissued():
    # Arrange
    alice = User.objects.create_user(username="alice")
    alice_uid = get_or_allocate_compute_identity(alice).uid
    alice.delete()
    bob = User.objects.create_user(username="bob")
    # Act
    bob_uid = get_or_allocate_compute_identity(bob).uid
    # Assert
    assert bob_uid > alice_uid


@pytest.mark.django_db
def test_non_posix_username_is_refused():
    # Arrange
    user = User.objects.create_user(username="Alice@example.org")
    allocate = get_or_allocate_compute_identity
    # Act
    # Assert
    with pytest.raises(ValueError, match="POSIX"):
        allocate(user)
