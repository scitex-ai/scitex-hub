#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew Registry API — hash registration and verification endpoints."""

from __future__ import annotations

import json
import logging
import re

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..models import HashRegistration

logger = logging.getLogger(__name__)

_HASH_MAX_LENGTH = 64
_VALID_SOURCE_TYPES = {"session", "file", "stamp", "manual"}
_HASH_PATTERN = re.compile(r"^[a-fA-F0-9]+$")


def _authenticate_request(request):
    """Authenticate via session cookie or API key. Returns user or None."""
    if request.user.is_authenticated:
        return request.user
    from apps.infra.accounts_app.auth import authenticate_api_key

    api_key = authenticate_api_key(request)
    if api_key:
        return api_key.user
    return None


@require_http_methods(["POST"])
def register_hash(request):
    """Register a hash with server-side timestamp.

    POST /clew/register/
    Body: {hash, source_type?, session_id?, metadata?}

    Authentication: session cookie or API key (Authorization: Bearer <key>).
    """
    user = _authenticate_request(request)
    if not user:
        return JsonResponse(
            {"success": False, "error": "Authentication required"},
            status=401,
        )

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body"},
            status=400,
        )

    hash_value = body.get("hash", "").strip()
    if not hash_value:
        return JsonResponse(
            {"success": False, "error": "Missing required field: hash"},
            status=400,
        )

    if len(hash_value) > _HASH_MAX_LENGTH:
        return JsonResponse(
            {
                "success": False,
                "error": f"Hash exceeds maximum length of {_HASH_MAX_LENGTH}",
            },
            status=400,
        )

    if not _HASH_PATTERN.match(hash_value):
        return JsonResponse(
            {"success": False, "error": "Hash must be hexadecimal"},
            status=400,
        )

    source_type = body.get("source_type", "manual")
    if source_type not in _VALID_SOURCE_TYPES:
        return JsonResponse(
            {
                "success": False,
                "error": f"Invalid source_type. Must be one of: {', '.join(sorted(_VALID_SOURCE_TYPES))}",
            },
            status=400,
        )

    session_id = body.get("session_id", "")
    metadata = body.get("metadata", {})

    registration, created = HashRegistration.objects.update_or_create(
        hash=hash_value,
        user=user,
        defaults={
            "source_type": source_type,
            "session_id": session_id,
            "metadata": metadata,
        },
    )

    return JsonResponse(
        {
            "success": True,
            "created": created,
            "data": {
                "hash": registration.hash,
                "registered_at": registration.registered_at.isoformat(),
                "source_type": registration.source_type,
                "session_id": registration.session_id,
            },
        },
        status=201 if created else 200,
    )


@require_http_methods(["GET"])
def verify_hash(request, hash_value):
    """Verify whether a hash has been registered.

    GET /clew/verify/<hash>/

    Public endpoint — returns anonymized proof data (no usernames).
    Third parties (reviewers, journals) can verify without a SciTeX account.
    """
    if len(hash_value) > _HASH_MAX_LENGTH or not _HASH_PATTERN.match(hash_value):
        return JsonResponse(
            {"success": False, "error": "Invalid hash format"},
            status=400,
        )

    registrations = HashRegistration.objects.filter(hash=hash_value)

    if not registrations.exists():
        return JsonResponse(
            {
                "success": True,
                "registered": False,
                "hash": hash_value,
                "registration_count": 0,
            }
        )

    first = registrations.order_by("registered_at").first()

    return JsonResponse(
        {
            "success": True,
            "registered": True,
            "hash": hash_value,
            "registration_count": registrations.count(),
            "first_registered_at": first.registered_at.isoformat(),
            "source_type": first.source_type,
        }
    )


_BADGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">
  <linearGradient id="a" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <rect rx="3" width="{width}" height="20" fill="#555"/>
  <rect rx="3" x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
  <rect rx="3" width="{width}" height="20" fill="url(#a)"/>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_x}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_x}" y="14">{label}</text>
    <text x="{value_x}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>"""


@require_http_methods(["GET"])
def badge(request, hash_value):
    """Return an SVG badge for a registered hash.

    GET /clew/badge/<hash>/?level=L3

    Verification Levels:
    - L1 (cache)      — hash comparison only (local)
    - L2 (rerun)      — full re-execution (local)
    - L3 (registered) — L2 + Clew Registry timestamp (server)

    Query params:
    - level: L1, L2, or L3 (default: auto-detect from registry)
    """
    from django.http import HttpResponse

    level = request.GET.get("level", "").upper()
    registration = HashRegistration.objects.filter(hash=hash_value).first()

    if level == "L1":
        label = "clew L1"
        value = "cache verified"
        color = "#2196f3"  # blue
    elif level == "L2":
        label = "clew L2"
        value = "reproducible"
        color = "#ff9800"  # orange
    elif registration:
        label = "clew L3"
        value = "registered"
        color = "#4c1"  # green
    else:
        label = "clew"
        value = "not registered"
        color = "#e05d44"  # red

    label_width = len(label) * 7 + 10
    value_width = len(value) * 7 + 10
    width = label_width + value_width

    svg = _BADGE_SVG.format(
        width=width,
        label_width=label_width,
        value_width=value_width,
        color=color,
        label=label,
        value=value,
        label_x=label_width / 2,
        value_x=label_width + value_width / 2,
    )

    return HttpResponse(svg, content_type="image/svg+xml")


# EOF
