#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps API views — install, star, toggle, reorder, config, fork, list."""

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
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    if not can_view_module(request.user, app_module):
        return JsonResponse(
            {"success": False, "error": "Module not available."}, status=403
        )

    _, created = ModuleInstallation.objects.get_or_create(
        user=request.user,
        module=app_module,
        defaults={"is_enabled": True, "tab_order": app_module.install_count + 50},
    )

    if not created:
        return JsonResponse(
            {"success": False, "error": "Module already installed."}, status=400
        )

    app_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "message": f"Installed {app_module.module_name}.",
            "install_count": app_module.install_count,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_uninstall(request, module_name):
    """Uninstall a module (remove from user's workspace)."""
    app_module = get_object_or_404(AppsModule, module_name=module_name)

    if app_module.is_builtin:
        return JsonResponse(
            {
                "success": False,
                "error": "Built-in modules cannot be uninstalled. Use disable instead.",
            },
            status=400,
        )

    deleted, _ = ModuleInstallation.objects.filter(
        user=request.user, module=app_module
    ).delete()

    if deleted == 0:
        return JsonResponse(
            {"success": False, "error": "Module not installed."}, status=400
        )

    app_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "message": f"Uninstalled {app_module.module_name}.",
            "install_count": app_module.install_count,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_toggle(request, module_name):
    """Toggle module enabled/disabled state."""
    ensure_builtin_modules()
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    installation = ModuleInstallation.objects.filter(
        user=request.user, module=app_module
    ).first()

    if not installation:
        installation = ModuleInstallation.objects.create(
            user=request.user,
            module=app_module,
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
    app_module = get_object_or_404(AppsModule, module_name=module_name)

    _, created = ModuleStar.objects.get_or_create(user=request.user, module=app_module)
    if not created:
        return JsonResponse({"success": False, "error": "Already starred."}, status=400)

    app_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "star_count": app_module.star_count,
            "message": f"Starred {module_name}.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_unstar(request, module_name):
    """Unstar a module."""
    app_module = get_object_or_404(AppsModule, module_name=module_name)

    deleted, _ = ModuleStar.objects.filter(
        user=request.user, module=app_module
    ).delete()
    if deleted == 0:
        return JsonResponse({"success": False, "error": "Not starred."}, status=400)

    app_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "star_count": app_module.star_count,
            "message": f"Unstarred {module_name}.",
        }
    )


@login_required
@require_http_methods(["POST"])
def api_review(request, module_name):
    """Create or update a review for a module."""
    app_module = get_object_or_404(AppsModule, module_name=module_name)

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
        user=request.user, module=app_module
    ).exists()

    review, created = ModuleReview.objects.update_or_create(
        user=request.user,
        module=app_module,
        defaults={
            "rating": int(rating),
            "title": title,
            "body": body,
            "is_from_installer": is_installer,
        },
    )

    app_module.update_stats()
    return JsonResponse(
        {
            "success": True,
            "created": created,
            "avg_rating": float(app_module.avg_rating),
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

    # Build AppsModule lookup for auto-creating missing installations
    all_modules = {m.module_name: m for m in AppsModule.objects.all()}

    for idx, name in enumerate(order):
        tab_order = (idx + 1) * 10
        if name in installations:
            inst = installations[name]
            inst.tab_order = tab_order
            inst.save(update_fields=["tab_order"])
        elif name in all_modules:
            # Auto-create installation for modules without one (e.g. clew)
            inst, _created = ModuleInstallation.objects.update_or_create(
                user=request.user,
                module=all_modules[name],
                defaults={"is_enabled": True, "tab_order": tab_order},
            )
            installations[name] = inst

    return JsonResponse({"success": True, "message": "Tab order updated."})


@login_required
@require_http_methods(["POST"])
def api_update_config(request, module_name):
    """Update per-user config for a module installation."""
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    inst = ModuleInstallation.objects.filter(
        user=request.user, module=app_module
    ).first()
    if not inst:
        return JsonResponse(
            {"success": False, "error": "Module not installed."}, status=400
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."}, status=400)

    # Merge incoming keys into existing config
    config = inst.config or {}
    for key, value in data.get("config", {}).items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    inst.config = config
    inst.save(update_fields=["config"])
    return JsonResponse({"success": True, "config": inst.config})


@login_required
@require_http_methods(["POST"])
def api_fork(request, module_name):
    """Fork a user app's source project into the requester's Gitea account."""
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    if not app_module.project:
        return JsonResponse(
            {"success": False, "error": "No source project to fork."}, status=400
        )
    if app_module.is_builtin:
        return JsonResponse(
            {"success": False, "error": "Built-in modules cannot be forked."},
            status=400,
        )

    try:
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()
        owner = app_module.project.owner.username
        repo = app_module.project.slug
        result = client.fork_repository(owner, repo, organization=request.user.username)
        fork_url = f"/{request.user.username}/{result.get('name', repo)}/"
        return JsonResponse({"success": True, "url": fork_url})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@require_http_methods(["GET"])
def api_list_public(request):
    """Public JSON listing of all public apps (unauthenticated)."""
    modules = AppsModule.objects.filter(visibility="public").values(
        "module_name",
        "short_description",
        "category",
        "star_count",
        "install_count",
        "is_builtin",
        "is_verified",
        "status",
    )
    return JsonResponse({"success": True, "apps": list(modules)})


# EOF
