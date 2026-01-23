"""Synchronization and upload utilities for repository services."""

import logging
from typing import List
from django.utils import timezone
from ....models import Dataset, RepositorySync, DatasetFile
from .factory import RepositoryServiceFactory
from .exceptions import RepositoryServiceError

logger = logging.getLogger(__name__)


def sync_dataset_with_repository(dataset: Dataset) -> RepositorySync:
    """Sync a dataset with its repository"""
    sync_record = RepositorySync.objects.create(
        user=dataset.owner,
        repository_connection=dataset.repository_connection,
        dataset=dataset,
        sync_type="full_sync",
        status="pending",
    )

    try:
        sync_record.status = "running"
        sync_record.started_at = timezone.now()
        sync_record.save()

        # Create service instance
        service = RepositoryServiceFactory.create_service(dataset.repository_connection)

        # Sync dataset metadata
        repo_data = service.get_dataset(dataset.repository_id)

        # Update local dataset
        dataset.title = repo_data.get("title", dataset.title)
        dataset.description = repo_data.get("description", dataset.description)
        dataset.repository_url = repo_data.get("url", dataset.repository_url)
        dataset.repository_doi = repo_data.get("doi", dataset.repository_doi)
        dataset.version = repo_data.get("version", dataset.version)
        dataset.status = "published" if repo_data.get("published") else "draft"
        dataset.last_synced = timezone.now()
        dataset.save()

        # Sync files
        files_data = repo_data.get("files", [])
        sync_record.total_items = len(files_data)

        for i, file_data in enumerate(files_data):
            service._sync_dataset_file(dataset, file_data)
            sync_record.completed_items = i + 1
            sync_record.save()

        sync_record.status = "completed"
        sync_record.completed_at = timezone.now()
        sync_record.result_data = {"synced_files": len(files_data)}

    except Exception as e:
        sync_record.status = "failed"
        sync_record.error_message = str(e)
        sync_record.completed_at = timezone.now()
        logger.error(f"Dataset sync failed: {e}")

    sync_record.save()
    return sync_record


def upload_dataset_to_repository(
    dataset: Dataset, file_paths: List[str] = None
) -> RepositorySync:
    """Upload a dataset to its repository"""
    sync_record = RepositorySync.objects.create(
        user=dataset.owner,
        repository_connection=dataset.repository_connection,
        dataset=dataset,
        sync_type="upload",
        status="pending",
    )

    try:
        sync_record.status = "running"
        sync_record.started_at = timezone.now()
        sync_record.save()

        # Create service instance
        service = RepositoryServiceFactory.create_service(dataset.repository_connection)

        # Prepare metadata
        metadata = {
            "title": dataset.title,
            "description": dataset.description,
            "keywords": dataset.keywords,
            "creators": [
                {
                    "name": dataset.owner.get_full_name() or dataset.owner.username,
                    "affiliation": getattr(dataset.owner, "affiliation", ""),
                }
            ],
            "license": dataset.license or "CC-BY-4.0",
            "version": dataset.version,
        }

        # Add collaborators as creators
        for collaborator in dataset.collaborators.all():
            metadata["creators"].append(
                {
                    "name": collaborator.get_full_name() or collaborator.username,
                    "affiliation": getattr(collaborator, "affiliation", ""),
                }
            )

        # Create or update dataset in repository
        if dataset.repository_id:
            repo_data = service.update_dataset(dataset.repository_id, metadata)
        else:
            repo_data = service.create_dataset(metadata)
            dataset.repository_id = repo_data["id"]
            dataset.repository_url = repo_data["url"]
            dataset.save()

        # Upload files
        files_to_upload = dataset.files.all()
        if file_paths:
            files_to_upload = files_to_upload.filter(file_path__in=file_paths)

        sync_record.total_items = files_to_upload.count()

        for i, dataset_file in enumerate(files_to_upload):
            if dataset_file.local_file:
                with dataset_file.local_file.open("rb") as f:
                    file_data = f.read()

                file_result = service.upload_file(
                    dataset.repository_id,
                    dataset_file.file_path or dataset_file.filename,
                    file_data,
                )

                # Update file information
                dataset_file.repository_file_id = file_result.get("file_id", "")
                dataset_file.download_url = file_result.get("download_url", "")
                dataset_file.save()

            sync_record.completed_items = i + 1
            sync_record.save()

        sync_record.status = "completed"
        sync_record.completed_at = timezone.now()
        sync_record.result_data = {
            "repository_id": dataset.repository_id,
            "repository_url": dataset.repository_url,
            "uploaded_files": sync_record.completed_items,
        }

    except Exception as e:
        sync_record.status = "failed"
        sync_record.error_message = str(e)
        sync_record.completed_at = timezone.now()
        logger.error(f"Dataset upload failed: {e}")

    sync_record.save()
    return sync_record

# EOF
