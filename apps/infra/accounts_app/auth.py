#!/usr/bin/env python3
# Timestamp: 2026-02-14
# File: apps/accounts_app/auth.py

"""API Key authentication helper for SciTeX Hub."""

from __future__ import annotations

from typing import Optional

from django.utils import timezone

from .models.api_key import APIKey


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

    raw_key = auth_header[7:]
    key_hash = APIKey.hash_key(raw_key)

    try:
        api_key = APIKey.objects.select_related("user").get(
            key_hash=key_hash, is_active=True
        )
    except APIKey.DoesNotExist:
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < timezone.now():
        return None

    # Update last_used timestamp
    APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

    return api_key


# EOF
