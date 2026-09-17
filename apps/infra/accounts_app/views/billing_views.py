"""Settings > Billing: trial status, saved card, paid plan, cancel, and portal.

Card data is entered only on the billing provider's hosted pages, so SciTeX
never sees PAN/CVC. With no provider keys configured the page says card
registration opens soon, never an error.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.infra.public_app.services.billing_provider import (
    card_registration_is_open,
    get_billing_provider,
    subscription_pricing_rows,
    trial_window,
)


@login_required
def billing_settings(request):
    if not card_registration_is_open():
        return render(request, "accounts_app/billing_settings.html", {"state": "soon"})

    user = request.user
    cards = list(user.payment_methods.order_by("-created_at"))
    default_card = next((c for c in cards if c.is_default and c.is_usable), None)
    current_subscription = next(
        (s for s in user.plan_subscriptions.all() if s.is_current), None
    )
    _, trial_end = trial_window(user)
    labels = {row["id"]: row["label"] for row in subscription_pricing_rows()}
    context = {
        "state": "saved" if default_card else "add",
        "default_card": default_card,
        "cards": cards,
        "trial_end": trial_end,
        "trial_active": timezone.now() < trial_end,
        "plans": get_billing_provider().subscribable_plans(),
        "current_subscription": current_subscription,
        "current_plan_label": labels.get(getattr(current_subscription, "pricing_id", ""), ""),
        "welcome": request.GET.get("welcome") == "1",
        "setup_result": request.GET.get("setup", ""),
    }
    return render(request, "accounts_app/billing_settings.html", context)


@login_required
def payment_step(request):
    """State the terms, then hand the card entry to the provider.

    Card: hub-signup-email-stripe-funnel-20260917. This is the dedicated step a
    verified user meets before Stripe — plan, price, what is due today, when the
    trial ends, when the first charge lands, renewal, cancellation and tax — with
    one explicit action that starts the provider's setup flow.

    It decides nothing about entitlement: a usable card is read from the account
    records the backend already owns, and the webhook still owns activation.
    """
    from ..payment_step import payment_disclosures, trial_state

    if not card_registration_is_open():
        return render(request, "accounts_app/billing_settings.html", {"state": "soon"})

    user = request.user
    has_usable_card = user.payment_methods.filter(is_usable=True).exists()
    state = trial_state(
        has_usable_card=has_usable_card,
        returned_from_setup=request.GET.get("setup") == "cancelled",
    )

    rows = subscription_pricing_rows()
    row = rows[0] if rows else {}
    label = row.get("label") or row.get("name") or "SciTeX Cloud"
    _, trial_end = trial_window(user)

    disclosures = payment_disclosures(
        plan_label=label,
        monthly_usd=float(row.get("amount") or 0),
        trial_end=trial_end,
        state=state,
    )
    return render(request, "accounts_app/payment_step.html", disclosures.as_context())


__all__ = ["billing_settings", "payment_step"]
