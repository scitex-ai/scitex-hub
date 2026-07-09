#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workspace home launcher — app-grid home page (approved design 2026-07-07).

Serves the iPhone-style app grid at the workspace root ("/"): a
responsive tile grid IS the home, with per-user pin-to-sidebar
persistence (capped at MAX_PINNED_MODULES).

Django stays thin here: this module only assembles registry data
(workspace module registry + published store apps) for the template.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.infra.workspace_app.registry import get_all_modules

from ..models import AppsModule, ModuleInstallation
from .helpers import ensure_builtin_modules

# Sidebar pin cap — keeps the reduced sidebar scannable.
MAX_PINNED_MODULES = 5

# Store apps published within this window get a NEW badge.
NEW_BADGE_DAYS = 14


def is_guest_launcher_user(user) -> bool:
    """True for pool visitors (visitor-*) and the shared readonly-visitor.

    Guest-mode launcher (card hub-visitor-ux-allapps): visitors keep the
    app grid but get a prominent Sign in / Sign up call-to-action instead
    of a personalized greeting. Role mapping is delegated to the canonical
    session-role model (no scattered username checks).
    """
    from apps.infra.project_app.services.visitor_pool import (
        ROLE_READONLY_VISITOR,
        ROLE_VISITOR,
        get_user_role,
    )

    return get_user_role(user) in (ROLE_VISITOR, ROLE_READONLY_VISITOR)


def get_pinned_module_names(user) -> list[str]:
    """Names of modules the user pinned to the sidebar (stable order)."""
    if not user.is_authenticated:
        return []
    return list(
        ModuleInstallation.objects.filter(user=user, config__pinned=True)
        .order_by("tab_order", "id")
        .values_list("module__module_name", flat=True)[:MAX_PINNED_MODULES]
    )


def _build_tiles(request) -> list[dict]:
    """Assemble launcher tiles: registry modules + published store apps."""
    catalog = {m.module_name: m for m in AppsModule.objects.all()}

    installed_names: set[str] = set()
    if request.user.is_authenticated:
        installed_names = set(
            ModuleInstallation.objects.filter(user=request.user).values_list(
                "module__module_name", flat=True
            )
        )
    pinned_names = set(get_pinned_module_names(request.user))
    new_cutoff = timezone.now() - timedelta(days=NEW_BADGE_DAYS)

    tiles: list[dict] = []
    seen: set[str] = set()

    # 1. Workspace module registry — same source that builds the sidebar.
    for mod in get_all_modules():
        row = catalog.get(mod.name)
        tiles.append(
            {
                "name": mod.name,
                "label": mod.label,
                "icon_fa": mod.icon_fa or "fas fa-puzzle-piece",
                "launch_url": mod.get_url(),
                "category": row.category if row else "other",
                "description": row.short_description if row else mod.ai_hint,
                "is_installed": True,  # registry modules are built in
                "is_pinned": mod.name in pinned_names,
                "is_new": False,
                "detail_url": f"/apps/store/{mod.name}/",
            }
        )
        seen.add(mod.name)

    # 2. Published store apps not in the registry (community apps).
    # Apps in this branch were NOT loaded into the workspace registry
    # (load_approved_apps registers every public app with a project at
    # startup), so there is no route that can render them —
    # /apps/<module_name>/ is not mounted and 404'd for installed apps
    # (nav-404 batch #5). The store detail page is the only truthful
    # navigation target until the app is registered.
    published = AppsModule.objects.filter(visibility="public").exclude(
        module_name__in=seen
    )
    for row in published:
        installed = row.module_name in installed_names
        tiles.append(
            {
                "name": row.module_name,
                "label": row.module_name,
                "icon_fa": "fas fa-puzzle-piece",
                "launch_url": f"/apps/store/{row.module_name}/",
                "category": row.category,
                "description": row.short_description,
                "is_installed": installed,
                "is_pinned": row.module_name in pinned_names,
                "is_new": row.created_at is not None and row.created_at >= new_cutoff,
                "detail_url": f"/apps/store/{row.module_name}/",
            }
        )

    # 3. Dev-installed apps (personal — previously reachable from the sidebar).
    if request.user.is_authenticated:
        from ..models import DevInstallation

        for dev in DevInstallation.objects.filter(user=request.user, is_enabled=True):
            tiles.append(
                {
                    "name": dev.module_name,
                    "label": dev.label or dev.source_repo,
                    "icon_fa": dev.icon or "fas fa-puzzle-piece",
                    "launch_url": f"/apps/{dev.module_name}/",
                    "category": "other",
                    "description": dev.description,
                    "is_installed": True,
                    "is_pinned": False,
                    "is_new": False,
                    "detail_url": f"/apps/{dev.module_name}/",
                }
            )
    return tiles


def launcher_context(request) -> dict:
    """Template context for the launcher home page."""
    ensure_builtin_modules()
    tiles = _build_tiles(request)
    return {
        "tiles": tiles,
        "installed_count": sum(1 for t in tiles if t["is_installed"]),
        "max_pins": MAX_PINNED_MODULES,
        # Guest mode: visitors see tiles + a prominent Sign in / Sign up CTA.
        "is_guest_launcher": is_guest_launcher_user(request.user),
    }


@login_required
def launcher(request):
    """Workspace home — the app-launcher grid (served at the root URL)."""
    return render(request, "apps_app/launcher.html", launcher_context(request))


@login_required
@require_http_methods(["POST"])
def api_pin(request, module_name):
    """Toggle a module's pinned-to-sidebar flag (per-user, capped)."""
    ensure_builtin_modules()
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    inst = ModuleInstallation.objects.filter(
        user=request.user, module=app_module
    ).first()
    currently_pinned = bool(inst and (inst.config or {}).get("pinned"))

    if not currently_pinned:
        pinned_count = ModuleInstallation.objects.filter(
            user=request.user, config__pinned=True
        ).count()
        if pinned_count >= MAX_PINNED_MODULES:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        f"Pin limit reached ({MAX_PINNED_MODULES}). "
                        "Unpin another app first."
                    ),
                },
                status=400,
            )

    if inst is None:
        # Pinning implies the module is part of the user's workspace.
        inst = ModuleInstallation.objects.create(
            user=request.user, module=app_module, is_enabled=True, tab_order=50
        )

    config = inst.config or {}
    if currently_pinned:
        config.pop("pinned", None)
    else:
        config["pinned"] = True
    inst.config = config
    inst.save(update_fields=["config"])

    return JsonResponse(
        {
            "success": True,
            "pinned": not currently_pinned,
            "pinned_modules": get_pinned_module_names(request.user),
        }
    )


# EOF
