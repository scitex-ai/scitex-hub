#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed the apps catalog with entries for all built-in registry modules.

Usage: python manage.py seed_apps
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.models import AppsModule, ModuleVersion

# Map module names to categories
_CATEGORY_MAP = {
    "writer": "writing",
    "scholar": "reference",
    "figrecipe": "visualization",
    "console": "utility",
    "clew": "reference",
    "home": "utility",
    "tools": "utility",
    "store": "utility",
    "discovery": "social",
    "docs": "reference",
    "todo": "utility",
    "storage": "data",
}

# Module descriptions
_DESCRIPTIONS = {
    "writer": "LaTeX manuscript editor with live preview, bibliography management, and figure insertion.",
    "scholar": "Literature search, BibTeX management, and citation enrichment powered by scitex.scholar.",
    "figrecipe": "Interactive figure editor: create and edit publication-ready matplotlib plots with drag-and-drop layout, statistical annotations, and multi-panel composition.",
    "console": "Python console with file browser for running scripts and managing project files.",
    "clew": "Verification system — trace manuscript claims (statistics, figures, tables) back through computational chains to source data.",
    "home": "Home workspace — project overview with recent activity, file browser, and quick actions.",
    "tools": "Collection of standalone research utilities — converters, calculators, and helpers.",
    "store": "Browse, install, and manage workspace modules.",
    "discovery": "Discover public repositories, researchers, and organizations across the SciTeX community.",
    "docs": "Documentation hub — Python packages, MCP tools, API reference, and self-hosting guide.",
    "todo": "Read-only board view of your project's task cards (scitex-todo store) — kanban columns, dependency graph, and status colors.",
    "storage": "Browse your storage across the machines you can reach.",
}

# Modules under active development
_WIP_MODULES: set[str] = set()


def ensure_builtin_modules(author_username="ywatanabe"):
    """Ensure all built-in registry modules have AppsModule records.

    Idempotent: uses update_or_create so safe to call multiple times.
    Returns (created_count, updated_count).
    """
    author = User.objects.filter(username=author_username).first()
    # BUILTIN modules only. get_all_modules() also returns runtime
    # registrations — user-published apps (app_loader.load_single_app)
    # and dev apps — and seeding those stamped them is_builtin/verified
    # AND copied their registry display label (the raw repo slug) into
    # the catalog columns, where it then fed back into the registry on
    # the next boot: a self-perpetuating garbage label. The loader's
    # partial_template prefix is the runtime-registration signature.
    modules = [
        m
        for m in get_all_modules()
        if not (m.partial_template or "").startswith("apps_app/user_apps/")
    ]
    created = 0
    updated = 0

    for mod in modules:
        defaults = {
            "author": author,
            "short_description": _DESCRIPTIONS.get(
                mod.name, f"{mod.label} workspace module."
            ),
            "category": _CATEGORY_MAP.get(mod.name, "other"),
            # Display metadata straight from the app's manifest.json (the
            # registry builds ModuleConfig from the manifests — SSoT). A
            # manifest without an icon leaves the column blank; readers
            # fall back to the generic puzzle icon.
            "label": mod.label,
            "icon": mod.icon_fa,
            "is_builtin": True,
            "is_verified": True,
            "visibility": "public",
            "status": "wip" if mod.name in _WIP_MODULES else "stable",
        }

        obj, was_created = AppsModule.objects.update_or_create(
            module_name=mod.name,
            defaults=defaults,
        )

        if not obj.versions.exists():
            suffix = "-alpha" if mod.name in _WIP_MODULES else ""
            ModuleVersion.objects.create(
                module=obj,
                version=f"0.1.0{suffix}",
                changelog="Initial release.",
                is_stable=suffix == "",
            )
        elif mod.name not in _WIP_MODULES:
            # Promote any lingering alpha versions to stable
            obj.versions.filter(version__endswith="-alpha").update(
                version="0.1.0", is_stable=True
            )

        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated


class Command(BaseCommand):
    help = "Seed apps catalog with built-in module entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--author",
            default="ywatanabe",
            help="Username of the author for built-in modules",
        )

    def handle(self, *args, **options):
        created, updated = ensure_builtin_modules(author_username=options["author"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created}, updated {updated} apps catalog entries."
            )
        )


# EOF
