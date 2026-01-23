# -*- coding: utf-8 -*-
# Timestamp: 2025-11-25
# Author: ywatanabe
# File: apps/scholar_app/tasks.py

"""
Celery tasks for Scholar App.

Provides async literature search and PDF processing with fair scheduling.
"""

import logging
from typing import Dict, List, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.scholar_app.tasks.search_papers",
    max_retries=3,
    soft_time_limit=60,
    time_limit=90,
    rate_limit="30/m",  # 30 searches per minute
)
def search_papers(
    self,
    user_id: int,
    query: str,
    sources: Optional[List[str]] = None,
    max_results: int = 20,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> Dict:
    """
    Search papers across multiple sources.

    This task is rate-limited to ensure fair access to external APIs.

    Args:
        user_id: User performing the search
        query: Search query string
        sources: List of sources (pubmed, arxiv, google_scholar)
        max_results: Maximum results per source
        year_from: Filter by publication year (start)
        year_to: Filter by publication year (end)

    Returns:
        Dict with search results grouped by source
    """
    sources = sources or ["pubmed", "arxiv"]

    logger.info(f"Paper search requested by user {user_id}: {query[:50]}...")

    try:
        # Try using SciTeX Scholar if available
        try:
            from scitex.scholar.pipelines.ScholarPipelineSearchParallel import (
                ScholarPipelineSearchParallel,
            )

            pipeline = ScholarPipelineSearchParallel()
            results = pipeline.search(
                query=query,
                sources=sources,
                max_results=max_results,
            )

            logger.info(f"Search completed for user {user_id}: {len(results)} results")
            return {
                "success": True,
                "user_id": user_id,
                "query": query,
                "results": results,
                "source": "scitex_scholar",
            }

        except ImportError:
            # Fallback to database search
            from apps.scholar_app.models import SearchIndex

            db_results = SearchIndex.objects.filter(
                title__icontains=query
            )[:max_results]

            results = [
                {
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "abstract": r.abstract,
                    "doi": r.doi,
                }
                for r in db_results
            ]

            logger.info(f"DB search completed for user {user_id}: {len(results)} results")
            return {
                "success": True,
                "user_id": user_id,
                "query": query,
                "results": results,
                "source": "database",
            }

    except SoftTimeLimitExceeded:
        logger.warning(f"Search timed out for user {user_id}")
        return {
            "success": False,
            "error": "Search timed out. Try a more specific query.",
        }
    except Exception as e:
        logger.error(f"Search failed for user {user_id}: {e}")
        self.retry(exc=e, countdown=2**self.request.retries)


@shared_task(
    bind=True,
    name="apps.scholar_app.tasks.process_pdf",
    max_retries=2,
    soft_time_limit=120,
    time_limit=180,
    rate_limit="20/m",
)
def process_pdf(
    self,
    user_id: int,
    pdf_path: str,
    extract_text: bool = True,
    extract_figures: bool = False,
    extract_tables: bool = False,
) -> Dict:
    """
    Process a PDF file to extract content.

    Args:
        user_id: User requesting processing
        pdf_path: Path to PDF file
        extract_text: Whether to extract text
        extract_figures: Whether to extract figures
        extract_tables: Whether to extract tables

    Returns:
        Dict with extracted content
    """
    logger.info(f"PDF processing requested by user {user_id}: {pdf_path}")

    try:
        # TODO: Implement PDF processing using scitex.scholar
        # from scitex.scholar import PDFProcessor
        # processor = PDFProcessor()
        # result = processor.process(pdf_path, ...)

        return {
            "success": True,
            "user_id": user_id,
            "pdf_path": pdf_path,
            "text": "Extracted text placeholder...",
            "message": "PDF processing completed (placeholder)",
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"PDF processing timed out for user {user_id}")
        return {
            "success": False,
            "error": "PDF processing timed out. File may be too large.",
        }
    except Exception as e:
        logger.error(f"PDF processing failed for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@shared_task(
    bind=True,
    name="apps.scholar_app.tasks.batch_process_pdfs",
    soft_time_limit=600,
    time_limit=900,
    rate_limit="5/m",  # More restrictive for batch
)
def batch_process_pdfs(
    self,
    user_id: int,
    pdf_paths: List[str],
) -> Dict:
    """
    Process multiple PDF files in batch.

    This is a heavier task, so it's more rate-limited.
    For very large batches (100+ PDFs), consider using SLURM instead.

    Args:
        user_id: User requesting batch processing
        pdf_paths: List of PDF file paths

    Returns:
        Dict with processing results for each file
    """
    logger.info(f"Batch PDF processing requested by user {user_id}: {len(pdf_paths)} files")

    if len(pdf_paths) > 100:
        logger.warning(f"Large batch ({len(pdf_paths)} files) - consider using SLURM")
        return {
            "success": False,
            "error": "Batch too large. Use SLURM for 100+ PDFs via /code/ app.",
            "suggestion": "Submit as a computational job in the Code app",
        }

    results = []
    for pdf_path in pdf_paths:
        # Process each PDF
        result = process_pdf.delay(user_id, pdf_path)
        results.append({"pdf_path": pdf_path, "task_id": result.id})

    return {
        "success": True,
        "user_id": user_id,
        "batch_size": len(pdf_paths),
        "tasks": results,
        "message": f"Queued {len(pdf_paths)} PDF processing tasks",
    }


@shared_task(
    bind=True,
    name="apps.scholar_app.tasks.fetch_paper_metadata",
    max_retries=3,
    soft_time_limit=30,
    time_limit=60,
    rate_limit="60/m",
)
def fetch_paper_metadata(
    self,
    user_id: int,
    identifier: str,
    identifier_type: str = "doi",
) -> Dict:
    """
    Fetch metadata for a paper by DOI, PMID, or arXiv ID.

    Args:
        user_id: User requesting metadata
        identifier: Paper identifier (DOI, PMID, arXiv ID)
        identifier_type: Type of identifier (doi, pmid, arxiv)

    Returns:
        Dict with paper metadata
    """
    logger.info(f"Metadata fetch requested by user {user_id}: {identifier_type}:{identifier}")

    try:
        # TODO: Implement metadata fetching
        # from scitex.scholar import fetch_metadata
        # result = fetch_metadata(identifier, identifier_type)

        return {
            "success": True,
            "user_id": user_id,
            "identifier": identifier,
            "identifier_type": identifier_type,
            "metadata": {
                "title": "Paper title placeholder",
                "authors": ["Author 1", "Author 2"],
                "year": 2024,
                "abstract": "Abstract placeholder...",
            },
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Metadata fetch timed out for user {user_id}")
        return {
            "success": False,
            "error": "Metadata fetch timed out.",
        }
    except Exception as e:
        logger.error(f"Metadata fetch failed for user {user_id}: {e}")
        self.retry(exc=e, countdown=2**self.request.retries)


# EOF
