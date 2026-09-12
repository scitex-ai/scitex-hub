"""Settings > Billing — card registration + usability status surface.

Shows the logged-in user their saved, validated card (safe display metadata
only: brand / last4 / expiry) and lets them add a new one via Stripe's hosted
``mode="setup"`` Checkout. Card data is captured on Stripe's page, so SciTeX
never sees PAN/CVC.

States (fail-loud, no fake data — mirrors the commerce page):
  * Stripe unconfigured (no secret key)  -> "unavailable"
  * configured, no saved card            -> "add card"
  * configured, saved usable card        -> show brand/last4/exp
Sign-in itself is card-free; this page is only ever reached by a logged-in
user.
"""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def billing_settings(request):
    stripe_configured = bool(settings.STRIPE_SECRET_KEY)
    cards = (
        request.user.payment_methods.order_by("-created_at")
        if stripe_configured
        else []
    )
    default_card = next((c for c in cards if c.is_default and c.is_usable), None)

    if not stripe_configured:
        state = "unavailable"
    elif default_card is not None:
        state = "saved"
    else:
        state = "add"

    context = {
        "stripe_configured": stripe_configured,
        "state": state,
        "default_card": default_card,
        "cards": cards,
    }
    return render(request, "accounts_app/billing_settings.html", context)


__all__ = ["billing_settings"]
