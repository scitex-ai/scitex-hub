#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signature check for webhooks that Gitea sends to the Hub.

Gitea signs every webhook body with the hook's secret and sends the
hex-encoded HMAC-SHA256 in ``X-Gitea-Signature``. Both Gitea → Hub
handlers (org/member sync and app-registry PR merge) change state, so they
must refuse any request that does not carry a valid signature.

The shared secret comes from ``SCITEX_HUB_GITEA_WEBHOOK_SECRET`` (Django
setting first, then the environment). With no secret configured the check
fails closed: an unconfigured deployment rejects webhooks instead of
accepting them from anyone.
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import logging
import os

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

SECRET_NAME = "SCITEX_HUB_GITEA_WEBHOOK_SECRET"
SIGNATURE_HEADER = "X-Gitea-Signature"


def gitea_webhook_secret() -> str:
    """Return the configured Gitea webhook secret, or ``""`` when unset."""
    return getattr(settings, SECRET_NAME, "") or os.environ.get(SECRET_NAME, "")


def sign_gitea_body(body: bytes, secret: str) -> str:
    """Return the signature Gitea would send for ``body`` under ``secret``."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def reject_unsigned_gitea_webhook(request) -> JsonResponse | None:
    """Return a 403/503 response when the request is not a signed Gitea webhook.

    Returns ``None`` when the signature is valid, so callers can write::

        denied = reject_unsigned_gitea_webhook(request)
        if denied:
            return denied
    """
    secret = gitea_webhook_secret()
    if not secret:
        logger.error(
            "Gitea webhook refused: %s is not configured (fail closed)", SECRET_NAME
        )
        return JsonResponse(
            {"error": "Webhook receiver is not configured."}, status=503
        )
    sent = request.headers.get(SIGNATURE_HEADER, "")
    expected = sign_gitea_body(request.body, secret)
    if not sent or not hmac.compare_digest(sent.lower(), expected):
        logger.warning("Gitea webhook refused: missing or invalid signature")
        return JsonResponse({"error": "Invalid webhook signature."}, status=403)
    return None


def require_gitea_signature(view):
    """Wrap a webhook view so it only runs for correctly signed Gitea requests."""

    @functools.wraps(view)
    def _wrapped(request, *args, **kwargs):
        denied = reject_unsigned_gitea_webhook(request)
        if denied:
            return denied
        return view(request, *args, **kwargs)

    return _wrapped


# EOF
