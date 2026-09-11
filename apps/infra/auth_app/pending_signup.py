#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The pending-signup lifecycle, in ONE place.

CARD: hub auth lifecycle P0 (pending signup / OTP). Observed live evidence:
``SignupForm.clean_username`` and ``clean_email`` reject existing ``User`` rows
BEFORE ``signup()`` can reach its inactive-account resume/expiry branch, so that
branch is unreachable; ``cleanup_unverified_users`` exists only as an
unscheduled manual command; and a live ACTIVE user can carry a later expired
``EmailVerification`` with ``is_verified=False``.

THE INVARIANTS THIS MODULE EXISTS TO MAKE TRUE. They were previously implicit,
and the implicit version was contradictory — the form said "already exists",
the view said "wait for it to expire", and nothing performed the expiry.

  I1  ``is_active=True`` IS a verified account. Anything pending is inactive.
  I2  ``is_active=False`` is a PENDING signup, which is either LIVE (inside the
      window) or EXPIRED (outside it). EXPIRED IS RESUMABLE — never a dead end.
  I3  Expiry is decided IN THE REQUEST PATH, so correctness does not depend on
      whether any cleanup sweep has run. Deletion stays a cleanup concern.
  I4  NO RESPONSE REVEALS WHETHER AN EMAIL OR USERNAME EXISTS. Collisions are
      answered with the same shape either way, and the actionable routes
      (verify / sign in / reset password) are offered unconditionally.
  I5  A resend is RATE LIMITED per address, so the endpoint cannot be used to
      mail-bomb a third party or to probe for accounts at speed.

WHY THE FORM NO LONGER CHECKS EXISTENCE. Format validation belongs in the form;
existence is a lifecycle question with four different answers (create / resend /
resume / refuse), and a field validator can only say "no". Moving it here is what
makes resume and expiry reachable at all — the defect, not a refactor.
"""

from __future__ import annotations

import enum
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

__all__ = [
    "PENDING_SIGNUP_WINDOW",
    "RESENDS_ALLOWED_PER_WINDOW",
    "SignupCollision",
    "classify_pending_signup",
    "clear_resend_budget",
    "pending_age",
    "resend_allowed",
    "resend_budget_message",
]

#: How long a pending (inactive) signup stays on its ORIGINAL verification code
#: before it is treated as resumable-with-a-fresh-code. SINGLE SOURCE OF TRUTH:
#: the view hard-coded ``timedelta(hours=1)`` and the cleanup command defaulted
#: to ``--hours 1``; two copies of a lifecycle number is how they drift.
PENDING_SIGNUP_WINDOW = timedelta(hours=1)

#: Resends permitted per address per window. Small on purpose: a legitimate
#: user needs one, occasionally two; a mail-bomb needs thousands.
RESENDS_ALLOWED_PER_WINDOW = 3

_RL_PREFIX = "pending_signup:resend:"


class SignupCollision(enum.Enum):
    """What a second signup attempt means, given what already exists."""

    #: Nothing exists under this email or username — create the account.
    NONE = "none"
    #: An inactive signup INSIDE the window — resend, do not recreate.
    PENDING_LIVE = "pending_live"
    #: An inactive signup PAST the window — resumable with a fresh code.
    PENDING_EXPIRED = "pending_expired"
    #: A verified, active account — never recreated, never deleted here.
    ACTIVE = "active"
    #: Two DIFFERENT accounts hold the submitted email and username.
    SPLIT = "split"
    #: Exactly ONE of the two matched, and they do not identify the same row.
    #:
    #: SECURITY (PR #775 hold, account takeover): this state exists because the
    #: one-sided case used to fall through to ``user = email_user or
    #: username_user``, treating whichever row matched as the submitter's own.
    #: POST attacker_email + victim_pending_username then classified as
    #: PENDING_LIVE with the VICTIM's row, and the caller minted an OTP bound to
    #: the victim while mailing it to the attacker. After expiry the same input
    #: reached the delete-and-recreate branch. A collision is a collision: the
    #: caller is given NO user, so it cannot act on a row it has not proven.
    ONE_SIDED = "one_sided"


def _by_email(email: str):
    return User.objects.filter(email__iexact=email).order_by("date_joined").first()


def _by_username(username: str):
    return (
        User.objects.filter(username__iexact=username).order_by("date_joined").first()
    )


def pending_age(user: User) -> timedelta:
    """How long this pending signup has been waiting."""
    return timezone.now() - user.date_joined


def classify_pending_signup(
    email: str, username: str = ""
) -> tuple[SignupCollision, User | None]:
    """The lifecycle state of a signup attempt for ``email`` / ``username``.

    Returns ``(collision, user)``. The user is the existing row the caller must
    act on — ``None`` only for :attr:`SignupCollision.NONE`.

    SPLIT is reported rather than resolved: if the email belongs to one account
    and the username to another, neither "create" nor "resume" is correct, and
    guessing would either hijack a username or strand the email. The caller
    answers with the generic collision message and the actionable routes.
    """
    email_user = _by_email(email)
    username_user = _by_username(username) if username else None

    if email_user is None and username_user is None:
        return SignupCollision.NONE, None

    # EXACT BOTH-VALUES PAIR ONLY (PR #775 security hold).
    #
    # A row may be treated as "the same pending signup" ONLY when it holds BOTH
    # the submitted email AND the submitted username. Every other combination is
    # a collision and returns NO user.
    #
    # The previous shape was:
    #     if both and different: SPLIT
    #     user = email_user or username_user      # <-- the takeover
    # which made POST attacker_email + victim_pending_username return
    # (PENDING_LIVE, victim). The caller then created an EmailVerification with
    # user=victim, email=attacker and mailed the code to the attacker — a code
    # that verifies the VICTIM's row, i.e. account takeover. Past the window the
    # same input reached the delete-and-recreate branch and let the attacker
    # take the victim's username outright.
    #
    # The asymmetry is deliberate: proving ownership of one field must not be
    # enough to act, because the two fields are supplied by different parties —
    # the username by whoever asks, the email by whoever can read it.
    if (
        email_user is not None
        and username_user is not None
        and email_user.pk == username_user.pk
    ):
        user = email_user
        if user.is_active:
            return SignupCollision.ACTIVE, user
        if pending_age(user) > PENDING_SIGNUP_WINDOW:
            return SignupCollision.PENDING_EXPIRED, user
        return SignupCollision.PENDING_LIVE, user

    # Crossed (two different rows) and one-sided are both collisions, and both
    # are reported with user=None so no caller can mutate anything from them.
    if email_user is not None and username_user is not None:
        return SignupCollision.SPLIT, None
    return SignupCollision.ONE_SIDED, None


# ---------------------------------------------------------------------------
# Rate limiting. Cache-backed and keyed by ADDRESS, not by user id, so it also
# covers the "no such account" case (an attacker probing addresses must not get
# a faster path than a real user).
# ---------------------------------------------------------------------------


def _rl_key(email: str) -> str:
    return f"{_RL_PREFIX}{email.strip().lower()}"


def resend_allowed(email: str) -> bool:
    """Whether another verification mail may be sent to ``email`` now."""
    return int(cache.get(_rl_key(email), 0)) < RESENDS_ALLOWED_PER_WINDOW


def record_resend(email: str) -> None:
    """Count one send. TTL is the window, so the budget refills with it."""
    key = _rl_key(email)
    used = int(cache.get(key, 0)) + 1
    cache.set(key, used, timeout=int(PENDING_SIGNUP_WINDOW.total_seconds()))


def clear_resend_budget(email: str) -> None:
    """Forget the budget for an address (used after a successful verify)."""
    cache.delete(_rl_key(email))


def resend_budget_message() -> str:
    """What a rate-limited caller is told — truthful, and not a dead end."""
    return (
        "We have already sent several verification emails to that address. "
        f"Please wait {int(PENDING_SIGNUP_WINDOW.total_seconds() // 60)} minutes "
        "before requesting another, or sign in and use “Resend verification” "
        "from the account page."
    )
