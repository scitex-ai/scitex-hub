"""Per-user academic discount grants: evaluate once, record, select by record.

Operator CCT4555. The email→academic→50%-off wiring has exactly three
moving parts, and they live here:

* :func:`grant_academic_discount` — evaluate the canonical accounts checker
  against a PROVEN address and persist the 1:1 ``UserDiscount`` row.
  Idempotent (``get_or_create``): double verification, replayed callbacks
  and the email+social double door all converge on one row.
* :func:`user_has_academic_discount` — the funnel's eligibility read. Reads
  the row, never the raw email. Safe for anonymous/unsaved users (False,
  not an exception).
* :func:`academic_row_for` — the academic catalog row when this account may
  take it: eligible AND still on the funnel default (free/empty) AND the row
  is chargeable on THIS deployment. Anything else is ``None`` and the
  normal resolver rules run untouched.

What this module deliberately does NOT do: touch Stripe. The academic price
is the ``subscription-student`` catalog row ($19 vs $39 — the 50%-off is the
row, not a coupon applied at the provider). Once the funnel resolves that
row, the existing machinery carries it: plan-bound setup sessions, metadata-
carried ``pricing_id``, provider-confirmed activation. The ``ACADEMIC50``
landing-table code path stays ``coming_soon`` (pricing.json) — a different
door, still unwired, out of scope.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "ACADEMIC_CODE",
    "ACADEMIC_PRICING_ID",
    "DEFAULT_FUNNEL_PRICING_IDS",
    "academic_row_for",
    "grant_academic_discount",
    "grant_approved_appeal",
    "user_has_academic_discount",
]

#: The public offer code a grant redeems (pricing.json ``coupons``).
ACADEMIC_CODE = "ACADEMIC50"

#: The catalog row an eligible account is placed on ($19/mo academic Pro).
ACADEMIC_PRICING_ID = "subscription-student"

#: Authority plans that mean "no choice made yet" — the only ones the
#: academic rule may supersede. A recorded non-free plan is a decision
#: (explicit ?plan=, or a step selection) and is never overridden.
DEFAULT_FUNNEL_PRICING_IDS = ("", "subscription-free")


def _checker():
    from apps.infra.accounts_app.academic import is_japanese_academic_email

    return is_japanese_academic_email


def grant_academic_discount(user, email):
    """Persist the academic grant for ``user`` when ``email`` qualifies.

    ``email`` must be PROVEN (verified OTP address, provider-verified social
    address) — callers pass it explicitly rather than reading ``user.email``,
    so a later address change cannot mint eligibility it never proved.

    Returns the ``UserDiscount`` row, or ``None`` when the address is not
    academic. A revoked grant stays revoked: revocation is an admin act and
    re-verification does not resurrect it.
    """
    from apps.infra.public_app.billing_models import UserDiscount

    if user is None or getattr(user, "pk", None) is None:
        return None
    if not _checker()(email):
        return None
    domain = str(email).lower().split("@", 1)[1]
    row, created = UserDiscount.objects.get_or_create(
        user=user,
        defaults={
            "code": ACADEMIC_CODE,
            "verified_email": str(email),
            "basis_domain": domain,
        },
    )
    if created:
        logger.info(
            "Academic discount granted for %s (domain=%s)", user.pk, domain
        )
    return row if row.is_active else None


def user_has_academic_discount(user) -> bool:
    """Whether this account holds a live academic grant."""
    try:
        if user is None or getattr(user, "pk", None) is None:
            return False
        return bool(user.discount.is_active)
    except Exception:
        # No row (RelatedObjectDoesNotExist), no database, half-built user
        # in a migration — all of those mean "not eligible", never a 500.
        return False


def grant_approved_appeal(appeal, *, by_user=None, note=""):
    """Issue the grant for an APPROVED appeal (operator CCT4558).

    The reviewer's decision substitutes for the automatic checker: the
    claimed address never passed it (that is why there is an appeal), and a
    human verified the affiliation instead. The grant records the appeal so
    the audit trail answers "why does this account pay $19".

    Idempotent and safe to call twice: an already-approved appeal returns
    its grant; an existing live grant for the account is linked to the
    appeal rather than duplicated (the 1:1 mapping holds). A revoked grant
    is NOT resurrected — revoke the revocation first, explicitly.
    """
    from django.db import transaction
    from django.utils import timezone

    from apps.infra.public_app.billing_models import DiscountAppeal, UserDiscount

    if appeal is None or getattr(appeal, "pk", None) is None:
        raise ValueError("grant_approved_appeal needs a saved appeal")
    with transaction.atomic():
        appeal = DiscountAppeal.objects.select_for_update().get(pk=appeal.pk)
        if appeal.status == DiscountAppeal.Status.APPROVED:
            existing = UserDiscount.objects.filter(appeal=appeal).first()
            if existing is not None:
                return existing
        if appeal.status != DiscountAppeal.Status.OPEN:
            raise ValueError(
                f"appeal {appeal.pk} is {appeal.status}, not open"
            )
        user = appeal.user
        email = (appeal.claimed_email or "").strip()
        domain = email.lower().split("@", 1)[1] if "@" in email else ""
        grant, _ = UserDiscount.objects.get_or_create(
            user=user,
            defaults={
                "code": ACADEMIC_CODE,
                "verified_email": email,
                "basis_domain": domain,
                "appeal": appeal,
            },
        )
        if not grant.is_active:
            raise ValueError(
                f"account {user.pk} holds a revoked grant; "
                "un-revoke it explicitly instead of appealing around it"
            )
        if grant.appeal_id != appeal.pk:
            grant.appeal = appeal
            grant.save(update_fields=["appeal", "updated_at"])
        appeal.status = DiscountAppeal.Status.APPROVED
        appeal.reviewer_note = note or appeal.reviewer_note
        appeal.decided_by = by_user
        appeal.decided_at = timezone.now()
        appeal.save(
            update_fields=[
                "status",
                "reviewer_note",
                "decided_by",
                "decided_at",
                "updated_at",
            ]
        )
        logger.info(
            "Appeal %s approved by %s: grant for account %s",
            appeal.pk,
            getattr(by_user, "pk", None),
            user.pk,
        )
        return grant


def academic_row_for(user, allowlist_rows) -> dict | None:
    """The academic row this account may take, or ``None``.

    Three gates, all of which must pass: the account holds a live grant; its
    onboarding authority is still on the funnel default (no plan decision
    made yet); the academic row is on this deployment's chargeable
    allowlist. The caller (``funnel_plan``) runs this BEFORE the recorded-
    plan rule, so an explicit choice always wins and this only ever fills
    the "no decision yet" gap.
    """
    if not user_has_academic_discount(user):
        return None
    try:
        from apps.infra.auth_app.onboarding import state_for
    except Exception:  # pragma: no cover - import-cycle guard
        return None
    authority = state_for(user)
    recorded = getattr(authority, "pricing_id", "") or ""
    if recorded not in DEFAULT_FUNNEL_PRICING_IDS:
        return None
    rows = allowlist_rows or []
    return next((r for r in rows if r.get("id") == ACADEMIC_PRICING_ID), None)
