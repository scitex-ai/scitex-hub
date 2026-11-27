"""Site-wide in-app alert: the highest unread spend alert, or a payment problem.

Cheap on purpose (two indexed lookups, no usage computation): it runs on every
page. The alert rows are written by the sweep / the settings page.
"""

from __future__ import annotations


def spend_banner(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    if request.path.startswith("/accounts/settings/spend/"):
        return {}  # the page itself shows the full state
    try:
        from .models import BillingAccountState
        from .services.gate import billing_url, spend_settings_url
        from .services.notify import unread_alerts

        state = (
            BillingAccountState.objects.filter(user=user)
            .values_list("state", "grace_until")
            .first()
        )
        if state and state[0] in ("past_due", "restricted"):
            return {
                "spend_banner": {
                    "kind": state[0],
                    "grace_until": state[1],
                    "url": billing_url(),
                }
            }
        # 100 % stays up all month (new work is refused, the holder must know
        # why); 80 % shows until the holder has opened Spend controls.
        from .models import SpendAlert
        from .services.usage import period_bounds

        period, _, _ = period_bounds()
        top = (
            SpendAlert.objects.filter(user=user, period=period, threshold=100).first()
            or unread_alerts(user)
            .filter(threshold__gte=80)
            .order_by("-threshold")
            .first()
        )
    except Exception:  # never break a page over a banner
        return {}
    if top is None:
        return {}
    return {
        "spend_banner": {
            "kind": f"cap{top.threshold}",
            "threshold": top.threshold,
            "spend_usd": top.spend_usd,
            "cap_usd": top.cap_usd,
            "url": spend_settings_url(),
        }
    }
