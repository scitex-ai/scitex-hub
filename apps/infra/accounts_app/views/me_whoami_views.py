#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``GET /api/me/`` — "who is this credential".

Sits next to :mod:`apps.infra.accounts_app.views.me_token_views` (the
``/api/me/token/`` mint/list/revoke surface) and shares its Redis
sliding-window rate limiter.

Contract (card ``hub-api-me-whoami-endpoint-for-api-keys-20260905``):

200 — body has EXACTLY these keys::

    {"id", "username", "is_staff", "is_superuser", "plan", "key_id", "expires_at"}

- ``id``: ``UserProfile.public_id`` — an opaque, stable, never-reused UUID.
  Never ``User.pk``: a sequential pk leaks user count and registration order
  into every agent/client log that records it, and cannot be withdrawn once
  published.
- ``plan``: the active subscription's plan id, or ``null``. Always present.
- ``key_id``: the APIKey id when authenticated by key, ``null`` otherwise.
- ``expires_at``: ISO-8601 key expiry, or ``null`` (session/JWT callers and
  non-expiring keys).
- No email, display name, token or secret fields.

401 — ONLY facts about the credential: ``{"error": "missing" | "invalid" |
"expired" | "revoked"}``. An anonymous request is ``missing``, never 200.

Hub-side failures (auth backend raising, DB error) are NOT caught here: they
propagate to Django's handler and become 5xx. Nothing in this module may
translate an unexpected exception into a 401 — that would tell a client its
valid credential is bad and make it throw the credential away.

Accepted credentials, checked in this order:

1. ``Authorization: Bearer scitex_…`` — a UI/CLI API key.
2. ``Authorization: Bearer <jwt>`` — SimpleJWT access token. Kept because the
   CLI's workspace login (``scitex_hub._cli._workspace_auth``) already probes
   this URL with a JWT; the response shape is the session shape.
3. A logged-in session cookie.

A presented Authorization header is judged on its own: a bad header is a 401
even if a session cookie is also attached.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.infra.accounts_app.auth import resolve_api_key
from apps.infra.accounts_app.models import APIKey, UserProfile
from apps.workspace.scholar_app.middleware.rate_limit import rate_limit

MISSING = "missing"
INVALID = "invalid"
EXPIRED = "expired"
REVOKED = "revoked"

_API_KEY_PREFIX = "scitex_"


def _unauthorized(reason: str) -> JsonResponse:
    response = JsonResponse({"error": reason}, status=401)
    response["WWW-Authenticate"] = 'Bearer realm="api"'
    return response


def _resolve_jwt(raw_token: str):
    """Return ``(user, None)`` for a usable JWT access token, else ``(None, reason)``.

    Only SimpleJWT's own credential exceptions map to a reason; anything else
    (DB down while loading the user, bad signing config) propagates.
    """
    from rest_framework.exceptions import AuthenticationFailed
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import (
        ExpiredTokenError,
        InvalidToken,
        TokenError,
    )
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        validated = AccessToken(raw_token)
    except ExpiredTokenError:
        return None, EXPIRED
    except TokenError:
        return None, INVALID
    try:
        user = JWTAuthentication().get_user(validated)
    except (InvalidToken, AuthenticationFailed):
        # Unknown user id, inactive user, or a token issued before a
        # password change: the credential no longer names a usable user.
        return None, INVALID
    return user, None


def _active_plan_id(user):
    """The user's active plan id (``SubscriptionPlan.plan_type``) or ``None``."""
    from apps.infra.public_app.models import Subscription

    subscription = (
        Subscription.objects.filter(
            user=user,
            status__in=["trial", "active"],
            current_period_end__gt=timezone.now(),
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    return subscription.plan.plan_type if subscription else None


def _identity_payload(user, api_key: APIKey | None) -> dict:
    profile, _created = UserProfile.objects.get_or_create(user=user)
    expires_at = api_key.expires_at if api_key is not None else None
    return {
        "id": str(profile.public_id),
        "username": user.username,
        "is_staff": bool(user.is_staff),
        "is_superuser": bool(user.is_superuser),
        "plan": _active_plan_id(user),
        "key_id": api_key.id if api_key is not None else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@require_GET
@rate_limit("api_me")
def api_me(request):
    """GET /api/me/ — describe the presented credential's user. See module doc."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header:
        scheme, _, credential = auth_header.partition(" ")
        credential = credential.strip()
        if scheme != "Bearer" or not credential:
            return _unauthorized(INVALID)
        if credential.startswith(_API_KEY_PREFIX):
            api_key, reason = resolve_api_key(credential)
            if api_key is None:
                return _unauthorized(reason)
            if not api_key.user.is_active:
                return _unauthorized(INVALID)
            APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
            return JsonResponse(_identity_payload(api_key.user, api_key))
        user, reason = _resolve_jwt(credential)
        if user is None:
            return _unauthorized(reason)
        return JsonResponse(_identity_payload(user, None))

    # No Authorization header: a session cookie is the only remaining
    # credential. Touching request.user runs the session auth backend; if
    # that raises, it propagates as a 5xx by design.
    if request.user.is_authenticated:
        return JsonResponse(_identity_payload(request.user, None))
    return _unauthorized(MISSING)


# EOF
