#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps view helpers — shared utilities for pages and API."""

from __future__ import annotations

import logging
import types

from django.conf import settings

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

    all_modules = get_all_modules()
    registered_names = {m.name for m in all_modules}
    existing_names = set(
        AppsModule.objects.filter(is_builtin=True).values_list("module_name", flat=True)
    )

    if registered_names <= existing_names:
        # All builtin names present. The manifest is the SSoT for release-
        # channel visibility, though: a row seeded before its manifest flipped
        # to "internal" keeps the stale "public" value, and this fast path would
        # never correct it — leaking internal builtins (Cards, Storage) to the
        # public App Store for anonymous users (hub-store-tiles-cards-internal-
        # visibility-regression-20260914). Take the fast path ONLY when no
        # builtin's stored visibility has drifted from its manifest; otherwise
        # fall through to the idempotent update_or_create sync below.
        registry_vis = {m.name: (m.visibility or "public") for m in all_modules}
        stored_vis = list(
            AppsModule.objects.filter(is_builtin=True).values_list(
                "module_name", "visibility"
            )
        )
        if all(registry_vis.get(n) == v for n, v in stored_vis):
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
        # Mark ensured ONLY after a successful sync. A transient failure
        # (DB blip, migration mid-flight) must NOT set the flag, or this
        # process would never retry and could keep serving stale
        # visibility rows (the resync-retry gap the review flagged).
        _builtins_ensured = True
    except Exception:
        logger.exception(
            "[apps] Failed to auto-seed built-in modules; _builtins_ensured "
            "stays False so the next call retries (a transient failure must "
            "not permanently skip the visibility resync in this process)."
        )


def can_view_internal_app(user) -> bool:
    """Whether ``user`` may see/open an ``internal``-visibility app.

    Operator ruling (card hub-cards-internal-entitlement-20260913, 2026-09-13):
    "internal" is a RELEASE-CHANNEL property, not an admin-role property. On a
    development deployment (where every authenticated account is a SciTeX team
    member), every authenticated user sees internal apps; anonymous users stay
    redirected. On production, internal apps stay hidden unless the deployment
    opts in via SCITEX_HUB_INTERNAL_APPS_RELEASED. Staff always see internal
    apps on any deployment (operators). DEBUG is deliberately NOT the switch —
    it is observed, not the product contract.
    """
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return bool(getattr(settings, "SCITEX_HUB_INTERNAL_APPS_RELEASED", False))


def can_open_plugin_tile(user, tile_url: str) -> bool:
    """Whether the plugin tile at ``tile_url`` would get past its mount.

    The generic tile/mount agreement: a tile a user can see must not open
    onto a 403. Mounts are matched by URL, never by app name, so no
    per-app gate table can drift out of sync with the routes. Mounts
    without a declared audience restriction are unaffected.
    """
    from apps.workspace.apps_app.services.plugin_guards import can_open_plugin_mount

    return can_open_plugin_mount(user, tile_url or "")


def can_view_module(user, app_module):
    """Check if user can view/install this module based on visibility.

    public   → everyone
    internal → release-channel gate (WIP apps); is_builtin must NOT bypass it
    unlisted → any authenticated user (direct URL / org-gated discovery)
    private  → author, staff, or users sharing an org with the author
    """
    # "internal" is a release-channel property, not a builtin/admin property.
    # The previous `or app_module.is_builtin` short-circuit leaked internal
    # builtins to EVERYONE — including anonymous users — in the App Store
    # (regression hub-store-tiles-cards-internal-visibility-regression-
    # 20260914). Gate internal FIRST so is_builtin can never override it;
    # delegate to can_view_internal_app (staff, or an authenticated user on
    # a deployment that opted in via SCITEX_HUB_INTERNAL_APPS_RELEASED;
    # anonymous -> False).
    if app_module.visibility == "internal":
        return can_view_internal_app(user)
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

    # Base: public apps always visible. "internal" is deliberately NOT in the
    # base — it is staff/operators-only (WIP apps before dogfood is stable),
    # added to the staff branch below (card compass-impl-app-visibility-gate).
    visibility_q = Q(visibility="public")

    if request.user.is_authenticated:
        # Unlisted: authenticated users can see with direct link — show to author + staff
        visibility_q |= Q(visibility="unlisted", author=request.user)
        # Internal is a RELEASE-CHANNEL decision (can_view_internal_app): staff
        # always, and a regular user on a RELEASED deployment. It is consulted
        # for EVERY authenticated user here — not only inside the is_staff
        # branch — so an ordinary authenticated dev (flag true on dev) sees the
        # internal builtins in the store, matching the can_view_module policy.
        # Anonymous never reaches this branch, so internal stays hidden from them.
        if can_view_internal_app(request.user):
            visibility_q |= Q(visibility="internal")
        if request.user.is_staff:
            # Staff/operators see unlisted + private + internal (WIP apps).
            visibility_q |= Q(visibility__in=["unlisted", "private", "internal"])
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
    STORE_HIDDEN: set[str] = {
        "console",
        "discovery",
        "files",
        "home",
        "my_projects",
        "repo",
        "slides",
        "store",
        "tools",
    }

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
