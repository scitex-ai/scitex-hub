#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 17:45:00 (ywatanabe)"
# File: ./apps/workspace_app/management/commands/cleanup_idle_containers.py

"""
Management command to stop idle user containers

Usage:
    python manage.py cleanup_idle_containers
    python manage.py cleanup_idle_containers --idle-minutes 60
"""

from django.core.management.base import BaseCommand
from apps.infra.workspace_app.services import UserContainerManager


class Command(BaseCommand):
    help = "Stop idle user workspace containers to free resources"

    def add_arguments(self, parser):
        parser.add_argument(
            "--idle-minutes",
            type=int,
            default=30,
            help="Minutes of inactivity before stopping container (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List idle containers without stopping them",
        )

    def handle(self, *args, **options):
        idle_minutes = options["idle_minutes"]
        dry_run = options["dry_run"]

        self.stdout.write(
            f"Checking for containers idle for {idle_minutes}+ minutes..."
        )

        manager = UserContainerManager()
        idle_containers = manager.list_idle_containers(idle_minutes)

        if not idle_containers:
            self.stdout.write(self.style.SUCCESS("✓ No idle containers found"))
            return

        self.stdout.write(f"Found {len(idle_containers)} idle container(s):")
        for user, container in idle_containers:
            self.stdout.write(f"  - {user.username}: {container.name}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n--dry-run: Not stopping containers")
            )
            return

        stopped_count = manager.cleanup_idle_containers(idle_minutes)
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Stopped {stopped_count} idle container(s)")
        )


# EOF
