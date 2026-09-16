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


__all__ = ["billing_settings"]
