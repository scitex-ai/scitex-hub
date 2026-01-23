"""
DOI manager service for dataset publication and metadata management.
Handles DOI assignment, publishing, and validation for datasets.
"""

import logging
from typing import Dict, Optional, Any

from django.utils import timezone

from ...models import Dataset, RepositoryConnection
from .services.factory import RepositoryServiceFactory
from .doi_exceptions import DOIAssignmentError, DOIMetadataError
from .doi_metadata_builder import DatasetMetadataBuilder

logger = logging.getLogger(__name__)


class DOIManager:
    """Service for managing DOI operations"""

    def __init__(self, repository_connection: RepositoryConnection):
        self.connection = repository_connection
        self.repository = repository_connection.repository
        self.metadata_builder = DatasetMetadataBuilder()

    def assign_doi_to_dataset(
        self, dataset: Dataset, publish: bool = False
    ) -> Optional[str]:
        """Assign a DOI to a dataset through the repository"""

        try:
            # Build metadata
            metadata_xml = self.metadata_builder.build_metadata(dataset)

            # Get repository service
            service = RepositoryServiceFactory.create_service(self.connection)

            # Create or update dataset in repository
            if dataset.repository_id:
                # Update existing dataset
                repo_data = service.update_dataset(
                    dataset.repository_id,
                    {
                        "title": dataset.title,
                        "description": dataset.description,
                        "metadata_xml": metadata_xml,
                    },
                )
            else:
                # Create new dataset
                repo_data = service.create_dataset(
                    {
                        "title": dataset.title,
                        "description": dataset.description,
                        "metadata_xml": metadata_xml,
                    }
                )
                dataset.repository_id = repo_data.get("id")
                dataset.repository_url = repo_data.get("url")

            # Get DOI from repository response
            doi = repo_data.get("doi") or repo_data.get("conceptdoi")

            if doi:
                dataset.repository_doi = doi
                dataset.save()

                logger.info(f"Assigned DOI {doi} to dataset {dataset.id}")

                # Publish if requested
                if publish and dataset.repository_id:
                    self.publish_dataset_doi(dataset)

                return doi
            else:
                raise DOIAssignmentError("No DOI returned from repository")

        except Exception as e:
            logger.error(f"Failed to assign DOI to dataset {dataset.id}: {e}")
            raise DOIAssignmentError(f"DOI assignment failed: {e}")

    def publish_dataset_doi(self, dataset: Dataset) -> bool:
        """Publish a dataset DOI to make it publicly available"""

        try:
            if not dataset.repository_id:
                raise DOIAssignmentError(
                    "Dataset must be uploaded to repository before publishing DOI"
                )

            # Get repository service
            service = RepositoryServiceFactory.create_service(self.connection)

            # Publish dataset
            result = service.publish_dataset(dataset.repository_id)

            # Update dataset status
            dataset.status = "published"
            dataset.published_at = timezone.now()
            dataset.repository_url = result.get("url", dataset.repository_url)
            dataset.repository_doi = result.get("doi", dataset.repository_doi)
            dataset.save()

            logger.info(
                f"Published DOI for dataset {dataset.id}: {dataset.repository_doi}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish DOI for dataset {dataset.id}: {e}")
            raise DOIAssignmentError(f"DOI publication failed: {e}")

    def update_dataset_metadata(self, dataset: Dataset) -> bool:
        """Update dataset metadata including DOI metadata"""

        try:
            if not dataset.repository_id:
                logger.warning(
                    f"Dataset {dataset.id} has no repository ID, cannot update metadata"
                )
                return False

            # Build updated metadata
            metadata_xml = self.metadata_builder.build_metadata(dataset)

            # Get repository service
            service = RepositoryServiceFactory.create_service(self.connection)

            # Update dataset
            service.update_dataset(
                dataset.repository_id,
                {
                    "title": dataset.title,
                    "description": dataset.description,
                    "metadata_xml": metadata_xml,
                },
            )

            dataset.last_synced = timezone.now()
            dataset.save()

            logger.info(f"Updated metadata for dataset {dataset.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update metadata for dataset {dataset.id}: {e}")
            raise DOIMetadataError(f"Metadata update failed: {e}")

    def validate_doi_metadata(self, dataset: Dataset) -> Dict[str, Any]:
        """Validate DOI metadata for a dataset"""

        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metadata_completeness": 0.0,
        }

        required_fields = [
            ("title", dataset.title),
            ("description", dataset.description),
            ("owner", dataset.owner),
            ("repository_connection", dataset.repository_connection),
        ]

        optional_fields = [
            ("keywords", dataset.keywords),
            ("license", dataset.license),
            ("version", dataset.version),
            ("collaborators", dataset.collaborators.exists()),
        ]

        # Check required fields
        missing_required = []
        for field_name, field_value in required_fields:
            if not field_value:
                missing_required.append(field_name)
                validation_results["errors"].append(
                    f"Missing required field: {field_name}"
                )

        if missing_required:
            validation_results["valid"] = False

        # Check optional fields for completeness
        filled_optional = sum(1 for _, field_value in optional_fields if field_value)
        validation_results["metadata_completeness"] = (
            len(required_fields) + filled_optional
        ) / (len(required_fields) + len(optional_fields))

        # Specific validations
        if dataset.title and len(dataset.title) < 10:
            validation_results["warnings"].append(
                "Title is very short (less than 10 characters)"
            )

        if dataset.description and len(dataset.description) < 50:
            validation_results["warnings"].append(
                "Description is very short (less than 50 characters)"
            )

        if not dataset.keywords:
            validation_results["warnings"].append(
                "No keywords provided - this helps with discoverability"
            )

        if not dataset.license:
            validation_results["warnings"].append(
                "No license specified - consider adding an open license"
            )

        if dataset.file_count == 0:
            validation_results["warnings"].append(
                "No files in dataset - add data files before publishing"
            )

        # Check ORCID IDs for authors
        if not hasattr(dataset.owner, "orcid_id") or not dataset.owner.orcid_id:
            validation_results["warnings"].append(
                "Owner has no ORCID ID - this improves author identification"
            )

        return validation_results
