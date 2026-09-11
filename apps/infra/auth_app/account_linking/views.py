#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``GET /auth/api/whoami/`` — the session surface the cards board consumes.

The phone flow this exists for: log in on scitex.ai, open the board, see YOUR
cards. The board's problem is that a Django session cookie tells it the
browser is authenticated but not which cards identity that maps to. This
endpoint answers exactly that and nothing more.

DELIBERATELY NOT A NEW TOKEN TYPE. Hub already mints API keys
(``/api/me/token/``) and already has session auth; inventing a third
credential would add a third thing to leak, rotate and revoke. This reads
whatever authentication the request already carries.

WHAT IT DOES NOT RETURN, and why (the operator asked for security to be
weighted heavily here, and an identity endpoint is a natural over-sharer):

* the OIDC ``subject`` — a provider-internal identifier the board has no use
  for. Returning it would leak a stable cross-site correlator for no gain.
* any other user's data, under any parameter. There is no lookup-by-id form
  of this endpoint on purpose: it answers only "who is THIS request", so
  there is no object reference for an attacker to tamper with.
* anything at all when unauthenticated, beyond ``authenticated: false``.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def whoami(request):
    """Return the requester's own identity, or ``authenticated: false``.

    Always 200: this is a state query, not a guarded resource, and the board
    renders a signed-out panel from the negative answer. A 401 here would
    make the board's fetch indistinguishable from a real failure.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return JsonResponse({"authenticated": False, "login_url": "/auth/login/"})

    from django.conf import settings

    from .models import LinkedIdentity, VerifiedEmail

    emails = list(
        VerifiedEmail.objects.filter(user=user)
        .order_by("email")
        .values_list("email", flat=True)
    )

    # The board keys on ONE cards user. Several identity rows can carry the
    # same id (one per provider); take the most recent non-blank so a stale
    # blank from a cards outage does not mask a later successful write.
    cards_user_id = (
        LinkedIdentity.objects.filter(user=user)
        .exclude(cards_user_id="")
        .order_by("-last_login_at")
        .values_list("cards_user_id", flat=True)
        .first()
    )

    issuers = sorted(
        set(
            LinkedIdentity.objects.filter(user=user).values_list(
                "issuer", flat=True
            )
        )
    )

    return JsonResponse(
        {
            "authenticated": True,
            "username": user.get_username(),
            "cards_user_id": cards_user_id or None,
            "verified_emails": emails,
            # Issuers only — never the subjects. Enough for the board to show
            # "signed in with Google", useless as a correlator.
            "issuers": issuers,
            "instance": str(
                getattr(settings, "SCITEX_INSTANCE_NAME", "") or ""
            ),
        }
    )


__all__ = ["whoami"]

# EOF
