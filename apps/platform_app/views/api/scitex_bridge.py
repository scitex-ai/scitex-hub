#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/platform_app/views/api/scitex_bridge.py
"""
REST API view for the ScitexBridge.

Endpoint
--------
POST /platform/api/scitex/<module>/<function>/

Body (JSON)
-----------
{
    "args":   [...],          // positional arguments (optional)
    "kwargs": {...},          // keyword arguments   (optional)
    "project_id": "<uuid>"   // optional — scopes the call to a project
}

Response (JSON)
---------------
{
    "success": true,
    "result":  <serialized return value>
}
— or on error —
{
    "success": false,
    "error":   "<message>",
    "code":    "<ERROR_CODE>"
}
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.platform_app.services.scitex_bridge import ScitexBridge
from apps.platform_app.services.scitex_bridge.bridge import (
    ALLOWED_MODULES,
    ScitexBridgeError,
)

logger = logging.getLogger(__name__)


@login_required
@require_POST
def scitex_call(request, module: str, function: str) -> JsonResponse:
    """
    Call ``scitex.<module>.<function>`` on behalf of the authenticated user.

    Login is required — anonymous callers receive HTTP 302 redirect.
    """
    # --- Parse request body -------------------------------------------------
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        return _error(f"Invalid JSON in request body: {exc}", "INVALID_JSON", 400)

    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})
    project_id = payload.get("project_id")

    if not isinstance(args, list):
        return _error("'args' must be a JSON array.", "INVALID_ARGS", 400)
    if not isinstance(kwargs, dict):
        return _error("'kwargs' must be a JSON object.", "INVALID_KWARGS", 400)

    # --- Guard: module allowlist (fast path before bridge init) -------------
    if module not in ALLOWED_MODULES:
        return _error(
            f"Module '{module}' is not allowed. "
            f"Allowed modules: {sorted(ALLOWED_MODULES)}",
            "MODULE_NOT_ALLOWED",
            403,
        )

    # --- Guard: no private functions ----------------------------------------
    if function.startswith("_"):
        return _error(
            f"Access to private function '{function}' is not allowed.",
            "PRIVATE_FUNCTION",
            403,
        )

    # --- Resolve project (optional) -----------------------------------------
    project = _resolve_project(project_id, request.user)

    # --- Dispatch via bridge ------------------------------------------------
    bridge = ScitexBridge(project=project, user=request.user)
    try:
        result = bridge.call(module, function, *args, **kwargs)
    except ScitexBridgeError as exc:
        logger.warning(
            "ScitexBridge call failed [user=%s module=%s fn=%s]: %s",
            request.user.username,
            module,
            function,
            exc,
        )
        return _error(str(exc), "BRIDGE_ERROR", 400)
    except Exception as exc:
        logger.exception(
            "Unexpected error in ScitexBridge [user=%s module=%s fn=%s]",
            request.user.username,
            module,
            function,
        )
        return _error(
            f"Unexpected error: {type(exc).__name__}: {exc}",
            "INTERNAL_ERROR",
            500,
        )

    return JsonResponse({"success": True, "result": result})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_project(project_id, user):
    """Return Project instance for project_id if provided and owned by user."""
    if not project_id:
        return None
    try:
        from apps.project_app.models import Project

        return Project.objects.get(pk=project_id, owner=user)
    except Exception as exc:
        logger.debug("Could not resolve project_id=%s: %s", project_id, exc)
        return None


def _error(message: str, code: str, status: int) -> JsonResponse:
    return JsonResponse(
        {"success": False, "error": message, "code": code},
        status=status,
    )


# EOF
