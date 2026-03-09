#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Management command to initialize arXiv categories in the database.

DEPRECATED: arXiv integration moved to separate service.
This command is a stub for backward compatibility.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from .arxiv_categories_data import get_all_categories

# Note: ArxivCategory model removed - arXiv integration delegated to separate service
# This import will fail if model doesn't exist
try:
    from apps.workspace.writer_app.models import ArxivCategory
except ImportError:
    ArxivCategory = None


class Command(BaseCommand):
    help = "Initialize arXiv categories in the database (DEPRECATED)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing categories with new information",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing categories before adding new ones",
        )

    def handle(self, *args, **options):
        if ArxivCategory is None:
            self.stderr.write(
                self.style.ERROR(
                    "ArxivCategory model not found. "
                    "arXiv integration has been moved to a separate service."
                )
            )
            return

        self.stdout.write("Initializing arXiv categories...")

        if options["clear"]:
            self.stdout.write("Clearing existing categories...")
            ArxivCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING("All existing categories cleared."))

        try:
            with transaction.atomic():
                created_count = self._create_categories(update=options["update"])

                if created_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully created {created_count} arXiv categories."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "No new categories were created. "
                            "Use --update to update existing categories."
                        )
                    )

        except Exception as e:
            raise CommandError(f"Error initializing categories: {str(e)}")

    def _create_categories(self, update=False):
        """Create arXiv categories based on official arXiv taxonomy."""
        categories_data = get_all_categories()
        created_count = 0

        for cat_data in categories_data:
            defaults = {
                "name": cat_data["name"],
                "description": cat_data["description"],
                "is_active": True,
            }

            if update:
                category, created = ArxivCategory.objects.update_or_create(
                    code=cat_data["code"], defaults=defaults
                )
            else:
                category, created = ArxivCategory.objects.get_or_create(
                    code=cat_data["code"], defaults=defaults
                )

            if created:
                created_count += 1
                self.stdout.write(f"Created: {cat_data['code']} - {cat_data['name']}")
            elif update:
                self.stdout.write(f"Updated: {cat_data['code']} - {cat_data['name']}")

        return created_count


# EOF
