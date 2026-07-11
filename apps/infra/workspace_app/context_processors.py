#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace context processors — inject module registry data into all templates.

Added to TEMPLATES["OPTIONS"]["context_processors"] in settings.
"""

from __future__ import annotations

import logging

from .registry import extract_module_from_path, get_all_modules, is_workspace_path

logger = logging.getLogger(__name__)


def workspace_context(request):
    """Provide workspace module info to all templates."""
    path = request.path
    is_ws = is_workspace_path(path)

    # /landing/ is never a workspace (hero must render outside workspace layout)
    if path == "/landing/":
        is_ws = False

    # Root "/" is workspace for all authenticated users — including visitor
    # sessions (visitor-* and readonly-visitor get the guest-mode launcher,
    # card hub-visitor-ux-allapps). Only true anonymous stays non-workspace.
    if path == "/" and not request.user.is_authenticated:
        is_ws = False

    # User profile pages (/<username>/...) should also show workspace chrome
    if not is_ws and request.user.is_authenticated:
        is_ws = _is_user_profile_path(path)

    # /new/ renders inside workspace frame with Hub as active module
    if path.rstrip("/") == "/new" and request.user.is_authenticated:
        is_ws = True

    # Core pane paths (/chat/, /console/, /files/) → workspace with panes
    _CORE_PANE_PATHS = {"/chat/", "/console/", "/files/"}
    if path in _CORE_PANE_PATHS and request.user.is_authenticated:
        is_ws = True

    # /ai-setup/ and /search/ paths → workspace with panes
    if path.startswith(("/ai-setup/", "/search/")) and request.user.is_authenticated:
        is_ws = True

    active_name = extract_module_from_path(path) if is_ws else None
    # Pages with a real module match get workspace sidebars (AI, worktree, viewer).
    # User profile pages (/<username>/) also get panes — they render inside Hub.
    # Extra workspace paths (e.g. /accounts/) get the tab bar but no sidebars.
    has_panes = is_ws and active_name is not None
    # Non-module workspace pages: user profiles get panes, others don't
    if is_ws and active_name is None:
        # Org profiles → Discovery context; user profiles → Home context
        active_name = "discovery" if _is_org_profile_path(path) else "home"
        if request.user.is_authenticated and (
            _is_user_profile_path(path)
            or path.rstrip("/") == "/new"
            or path in _CORE_PANE_PATHS
            or path.startswith("/accounts/")
        ):
            has_panes = True

    all_modules = get_all_modules()
    modules = _filter_modules_for_user(request, all_modules)

    for mod in modules:
        mod.is_active = mod.name == active_name

    active_mod = None
    if active_name:
        active_mod = next((m for m in modules if m.name == active_name), None)

    # Capitalized display name for the module header (e.g. "Hub", "Writer")
    active_label = (
        active_mod.label if active_mod and hasattr(active_mod, "label") else None
    )
    if not active_label and active_name:
        active_label = active_name.capitalize()

    # Expose current_project for the worktree pane and other global partials.
    # Priority: request.project (set by @project_access_required), then fallback
    # to get_current_project() which checks session/profile/first-owned project.
    current_project = getattr(request, "project", None)
    if current_project is None and has_panes and request.user.is_authenticated:
        try:
            from apps.infra.project_app.services.project_utils import (
                get_current_project,
            )

            current_project = get_current_project(request)
        except Exception:
            pass

    return {
        "is_workspace_page": is_ws,
        "workspace_has_panes": has_panes,
        "workspace_modules": modules,
        "workspace_pinned_modules": _pinned_modules_for_user(request, modules),
        "workspace_module_names_csv": ",".join(m.name for m in modules),
        "active_module_name": active_name,
        "active_module": active_mod,
        "active_module_label": active_label,
        "current_project": current_project,
    }


def _is_user_profile_path(path: str) -> bool:
    """Check if path is a user profile page (/<username>/...)."""
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return False
    first = parts[0]
    # Skip registered module names
    from .registry import _registry_by_name

    if first in _registry_by_name:
        return False
    # Skip known non-user URL prefixes
    _NON_USER_PREFIXES = {
        "admin",
        "api",
        "static",
        "media",
        "auth",
        "healthz",
        "new",
        "files",
        "accounts",
        "public",
        "invite",
        "dev",
        "docs",
        "landing",
        "cloud",
        "about",
        "setup",
        "open-source",
        "demos",
        "publications",
        "contributors",
        "pricing",
        "keyboard-shortcuts",
        "donate",
        "contact",
        "privacy",
        "terms",
        "cookies",
        "demo",
        "releases",
        "api-keys",
        "api-docs",
        "server-status",
        "visitor-status",
        "visitor-expired",
        "visitor-restart",
        "visitor-pool-full",
        "__reload__",
    }
    return first not in _NON_USER_PREFIXES


def _is_org_profile_path(path: str) -> bool:
    """Check if path is an organization profile (/<org-slug>/...)."""
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return False
    first = parts[0]
    try:
        from apps.infra.organizations_app.models import Organization

        return Organization.objects.filter(slug=first).exists()
    except Exception:
        return False


def _filter_modules_for_user(request, modules):
    """Filter and reorder modules based on user's apps installations."""
    if not request.user.is_authenticated:
        for mod in modules:
            mod.accent_color = ""
        return modules

    try:
        from apps.workspace.apps_app.models import AppsModule, ModuleInstallation

        installations = {
            inst.module.module_name: inst
            for inst in ModuleInstallation.objects.filter(
                user=request.user
            ).select_related("module")
        }

        # Populate version from AppsModule (latest version per module)
        from django.db.models import OuterRef, Subquery

        from apps.workspace.apps_app.models import ModuleVersion

        latest_ver_sq = (
            ModuleVersion.objects.filter(module=OuterRef("pk"))
            .order_by("-released_at")
            .values("version")[:1]
        )
        mp_data = dict(
            AppsModule.objects.filter(module_name__in=[m.name for m in modules])
            .annotate(latest_version=Subquery(latest_ver_sq))
            .values_list("module_name", "latest_version")
        )
        for mod in modules:
            # A published DB store version wins; otherwise fall back to the
            # manifest version already on the ModuleConfig (the SSOT), never
            # the old hardcoded "0.1.0" which mislabelled every built-in app
            # (e.g. Writer showed 0.1.0 instead of its manifest 0.14.0).
            mod.version = mp_data.get(mod.name) or getattr(mod, "version", "") or ""
    except Exception:
        # apps_app not migrated yet or other DB issue
        for mod in modules:
            mod.accent_color = ""
        return modules

    if not installations:
        # No installations = first-time user, show default-enabled modules
        result = [m for m in modules if m.default_enabled]
        for mod in result:
            mod.accent_color = ""
        result = _append_dev_apps(request.user, result)
        return result

    # Show modules unless explicitly disabled via installation record
    visible = []
    for idx, mod in enumerate(modules):
        inst = installations.get(mod.name)
        if inst is None:
            if not mod.default_enabled:
                continue  # Respect registry default_enabled=False
            # No record = default visible, keep registry order
            # mod.order already set by registry (ModuleConfig.order)
            mod.accent_color = ""
            visible.append(mod)
        elif inst.is_enabled:
            mod.order = inst.tab_order
            mod.accent_color = (inst.config or {}).get("accent_color", "")
            visible.append(mod)

    visible = _append_dev_apps(request.user, visible)
    visible.sort(key=lambda m: m.order)
    return visible


def _pinned_modules_for_user(request, modules):
    """Modules the user pinned to the sidebar (launcher 'Pin to sidebar').

    The reduced sidebar shows only Home + pinned favourites + All apps;
    pins persist per user in ModuleInstallation.config["pinned"].
    """
    if not request.user.is_authenticated:
        return []
    try:
        from apps.workspace.apps_app.views.launcher import get_pinned_module_names

        pinned_names = get_pinned_module_names(request.user)
    except Exception:
        # apps_app not migrated yet or other DB issue
        return []
    by_name = {m.name: m for m in modules}
    return [by_name[name] for name in pinned_names if name in by_name]


def _append_dev_apps(user, modules):
    """Inject dev-installed app tabs for this user."""
    try:
        from apps.workspace.apps_app.models import DevInstallation
        from apps.workspace.apps_app.services.dev_app_loader import build_module_config

        dev_installs = DevInstallation.objects.filter(user=user, is_enabled=True)
        for dev_inst in dev_installs:
            config = build_module_config(dev_inst)
            config.accent_color = ""
            config.version = "0.1.0-dev"
            modules.append(config)
    except Exception:
        pass  # apps_app not migrated yet
    return modules


# EOF
