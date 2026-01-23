"""
Utility functions for manuscript repository integration.
"""

import logging
from typing import Optional

from apps.scholar_app.models import RepositoryConnection

logger = logging.getLogger(__name__)


def auto_create_supplementary_dataset(manuscript) -> Optional:
    """Automatically create a supplementary dataset when manuscript is submitted"""
    from .service import ManuscriptRepositoryIntegrator

    # Check if user has auto-sync enabled
    default_connection = RepositoryConnection.objects.filter(
        user=manuscript.owner, is_default=True, auto_sync_enabled=True, status="active"
    ).first()

    if not default_connection:
        logger.info(
            f"No auto-sync repository connection for user {manuscript.owner.username}"
        )
        return None

    try:
        integrator = ManuscriptRepositoryIntegrator(manuscript, default_connection)
        dataset = integrator.create_supplementary_dataset(
            auto_upload=False
        )  # Don't auto-upload, let user review first

        if dataset:
            logger.info(
                f"Auto-created supplementary dataset {dataset.id} for manuscript {manuscript.slug}"
            )

        return dataset

    except Exception as e:
        logger.error(f"Failed to auto-create supplementary dataset: {e}")
        return None
