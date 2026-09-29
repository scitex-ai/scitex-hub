#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provider failures as actionable cards — computed, never echoed.

Card: hub-chat-free-daily-message-allowance-20260917.
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §6 — "Never render raw
LiteLLM/provider exceptions. Normalize and sanitize at least: insufficient
provider balance; workspace/user quota reached; provider authentication failure;
rate limit with retry time; unavailable/unauthorized/deprecated model; timeout;
provider overload/outage. Each state identifies whether the user, workspace
admin, SciTeX, or provider must act; preserves the failed prompt; offers one
primary action; and exposes only a sanitized support ID under technical details."

The redaction here is structural, not a filter: the raw provider text is ACCEPTED
and DISCARDED. Nothing downstream can interpolate it, so no future copy edit can
reintroduce a leaked key or a raw stack message by accident. Anything that must
reach a human goes through the sanitized support id instead.

Boundary: deciding WHICH category a given provider failure is belongs to the
backend classifier (scitex-hub). This module is the presentation table for the
categories it hands over.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.utils.translation import gettext_lazy as _

# Who has to act for each category — named so the user is not left guessing.
ACTOR_USER = "user"
ACTOR_SCITEX = "scitex"
ACTOR_PROVIDER = "provider"

SUPPORT_URL = "/contact/"

#: category -> card. One primary action each, chosen as the shortest path that
#: actually unblocks the person reading it.
CARD_SPECS: Dict[str, Dict[str, Any]] = {
    "insufficient_balance": {
        "title": _("SciTeX could not reach the AI provider"),
        # SciTeX funds these messages, so the shortfall is ours to fix, not the
        # reader's — do not push them at a payment page for our account.
        "detail": _("This one is on us: our provider account needs attention. Nothing is wrong with your account or your project."),
        "actor": ACTOR_SCITEX,
        "action_label": _("Tell us"),
        "action_url": SUPPORT_URL,
        "action_key": "",
    },
    "quota_reached": {
        "title": _("You have used today's free messages"),
        "detail": _("Your draft is saved. You can connect your own AI provider, or add a paid allowance to keep going now."),
        "actor": ACTOR_USER,
        "action_label": _("See paid allowance"),
        "action_url": "/pricing/",
        "action_key": "",
    },
    "provider_auth": {
        "title": _("The AI provider rejected our credentials"),
        "detail": _("This is a SciTeX-side configuration problem, not something you can fix from here."),
        "actor": ACTOR_SCITEX,
        "action_label": _("Tell us"),
        "action_url": SUPPORT_URL,
        "action_key": "",
    },
    "rate_limit": {
        "title": _("The provider is rate-limiting requests"),
        "detail": _("Your message was kept. Waiting a moment before retrying usually clears it."),
        "actor": ACTOR_PROVIDER,
        "action_label": _("Retry"),
        "action_url": "",
        "action_key": "retry",
    },
    "model_unavailable": {
        "title": _("That model is not available right now"),
        "detail": _("Pick a different model — your message is still here."),
        "actor": ACTOR_USER,
        "action_label": _("Choose another model"),
        "action_url": "",
        "action_key": "choose-model",
    },
    "timeout": {
        "title": _("The provider took too long to answer"),
        "detail": _("Your message was kept. Retrying checks the same request without sending it twice."),
        "actor": ACTOR_PROVIDER,
        "action_label": _("Retry"),
        "action_url": "",
        "action_key": "retry",
    },
    "provider_outage": {
        "title": _("The AI provider is having an outage"),
        "detail": _("We are tracking it. Your message was kept. Retrying checks the same request without sending it twice."),
        "actor": ACTOR_PROVIDER,
        "action_label": _("Retry"),
        "action_url": "",
        "action_key": "retry",
    },
}

#: Fallback card for a category this client does not know yet. It still says who
#: acts and still offers a way forward — an unknown failure is not a blank screen.
GENERIC_CARD: Dict[str, Any] = {
    "title": _("Something went wrong talking to the AI provider"),
    "detail": _("Your message was kept. The technical details are recorded with the support id below, so you do not have to copy an error."),
    "actor": ACTOR_SCITEX,
    "action_label": _("Tell us"),
    "action_url": SUPPORT_URL,
    "action_key": "",
}


def error_card(
    category: Optional[str] = None,
    *,
    provider_message: str = "",
    retry_after: str = "",
    support_id: str = "",
) -> Dict[str, Any]:
    """Build the card for ``category``.

    ``provider_message`` is deliberately read and thrown away — see the module
    docstring. It exists in the signature so callers can pass it by habit without
    ever creating a path where it reaches a template.
    """
    del provider_message  # structural redaction: accepted, never used

    spec = CARD_SPECS.get(category or "", GENERIC_CARD)
    card = dict(spec)
    card["category"] = category if category in CARD_SPECS else "unknown"
    card["retry_after"] = retry_after or ""
    card["support_id"] = support_id or ""
    return card


# EOF
