#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/utils.py

"""
BibTeX Processing Utilities

Core enrichment job processing logic.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from ...models import BibTeXEnrichmentJob

logger = logging.getLogger(__name__)


def process_bibtex_job(job):
    """Process a BibTeX enrichment job using ScholarPipelineMetadataParallel.

    In production, this should be a Celery task for async processing.
    """

    def progress_callback(current: int, total: int, info: dict):
        """Callback to capture and store progress messages in real-time."""
        from asgiref.sync import sync_to_async

        async def update_job():
            try:
                await sync_to_async(job.refresh_from_db)()

                # Check if job was cancelled
                if await sync_to_async(lambda: job.status)() == "cancelled":
                    return

                # Create progress message
                title = info.get("title", "Unknown")
                if len(title) > 50:
                    title = title[:50] + "..."
                status_icon = "✓" if info.get("success") else "✗"
                message = f"[{current}/{total}] {status_icon} {title}"

                current_log = await sync_to_async(lambda: job.processing_log)()
                if current_log:
                    job.processing_log = current_log + f"\n{message}"
                else:
                    job.processing_log = message

                job.processed_papers = current
                await sync_to_async(job.save)(
                    update_fields=["processing_log", "processed_papers"]
                )
            except Exception as e:
                logger.warning(f"Failed to update job {job.id}: {e}")

        try:
            asyncio.create_task(update_job())
        except RuntimeError:
            asyncio.run(update_job())

    try:
        # Get user-specific SCITEX directory (thread-safe approach)
        from apps.workspace.scholar_app.integrations.scitex_scholar import (
            get_user_scitex_dir,
        )

        session_key = getattr(job, "session_key", None)
        user_scitex_dir = get_user_scitex_dir(job.user, session_key=session_key)
        logger.info(f"Using SCITEX_DIR: {user_scitex_dir} for job {job.id}")

        # NOTE: We no longer set os.environ["SCITEX_DIR"] as it's not thread-safe.
        # Instead, pass scholar_dir directly to ScholarConfig when needed.

        # Check if job was cancelled before starting
        try:
            job.refresh_from_db()
            if job.status == "cancelled":
                logger.info(f"Job {job.id} was cancelled before processing started")
                return
        except BibTeXEnrichmentJob.DoesNotExist:
            logger.warning(f"Job {job.id} was deleted before processing started")
            return

        job.status = "processing"
        job.started_at = timezone.now()
        job.processing_log = "Loading BibTeX file..."
        job.save(update_fields=["status", "started_at", "processing_log"])
        logger.info(f"Starting BibTeX job {job.id}")

        # Import scholar components
        from scitex.scholar.pipelines import ScholarPipelineMetadataParallel
        from scitex.scholar.storage import BibTeXHandler
        from scitex.scholar import ScholarConfig

        # Create user-specific config (thread-safe)
        scholar_config = ScholarConfig(scholar_dir=user_scitex_dir)

        # Get input file path
        input_path = Path(settings.MEDIA_ROOT) / job.input_file.name
        logger.info(f"Input file path: {input_path}")

        # Load papers from BibTeX
        bibtex_handler = BibTeXHandler(project=job.project_name, config=scholar_config)
        papers = bibtex_handler.papers_from_bibtex(input_path)
        logger.info(f"Loaded {len(papers) if papers else 0} papers")

        if not papers:
            raise ValueError("No papers found in BibTeX file")

        job.total_papers = len(papers)
        job.processing_log += f"\nFound {len(papers)} papers in BibTeX file"
        job.save(update_fields=["total_papers", "processing_log"])

        # Create metadata enrichment pipeline with user-specific config
        pipeline = ScholarPipelineMetadataParallel(
            num_workers=job.num_workers,
            config=scholar_config,
        )

        # Enrich papers with timeout
        async def enrich_with_timeout():
            return await asyncio.wait_for(
                pipeline.enrich_papers_async(
                    papers=papers,
                    force=not job.use_cache,
                    on_progress=progress_callback,
                ),
                timeout=600,
            )

        try:
            enriched_papers = asyncio.run(enrich_with_timeout())
        except asyncio.TimeoutError:
            job.status = "failed"
            job.error_message = "Enrichment process timed out after 10 minutes."
            job.completed_at = timezone.now()
            job.processing_log += f"\n\n✗ TIMEOUT: Job exceeded 10-minute limit"
            job.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                    "processing_log",
                ]
            )
            logger.error(f"BibTeX job {job.id} timed out after 10 minutes")
            return

        # Create output path
        original_name = (
            Path(job.original_filename).stem
            if job.original_filename
            else Path(job.input_file.name).stem
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{original_name}-enriched-by-scitex_{timestamp}.bib"

        user_dir = str(job.user.id) if job.user else "visitor"
        output_path = (
            Path(settings.MEDIA_ROOT) / "bibtex_enriched" / user_dir / output_filename
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save enriched BibTeX
        bibtex_handler.papers_to_bibtex(enriched_papers, output_path)

        # Update job with results
        job.total_papers = len(papers)
        job.processed_papers = len(enriched_papers)
        job.failed_papers = 0
        job.output_file = str(output_path.relative_to(settings.MEDIA_ROOT))

        # Gitea Integration
        if job.project and job.project.git_clone_path:
            try:
                from apps.infra.project_app.services.git_service import auto_commit_file
                from apps.infra.project_app.services.bibliography_manager import (
                    ensure_bibliography_structure,
                    regenerate_bibliography,
                )

                # Create directory
                project_bib_dir = (
                    Path(job.project.git_clone_path)
                    / "scitex"
                    / "scholar"
                    / "bib_files"
                )
                project_bib_dir.mkdir(parents=True, exist_ok=True)

                # Generate filenames
                original_name = (
                    Path(job.original_filename).stem
                    if job.original_filename
                    else "references"
                )
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                original_filename = f"{original_name}_original-{timestamp}.bib"
                enriched_filename = f"{original_name}_enriched-{timestamp}.bib"

                # Copy files
                input_file_path = Path(settings.MEDIA_ROOT) / job.input_file.name
                shutil.copy(input_file_path, project_bib_dir / original_filename)
                shutil.copy(output_path, project_bib_dir / enriched_filename)

                # Regenerate bibliography
                project_path = Path(job.project.git_clone_path)
                ensure_bibliography_structure(project_path)
                results = regenerate_bibliography(project_path, job.project.name)

                if results["success"]:
                    scholar_count = results.get("scholar_count", 0)
                    duplicates = results.get("duplicates_removed", 0)
                    logger.info(
                        f"Bibliography regenerated: "
                        f"scholar={scholar_count} entries, "
                        f"duplicates_removed={duplicates}"
                    )
                    job.enrichment_summary["bibliography_merged"] = True
                    job.enrichment_summary["total_citations"] = scholar_count
                else:
                    logger.warning(
                        f"Bibliography regeneration had errors: {results['errors']}"
                    )

                # Auto-commit disabled - users should commit manually when ready
                # Changes will show in git gutter until committed
                job.enrichment_summary["gitea_commit"] = False
                job.enrichment_summary["gitea_message"] = (
                    "Auto-commit disabled - commit manually when ready"
                )

            except Exception as gitea_error:
                logger.error(f"Gitea integration error: {gitea_error}")
                job.enrichment_summary["gitea_commit"] = False
                job.enrichment_summary["gitea_error"] = str(gitea_error)

        job.status = "completed"
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "completed_at",
                "total_papers",
                "processed_papers",
                "failed_papers",
                "output_file",
                "enrichment_summary",
            ]
        )

    except Exception as e:
        import traceback

        error_details = str(e)

        # Provide user-friendly error messages
        if "duplicate key" in error_details.lower():
            job.error_message = "Database constraint error - please try again."
        elif "no papers found" in error_details.lower():
            job.error_message = "No valid BibTeX entries found in the uploaded file."
        else:
            job.error_message = f"Processing failed: {error_details}"

        job.status = "failed"
        job.completed_at = timezone.now()
        job.processing_log += f"\n\n✗ ERROR: {job.error_message}"
        job.save(
            update_fields=["status", "error_message", "completed_at", "processing_log"]
        )

        logger.error(
            f"BibTeX job {job.id} failed: {error_details}\n{traceback.format_exc()}"
        )


# EOF
