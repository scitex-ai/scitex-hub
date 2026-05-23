#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps view helpers — shared utilities for pages and API."""

from __future__ import annotations

import logging
import types

from apps.infra.workspace_app.registry import get_module

from ..models import (
    AppsModule,
    ModuleInstallation,
    ModuleStar,
)

logger = logging.getLogger(__name__)


class _DevAppProxy:
    """Make DevInstallation quack like AppsModule for the shared card template."""

    def __init__(self, dev, owner_user=None):
        self.module_name = dev.label or dev.source_repo
        self.category = "other"
        self.star_count = 0
        self.install_count = 0
        self.avg_rating = None
        self.created_at = dev.installed_at
        self.short_description = dev.description or ""
        self.status = "stable"
        self.visibility = "public"
        self.is_builtin = False
        self.is_verified = False
        self.author = owner_user
        self.registry_repo_url = ""
        self.latest_version = "0.1.0-dev"

    def get_category_display(self):
        return "Other"


# Module-level flag — ensures built-in modules exist on first apps visit
_builtins_ensured = False


def ensure_builtin_modules():
    """Ensure all built-in modules exist in DB. Runs once per process."""
    global _builtins_ensured
    if _builtins_ensured:
        return

    from apps.infra.workspace_app.registry import get_all_modules

    registered_names = {m.name for m in get_all_modules()}
    existing_names = set(
        AppsModule.objects.filter(is_builtin=True).values_list("module_name", flat=True)
    )

    if registered_names <= existing_names:
        _builtins_ensured = True
        return

    try:
        from django.db import transaction

        from ..management.commands.seed_apps import (
            ensure_builtin_modules as seed_builtins,
        )

        with transaction.atomic():
            created, _ = seed_builtins()
        if created:
            logger.info("[apps] Auto-seeded %d built-in modules", created)
    except Exception:
        logger.exception("[apps] Failed to auto-seed built-in modules")
    _builtins_ensured = True


def can_view_module(user, app_module):
    """Check if user can view/install this module based on visibility.

    public   → everyone
    unlisted → any authenticated user (direct URL / org-gated discovery)
    private  → author, staff, or users sharing an org with the author
    """
    if app_module.visibility == "public" or app_module.is_builtin:
        return True
    if not user.is_authenticated:
        return False
    if app_module.author == user or user.is_staff:
        return True
    if app_module.visibility == "unlisted":
        return True  # any authenticated user with the direct link
    # private: check shared org membership with author
    return _shares_org(user, app_module.author)


def _shares_org(user, other_user) -> bool:
    """Return True if two users share at least one organization."""
    if other_user is None:
        return False
    from apps.infra.organizations_app.models import Organization

    user_org_ids = set(
        Organization.objects.filter(members=user).values_list("id", flat=True)
    )
    if not user_org_ids:
        return False
    return Organization.objects.filter(id__in=user_org_ids, members=other_user).exists()


def browse_context(request, current_project=None):
    """Build browse page context — all modules returned, filtering is client-side."""
    ensure_builtin_modules()

    from django.db.models import OuterRef, Subquery

    from ..models import ModuleVersion

    latest_ver_sq = (
        ModuleVersion.objects.filter(module=OuterRef("pk"))
        .order_by("-released_at")
        .values("version")[:1]
    )
    from django.db.models import Q

    # Base: public apps always visible
    visibility_q = Q(visibility="public")

    if request.user.is_authenticated:
        # Unlisted: authenticated users can see with direct link — show to author + staff
        visibility_q |= Q(visibility="unlisted", author=request.user)
        if request.user.is_staff:
            visibility_q |= Q(visibility__in=["unlisted", "private"])
        else:
            # Private: author or shared-org members
            from apps.infra.organizations_app.models import Organization

            user_org_ids = list(
                Organization.objects.filter(members=request.user).values_list(
                    "id", flat=True
                )
            )
            if user_org_ids:
                org_author_ids = Organization.objects.filter(
                    id__in=user_org_ids
                ).values_list("members__id", flat=True)
                visibility_q |= Q(visibility="private", author__id__in=org_author_ids)
            visibility_q |= Q(visibility="private", author=request.user)

    modules = (
        AppsModule.objects.filter(visibility_q)
        .select_related("author", "author__auth_profile")
        .annotate(latest_version=Subquery(latest_ver_sq))
        .order_by("-star_count", "-install_count")
        .distinct()
    )

    # Modules disabled by default (installed but hidden from tab bar)
    DEFAULT_DISABLED: set[str] = set()

    # Core modules that should not appear in the store listing
    STORE_HIDDEN: set[str] = {"console", "home", "store"}

    # Annotate with user-specific state
    install_map = {}  # module_name -> {is_enabled, tab_order}
    starred_names = set()
    if request.user.is_authenticated:
        for row in ModuleInstallation.objects.filter(user=request.user).values_list(
            "module__module_name", "is_enabled", "tab_order"
        ):
            install_map[row[0]] = {"is_enabled": row[1], "tab_order": row[2]}
        starred_names = set(
            ModuleStar.objects.filter(user=request.user).values_list(
                "module__module_name", flat=True
            )
        )

    module_list = []
    for mp in modules:
        if mp.module_name in STORE_HIDDEN:
            continue
        reg = get_module(mp.module_name)
        installed = mp.is_builtin or mp.module_name in install_map
        info = install_map.get(mp.module_name)
        if info:
            enabled = info["is_enabled"]
            tab_order = info["tab_order"]
        else:
            # Builtin without explicit installation record
            enabled = mp.module_name not in DEFAULT_DISABLED
            tab_order = reg.order if reg else 50
        module_list.append(
            {
                "app": mp,
                "reg": reg,
                "is_installed": installed,
                "is_enabled": enabled,
                "tab_order": tab_order,
                "is_starred": mp.module_name in starred_names,
            }
        )

    from ..models import CATEGORY_CHOICES, DevInstallation

    # Dev installations → same mod_item shape as public modules (single card template)
    dev_modules = []
    if request.user.is_authenticated:
        dev_installs = list(
            DevInstallation.objects.filter(user=request.user).order_by("tab_order")
        )
        if dev_installs:
            from django.contrib.auth.models import User

            owner_names = {d.source_owner for d in dev_installs}
            owner_users = {
                u.username: u
                for u in User.objects.filter(username__in=owner_names).select_related(
                    "auth_profile"
                )
            }
            for d in dev_installs:
                owner_user = owner_users.get(d.source_owner)
                dev_modules.append(
                    {
                        "app": _DevAppProxy(d, owner_user),
                        "reg": types.SimpleNamespace(
                            name=d.module_name,
                            icon_fa=d.icon,
                            order=d.tab_order,
                            status="",
                        ),
                        "is_installed": True,
                        "is_enabled": d.is_enabled,
                        "tab_order": d.tab_order,
                        "is_starred": False,
                        "is_dev": True,
                        "dev_owner": d.source_owner,
                        "dev_repo": d.source_repo,
                    }
                )

    from django.conf import settings

    gitea_url = getattr(settings, "SCITEX_HUB_GITEA_URL", "")

    return {
        "current_project": current_project,
        "modules": module_list,
        "categories": CATEGORY_CHOICES,
        "dev_modules": dev_modules,
        "gitea_url": gitea_url,
        "apps_org": "scitex-apps",
    }


# EOF
