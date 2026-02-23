#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Maker — CRUD API endpoints for user modules."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from apps.project_app.services.project_utils import get_current_project

from ..models import ModuleExecution, UserModule
from ._helpers import has_forbidden_patterns

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_create_module(request):
    """Create a new user module from JSON payload."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    label = data.get("label", "").strip()
    source_code = data.get("source_code", "").strip()
    icon = data.get("icon", "fa-puzzle-piece").strip()
    category = data.get("category", "utility").strip()
    description = data.get("description", "").strip()

    if not label:
        return JsonResponse(
            {"success": False, "error": "Label is required."}, status=400
        )
    if not source_code:
        return JsonResponse(
            {"success": False, "error": "Source code is required."}, status=400
        )

    if has_forbidden_patterns(source_code):
        return JsonResponse(
            {"success": False, "error": "Source code contains forbidden patterns."},
            status=400,
        )

    slug = slugify(label)[:60]
    if not slug:
        return JsonResponse(
            {"success": False, "error": "Label must produce a valid slug."},
            status=400,
        )

    if UserModule.objects.filter(author=request.user, slug=slug).exists():
        return JsonResponse(
            {"success": False, "error": f"Module with slug '{slug}' already exists."},
            status=400,
        )

    user_module = UserModule.objects.create(
        slug=slug,
        label=label,
        author=request.user,
        source_code=source_code,
        icon=icon,
        category=category,
        description=description[:300],
    )

    return JsonResponse(
        {
            "success": True,
            "slug": user_module.slug,
            "message": f"Module '{label}' created.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_update_module(request, slug):
    """Update an existing user module."""
    user_module = get_object_or_404(
        UserModule, slug=slug, author=request.user, is_active=True
    )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    source_code = data.get("source_code")
    if source_code is not None:
        source_code = source_code.strip()
        if has_forbidden_patterns(source_code):
            return JsonResponse(
                {"success": False, "error": "Source code contains forbidden patterns."},
                status=400,
            )
        user_module.source_code = source_code

    for field in ("label", "icon", "category", "description", "visibility"):
        value = data.get(field)
        if value is not None:
            setattr(user_module, field, str(value).strip()[:300])

    user_module.save()

    return JsonResponse(
        {
            "success": True,
            "slug": user_module.slug,
            "message": f"Module '{user_module.label}' updated.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_run_module(request, slug):
    """Trigger module execution (placeholder for MVP).

    In the full implementation this will delegate to sandboxed execution
    via scitex_cloud.module._runner.run_module().
    For now it creates a success execution record as a placeholder.
    """
    user_module = get_object_or_404(UserModule, slug=slug, is_active=True)

    if user_module.visibility == "private" and user_module.author != request.user:
        return JsonResponse(
            {"success": False, "error": "Permission denied."}, status=403
        )

    current_project = get_current_project(request)

    execution = ModuleExecution.objects.create(
        module=user_module,
        user=request.user,
        project=current_project,
        status="success",
        output_json=[
            {
                "type": "text",
                "content": (
                    f"Module '{user_module.label}' executed successfully (placeholder). "
                    "Real execution engine coming soon."
                ),
            }
        ],
    )

    from django.utils import timezone

    user_module.run_count += 1
    user_module.last_run_at = timezone.now()
    user_module.save(update_fields=["run_count", "last_run_at"])

    return JsonResponse(
        {
            "success": True,
            "execution_id": execution.id,
            "status": execution.status,
            "outputs": execution.output_json,
            "message": f"Module '{user_module.label}' executed.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_delete_module(request, slug):
    """Soft-delete a user module (set is_active=False)."""
    user_module = get_object_or_404(
        UserModule, slug=slug, author=request.user, is_active=True
    )

    user_module.is_active = False
    user_module.save(update_fields=["is_active"])

    return JsonResponse(
        {
            "success": True,
            "message": f"Module '{user_module.label}' deleted.",
        }
    )


# EOF
