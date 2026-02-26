#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed the marketplace with entries for all built-in registry modules.

Usage: python manage.py seed_marketplace
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.marketplace_app.models import MarketplaceModule, ModuleVersion
from apps.workspace_app.registry import get_all_modules

# Map module names to categories
_CATEGORY_MAP = {
    "writer": "writing",
    "scholar": "reference",
    "vis": "visualization",
    "console": "utility",
    "clew": "reference",
    "hub": "utility",
    "tools": "utility",
    "example": "other",
    "marketplace": "utility",
    "modulemaker": "utility",
}

# Module descriptions
_DESCRIPTIONS = {
    "writer": "LaTeX manuscript editor with live preview, bibliography management, and figure insertion.",
    "scholar": "Literature search, BibTeX management, and citation enrichment powered by scitex.scholar.",
    "vis": "Data visualization workspace for creating publication-ready figures.",
    "console": "Python console with file browser for running scripts and managing project files.",
    "clew": "Research discovery — explore connected papers, authors, and citation networks.",
    "hub": "Project dashboard showing recent activity, file browser, and quick actions.",
    "tools": "Collection of standalone research utilities — converters, calculators, and helpers.",
    "example": "Reference implementation for module developers. Copy this to create your own module.",
    "marketplace": "Browse, install, and manage workspace modules.",
    "modulemaker": "Create, edit, and manage custom workspace modules with @stx.module.",
}

# Modules under active development
_WIP_MODULES = {"modulemaker", "example", "clew", "vis", "marketplace"}


def ensure_builtin_modules(author_username="ywatanabe"):
    """Ensure all built-in registry modules have MarketplaceModule records.

    Idempotent: uses update_or_create so safe to call multiple times.
    Returns (created_count, updated_count).
    """
    author = User.objects.filter(username=author_username).first()
    modules = get_all_modules()
    created = 0
    updated = 0

    for mod in modules:
        defaults = {
            "author": author,
            "short_description": _DESCRIPTIONS.get(
                mod.name, f"{mod.label} workspace module."
            ),
            "category": _CATEGORY_MAP.get(mod.name, "other"),
            "is_builtin": True,
            "is_verified": True,
            "visibility": "public",
            "status": "wip" if mod.name in _WIP_MODULES else "stable",
        }

        obj, was_created = MarketplaceModule.objects.update_or_create(
            module_name=mod.name,
            defaults=defaults,
        )

        if not obj.versions.exists():
            ModuleVersion.objects.create(
                module=obj,
                version="1.0.0",
                changelog="Initial built-in release.",
                is_stable=True,
            )

        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated


class Command(BaseCommand):
    help = "Seed marketplace with built-in module entries"

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
                f"Done. Created {created}, updated {updated} marketplace entries."
            )
        )


# EOF
