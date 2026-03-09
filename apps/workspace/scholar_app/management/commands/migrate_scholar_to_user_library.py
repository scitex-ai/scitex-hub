#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to migrate Scholar papers from Django media to user library.

This command migrates UserLibrary entries from the legacy Django FileField storage
(media/user_library/) to the new user-level library structure (~/.scitex/scholar/library/).

Phase 2 of Scholar migration:
- Phase 1: Create new storage infrastructure (UserLibraryService)
- Phase 2: Migrate existing papers (this command)
- Phase 3: Remove legacy FileField storage

Architecture:
    Legacy: personal_pdf/personal_bibtex → Django media/user_library/
    New: user_library_pdf_path/user_library_bibtex_path → ~/.scitex/scholar/library/

Usage:
    python manage.py migrate_scholar_to_user_library --dry-run
    python manage.py migrate_scholar_to_user_library --user=test-user --confirm
    python manage.py migrate_scholar_to_user_library --confirm
"""

import logging
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.workspace.scholar_app.models import UserLibrary
from apps.workspace.scholar_app.services import UserLibraryService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate Scholar papers from Django media storage to user-level library"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="Migrate papers for a specific user (username)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview migration without making changes",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm and execute migration (safety gate)",
        )

    def handle(self, *args, **options):
        username = options.get("user")
        dry_run = options["dry_run"]
        confirm = options["confirm"]

        # Safety gate: require explicit confirmation unless dry-run
        if not dry_run and not confirm:
            self.stdout.write(
                self.style.ERROR(
                    "ERROR: Migration requires --confirm flag or use --dry-run to preview"
                )
            )
            self.stdout.write("\nUsage:")
            self.stdout.write("  --dry-run           Preview migration")
            self.stdout.write("  --confirm           Execute migration")
            self.stdout.write("  --user=USERNAME     Filter by user")
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Get target users
        if username:
            try:
                users = [User.objects.get(username=username)]
                self.stdout.write(f"Targeting user: {username}")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"ERROR: User '{username}' not found")
                )
                return
        else:
            users = User.objects.all()
            self.stdout.write(f"Targeting all users: {users.count()} users")

        # Migration stats
        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "already_migrated": 0,
        }

        # Process each user
        for user in users:
            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(f"Processing user: {user.username}")
            self.stdout.write("=" * 60)

            # Get papers needing migration
            papers_to_migrate = UserLibrary.objects.filter(
                user=user, storage_mode="django_media"
            )
            user_total = papers_to_migrate.count()
            stats["total"] += user_total

            if user_total == 0:
                self.stdout.write(
                    self.style.SUCCESS(f"No papers to migrate for {user.username}")
                )
                continue

            self.stdout.write(f"Found {user_total} papers to migrate")

            # Initialize service
            try:
                service = UserLibraryService(user)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Failed to initialize UserLibraryService for {user.username}: {e}"
                    )
                )
                stats["errors"] += user_total
                continue

            # Process each paper
            for library_entry in papers_to_migrate:
                stats_result = self._migrate_paper(
                    library_entry, service, dry_run=dry_run
                )
                stats["migrated"] += stats_result.get("migrated", 0)
                stats["skipped"] += stats_result.get("skipped", 0)
                stats["errors"] += stats_result.get("errors", 0)
                stats["already_migrated"] += stats_result.get("already_migrated", 0)

        # Final summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Migration Summary:")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total papers found:      {stats['total']}")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully migrated:   {stats['migrated']}")
        )
        self.stdout.write(
            self.style.WARNING(f"Already migrated:        {stats['already_migrated']}")
        )
        self.stdout.write(
            self.style.WARNING(f"Skipped (no files):      {stats['skipped']}")
        )
        self.stdout.write(
            self.style.ERROR(f"Errors:                  {stats['errors']}")
        )
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN COMPLETE - Run with --confirm to apply changes"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Migration complete"))

    def _migrate_paper(
        self, library_entry: UserLibrary, service: UserLibraryService, dry_run: bool
    ) -> dict:
        """
        Migrate a single paper from Django media to user library.

        Args:
            library_entry: UserLibrary instance to migrate
            service: UserLibraryService instance for the user
            dry_run: If True, only preview without making changes

        Returns:
            Dict with migration stats: {"migrated": 0/1, "skipped": 0/1, "errors": 0/1}
        """
        stats = {"migrated": 0, "skipped": 0, "errors": 0, "already_migrated": 0}
        paper = library_entry.paper

        # Get paper identifier
        identifier, id_type = self._get_paper_identifier(paper)
        if not identifier:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⊘ Skipped: {paper.title[:60]} (no identifier found)"
                )
            )
            stats["skipped"] = 1
            return stats

        # Check if already migrated (shouldn't happen with filter, but safety check)
        if library_entry.storage_mode == "user_library":
            self.stdout.write(
                self.style.WARNING(
                    f"  ⊘ Already migrated: {identifier} ({paper.title[:50]})"
                )
            )
            stats["already_migrated"] = 1
            return stats

        # Check if files exist in Django media
        has_pdf = bool(library_entry.personal_pdf)
        has_bibtex = bool(library_entry.personal_bibtex)

        if not has_pdf and not has_bibtex:
            self.stdout.write(
                self.style.WARNING(f"  ⊘ Skipped: {identifier} (no files to migrate)")
            )
            stats["skipped"] = 1
            return stats

        # Get file paths
        pdf_path = None
        bibtex_content = None

        try:
            if has_pdf:
                pdf_path = Path(library_entry.personal_pdf.path)
                if not pdf_path.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⊘ Warning: PDF file not found: {pdf_path}"
                        )
                    )
                    pdf_path = None

            if has_bibtex:
                bibtex_path = Path(library_entry.personal_bibtex.path)
                if bibtex_path.exists():
                    bibtex_content = bibtex_path.read_text(encoding="utf-8")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⊘ Warning: BibTeX file not found: {bibtex_path}"
                        )
                    )

        except (ValueError, AttributeError, IOError) as e:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Error reading files for {identifier}: {e}")
            )
            stats["errors"] = 1
            return stats

        # Skip if no valid files
        if not pdf_path and not bibtex_content:
            self.stdout.write(
                self.style.WARNING(f"  ⊘ Skipped: {identifier} (no valid files found)")
            )
            stats["skipped"] = 1
            return stats

        # Preview mode
        if dry_run:
            files_to_migrate = []
            if pdf_path:
                files_to_migrate.append("PDF")
            if bibtex_content:
                files_to_migrate.append("BibTeX")

            self.stdout.write(
                f"  → Would migrate: {identifier} ({', '.join(files_to_migrate)})"
            )
            self.stdout.write(f"     Title: {paper.title[:60]}")
            stats["migrated"] = 1
            return stats

        # Execute migration
        try:
            with transaction.atomic():
                # Copy files to user library
                result = service.add_paper(
                    identifier=identifier,
                    id_type=id_type,
                    pdf_path=pdf_path,
                    bibtex_content=bibtex_content,
                )

                # Update database record
                if "pdf" in result:
                    library_entry.user_library_pdf_path = str(result["pdf"])
                if "bibtex" in result:
                    library_entry.user_library_bibtex_path = str(result["bibtex"])

                library_entry.storage_mode = "user_library"
                library_entry.save(
                    update_fields=[
                        "user_library_pdf_path",
                        "user_library_bibtex_path",
                        "storage_mode",
                    ]
                )

                files_migrated = []
                if "pdf" in result:
                    files_migrated.append("PDF")
                if "bibtex" in result:
                    files_migrated.append("BibTeX")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Migrated: {identifier} ({', '.join(files_migrated)})"
                    )
                )
                stats["migrated"] = 1

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Error migrating {identifier}: {e}")
            )
            logger.exception(f"Migration error for paper {identifier}")
            stats["errors"] = 1

        return stats

    def _get_paper_identifier(self, paper) -> tuple[str, str]:
        """
        Get paper identifier and type (DOI, PMID, arXiv ID).

        Args:
            paper: SearchIndex instance

        Returns:
            Tuple of (identifier, id_type) or (None, None) if no identifier found
        """
        if paper.doi:
            return (paper.doi, "doi")
        elif paper.pmid:
            return (paper.pmid, "pmid")
        elif paper.arxiv_id:
            return (paper.arxiv_id, "arxiv")
        else:
            return (None, None)
