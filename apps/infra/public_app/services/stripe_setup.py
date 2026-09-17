"""Stripe card registration + usability validation service (hosted setup).

Card data is entered ONLY on Stripe's hosted Checkout page (``mode="setup"``),
so SciTeX never sees PAN/CVC. This module persists just the Stripe identifiers
(customer / payment method) plus safe display metadata (brand, last4, expiry).

Usability is validated two ways (per the operator spec):
  1. the Stripe API result — ``start_card_setup`` returns a live session URL;
  2. a SIGNED ``checkout.session.completed`` webhook — ``apply_setup_completed``
     flips the stored card to ``is_usable=True`` only after signature
     verification (done in views/billing.py) confirms the event is genuine.

STX-NM001 (no mocks): the Stripe client is an injected collaborator
(``stripe_client`` keyword), exactly the hand-rolled-fake pattern used by
``apps/.../terminal_provider.py`` tests. The real client is produced by
:func:`build_stripe_client`; tests pass a ``FakeStripeClient`` with the same
call shapes (``Customer.create`` / ``checkout.Session.create`` /
``SetupIntent.retrieve`` / ``PaymentMethod.retrieve``). No live charge ever happens — setup mode is a
zero-dollar card validation.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("scitex")

# Stripe rejects a setup-mode Checkout Session without a currency; USD is the
# only stored currency in the Services SSOT (data/pricing.json).
CARD_SETUP_CURRENCY = "usd"

#: How long an open hosted session is reused instead of replaced. Stripe expires
#: Checkout sessions after 24h; a minute of headroom means we never hand a user
#: a URL the provider would refuse.
HOSTED_SESSION_TTL = timedelta(hours=23)


def customer_idempotency_key(user) -> str:
    """The Stripe idempotency key for "this user's customer", and only that.

    PR #934 review, blocker 4. Derived from the USER, not from the request, so
    two concurrent clicks cannot produce two customers: Stripe collapses them
    into one object because the key is the same. It carries no secret and no
    personal data — a user pk is already in the Customer's metadata.
    """
    return f"scitex-customer-{user.pk}"


def session_idempotency_key(user, pricing_id: str, attempt: int) -> str:
    """The Stripe idempotency key for ONE hosted setup attempt.

    Keyed by attempt as well as user so that retrying after a cancel creates a
    genuinely new session, while two requests inside the SAME attempt collapse
    into one. That is exactly the property blocker 4 was missing.
    """
    return f"scitex-setup-{user.pk}-{pricing_id or 'none'}-{int(attempt)}"


def session_is_reusable(row, pricing_id: str, *, now=None) -> bool:
    """Whether the stored session may be handed back instead of creating one.

    Pure, so the rule is testable without a database. It is reused only when ALL
    four hold: it is still open, it is for the SAME plan (a plan change must not
    silently keep the old price), the provider gave us a URL, and it is inside
    :data:`HOSTED_SESSION_TTL`.
    """
    from ..models import BillingSetupSession

    if row is None:
        return False
    if row.status != BillingSetupSession.Status.OPEN:
        return False
    if not row.session_url or not row.session_id:
        return False
    if (row.pricing_id or "") != (pricing_id or ""):
        return False
    reference = now or timezone.now()
    # ``updated_at``, not ``created_at``: it is refreshed when the session is
    # stored, so a retry AFTER a cancel still counts its own fresh session as
    # recent instead of inheriting the row's original age.
    return reference - row.updated_at < HOSTED_SESSION_TTL


class HostedSetup:
    """The answer to "where does this user enter their card?".

    ``reused`` is carried out of the service rather than logged and forgotten:
    a test (and an operator reading the response) can tell a fresh session from
    a repeated click, which is the whole observable difference blocker 4 was about.
    """

    __slots__ = ("session_id", "url", "reused", "attempt")

    def __init__(self, *, session_id: str, url: str, reused: bool, attempt: int):
        self.session_id = session_id
        self.url = url
        self.reused = reused
        self.attempt = attempt


def build_stripe_client(secret_key: str | None):
    """Return a usable Stripe client for ``secret_key``, or ``None``.

    ``None`` is the fail-loud signal the views turn into a 503 "not
    configured" state. The SDK is imported here (not at module import) so this
    service stays importable where ``stripe`` is absent, mirroring the existing
    behaviour in views/billing.py.
    """
    if not secret_key:
        return None
    import stripe

    stripe.api_key = secret_key
    return stripe


def _field(obj, name, default=None):
    """Read ``name`` from a dict OR a stripe object uniformly."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _existing_customer_id(user):
    from ..models import PaymentMethod

    row = (
        PaymentMethod.objects.filter(user=user)
        .exclude(stripe_customer_id="")
        .order_by("-created_at")
        .first()
    )
    return row.stripe_customer_id if row else None


def _open_setup_row(user):
    """This user's setup row, locked for the rest of the transaction.

    ``OneToOne`` means there can only ever be one, which is what makes the
    second click in a double-submit a reuse rather than a race. The row is
    created on first use (``attempt=0``); a concurrent create loses to the
    unique constraint and re-reads the winner's row.
    """
    from django.db import IntegrityError

    from ..models import BillingSetupSession

    row = BillingSetupSession.objects.select_for_update().filter(user=user).first()
    if row is not None:
        return row
    try:
        BillingSetupSession.objects.create(user=user, attempt=0)
    except IntegrityError:  # another request created it first — that is the point
        pass
    return BillingSetupSession.objects.select_for_update().get(user=user)


def start_card_setup(user, *, pricing_id, stripe_client, success_url, cancel_url):
    """Ensure the user's Stripe customer and return a hosted setup session.

    Returns a :class:`HostedSetup`. The card is captured on Stripe's page; the
    signed completion webhook persists it and activates the trial.

    IDEMPOTENT BY CONSTRUCTION (PR #934 review, blocker 4). Three separate
    mechanisms, because any one alone leaves a hole:

    1. a persisted row, locked for the duration, so two requests serialise;
    2. an OPEN session for the same plan inside its TTL is returned AS IS, with
       no provider call at all — the common double-click reaches Stripe zero
       times;
    3. both provider calls carry deterministic idempotency keys derived from the
       row (customer per user, session per attempt), so even a race that got
       past (1) and (2) collapses inside Stripe instead of creating a second
       customer.

    ``pricing_id`` is written onto the Stripe session's metadata AND the
    customer's, so the webhook activates the plan the user was shown.
    """
    from ..models import BillingSetupSession

    with transaction.atomic():
        row = _open_setup_row(user)
        now = timezone.now()

        if session_is_reusable(row, pricing_id, now=now):
            logger.info(
                "Reusing open Stripe setup session %s for user %s (attempt %s)",
                row.session_id, user.pk, row.attempt,
            )
            return HostedSetup(
                session_id=row.session_id, url=row.session_url,
                reused=True, attempt=row.attempt,
            )

        if row.session_id:
            # A genuinely new attempt: a session already existed and is being
            # replaced (cancelled, expired, or for a different plan). A brand-new
            # row keeps attempt 0 — the first attempt IS attempt zero.
            row.attempt = (row.attempt or 0) + 1

        customer_id = row.stripe_customer_id or _existing_customer_id(user)
        if not customer_id:
            customer = stripe_client.Customer.create(
                email=getattr(user, "email", "") or "",
                metadata={"user_pk": str(user.pk), "pricing_id": pricing_id or ""},
                idempotency_key=customer_idempotency_key(user),
            )
            customer_id = customer.id
        row.stripe_customer_id = customer_id

        session = stripe_client.checkout.Session.create(
            mode="setup",
            currency=CARD_SETUP_CURRENCY,
            customer=customer_id,
            # Maps the completed session back to the user and the plan without
            # a User migration or a query parameter the browser could edit.
            client_reference_id=str(user.pk),
            metadata={"user_pk": str(user.pk), "pricing_id": pricing_id or ""},
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=session_idempotency_key(user, pricing_id, row.attempt),
        )

        row.session_id = _field(session, "id", "") or ""
        row.session_url = _field(session, "url", "") or ""
        row.pricing_id = pricing_id or ""
        row.status = BillingSetupSession.Status.OPEN
        row.save(
            update_fields=[
                "attempt", "stripe_customer_id", "session_id", "session_url",
                "pricing_id", "status", "updated_at",
            ]
        )
        return HostedSetup(
            session_id=row.session_id, url=row.session_url,
            reused=False, attempt=row.attempt,
        )


def mark_setup_cancelled(user) -> None:
    """Record that the user came back from the hosted page without finishing.

    The stored session is retired so the next attempt is genuinely new (and gets
    a fresh idempotency key), while the customer id is KEPT: the account already
    has a Stripe customer, and minting a second one for a retry is the exact
    duplication blocker 4 was about.
    """
    from ..models import BillingSetupSession

    BillingSetupSession.objects.filter(
        user=user, status=BillingSetupSession.Status.OPEN
    ).update(status=BillingSetupSession.Status.CANCELLED, updated_at=timezone.now())


def session_pricing_id(stripe_event) -> str:
    """The allowlisted plan id the completed session was opened for, if any."""
    session = _field(_field(stripe_event, "data"), "object")
    return _field(_field(session, "metadata"), "pricing_id", "") or ""


def apply_setup_completed(stripe_event, *, stripe_client=None):
    """Persist a validated card from a SIGNED ``checkout.session.completed``.

    ``stripe_event`` is the verified event (a dict from the webhook, or a
    stripe object). Only setup-mode sessions that carry a
    ``client_reference_id`` we can map to a user are handled. Returns the
    ``PaymentMethod`` row, or ``None`` when the event is not a card setup we
    can attribute.

    ``stripe_client`` is required to persist anything: a completed setup-mode
    session carries only its ``setup_intent`` id, and the payment method (plus
    brand / last4 / expiry) has to be read back from Stripe.
    """
    from django.contrib.auth import get_user_model

    from ..models import BillingSetupSession, PaymentMethod

    User = get_user_model()

    data = _field(stripe_event, "data")
    session = _field(data, "object")
    if _field(session, "mode") != "setup":
        return None

    setup_intent_id = _field(session, "setup_intent")
    customer_id = _field(session, "customer")
    user_pk = _field(session, "client_reference_id")
    if not (setup_intent_id and customer_id and user_pk and stripe_client):
        return None

    pm_id = _field(stripe_client.SetupIntent.retrieve(setup_intent_id), "payment_method")
    if not pm_id:
        logger.warning("setup intent %s has no payment method", setup_intent_id)
        return None

    try:
        user = User.objects.get(pk=int(user_pk))
    except (ValueError, User.DoesNotExist):
        logger.warning("setup completed for unknown user_pk=%r", user_pk)
        return None

    row, _created = PaymentMethod.objects.update_or_create(
        stripe_payment_method_id=pm_id,
        defaults={
            "user": user,
            "stripe_customer_id": customer_id,
            # A completed setup session IS the zero-dollar validation.
            "is_usable": True,
            "is_default": True,
        },
    )

    if not row.brand:
        pm = stripe_client.PaymentMethod.retrieve(pm_id)
        card = _field(pm, "card")
        row.brand = _field(card, "brand", "") or ""
        row.last4 = _field(card, "last4", "") or ""
        row.exp_month = _field(card, "exp_month")
        row.exp_year = _field(card, "exp_year")
        row.save(update_fields=["brand", "last4", "exp_month", "exp_year"])

    # Newest validated card becomes the default; demote the rest.
    PaymentMethod.objects.filter(user=user).exclude(pk=row.pk).update(
        is_default=False
    )

    # The attempt is FINISHED. Recording it here (not on the browser's return)
    # is what keeps the setup row and the provider in agreement: only a signed
    # completion retires the attempt.
    BillingSetupSession.objects.filter(
        user=user, session_id=_field(session, "id", "") or ""
    ).update(
        status=BillingSetupSession.Status.COMPLETED,
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )
    return row

