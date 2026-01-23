"""
Base dataset management viewset with listing and creation.
"""

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.paginator import Paginator
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import Dataset, RepositoryConnection

logger = logging.getLogger(__name__)


class DatasetBaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet for managing datasets with list and create operations"""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Dataset.objects.filter(owner=self.request.user)
            .select_related(
                "repository_connection__repository", "project", "generated_by_job"
            )
            .prefetch_related("collaborators", "files")
        )

    def list(self, request):
        """List user's datasets"""
        queryset = self.get_queryset()

        # Apply filters
        if request.GET.get("status"):
            queryset = queryset.filter(status=request.GET.get("status"))
        if request.GET.get("dataset_type"):
            queryset = queryset.filter(dataset_type=request.GET.get("dataset_type"))
        if request.GET.get("repository_type"):
            queryset = queryset.filter(
                repository_connection__repository__repository_type=request.GET.get(
                    "repository_type"
                )
            )
        if request.GET.get("project"):
            queryset = queryset.filter(project_id=request.GET.get("project"))

        # Pagination
        page_size = int(request.GET.get("page_size", 20))
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(request.GET.get("page", 1))

        data = []
        for dataset in page:
            data.append(
                {
                    "id": str(dataset.id),
                    "title": dataset.title,
                    "description": dataset.description,
                    "dataset_type": dataset.dataset_type,
                    "status": dataset.status,
                    "visibility": dataset.visibility,
                    "version": dataset.version,
                    "file_count": dataset.file_count,
                    "total_size_bytes": dataset.total_size_bytes,
                    "size_display": dataset.get_file_size_display(),
                    "repository": {
                        "name": dataset.repository_connection.repository.name,
                        "type": dataset.repository_connection.repository.repository_type,
                    },
                    "repository_url": dataset.repository_url,
                    "repository_doi": dataset.repository_doi,
                    "project": dataset.project.name if dataset.project else None,
                    "created_at": dataset.created_at,
                    "updated_at": dataset.updated_at,
                    "published_at": dataset.published_at,
                    "last_synced": dataset.last_synced,
                }
            )

        return Response(
            {
                "datasets": data,
                "pagination": {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "current_page": page.number,
                    "has_next": page.has_next(),
                    "has_previous": page.has_previous(),
                },
            }
        )

    def create(self, request):
        """Create a new dataset"""
        try:
            data = request.data

            # Get repository connection
            connection = get_object_or_404(
                RepositoryConnection,
                id=data.get("repository_connection_id"),
                user=request.user,
            )

            with transaction.atomic():
                dataset = Dataset.objects.create(
                    title=data.get("title"),
                    description=data.get("description", ""),
                    dataset_type=data.get("dataset_type", "raw_data"),
                    keywords=data.get("keywords", ""),
                    owner=request.user,
                    repository_connection=connection,
                    version=data.get("version", "1.0"),
                    visibility=data.get("visibility", "private"),
                    license=data.get("license", ""),
                    project_id=data.get("project_id")
                    if data.get("project_id")
                    else None,
                )

                # Add collaborators
                if "collaborator_ids" in data:
                    dataset.collaborators.set(data["collaborator_ids"])

                # Link to related papers
                if "related_paper_ids" in data:
                    dataset.related_papers.set(data["related_paper_ids"])

            return Response(
                {"id": str(dataset.id), "message": "Dataset created successfully"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
