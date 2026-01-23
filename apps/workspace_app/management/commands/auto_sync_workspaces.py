#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-15 00:56:00 (ywatanabe)"
# File: ./apps/workspace_app/management/commands/auto_sync_workspaces.py
"""
DEPRECATED: Auto-sync daemon has been removed from the architecture.

New Architecture:
- Manual sync: User runs 'scitex cloud push/pull' from local machine
- Auto backup: Simple rsync snapshots (see: scripts/deployment/backup_workspaces.sh)

Reason for removal:
- Auto-git-sync creates dirty commits during editing
- Pollutes Git history with meaningless commits
- Causes merge conflicts in background
- Users have no control over timing

This command is kept for backwards compatibility but does nothing.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "[DEPRECATED] Auto-sync has been replaced with manual sync + rsync backups"

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='[DEPRECATED] No longer functional',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='[DEPRECATED] No longer functional',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "\n⚠️  This command is DEPRECATED and has been disabled.\n"
            )
        )
        self.stdout.write(
            "\n"
            "Auto-git-sync has been removed from the architecture because:\n"
            "  • Creates dirty commits during editing\n"
            "  • Pollutes Git history\n"
            "  • Causes background merge conflicts\n"
            "\n"
            "New workflow:\n"
            "  1. Users work in workspace (web/SSH)\n"
            "  2. Sync manually: 'scitex cloud push/pull' (from local machine)\n"
            "  3. Auto-backups: rsync snapshots every 5 minutes (transparent)\n"
            "\n"
            "For disaster recovery backups, see: scripts/deployment/backup_workspaces.sh\n"
        )


# EOF
