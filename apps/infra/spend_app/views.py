"""Settings > Spend controls: usage this month, the cap, alerts, cancellation."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .models import BillingAccountEvent, BillingAccountState, SpendAlert, SpendControl
from .services import cancellation, gate, notify, policy


def _status_json(status: gate.AccountStatus) -> dict:
    snap = status.snapshot
    return {
        "period": snap.period,
        "plan": status.terms.pricing_id,
        "standing": status.standing.value,
        "mode": status.mode,
        "cap_usd": str(status.cap_usd),
        "cap_is_plan_default": status.cap_is_default,
        "max_cap_usd": str(status.terms.max_cap_usd),
        "spend_usd": str(status.spend_usd),
        "percent": status.percent,
        "level": int(status.level),
        "provisional": snap.provisional,
        "lines": [
            {
                "resource": l.resource,
                "quantity": str(l.quantity),
                "unit": l.unit,
                "amount_usd": str(l.amount_usd),
                "source": l.source,
                "provisional": l.provisional,
                "note": l.note,
            }
            for l in snap.lines
        ],
    }


@login_required
def spend_settings(request):
    status = gate.account_status(request.user, fresh=True)
    # The page is also an evaluation point, so a holder who just crossed a
    # threshold sees it here even before the next sweep.
    notify.evaluate_alerts(request.user, status)
    status = gate.account_status(request.user)
    alerts = list(
        SpendAlert.objects.filter(user=request.user).order_by("-created_at")[:12]
    )
    notify.mark_read(request.user)
    from .services.enforcement import verdict_for

    verdict = verdict_for(status)
    context = {
        "active": "spend",
        "status": status,
        "lines": status.snapshot.lines,
        "alerts": alerts,
        "verdict": verdict,
        "new_work_refused": policy.decide(
            status.standing, status.level, policy.Action.START_COMPUTE
        ).refused,
        "eligibility": cancellation.eligibility(request.user),
        "events": BillingAccountEvent.objects.filter(user=request.user)[:10],
        "state_row": BillingAccountState.objects.filter(user=request.user).first(),
    }
    return render(request, "spend_app/spend_settings.html", context)


@login_required
@require_POST
def set_cap(request):
    raw = (request.POST.get("monthly_cap_usd") or "").strip()
    terms = gate.effective_cap(request.user)[2]
    with transaction.atomic():
        row, _created = SpendControl.objects.select_for_update().get_or_create(
            user=request.user
        )
        before = row.monthly_cap_usd
        if raw == "" or request.POST.get("reset") == "1":
            row.monthly_cap_usd = None
        else:
            try:
                row.monthly_cap_usd = policy.clamp_cap(
                    Decimal(raw), max_cap=terms.max_cap_usd
                )
            except (InvalidOperation, ValueError) as exc:
                messages.error(request, str(exc) or _("Enter an amount in USD."))
                return redirect("spend_app:settings")
        row.save()
        BillingAccountEvent.objects.create(
            user=request.user,
            kind="cap_changed",
            detail={"from": str(before), "to": str(row.monthly_cap_usd)},
        )
    # Thresholds the NEW cap no longer crosses may fire again later this month,
    # and the 100 % grace window restarts if the cap is reached again.
    status = gate.account_status(request.user, fresh=True)
    SpendAlert.objects.filter(
        user=request.user,
        period=status.snapshot.period,
        threshold__gt=int(status.level),
    ).delete()
    messages.success(
        request,
        _("Monthly cap set to $%(cap)s.") % {"cap": f"{status.cap_usd:.2f}"},
    )
    return redirect("spend_app:settings")


@login_required
@require_POST
def cancel_within_window(request):
    try:
        result = cancellation.cancel_with_actual_usage(request.user)
    except cancellation.CancellationRefused as exc:
        messages.error(request, str(exc))
        return redirect("spend_app:settings")
    except Exception as exc:  # provider failure: say so, change nothing local
        import logging

        logging.getLogger("scitex").exception(
            "cancellation failed for %s", request.user.pk
        )
        messages.error(
            request,
            _("The cancellation could not be completed (%(err)s). Nothing was changed.")
            % {"err": type(exc).__name__},
        )
        return redirect("spend_app:settings")
    messages.success(
        request,
        _(
            "Your plan is cancelled. You are billed only for actual usage "
            "($%(usd)s). Your data is kept."
        )
        % {"usd": f"{result['usage_cents'] / 100:.2f}"},
    )
    return redirect("spend_app:settings")


@login_required
@require_GET
def status_api(request):
    return JsonResponse(_status_json(gate.account_status(request.user)))


__all__ = ["cancel_within_window", "set_cap", "spend_settings", "status_api"]
