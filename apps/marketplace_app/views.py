#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marketplace views — browse, detail, my modules, and AJAX API endpoints.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.project_app.services.project_utils import get_current_project
from apps.workspace_app.registry import get_module

from .models import (
    MarketplaceModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
)

logger = logging.getLogger(__name__)

# Module-level flag — ensures built-in modules exist on first marketplace visit
_builtins_ensured = False


def _ensure_builtin_modules():
    """Ensure all built-in modules exist in DB. Runs once per process."""
    global _builtins_ensured
    if _builtins_ensured:
        return

    from apps.workspace_app.registry import get_all_modules

    registered_names = {m.name for m in get_all_modules()}
    existing_names = set(
        MarketplaceModule.objects.filter(is_builtin=True).values_list(
            "module_name", flat=True
        )
    )

    if registered_names <= existing_names:
        _builtins_ensured = True
        return

    try:
        from .management.commands.seed_marketplace import ensure_builtin_modules

        created, _ = ensure_builtin_modules()
        if created:
            logger.info("[marketplace] Auto-seeded %d built-in modules", created)
    except Exception:
        logger.exception("[marketplace] Failed to auto-seed built-in modules")
    _builtins_ensured = True


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------
def build_marketplace_context(request, current_project=None):
    """Context builder for SPA tab switching."""
    return _browse_context(request, current_project)


def browse(request):
    """Marketplace browse page — grid of module cards."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = _browse_context(request, current_project)
    return render(request, "marketplace_app/browse.html", context)


def detail(request, module_name):
    """Module detail page — description, reviews, install button."""
    _ensure_builtin_modules()
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)
    reg_module = get_module(module_name)

    is_installed = False
    is_starred = False
    user_review = None
    if request.user.is_authenticated:
        is_installed = ModuleInstallation.objects.filter(
            user=request.user, module=mp_module
        ).exists()
        is_starred = ModuleStar.objects.filter(
            user=request.user, module=mp_module
        ).exists()
        user_review = ModuleReview.objects.filter(
            user=request.user, module=mp_module
        ).first()

    reviews = mp_module.reviews.select_related("user")[:20]
    versions = mp_module.versions.all()[:10]

    return render(
        request,
        "marketplace_app/detail.html",
        {
            "mp_module": mp_module,
            "reg_module": reg_module,
            "is_installed": is_installed,
            "is_starred": is_starred,
            "user_review": user_review,
            "reviews": reviews,
            "versions": versions,
        },
    )


@login_required
def my_modules(request):
    """User's installed modules with enable/disable toggles."""
    installations = (
        ModuleInstallation.objects.filter(user=request.user)
        .select_related("module")
        .order_by("tab_order")
    )
    return render(
        request,
        "marketplace_app/my_modules.html",
        {"installations": installations},
    )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@login_required
@require_http_methods(["POST"])
def api_install(request, module_name):
    """Install a module (add to user's workspace)."""
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)

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
    _ensure_builtin_modules()
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)
    installation = ModuleInstallation.objects.filter(
        user=request.user, module=mp_module
    ).first()

    if not installation:
        # No record = implicitly enabled → toggle creates disabled record
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _browse_context(request, current_project=None):
    """Build browse page context."""
    _ensure_builtin_modules()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "popular")
    q = request.GET.get("q", "")

    modules = MarketplaceModule.objects.filter(visibility="public")

    if category:
        modules = modules.filter(category=category)
    if q:
        modules = modules.filter(module_name__icontains=q)

    if sort == "newest":
        modules = modules.order_by("-created_at")
    elif sort == "rating":
        modules = modules.order_by("-avg_rating", "-star_count")
    else:
        modules = modules.order_by("-star_count", "-install_count")

    # Annotate with user-specific state
    installed_names = set()
    starred_names = set()
    if request.user.is_authenticated:
        installed_names = set(
            ModuleInstallation.objects.filter(user=request.user).values_list(
                "module__module_name", flat=True
            )
        )
        starred_names = set(
            ModuleStar.objects.filter(user=request.user).values_list(
                "module__module_name", flat=True
            )
        )

    module_list = []
    for mp in modules:
        reg = get_module(mp.module_name)
        module_list.append(
            {
                "mp": mp,
                "reg": reg,
                "is_installed": mp.module_name in installed_names,
                "is_starred": mp.module_name in starred_names,
            }
        )

    from .models import CATEGORY_CHOICES

    return {
        "current_project": current_project,
        "modules": module_list,
        "categories": CATEGORY_CHOICES,
        "active_category": category,
        "active_sort": sort,
        "search_query": q,
    }


# EOF
