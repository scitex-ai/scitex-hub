#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marketplace API views — install, star, review, submit, and admin endpoints."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models import (
    AppsModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
)
from .helpers import can_view_module, ensure_builtin_modules


@login_required
@require_http_methods(["POST"])
def api_install(request, module_name):
    """Install a module (add to user's workspace)."""
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)
    if not can_view_module(request.user, mp_module):
        return JsonResponse(
            {"success": False, "error": "Module not available."}, status=403
        )

    _, created = ModuleInstallation.objects.get_or_create(
        user=request.user,
        module=mp_module,
        defaults={"is_enabled": True, "tab_order": mp_module.install_count + 50},
    )

    if not created:
        return JsonResponse(
            {"success": False, "error": "Module already installed."}, status=400
        )

    mp_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "message": f"Installed {mp_module.module_name}.",
            "install_count": mp_module.install_count,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_uninstall(request, module_name):
    """Uninstall a module (remove from user's workspace)."""
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)

    if mp_module.is_builtin:
        return JsonResponse(
            {
                "success": False,
                "error": "Built-in modules cannot be uninstalled. Use disable instead.",
            },
            status=400,
        )

    deleted, _ = ModuleInstallation.objects.filter(
        user=request.user, module=mp_module
    ).delete()

    if deleted == 0:
        return JsonResponse(
            {"success": False, "error": "Module not installed."}, status=400
        )

    mp_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "message": f"Uninstalled {mp_module.module_name}.",
            "install_count": mp_module.install_count,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_toggle(request, module_name):
    """Toggle module enabled/disabled state."""
    ensure_builtin_modules()
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)
    installation = ModuleInstallation.objects.filter(
        user=request.user, module=mp_module
    ).first()

    if not installation:
        installation = ModuleInstallation.objects.create(
            user=request.user,
            module=mp_module,
            is_enabled=False,
            tab_order=50,
        )
    else:
        installation.is_enabled = not installation.is_enabled
        installation.save(update_fields=["is_enabled"])

    return JsonResponse(
        {
            "success": True,
            "is_enabled": installation.is_enabled,
            "message": f"{'Enabled' if installation.is_enabled else 'Disabled'} {module_name}.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_star(request, module_name):
    """Star a module."""
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)

    _, created = ModuleStar.objects.get_or_create(user=request.user, module=mp_module)
    if not created:
        return JsonResponse({"success": False, "error": "Already starred."}, status=400)

    mp_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "star_count": mp_module.star_count,
            "message": f"Starred {module_name}.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_unstar(request, module_name):
    """Unstar a module."""
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)

    deleted, _ = ModuleStar.objects.filter(user=request.user, module=mp_module).delete()
    if deleted == 0:
        return JsonResponse({"success": False, "error": "Not starred."}, status=400)

    mp_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "star_count": mp_module.star_count,
            "message": f"Unstarred {module_name}.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_review(request, module_name):
    """Create or update a review for a module."""
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    rating = data.get("rating")
    title = data.get("title", "")
    body = data.get("body", "")

    if not rating or not (1 <= int(rating) <= 5):
        return JsonResponse(
            {"success": False, "error": "Rating must be 1-5."}, status=400
        )

    is_installer = ModuleInstallation.objects.filter(
        user=request.user, module=mp_module
    ).exists()

    review, created = ModuleReview.objects.update_or_create(
        user=request.user,
        module=mp_module,
        defaults={
            "rating": int(rating),
            "title": title,
            "body": body,
            "is_from_installer": is_installer,
        },
    )

    mp_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "created": created,
            "avg_rating": float(mp_module.avg_rating),
            "message": f"{'Created' if created else 'Updated'} review.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_reorder(request):
    """Reorder user's installed modules."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    order = data.get("order", [])
    if not isinstance(order, list):
        return JsonResponse(
            {"success": False, "error": "order must be a list of module names."},
            status=400,
        )

    installations = {
        inst.module.module_name: inst
        for inst in ModuleInstallation.objects.filter(user=request.user).select_related(
            "module"
        )
    }

    for idx, name in enumerate(order):
        if name in installations:
            inst = installations[name]
            inst.tab_order = (idx + 1) * 10
            inst.save(update_fields=["tab_order"])

    return JsonResponse({"success": True, "message": "Tab order updated."})


@login_required
@require_http_methods(["POST"])
def api_submit_for_review(request, module_name):
    """Submit a private module for marketplace publication review."""
    mp_module = get_object_or_404(
        MarketplaceModule, module_name=module_name, author=request.user
    )

    from ..models import ModuleSubmission
    from ..validators import validate_module_for_publication

    errors = validate_module_for_publication(mp_module)
    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)

    if ModuleSubmission.objects.filter(module=mp_module, status="pending").exists():
        return JsonResponse(
            {"success": False, "error": "A submission is already pending review."},
            status=400,
        )

    ModuleSubmission.objects.create(module=mp_module, submitted_by=request.user)
    return JsonResponse({"success": True, "message": "Submitted for review."})


@login_required
@require_http_methods(["POST"])
def api_review_submission(request, submission_id):
    """Admin approves or rejects a module submission."""
    if not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Staff only."}, status=403)

    from django.utils import timezone

    from ..models import ModuleSubmission

    submission = get_object_or_404(ModuleSubmission, id=submission_id)
    if submission.status != "pending":
        return JsonResponse(
            {"success": False, "error": "Submission already reviewed."}, status=400
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    action = data.get("action")  # "approve" or "reject"
    note = data.get("note", "")

    if action == "approve":
        submission.status = "approved"
        submission.reviewer = request.user
        submission.review_note = note
        submission.reviewed_at = timezone.now()
        submission.save()
        submission.module.visibility = "public"
        submission.module.is_verified = True
        submission.module.save(update_fields=["visibility", "is_verified"])
        return JsonResponse(
            {"success": True, "message": f"Approved {submission.module.module_name}."}
        )
    elif action == "reject":
        submission.status = "rejected"
        submission.reviewer = request.user
        submission.review_note = note
        submission.reviewed_at = timezone.now()
        submission.save()
        return JsonResponse(
            {"success": True, "message": f"Rejected {submission.module.module_name}."}
        )

    return JsonResponse(
        {"success": False, "error": "action must be 'approve' or 'reject'."},
        status=400,
    )


# EOF
