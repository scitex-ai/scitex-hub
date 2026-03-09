#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rename AppsModule record: module_name 'apps' → 'store'."""

from django.core.management.base import BaseCommand

from apps.workspace.apps_app.models import AppsModule


class Command(BaseCommand):
    help = "Rename AppsModule record from 'apps' to 'store'"

    def handle(self, *args, **options):
        store_exists = AppsModule.objects.filter(module_name="store").exists()
        if store_exists:
            deleted, _ = AppsModule.objects.filter(module_name="apps").delete()
            self.stdout.write(
                f"Deleted {deleted} stale 'apps' record(s) ('store' already exists)"
            )
        else:
            updated = AppsModule.objects.filter(module_name="apps").update(
                module_name="store"
            )
            if updated:
                self.stdout.write(
                    self.style.SUCCESS(f"Renamed {updated} record(s): apps → store")
                )
            else:
                self.stdout.write(
                    "No 'apps' record found (already renamed or not seeded yet)."
                )
        self.stdout.write(self.style.SUCCESS("Done."))


# EOF
