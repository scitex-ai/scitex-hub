"""Allocate each hub user a stable POSIX uid/gid on first compute use."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Max

from apps.workspace.console_app.models import ComputeIdentity

from .compute_user import COMPUTE_UID_BASE, validate_posix_username

_ALLOCATE_ATTEMPTS = 5


def get_or_allocate_compute_identity(user) -> ComputeIdentity:
    """Return the user's identity, allocating the next uid if they have none.

    uid = max(every uid ever issued) + 1. Rows outlive their user
    (SET_NULL), so the maximum never drops and a uid is never reused.
    gid mirrors uid (one private group per user).
    """
    validate_posix_username(user.username)
    existing = ComputeIdentity.objects.filter(user=user).first()
    if existing:
        return existing
    for _ in range(_ALLOCATE_ATTEMPTS):
        try:
            with transaction.atomic():
                top = ComputeIdentity.objects.aggregate(top=Max("uid"))["top"]
                uid = max(COMPUTE_UID_BASE, (top or 0) + 1)
                return ComputeIdentity.objects.create(
                    user=user, username=user.username, uid=uid, gid=uid
                )
        except IntegrityError:
            # A concurrent allocation took this uid, or this user's row.
            existing = ComputeIdentity.objects.filter(user=user).first()
            if existing:
                return existing
    raise RuntimeError(f"could not allocate a compute uid for {user.username}")


def compute_identity_for_username(username: str) -> ComputeIdentity:
    user = get_user_model().objects.get(username=username)
    return get_or_allocate_compute_identity(user)
