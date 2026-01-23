"""
Dataset creation functionality for manuscript repository integration.
"""

import logging
from typing import List, Optional

from django.db import transaction

from apps.scholar_app.models import Dataset
from apps.scholar_app.services.repository_services import (
    upload_dataset_to_repository,
)
from .files import (
    add_manuscript_files_to_dataset,
    add_replication_materials_to_dataset,
    add_arxiv_files_to_dataset,
)
from .metadata import (
    generate_dataset_description,
    generate_replication_description,
    generate_arxiv_dataset_description,
    generate_keywords,
)

logger = logging.getLogger(__name__)


def create_supplementary_dataset_impl(
    integrator, title: str = None, description: str = None, auto_upload: bool = True
) -> Optional[Dataset]:
    """Create a supplementary dataset for the manuscript"""

    if not integrator.repository_connection:
        logger.warning(
            f"No repository connection available for user {integrator.manuscript.owner.username}"
        )
        return None

    try:
        with transaction.atomic():
            # Create dataset
            dataset_title = (
                title or f"Supplementary Data for: {integrator.manuscript.title}"
            )
            dataset_description = (
                description or generate_dataset_description(integrator.manuscript)
            )

            dataset = Dataset.objects.create(
                title=dataset_title,
                description=dataset_description,
                dataset_type="supplementary",
                owner=integrator.manuscript.owner,
                repository_connection=integrator.repository_connection,
                keywords=generate_keywords(integrator.manuscript),
                status="draft",
                license="CC-BY-4.0",  # Default open license
            )

            # Link dataset to manuscript
            dataset.cited_in_manuscripts.add(integrator.manuscript)

            # Add manuscript files to dataset
            add_manuscript_files_to_dataset(dataset, integrator.manuscript)

            # Auto-upload if requested
            if auto_upload:
                upload_dataset_to_repository(dataset)

            logger.info(
                f"Created supplementary dataset {dataset.id} for manuscript {integrator.manuscript.slug}"
            )
            return dataset

    except Exception as e:
        logger.error(f"Failed to create supplementary dataset: {e}")
        return None


def create_replication_dataset_impl(
    integrator,
    code_outputs: List = None,
    analysis_data: List = None,
    auto_upload: bool = True,
) -> Optional[Dataset]:
    """Create a replication dataset with code and data for reproducibility"""

    if not integrator.repository_connection:
        logger.warning(
            f"No repository connection available for user {integrator.manuscript.owner.username}"
        )
        return None

    try:
        with transaction.atomic():
            dataset = Dataset.objects.create(
                title=f"Replication Data for: {integrator.manuscript.title}",
                description=generate_replication_description(integrator.manuscript),
                dataset_type="replication_data",
                owner=integrator.manuscript.owner,
                repository_connection=integrator.repository_connection,
                keywords=f"replication, reproducibility, {generate_keywords(integrator.manuscript)}",
                status="draft",
                license="CC-BY-4.0",
            )

            # Link dataset to manuscript
            dataset.cited_in_manuscripts.add(integrator.manuscript)

            # Add replication materials
            add_replication_materials_to_dataset(
                dataset, integrator.manuscript, code_outputs, analysis_data
            )

            # Auto-upload if requested
            if auto_upload:
                upload_dataset_to_repository(dataset)

            logger.info(
                f"Created replication dataset {dataset.id} for manuscript {integrator.manuscript.slug}"
            )
            return dataset

    except Exception as e:
        logger.error(f"Failed to create replication dataset: {e}")
        return None


def create_arxiv_dataset_impl(integrator, arxiv_submission) -> Optional[Dataset]:
    """Create a dataset for arXiv submission materials"""

    if not integrator.repository_connection:
        logger.warning(
            f"No repository connection available for user {integrator.manuscript.owner.username}"
        )
        return None

    try:
        with transaction.atomic():
            dataset = Dataset.objects.create(
                title=f"arXiv Submission Materials: {arxiv_submission.title}",
                description=generate_arxiv_dataset_description(arxiv_submission),
                dataset_type="supplementary",
                owner=integrator.manuscript.owner,
                repository_connection=integrator.repository_connection,
                keywords=f"arxiv, preprint, {generate_keywords(integrator.manuscript)}",
                status="draft",
                license="CC-BY-4.0",
            )

            # Link dataset to manuscript
            dataset.cited_in_manuscripts.add(integrator.manuscript)

            # Add arXiv submission files
            add_arxiv_files_to_dataset(dataset, arxiv_submission)

            logger.info(
                f"Created arXiv dataset {dataset.id} for submission {arxiv_submission.submission_id}"
            )
            return dataset

    except Exception as e:
        logger.error(f"Failed to create arXiv dataset: {e}")
        return None
