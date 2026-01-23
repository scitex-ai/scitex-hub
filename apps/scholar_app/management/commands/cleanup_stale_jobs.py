#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to clean up stale BibTeX enrichment jobs.

This should be run periodically (e.g., via cron or systemd timer) to:
- Fail jobs stuck in processing for >10 minutes
- Fail jobs stuck in pending for >5 minutes
- Delete old completed/failed jobs (>30 days)
- Prevent malicious resource exhaustion attacks

Usage:
    python manage.py cleanup_stale_jobs
    python manage.py cleanup_stale_jobs --delete-old-jobs  # Also delete old jobs
    python manage.py cleanup_stale_jobs --dry-run  # Show what would be done
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.scholar_app.models import BibTeXEnrichmentJob


class Command(BaseCommand):
    help = "Clean up stale BibTeX enrichment jobs to prevent resource exhaustion"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--delete-old-jobs",
            action="store_true",
            help="Delete completed/failed jobs older than 30 days",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=30,
            help="Number of days to retain old jobs (default: 30)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        delete_old = options["delete_old_jobs"]
        retention_days = options["retention_days"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # 1. Find and fail stale processing jobs (>10 minutes)
        stale_processing = BibTeXEnrichmentJob.objects.filter(
            status="processing", started_at__lt=timezone.now() - timedelta(minutes=10)
        )

        processing_count = stale_processing.count()
        if processing_count > 0:
            self.stdout.write(
                f"Found {processing_count} stale processing jobs (>10 minutes)"
            )

            if not dry_run:
                for job in stale_processing:
                    job.status = "failed"
                    job.error_message = "Job timed out (automatic cleanup)"
                    job.completed_at = timezone.now()
                    job.processing_log += "\n\n✗ Automatically failed by cleanup task (processing >10 min)"
                    job.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "completed_at",
                            "processing_log",
                        ]
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Failed {processing_count} stale processing jobs"
                    )
                )
            else:
                for job in stale_processing:
                    user = job.user.username if job.user else "visitor"
                    duration = (timezone.now() - job.started_at).total_seconds() / 60
                    self.stdout.write(
                        f"  - Would fail: {job.original_filename} (user: {user}, running for {duration:.1f} min)"
                    )

        # 2. Find and fail stale pending jobs (>5 minutes)
        stale_pending = BibTeXEnrichmentJob.objects.filter(
            status="pending", created_at__lt=timezone.now() - timedelta(minutes=5)
        )

        pending_count = stale_pending.count()
        if pending_count > 0:
            self.stdout.write(f"Found {pending_count} stale pending jobs (>5 minutes)")

            if not dry_run:
                for job in stale_pending:
                    job.status = "failed"
                    job.error_message = "Job stuck in pending state (automatic cleanup)"
                    job.completed_at = timezone.now()
                    job.processing_log += (
                        "\n\n✗ Automatically failed by cleanup task (pending >5 min)"
                    )
                    job.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "completed_at",
                            "processing_log",
                        ]
                    )

                self.stdout.write(
                    self.style.SUCCESS(f"✓ Failed {pending_count} stale pending jobs")
                )
            else:
                for job in stale_pending:
                    user = job.user.username if job.user else "visitor"
                    duration = (timezone.now() - job.created_at).total_seconds() / 60
                    self.stdout.write(
                        f"  - Would fail: {job.original_filename} (user: {user}, pending for {duration:.1f} min)"
                    )

        # 3. Delete old completed/failed jobs (optional)
        if delete_old:
            cutoff_date = timezone.now() - timedelta(days=retention_days)
            old_jobs = BibTeXEnrichmentJob.objects.filter(
                status__in=["completed", "failed", "cancelled"],
                completed_at__lt=cutoff_date,
            )

            old_count = old_jobs.count()
            if old_count > 0:
                self.stdout.write(
                    f"Found {old_count} old jobs (>{retention_days} days)"
                )

                if not dry_run:
                    # Delete associated files first
                    for job in old_jobs:
                        if job.input_file:
                            try:
                                job.input_file.delete(save=False)
                            except Exception:
                                pass
                        if job.output_file:
                            try:
                                job.output_file.delete(save=False)
                            except Exception:
                                pass

                    old_jobs.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Deleted {old_count} old jobs")
                    )
                else:
                    for job in old_jobs:
                        user = job.user.username if job.user else "visitor"
                        self.stdout.write(
                            f"  - Would delete: {job.original_filename} (user: {user}, completed: {job.completed_at})"
                        )

        # 4. Summary statistics
        total_jobs = BibTeXEnrichmentJob.objects.count()
        active_jobs = BibTeXEnrichmentJob.objects.filter(
            status__in=["pending", "processing"]
        ).count()
        completed_jobs = BibTeXEnrichmentJob.objects.filter(status="completed").count()
        failed_jobs = BibTeXEnrichmentJob.objects.filter(status="failed").count()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Current System Status:")
        self.stdout.write(f"  Total jobs: {total_jobs}")
        self.stdout.write(f"  Active jobs: {active_jobs}")
        self.stdout.write(f"  Completed jobs: {completed_jobs}")
        self.stdout.write(f"  Failed jobs: {failed_jobs}")
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN COMPLETE - Run without --dry-run to apply changes"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Cleanup complete"))
