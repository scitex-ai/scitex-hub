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
``PaymentMethod.retrieve``). No live charge ever happens — setup mode is a
zero-dollar card validation.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("scitex")


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


def start_card_setup(user, *, stripe_client, success_url, cancel_url):
    """Ensure the user's Stripe customer and return a hosted setup session.

    Returns an object exposing ``.id`` and ``.url`` (the Checkout session). The
    view redirects the browser to ``.url``; the card is then captured on
    Stripe's page, and the signed completion webhook persists it.
    """
    customer_id = _existing_customer_id(user)
    if not customer_id:
        customer = stripe_client.Customer.create(
            email=getattr(user, "email", "") or "",
            metadata={"user_pk": str(user.pk)},
        )
        customer_id = customer.id

    session = stripe_client.checkout.Session.create(
        mode="setup",
        customer=customer_id,
        # Maps the completed session back to the user without a User migration.
        client_reference_id=str(user.pk),
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session


def apply_setup_completed(stripe_event, *, stripe_client=None):
    """Persist a validated card from a SIGNED ``checkout.session.completed``.

    ``stripe_event`` is the verified event (a dict from the webhook, or a
    stripe object). Only setup-mode sessions that carry a
    ``client_reference_id`` we can map to a user are handled. Returns the
    ``PaymentMethod`` row, or ``None`` when the event is not a card setup we
    can attribute.

    ``stripe_client`` is optional: when provided the card's display metadata
    (brand / last4 / expiry) is fetched from Stripe and stored; when ``None``
    (e.g. the webhook ran with no secret key) the core row — ids +
    ``is_usable=True`` — is still persisted, which is the usability signal.
    """
    from django.contrib.auth import get_user_model

    from ..models import PaymentMethod

    User = get_user_model()

    data = _field(stripe_event, "data")
    session = _field(data, "object")
    if _field(session, "mode") != "setup":
        return None

    pm_id = _field(session, "payment_method")
    customer_id = _field(session, "customer")
    user_pk = _field(session, "client_reference_id")
    if not (pm_id and customer_id and user_pk):
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

    if stripe_client is not None and not row.brand:
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
    return row
