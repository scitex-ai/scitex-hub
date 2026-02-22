#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Management command to validate all registered workspace modules.

Usage: python manage.py validate_modules
"""

from django.core.management.base import BaseCommand
from django.template.loader import get_template


class Command(BaseCommand):
    help = "Validate all registered workspace modules"

    def handle(self, *args, **options):
        from apps.workspace_app.registry import _import_builder, get_all_modules

        modules = get_all_modules()
        errors = 0
        warnings = 0

        self.stdout.write(f"\nValidating {len(modules)} registered modules...\n")

        for mod in modules:
            self.stdout.write(f"\n  [{mod.name}] {mod.label} (order={mod.order})")

            # Check partial template exists
            if mod.partial_template:
                try:
                    get_template(mod.partial_template)
                    self.stdout.write(
                        self.style.SUCCESS(f"    template: {mod.partial_template}")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    template: MISSING — {mod.partial_template} ({e})"
                        )
                    )
                    errors += 1
            else:
                self.stdout.write(self.style.WARNING("    template: not set"))
                warnings += 1

            # Check context builder importable
            if mod.context_builder:
                builder = _import_builder(mod.context_builder)
                if builder and callable(builder):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    context_builder: {mod.context_builder}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    context_builder: CANNOT IMPORT — {mod.context_builder}"
                        )
                    )
                    errors += 1
            else:
                self.stdout.write("    context_builder: none (default context)")

            # Check icon
            if mod.icon_fa:
                self.stdout.write(f"    icon: FA {mod.icon_fa}")
            elif mod.icon_svg_tab:
                self.stdout.write("    icon: custom SVG")
            else:
                self.stdout.write(self.style.WARNING("    icon: NONE"))
                warnings += 1

            # Check Django app exists
            try:
                from django.apps import apps

                apps.get_app_config(mod.app_name)
                self.stdout.write(self.style.SUCCESS(f"    app: {mod.app_name}"))
            except LookupError:
                self.stdout.write(
                    self.style.ERROR(f"    app: NOT INSTALLED — {mod.app_name}")
                )
                errors += 1

        # Summary
        self.stdout.write(f"\n{'=' * 50}")
        if errors == 0 and warnings == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nAll {len(modules)} modules validated successfully!"
                )
            )
        else:
            if errors:
                self.stdout.write(self.style.ERROR(f"\n{errors} error(s) found"))
            if warnings:
                self.stdout.write(self.style.WARNING(f"{warnings} warning(s)"))

        return "" if errors == 0 else "Validation failed"


# EOF
