#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE onboarding authority — one typed answer to "what must this account do next?".

Card: hub-signup-email-stripe-funnel-20260917. PR #934 review, blockers 1, 2 and 7.

THE INTERFACE (kept deliberately tiny — the contract the auth and payment
surfaces share is written down in
``docs/product/ONBOARDING_AUTHORITY_INTERFACE.md``):

    begin_signup(user, email, source)       the email signup form made the account
    mark_verified(user, source)             the address is proven; signup is done
    begin_social_signup(user, provider)     a provider-verified social signup
    step_for(user) -> Step | None           authoritative, durable
    payment_required(user) -> bool          the PRODUCT GATE's single question
    mark_activated(user, pricing_id)        a PROVIDER confirmed the subscription
    next_url(user) -> str                   where to send the account now

WHY IT EXISTS. Before this module the funnel's state lived in two places that
never met: ``PendingSignup`` (deleted the instant the OTP was accepted) and the
presence of a ``PaymentMethod`` row. So a verified account that had never been
near a card was indistinguishable from a finished one, nothing enforced the
card requirement on any product route, and social signups never entered the
funnel at all — the review's blockers 1 and 7. The authority is the single
durable record every one of those paths now reads and writes.

WHAT IT DELIBERATELY IS NOT. Entitlement is not inferred from a saved card: a
``PaymentMethod`` may exist while the provider has never confirmed a
subscription, and that account is still at ``Step.PAYMENT``. Only
:func:`mark_activated`, driven by provider-confirmed webhook state, advances
the step.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .models import OnboardingState, PendingSignup

logger = logging.getLogger(__name__)

__all__ = [
    "PAYMENT",
    "PRODUCT",
    "Step",
    "begin_signup",
    "begin_social_signup",
    "mark_verified",
    "mark_activated",
    "state_for",
    "step_for",
    "payment_required",
    "next_url",
]

#: The model's own choices, re-exported so callers can compare steps without
#: importing the model. ``PAYMENT``/``PRODUCT`` are the same strings, spelled
#: once, in the model.
Step = OnboardingState.Step
PAYMENT = OnboardingState.Step.PAYMENT
PRODUCT = OnboardingState.Step.PRODUCT


def state_for(user) -> Optional[OnboardingState]:
    """This account's authority row, or ``None`` when it is not in the funnel.

    ``None`` is a real answer, not a missing one: an account that never came
    through signup (an operator-created, migrated, or pre-funnel account) has no
    authority, is not on the payment path, and must never be gated.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return OnboardingState.objects.filter(user=user).first()


def step_for(user) -> Optional[str]:
    """The durable step, or ``None`` when the account is outside the funnel."""
    row = state_for(user)
    return row.step if row is not None else None


def _ensure(user, *, source: str) -> OnboardingState:
    """Create the authority for ``user`` at PAYMENT if it does not exist yet.

    Idempotent by construction (``get_or_create`` on a OneToOne), because both
    callers — the OTP verifier and the social adapter — can be reached twice for
    one account: a double-submitted verify, a replayed allauth callback. The
    second call must be a no-op, never a second row and never a reset of a row
    that has already reached PRODUCT.
    """
    row, created = OnboardingState.objects.get_or_create(
        user=user,
        defaults={"step": PAYMENT, "source": source or ""},
    )
    if created:
        logger.info("Onboarding authority created for %s (source=%s)", user.pk, source)
    return row


def begin_signup(user, email: str = "", source: str = "email") -> None:
    """The account was just created by the email signup form.

    Nothing is written here, on purpose. The pre-verification half of the funnel
    stays in ``PendingSignup`` (its authority is about codes, not products), and
    creating the authority before the address is proven would make an
    unverified signup look verified to :func:`payment_required`.
    """
    return None


def mark_verified(user, source: str = "email") -> OnboardingState:
    """The signup is COMPLETE: address proven, payment method still owed.

    One transaction, two effects, and both are load-bearing:

    * the ``PendingSignup`` marker is DELETED — it must not outlive the signup,
      or a later administrator deactivation of this account would find signup
      evidence where there is none (the PR #775 bypass);
    * the authority row is CREATED at PAYMENT — the fact that survives.

    Doing only the first is exactly the defect this fixes: verification left
    nothing behind, so "has this account finished signing up?" had no answer.
    """
    with transaction.atomic():
        pending = PendingSignup.objects.filter(user=user).first()
        chosen_plan = getattr(pending, "plan", "") or "trial"
        PendingSignup.objects.filter(user=user).delete()
        row = _ensure(user, source=source)
        if chosen_plan == "free":
            # Free tier owes no card and no provider event will ever come:
            # verification COMPLETES this funnel. Same shape as the verified
            # card-skip below (verified + owes nothing -> PRODUCT), but keyed
            # on the submitter's own choice read from the marker before it
            # was deleted — never from a browser claim, never inferred.
            row.step = PRODUCT
            row.pricing_id = "subscription-free"
            row.activated_at = timezone.now()
            row.save(
                update_fields=["step", "pricing_id", "activated_at", "updated_at"]
            )
            logger.info("Onboarding completed free for %s", user.pk)
            return row
    # One-shot signup may already hold a usable card (taken on the signup
    # page before the address was proven). A verified account with a card on
    # file owes nothing: advance straight past the payment step instead of
    # gating an already-paid account.
    try:
        if user.payment_methods.filter(is_usable=True).exists():
            advanced = mark_activated(user, pricing_id=str(row.pricing_id or ""))
            return advanced if advanced is not None else row
    except Exception:
        logger.exception("Verified card-skip check failed open for %s", user.pk)
    return row


def begin_social_signup(user, provider: str) -> OnboardingState:
    """A provider-verified social signup: same funnel, same authority.

    Blocker 7 was that Google/ORCID auto-signup redirected to ``/`` and never
    consulted the funnel's redirect policy at all, so a social account sailed
    past the payment step. Social signups do not go through OTP (the provider
    already proved the address), so this is the equivalent of
    :func:`mark_verified`, not of :func:`begin_signup`.
    """
    return _ensure(user, source=provider or "social")


def mark_activated(user, *, pricing_id: str = "") -> Optional[OnboardingState]:
    """A PROVIDER confirmed a subscription: advance PAYMENT -> PRODUCT.

    Called from webhook state only. Never from a browser redirect: the success
    URL is a claim made by the browser, and this transition is the boundary the
    funnel is made of. Idempotent — a replayed webhook re-marks the same row and
    does not reset ``activated_at``.
    """
    row = state_for(user)
    if row is None:
        return None
    if row.step == PRODUCT:
        return row
    row.step = PRODUCT
    if pricing_id:
        row.pricing_id = pricing_id
    row.activated_at = timezone.now()
    row.save(update_fields=["step", "pricing_id", "activated_at", "updated_at"])
    logger.info("Onboarding activated for %s (pricing_id=%r)", user.pk, pricing_id)
    return row


def mark_free(user, *, source: str = "payment-step") -> Optional[OnboardingState]:
    """The account chose the Free plan: PAYMENT -> PRODUCT with no card.

    The escape hatch for anyone the funnel holds at the payment step — a
    social signup, a legacy trial-plan marker, or anyone who simply does not
    want a trial. Same durable shape as the free branch of
    :func:`mark_verified` (verified + owes nothing -> PRODUCT), but callable
    after the fact. Idempotent; a non-funnel account returns None and the
    gate never sees them.
    """
    row = state_for(user)
    if row is None:
        return None
    if row.step == PRODUCT:
        return row
    if row.step != PAYMENT:
        return row
    row.step = PRODUCT
    row.pricing_id = "subscription-free"
    row.activated_at = timezone.now()
    row.save(update_fields=["step", "pricing_id", "activated_at", "updated_at"])
    logger.info("Onboarding completed free for %s (source=%s)", user.pk, source)
    return row


def deployment_can_take_a_payment() -> bool:
    """Whether ANY account in this deployment can satisfy the funnel's rule.

    The honest escape valve, stated once and in one place. When the provider is
    unconfigured no card can be entered by anybody, so a gate that demanded one
    would not be a boundary — it would be a permanent lockout of every account
    that signs up, which is worse than the bug it fixes. The requirement is
    therefore SUSPENDED rather than silently passed: the payment step still
    renders its ``not_open`` state and says activation is waiting.
    """
    try:
        from apps.infra.public_app.services.billing_provider import (
            card_registration_is_open,
        )
    except Exception:  # pragma: no cover - import-cycle guard
        return False
    return bool(card_registration_is_open())


def payment_required(user) -> bool:
    """THE product gate's single question — the one function middleware asks.

    True only when BOTH hold: the authority says this account still owes a
    payment method, AND the deployment can actually take one. An account with no
    authority row (existing users, staff, everything pre-funnel) is never gated:
    the gate is scoped to the funnel it belongs to.
    """
    if step_for(user) != PAYMENT:
        return False
    return deployment_can_take_a_payment()


def next_url(user) -> str:
    """Where this account must go right now — the funnel's one redirect policy.

    Shared by the OTP success handler and the social adapter (blocker 7), so the
    two doors cannot diverge again. Outside the funnel it is the ordinary
    post-login destination.
    """
    from django.conf import settings

    from apps.infra.accounts_app.funnel import payment_step_url

    if step_for(user) == PAYMENT:
        return payment_step_url()
    return getattr(settings, "LOGIN_REDIRECT_URL", "/") or "/"
