"""
Main repository integration service for Writer manuscripts.
"""

import logging
from typing import Dict, List, Optional

from django.db import transaction

from ...models import Manuscript, ArxivSubmission
from apps.scholar_app.models import (
    Dataset,
    RepositoryConnection,
)
from apps.scholar_app.services.repository_services import (
    upload_dataset_to_repository,
)
from .datasets import (
    create_supplementary_dataset_impl,
    create_replication_dataset_impl,
    create_arxiv_dataset_impl,
)
from .metadata import (
    generate_data_availability_statement_impl,
    get_citation_entries_impl,
)

logger = logging.getLogger(__name__)


class ManuscriptRepositoryIntegrator:
    """Service for integrating manuscripts with research data repositories"""

    def __init__(
        self,
        manuscript: Manuscript,
        repository_connection: Optional[RepositoryConnection] = None,
    ):
        self.manuscript = manuscript
        self.repository_connection = (
            repository_connection or self._get_default_connection()
        )

    def _get_default_connection(self) -> Optional[RepositoryConnection]:
        """Get user's default repository connection"""
        return RepositoryConnection.objects.filter(
            user=self.manuscript.owner, is_default=True, status="active"
        ).first()

    def create_supplementary_dataset(
        self, title: str = None, description: str = None, auto_upload: bool = True
    ) -> Optional[Dataset]:
        """Create a supplementary dataset for the manuscript"""
        return create_supplementary_dataset_impl(
            self, title, description, auto_upload
        )

    def create_replication_dataset(
        self,
        code_outputs: List = None,
        analysis_data: List = None,
        auto_upload: bool = True,
    ) -> Optional[Dataset]:
        """Create a replication dataset with code and data for reproducibility"""
        return create_replication_dataset_impl(
            self, code_outputs, analysis_data, auto_upload
        )

    def create_arxiv_dataset_for_submission(
        self, arxiv_submission: ArxivSubmission
    ) -> Optional[Dataset]:
        """Create a dataset for arXiv submission materials"""
        return create_arxiv_dataset_impl(self, arxiv_submission)

    def link_existing_datasets(self, dataset_ids: List[str]) -> int:
        """Link existing datasets to the manuscript"""

        linked_count = 0

        for dataset_id in dataset_ids:
            try:
                dataset = Dataset.objects.get(
                    id=dataset_id, owner=self.manuscript.owner
                )
                dataset.cited_in_manuscripts.add(self.manuscript)
                linked_count += 1

            except Dataset.DoesNotExist:
                logger.warning(f"Dataset {dataset_id} not found or not owned by user")

        logger.info(
            f"Linked {linked_count} datasets to manuscript {self.manuscript.slug}"
        )
        return linked_count

    def generate_data_availability_statement(self) -> str:
        """Generate a data availability statement for the manuscript"""
        return generate_data_availability_statement_impl(self.manuscript)

    def get_citation_entries_for_datasets(self) -> List[Dict]:
        """Generate citation entries for linked datasets"""
        return get_citation_entries_impl(self.manuscript)
