"""Settings > Billing: trial status, saved card, paid plan, cancel, and portal.

Card data is entered only on the billing provider's hosted pages, so SciTeX
never sees PAN/CVC. With no provider keys configured the page says card
registration opens soon, never an error.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.infra.public_app.services.billing_provider import (
    card_registration_is_open,
    confirmed_trial_window,
    get_billing_provider,
    inline_card_form_info,
    subscription_pricing_rows,
    trial_window,
)

from ..funnel import first_product_url


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
    # A trial is RUNNING only when the provider says so (blocker 2). The previous
    # page said "trial active" whenever now < date_joined + 30 days, i.e. for
    # anyone who had ever signed up — including accounts that had never entered a
    # card and had no subscription at all.
    confirmed = confirmed_trial_window(user)
    context = {
        "state": "saved" if default_card else "add",
        "default_card": default_card,
        "cards": cards,
        "trial_end": trial_end if confirmed is not None else None,
        "trial_active": confirmed is not None and timezone.now() < trial_end,
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
    records the backend already owns, and the webhook still owns activation. What
    it does decide is which of the funnel's states is true, and it decides that
    from durable state only.

    PR #934 review:
      * (1) only an account the onboarding authority puts in the funnel may use
        this step — an existing user is sent to billing settings instead, so the
        signup funnel is not a page anyone can wander into;
      * (3) ``?setup=`` markers are read here, so success, cancel and failure all
        land on a surface that can say what happened and what to do next;
      * (5) the plan comes from the allowlist through :func:`funnel_plan`, and
        the selection is written onto the account so the POST and the webhook
        charge the plan that was shown.
    """
    from apps.infra.auth_app.models import OnboardingState
    from apps.infra.auth_app.onboarding import state_for

    from ..payment_step import (
        NOT_OPEN,
        PLAN_UNSET,
        funnel_plan,
        payment_disclosures,
        trial_state,
    )

    user = request.user
    authority = state_for(user)
    if authority is None:
        # Not a funnel account: this is not their step, and offering it would be
        # the "any existing user can enter the signup payment flow" defect.
        return redirect("accounts_app:billing")

    if request.method == "POST" and request.POST.get("action") == "continue-free":
        # The free exit: no card, no trial, no provider round-trip. The user
        # must be able to be free — this page may never be a dead end that
        # only a card can open.
        from apps.infra.auth_app.onboarding import mark_free

        if mark_free(user) is None:
            return redirect("accounts_app:billing")
        return redirect(first_product_url())

    if not card_registration_is_open():
        # No card can be taken yet (provider not configured). Still render THIS
        # step rather than borrowing the generic billing page: the funnel stays one
        # coherent step, and the surface carries its own marker so both a reader and
        # a test can tell which step they are on.
        disclosures = payment_disclosures(
            plan_label="",
            monthly_usd=0.0,
            trial_end=None,
            state=NOT_OPEN,
        )
        return render(request, "accounts_app/payment_step.html", disclosures.as_context())

    # Which plan a new signup is put on must be DETERMINED and CHARGEABLE, not
    # whichever catalog row comes first and not whatever ``?plan=`` names.
    row = funnel_plan(user, requested_id=request.GET.get("plan"))

    # The way the last attempt ended, read from the provider's return markers.
    setup_marker = (request.GET.get("setup") or "").lower()
    if setup_marker == "cancelled":
        # Retire the stored attempt so the retry is genuinely new (fresh
        # idempotency key) while the Stripe CUSTOMER is kept (blocker 4).
        from apps.infra.public_app.services.stripe_setup import mark_setup_cancelled

        mark_setup_cancelled(user)

    if row is None:
        disclosures = payment_disclosures(
            plan_label="",
            monthly_usd=0.0,
            trial_end=None,
            state=PLAN_UNSET,
        )
        return render(request, "accounts_app/payment_step.html", disclosures.as_context())

    # Record the selection on the account: the POST and the webhook read it from
    # there rather than re-deciding (blocker 5).
    if authority.pricing_id != row["id"]:
        authority.pricing_id = row["id"]
        authority.save(update_fields=["pricing_id", "updated_at"])

    state = trial_state(
        has_usable_card=user.payment_methods.filter(is_usable=True).exists(),
        # The AUTHORITY answers this, not a second query: it is advanced only by
        # provider-confirmed webhook state (``onboarding.mark_activated``), which
        # is precisely what "activated" means. Reading the subscription row here
        # as well would be a second source of the same fact.
        has_confirmed_trial=authority.step == OnboardingState.Step.PRODUCT,
        returned_from_setup=setup_marker == "cancelled",
        setup_failed=setup_marker == "failed",
    )

    label = row.get("label") or row.get("name") or ""
    _, trial_end = trial_window(user)

    context = payment_disclosures(
        plan_label=label,
        monthly_usd=float(row.get("amount") or 0),
        trial_end=trial_end,
        state=state,
    ).as_context()
    context.update(
        {
            "pricing_id": row["id"],
            # The funnel's last step: a provider-confirmed account goes to its
            # first project rather than being left on this page.
            "first_product_url": first_product_url(),
            # Inline Elements form (card number/CVC on this page, confirmed
            # browser-to-Stripe). Offered only when the deployment holds both
            # keys; otherwise the hosted Checkout button stays the only path.
            "inline_card": inline_card_form_info(),
        }
    )
    return render(request, "accounts_app/payment_step.html", context)


__all__ = ["billing_settings", "payment_step"]
