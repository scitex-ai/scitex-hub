# -*- coding: utf-8 -*-
# Timestamp: 2025-11-25
# Author: ywatanabe
# File: apps/writer_app/tasks.py

"""
Celery tasks for Writer App.

Provides async AI operations with fair scheduling and rate limiting.
"""

import logging
from typing import Dict, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.writer_app.tasks.ai_suggest",
    max_retries=3,
    soft_time_limit=60,
    time_limit=120,
    rate_limit="10/m",  # 10 calls per minute per worker
)
def ai_suggest(
    self,
    user_id: int,
    content: str,
    section_type: str,
    target: str = "clarity",
    context: Optional[Dict] = None,
) -> Dict:
    """
    Get AI suggestions for improving text.

    This task is rate-limited to ensure fair access for all users.

    Args:
        user_id: User requesting the suggestion
        content: Current section content
        section_type: Type of section (abstract, introduction, etc.)
        target: Improvement target (clarity, conciseness, etc.)
        context: Additional context

    Returns:
        Dict with suggested_text, explanation, and changes
    """
    from .services.ai_service import WriterAI

    logger.info(f"AI suggestion requested by user {user_id} for {section_type}")

    try:
        ai = WriterAI()
        result = ai.get_suggestion(
            content=content,
            section_type=section_type,
            target=target,
            context=context,
        )

        logger.info(f"AI suggestion completed for user {user_id}")
        return {
            "success": True,
            "user_id": user_id,
            "section_type": section_type,
            "result": result,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"AI suggestion timed out for user {user_id}")
        return {
            "success": False,
            "error": "Request timed out. Please try a shorter text.",
        }
    except Exception as e:
        logger.error(f"AI suggestion failed for user {user_id}: {e}")
        # Retry with exponential backoff
        self.retry(exc=e, countdown=2**self.request.retries)


@shared_task(
    bind=True,
    name="apps.writer_app.tasks.ai_generate",
    max_retries=2,
    soft_time_limit=120,
    time_limit=180,
    rate_limit="5/m",  # More restrictive for generation
)
def ai_generate(
    self,
    user_id: int,
    section_type: str,
    target_words: int,
    context: Optional[Dict] = None,
) -> Dict:
    """
    Generate content for a section.

    This task is more rate-limited than suggestions as it's more resource-intensive.

    Args:
        user_id: User requesting generation
        section_type: Type of section to generate
        target_words: Target word count
        context: Context from other sections

    Returns:
        Dict with generated_text and metadata
    """
    from .services.ai_service import WriterAI

    logger.info(f"AI generation requested by user {user_id} for {section_type}")

    try:
        ai = WriterAI()
        result = ai.generate_content(
            section_type=section_type,
            target_words=target_words,
            context=context,
        )

        logger.info(f"AI generation completed for user {user_id}")
        return {
            "success": True,
            "user_id": user_id,
            "section_type": section_type,
            "result": result,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"AI generation timed out for user {user_id}")
        return {
            "success": False,
            "error": "Generation timed out. Try a smaller target word count.",
        }
    except Exception as e:
        logger.error(f"AI generation failed for user {user_id}: {e}")
        self.retry(exc=e, countdown=5**self.request.retries)


@shared_task(
    bind=True,
    name="apps.writer_app.tasks.compile_latex",
    soft_time_limit=300,
    time_limit=360,
    rate_limit="20/m",
)
def compile_latex(
    self,
    user_id: int,
    document_id: str,
    output_format: str = "pdf",
) -> Dict:
    """
    Compile LaTeX document to PDF or other format.

    Args:
        user_id: User requesting compilation
        document_id: Document to compile
        output_format: Output format (pdf, html, etc.)

    Returns:
        Dict with compiled file path or error
    """
    logger.info(f"LaTeX compilation requested by user {user_id} for {document_id}")

    try:
        # TODO: Implement LaTeX compilation using scitex.writer
        # from scitex.writer import compile_document
        # result = compile_document(document_id, output_format)

        return {
            "success": True,
            "user_id": user_id,
            "document_id": document_id,
            "output_format": output_format,
            "message": "Compilation completed (placeholder)",
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"LaTeX compilation timed out for user {user_id}")
        return {
            "success": False,
            "error": "Compilation timed out. Document may be too complex.",
        }
    except Exception as e:
        logger.error(f"LaTeX compilation failed for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# EOF
