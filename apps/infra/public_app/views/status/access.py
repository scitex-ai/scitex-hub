#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Who may see the HOST behind the status pages.

Site audit 2026-09-14 (card hub-site-audit-2-defect-backlog-20260914): every
status endpoint answered 200 to a signed-out visitor with the host's CPU,
memory, disk, GPU and network counters, 24 h of history, container images,
internal URLs and package versions. The public half of that — is the service
up, degraded or down — stays public (``/status/``, ``/api/public-status/``).
The host half is for instance admins only.

"Instance admin" is ``is_staff`` or ``is_superuser``: the same test the hub
already applies to its other operator-only surfaces (the staff-only
notification bell, billing admin, the SAC fleet mount).

The check is a plain function called INSIDE each view, not a decorator: the
routing tests assert ``resolve(path).func is <view>``, and a wrapper would
silently break that identity.
"""

from __future__ import annotations

from django.http import JsonResponse

ADMIN_ONLY_MESSAGE = "Host metrics are available to instance administrators only."


def is_instance_admin(user) -> bool:
    """True for a signed-in staff member or superuser; False for everyone else."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def admin_only_json_response(request):
    """Return a 403 JSON response for a non-admin, or None to let the view run."""
    if is_instance_admin(getattr(request, "user", None)):
        return None
    return JsonResponse(
        {"error": "forbidden", "detail": ADMIN_ONLY_MESSAGE},
        status=403,
    )


# EOF
