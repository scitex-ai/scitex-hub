#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The card-required wall, as middleware.

Card: hub-card-required-entitlement-gate-20260917. The decision lives in
:mod:`apps.infra.accounts_app.entitlement` (pure, unit-tested); this module is the
adapter that applies it to a request, so there is exactly one place where the rule is
written and exactly one place where it is enforced.

Deliberately server-side. PR #934's payment step is the surface that ASKS; a client
redirect cannot be the boundary, because the browser is the thing we are protecting
against.
"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import redirect

from .entitlement import GATED, card_required_decision, enforcement_enabled

#: API paths get a status code instead of a redirect: bouncing a JSON client to an HTML
#: payment page turns "you need a card" into "your client parsed HTML". Everything else
#: gets the redirect a browser can act on.
API_PREFIXES = ("/api/",)


class CardRequiredMiddleware:
    """Send a card-less verified user to the payment step, and nothing else."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        decision, target = card_required_decision(
            getattr(request, "path_info", "") or "",
            getattr(request, "user", None),
            enforced=enforcement_enabled(),
        )
        if decision == GATED:
            if request.path_info.startswith(API_PREFIXES):
                return JsonResponse(
                    {"error": "card_required", "detail": "Add a payment method to continue."},
                    status=403,
                )
            return redirect(target)
        return self.get_response(request)


# EOF
