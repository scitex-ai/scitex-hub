#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/project_app/management/commands/migrate_to_scitex.py

"""
Management command to migrate existing projects to use scitex.project package.

This command initializes scitex/.metadata/ for projects that don't have it yet.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.infra.project_app.models import Project
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate existing projects to use SciTeX metadata (scitex/.metadata/)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--username", type=str, help="Only migrate projects for specific user"
        )
        parser.add_argument(
            "--project-id", type=int, help="Only migrate specific project by ID"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force migration even if directory does not exist",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        username = options.get("username")
        project_id = options.get("project_id")
        force = options.get("force")

        # Build queryset
        projects = Project.objects.all()

        if username:
            try:
                user = User.objects.get(username=username)
                projects = projects.filter(owner=user)
                self.stdout.write(f"Filtering projects for user: {username}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{username}' not found"))
                return

        if project_id:
            projects = projects.filter(id=project_id)
            self.stdout.write(f"Filtering projects with ID: {project_id}")

        total = projects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No projects found matching criteria"))
            return

        migrated = 0
        skipped = 0
        errors = 0

        self.stdout.write("=" * 60)
        self.stdout.write(f"Found {total} projects to process")
        self.stdout.write("=" * 60)

        for project in projects:
            project_label = f"{project.owner.username}/{project.slug}"

            # Skip if already has scitex metadata
            if project.has_scitex_metadata():
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP: {project_label} (already has scitex/.metadata/)"
                    )
                )
                skipped += 1
                continue

            # Check if directory exists
            local_path = project.get_local_path()
            if not local_path.exists():
                if force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARN: {project_label} (directory not found but --force specified)"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  SKIP: {project_label} (directory not found: {local_path})"
                        )
                    )
                    skipped += 1
                    continue

            if dry_run:
                self.stdout.write(f"  WOULD MIGRATE: {project_label}")
                self.stdout.write(f"    Path: {local_path}")
                self.stdout.write(f"    Name: {project.name}")
                self.stdout.write(
                    f"    Description: {project.description[:50]}..."
                    if len(project.description) > 50
                    else f"    Description: {project.description}"
                )
                migrated += 1
                continue

            # Migrate project
            try:
                scitex_project = project.initialize_scitex_metadata()
                self.stdout.write(self.style.SUCCESS(f"  ✓ MIGRATED: {project_label}"))
                self.stdout.write(f"    SciTeX ID: {scitex_project.project_id}")
                self.stdout.write(f"    Local path: {local_path}")
                migrated += 1

            except ImportError as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ ERROR: {project_label} - scitex package not installed"
                    )
                )
                self.stdout.write(f"    {e}")
                errors += 1

            except FileExistsError as e:
                self.stdout.write(self.style.WARNING(f"  SKIP: {project_label} - {e}"))
                skipped += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ ERROR: {project_label} - {type(e).__name__}: {e}"
                    )
                )
                logger.error(
                    f"Migration failed for project {project.id} ({project_label}): {e}",
                    exc_info=True,
                )
                errors += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("MIGRATION SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total projects: {total}")
        if migrated > 0:
            self.stdout.write(self.style.SUCCESS(f"Migrated: {migrated}"))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {errors}"))

        if dry_run:
            self.stdout.write(
                "\n"
                + self.style.WARNING(
                    "This was a dry run. Use without --dry-run to actually migrate."
                )
            )
        elif migrated > 0:
            self.stdout.write(
                "\n" + self.style.SUCCESS("Migration completed successfully!")
            )

        # Exit code
        if errors > 0:
            self.stdout.write(
                self.style.ERROR(
                    "\nMigration completed with errors. Check logs for details."
                )
            )
            exit(1)


# EOF
