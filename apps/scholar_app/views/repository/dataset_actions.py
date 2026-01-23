"""
Dataset action methods for sync, upload, publish, and file listing.
"""

import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .dataset_base import DatasetBaseViewSet
from ...services.repository import (
    RepositoryServiceFactory,
    sync_dataset_with_repository,
    upload_dataset_to_repository,
)

logger = logging.getLogger(__name__)


class DatasetViewSet(DatasetBaseViewSet):
    """ViewSet for managing datasets with all actions"""

    @action(detail=True, methods=["post"])
    def sync_with_repository(self, request, pk=None):
        """Sync dataset with remote repository"""
        dataset = self.get_object()

        try:
            sync_record = sync_dataset_with_repository(dataset)

            return Response(
                {
                    "sync_id": str(sync_record.id),
                    "status": sync_record.status,
                    "message": "Sync started successfully",
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to start sync: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def upload_to_repository(self, request, pk=None):
        """Upload dataset to repository"""
        dataset = self.get_object()

        try:
            file_paths = request.data.get(
                "file_paths"
            )  # Optional: specific files to upload
            sync_record = upload_dataset_to_repository(dataset, file_paths)

            return Response(
                {
                    "sync_id": str(sync_record.id),
                    "status": sync_record.status,
                    "message": "Upload started successfully",
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to start upload: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish dataset in repository"""
        dataset = self.get_object()

        try:
            if not dataset.repository_id:
                return Response(
                    {
                        "error": "Dataset must be uploaded to repository before publishing"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service = RepositoryServiceFactory.create_service(
                dataset.repository_connection
            )
            result = service.publish_dataset(dataset.repository_id)

            # Update local dataset
            dataset.status = "published"
            dataset.published_at = timezone.now()
            dataset.repository_url = result.get("url", dataset.repository_url)
            dataset.repository_doi = result.get("doi", dataset.repository_doi)
            dataset.save()

            return Response(
                {
                    "message": "Dataset published successfully",
                    "doi": dataset.repository_doi,
                    "url": dataset.repository_url,
                }
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to publish dataset: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def files(self, request, pk=None):
        """List files in dataset"""
        dataset = self.get_object()

        files = dataset.files.all().order_by("file_path", "filename")

        data = []
        for file_obj in files:
            data.append(
                {
                    "id": str(file_obj.id),
                    "filename": file_obj.filename,
                    "file_path": file_obj.file_path,
                    "file_type": file_obj.file_type,
                    "file_format": file_obj.file_format,
                    "size_bytes": file_obj.size_bytes,
                    "size_display": file_obj.get_size_display(),
                    "download_url": file_obj.download_url,
                    "download_count": file_obj.download_count,
                    "created_at": file_obj.created_at,
                }
            )

        return Response(
            {
                "files": data,
                "total_files": len(data),
                "total_size": dataset.total_size_bytes,
                "total_size_display": dataset.get_file_size_display(),
            }
        )
