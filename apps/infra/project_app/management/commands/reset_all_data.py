#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-11 08:32:01 (ywatanabe)"


"""
Django management command to delete all users and projects for fresh start

This is a DANGEROUS command that will:
1. Delete all projects (and their Gitea repos)
2. Delete all users except superusers
3. Delete project directories from filesystem
4. Clean up incomplete writer directories

Usage:
    python manage.py reset_all_data --confirm

    For local development (RECOMMENDED):
    python manage.py reset_all_data --confirm --delete-directories

Safety features:
    - Requires explicit --confirm flag
    - Preserves superuser accounts
    - Provides dry-run option
    - Shows summary before deletion
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.infra.project_app.models import Project
from apps.workspace.writer_app.models import Manuscript
from apps.infra.gitea_app.api_client import GiteaClient
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Delete all users and projects for fresh start (DANGEROUS!)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm that you want to delete everything",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--keep-users",
            action="store_true",
            help="Only delete projects, keep users",
        )
        parser.add_argument(
            "--delete-directories",
            action="store_true",
            help="Also delete project directories from filesystem",
        )

    def handle(self, *args, **options):
        confirm = options.get("confirm")
        dry_run = options.get("dry_run")
        keep_users = options.get("keep_users")
        delete_dirs = options.get("delete_directories")

        if not confirm and not dry_run:
            self.stdout.write(
                self.style.ERROR("⚠️  DANGER: This will delete all users and projects!")
            )
            self.stdout.write(
                self.style.ERROR(
                    "Add --confirm flag to proceed, or --dry-run to preview"
                )
            )
            return

        self.stdout.write(self.style.WARNING("\n" + "=" * 60))
        self.stdout.write(self.style.WARNING("🔥 RESET ALL DATA 🔥"))
        self.stdout.write(self.style.WARNING("=" * 60 + "\n"))

        # Count what we'll delete
        total_projects = Project.objects.count()
        non_superusers = User.objects.filter(is_superuser=False)
        total_users = non_superusers.count()
        total_manuscripts = Manuscript.objects.count()

        self.stdout.write(f"📊 Current state:")
        self.stdout.write(f"   - Projects: {total_projects}")
        self.stdout.write(f"   - Manuscripts: {total_manuscripts}")
        self.stdout.write(f"   - Non-superusers: {total_users}")
        self.stdout.write(
            f"   - Superusers: {User.objects.filter(is_superuser=True).count()} (will be preserved)"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n[DRY RUN] No actual deletions will be performed\n"
                )
            )

        # Step 1: Delete all projects
        self.stdout.write("\n📁 Step 1: Deleting projects...")
        projects_deleted = 0
        gitea_repos_deleted = 0
        errors = 0

        for project in Project.objects.all():
            try:
                project_name = f"{project.owner.username}/{project.slug}"

                # Delete Gitea repository
                if project.gitea_repo_name:
                    if dry_run:
                        self.stdout.write(
                            f"   [DRY RUN] Would delete Gitea repo: {project_name}"
                        )
                    else:
                        try:
                            client = GiteaClient()
                            client.delete_repository(
                                project.owner.username, project.gitea_repo_name
                            )
                            gitea_repos_deleted += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"   ✓ Deleted Gitea repo: {project_name}"
                                )
                            )
                        except Exception as e:
                            logger.warning(
                                f"Could not delete Gitea repo {project_name}: {e}"
                            )

                # Delete project directory if requested
                if delete_dirs and project.git_clone_path:
                    project_path = Path(project.git_clone_path)
                    if project_path.exists():
                        if dry_run:
                            self.stdout.write(
                                f"   [DRY RUN] Would delete directory: {project_path}"
                            )
                        else:
                            try:
                                shutil.rmtree(project_path)
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"   ✓ Deleted directory: {project_path}"
                                    )
                                )
                            except Exception as e:
                                logger.error(
                                    f"Could not delete directory {project_path}: {e}"
                                )
                                errors += 1

                # Delete Django project
                if dry_run:
                    self.stdout.write(
                        f"   [DRY RUN] Would delete project: {project_name}"
                    )
                else:
                    project.delete()
                    projects_deleted += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"   ✓ Deleted project: {project_name}")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"   ✗ Error deleting project {project.slug}: {e}")
                )
                errors += 1

        # Step 2: Delete manuscripts (in case some weren't cascade-deleted)
        self.stdout.write("\n📝 Step 2: Deleting manuscripts...")
        if dry_run:
            self.stdout.write(
                f"   [DRY RUN] Would delete {total_manuscripts} manuscripts"
            )
        else:
            manuscripts_deleted = Manuscript.objects.all().delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f"   ✓ Deleted {manuscripts_deleted} manuscripts")
            )

        # Step 2.5: Clean up incomplete writer directories
        self.stdout.write("\n🧹 Step 2.5: Cleaning incomplete writer directories...")
        from django.conf import settings

        data_dir = Path(settings.BASE_DIR) / "data" / "users"
        incomplete_dirs_cleaned = 0

        if data_dir.exists():
            for user_dir in data_dir.iterdir():
                if not user_dir.is_dir() or user_dir.name.startswith("."):
                    continue

                for project_dir in user_dir.iterdir():
                    if not project_dir.is_dir() or project_dir.name.startswith("."):
                        continue

                    writer_dir = project_dir / "scitex" / "writer"
                    if writer_dir.exists():
                        # Check if writer directory is incomplete
                        # (has old bib_files/ structure OR missing required directories)
                        old_structure = (writer_dir / "bib_files").exists()
                        missing_required = not (
                            writer_dir / "02_supplementary"
                        ).exists()

                        if old_structure or missing_required:
                            if dry_run:
                                self.stdout.write(
                                    f"   [DRY RUN] Would clean incomplete writer: {writer_dir.relative_to(data_dir)}"
                                )
                            else:
                                try:
                                    shutil.rmtree(writer_dir)
                                    incomplete_dirs_cleaned += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"   ✓ Cleaned incomplete writer: {writer_dir.relative_to(data_dir)}"
                                        )
                                    )
                                except Exception as e:
                                    logger.error(f"Could not clean {writer_dir}: {e}")

        if incomplete_dirs_cleaned > 0 or dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✓ Cleaned {incomplete_dirs_cleaned} incomplete writer directories"
                )
            )
        else:
            self.stdout.write("   No incomplete writer directories found")

        # Step 3: Delete users
        if not keep_users:
            self.stdout.write("\n👤 Step 3: Deleting users (except superusers)...")
            users_deleted = 0

            for user in non_superusers:
                if dry_run:
                    self.stdout.write(
                        f"   [DRY RUN] Would delete user: {user.username}"
                    )
                else:
                    username = user.username
                    user.delete()
                    users_deleted += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"   ✓ Deleted user: {username}")
                    )
        else:
            self.stdout.write("\n👤 Step 3: Skipping user deletion (--keep-users flag)")
            users_deleted = 0

        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN SUMMARY (no actual deletions)")
            )
        else:
            self.stdout.write(self.style.SUCCESS("✅ DELETION SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"   Projects deleted: {projects_deleted}")
        self.stdout.write(f"   Gitea repos deleted: {gitea_repos_deleted}")
        if not keep_users:
            self.stdout.write(f"   Users deleted: {users_deleted}")
        if errors > 0:
            self.stdout.write(self.style.ERROR(f"   Errors: {errors}"))
        self.stdout.write("=" * 60 + "\n")

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "✨ Fresh start ready! You can now create new projects."
                )
            )


# EOF
