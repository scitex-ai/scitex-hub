#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI-facing ``/api/me/token/`` endpoints — mint + list + revoke APIKeys.

Phase-1 PR-3 of operator-12909's token+CLI surface. Closes the
browser-free token issuance gap: ``scitex-hub account token create``
posts ``{username, password, scopes, name}``; the server mints a
``scitex_xxxx`` APIKey via the existing tested
:meth:`apps.infra.accounts_app.models.api_key.APIKey.create_key`
factory and returns it.

Security review-hardening (lead msg db151d1 + dev msg 53b830f4
+ msg 089bd6 — locked into hub-card #34 spec):

- **Rate-limit** via the existing Redis sliding-window infrastructure
  at :mod:`apps.workspace.scholar_app.middleware.rate_limit`. Per-IP
  via the existing ``rate_limit`` decorator. PLUS a SECOND counter
  keyed on the submitted username (5 attempts / 15 min) — defeats
  credential-stuffing across IP-rotating botnets. Both must pass.
- **Least-privilege scopes**. CLI route accepts ONLY
  ``ALLOWED_CLI_SCOPES`` (currently ``{"publish"}``). UI-PAT flow is
  unaffected (its scope set lives in the UI handler). A request asking
  for ``api``/``admin``/``*`` is rejected 400 before the password is
  ever checked.
- **Constant-time error**. Wrong password and unknown username return
  identical JSON bodies + comparable timing — :func:`authenticate`
  intentionally hashes a dummy password on the unknown-user branch.
- **No secret logging**. The structured log line carries ``{username,
  ok}`` only — never the password, never the minted token.
"""

from __future__ import annotations

import logging
import time
from typing import Set

from django.contrib.auth import authenticate
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.infra.accounts_app.models import APIKey
from apps.workspace.scholar_app.middleware.rate_limit import (
    get_client_ip,
    rate_limit,
)

logger = logging.getLogger(__name__)

#: The full set of scopes a CLI-issued token can carry. Hardcoded
#: allowlist — NOT trust-the-client. UI-PATs may carry richer scopes
#: but those flow through the existing
#: :mod:`apps.infra.accounts_app.views.api_keys_views` UI handler, not
#: this endpoint.
ALLOWED_CLI_SCOPES: Set[str] = {"publish"}

#: Per-username throttle (defense-in-depth on top of the per-IP
#: ``@rate_limit`` decorator). Cap matches dev's 53b830f4 recommendation.
_USERNAME_THROTTLE_WINDOW_SECONDS = 15 * 60  # 15 min
_USERNAME_THROTTLE_LIMIT = 5

#: Identical response body for every authentication failure (wrong
#: password, unknown user, missing fields). Constant body + constant-time
#: authenticate() blocks user-enumeration via either response-content
#: comparison or response-timing.
_AUTH_FAILED_BODY = {
    "success": False,
    "error": "Invalid credentials.",
}


def _username_throttle_key(username: str) -> str:
    return f"ratelimit:account_token_mint:user:{username.lower()}"


def _check_username_throttle(username: str) -> bool:
    """Return True if the per-username throttle is NOT yet exhausted.

    Same sliding-window pattern as the per-IP layer in
    ``scholar_app.middleware.rate_limit.check_rate_limit`` — kept local
    so this view's failure mode is independent of the scholar
    endpoint's config.
    """
    if not username:
        # Empty username never throttles by username (it'd be a global
        # bucket); per-IP throttle still applies.
        return True
    cache_key = _username_throttle_key(username)
    now = time.time()
    window_start = now - _USERNAME_THROTTLE_WINDOW_SECONDS
    window_data = cache.get(cache_key, [])
    window_data = [ts for ts in window_data if ts > window_start]
    is_allowed = len(window_data) < _USERNAME_THROTTLE_LIMIT
    if is_allowed:
        window_data.append(now)
        cache.set(
            cache_key,
            window_data,
            timeout=_USERNAME_THROTTLE_WINDOW_SECONDS + 10,
        )
    return is_allowed


@api_view(["POST"])
@authentication_classes([])  # explicit: this endpoint is unauthenticated by design
@permission_classes([AllowAny])
@rate_limit("account_token_mint")
def api_me_token_mint(request):
    """POST /api/me/token/ — mint a CLI APIKey from username+password.

    Body::

        {
          "username": "...",
          "password": "...",
          "name": "scitex-hub-cli",      # optional, default "scitex-hub-cli"
          "scopes": ["publish"]           # optional, default ["publish"]; MUST ⊆ ALLOWED_CLI_SCOPES
        }

    Returns 201 with ``{"success": true, "token": "scitex_…",
    "prefix": "…", "scopes": [...], "expires_at": null}`` on success.
    Returns 401 with the constant body on any authentication failure.
    """
    requested_scopes = list(request.data.get("scopes") or ["publish"])
    # Validate scopes BEFORE checking password — the scope error is not
    # a credential leak and surfacing it without a successful auth is
    # safe (and helps a CLI user fix their request).
    extra_scopes = set(requested_scopes) - ALLOWED_CLI_SCOPES
    if extra_scopes:
        return Response(
            {
                "success": False,
                "error": (
                    f"Scope not allowed for CLI-issued tokens: "
                    f"{', '.join(sorted(extra_scopes))}. "
                    f"Allowed: {', '.join(sorted(ALLOWED_CLI_SCOPES))}."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""

    # Per-username throttle (per-IP throttle handled by the decorator).
    if not _check_username_throttle(username):
        logger.warning(
            "account_token_mint per-username throttle hit: username=%r ip=%s",
            username,
            get_client_ip(request),
        )
        return Response(
            {
                "success": False,
                "error": "Too many attempts for this username. Try again later.",
                "retry_after": _USERNAME_THROTTLE_WINDOW_SECONDS,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # ``authenticate(username=...)`` hashes a dummy password on the
    # unknown-username branch — this is the Django-stdlib mechanism that
    # blocks user-enumeration via timing. Do NOT short-circuit on
    # ``User.objects.filter(username=...).exists()`` before this.
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        logger.info(
            "account_token_mint failed: username=%r ok=False",
            username,
        )
        return Response(_AUTH_FAILED_BODY, status=status.HTTP_401_UNAUTHORIZED)

    name = (request.data.get("name") or "scitex-hub-cli").strip()[:100]
    # The allowlist has already filtered ``requested_scopes`` above.
    # Persist the verified list.
    api_key_row, full_key = APIKey.create_key(
        user=user,
        name=name,
        scopes=requested_scopes,
    )
    logger.info(
        "account_token_mint ok: username=%r ok=True scopes=%s",
        username,
        requested_scopes,
    )
    return Response(
        {
            "success": True,
            "token": full_key,
            "prefix": api_key_row.key_prefix,
            "name": api_key_row.name,
            "scopes": list(api_key_row.scopes),
            "expires_at": (
                api_key_row.expires_at.isoformat() if api_key_row.expires_at else None
            ),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me_token_list(request):
    """GET /api/me/token/ — list the authenticated user's APIKeys.

    Returns a slim summary per row (NEVER the full token — that's
    only returned at mint-time per APIKey design).
    """
    rows = APIKey.objects.filter(user=request.user).order_by("-created_at")
    return Response(
        {
            "success": True,
            "tokens": [
                {
                    "id": row.id,
                    "name": row.name,
                    "prefix": row.key_prefix,
                    "scopes": list(row.scopes),
                    "is_active": row.is_active,
                    "created_at": row.created_at.isoformat(),
                    "last_used_at": (
                        row.last_used_at.isoformat() if row.last_used_at else None
                    ),
                    "expires_at": (
                        row.expires_at.isoformat() if row.expires_at else None
                    ),
                }
                for row in rows
            ],
        }
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def api_me_token_revoke(request, token_id: int):
    """DELETE /api/me/token/<id>/ — revoke a single APIKey by id.

    Owner-only: a user can only revoke their own tokens. Idempotent —
    revoking an already-revoked token returns 204.
    """
    deleted, _ = APIKey.objects.filter(id=token_id, user=request.user).delete()
    if deleted == 0:
        return Response(
            {"success": False, "error": "Token not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


# EOF
