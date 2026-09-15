#!/usr/bin/env python3
# Timestamp: 2026-02-14
# File: apps/accounts_app/auth.py

"""API Key authentication helper for SciTeX Hub."""

from __future__ import annotations

from typing import Optional, Tuple

from django.utils import timezone

from .models.api_key import APIKey

#: Credential-fact reasons a presented API key can fail with. These are
#: facts about the CREDENTIAL, never about the hub: a DB error or any other
#: hub-side failure propagates as an exception instead of mapping here.
KEY_INVALID = "invalid"
KEY_EXPIRED = "expired"
KEY_REVOKED = "revoked"


def resolve_api_key(raw_key: str) -> Tuple[Optional[APIKey], Optional[str]]:
    """Look up a raw ``scitex_…`` key and say WHY it fails when it does.

    Returns ``(api_key, None)`` for a usable key, else ``(None, reason)``
    where reason is one of ``KEY_INVALID`` (no such key), ``KEY_REVOKED``
    (the row exists but was deactivated) or ``KEY_EXPIRED``. Does not
    touch ``last_used_at`` and does not catch database errors.
    """
    if not raw_key:
        return None, KEY_INVALID
    key_hash = APIKey.hash_key(raw_key)
    api_key = APIKey.objects.select_related("user").filter(key_hash=key_hash).first()
    if api_key is None:
        return None, KEY_INVALID
    if not api_key.is_active:
        return None, KEY_REVOKED
    if api_key.expires_at and api_key.expires_at < timezone.now():
        return None, KEY_EXPIRED
    return api_key, None


def authenticate_api_key(request) -> Optional[APIKey]:
    """Extract and validate API key from Authorization header.

    Expects: Authorization: Bearer scitex_xxxx...

    Parameters
    ----------
    request : HttpRequest
        Django request object.

    Returns
    -------
    APIKey or None
        Validated APIKey instance, or None if invalid/missing.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None

    api_key, _reason = resolve_api_key(auth_header[7:])
    if api_key is None:
        return None

    # Update last_used timestamp
    APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

    return api_key


# EOF
