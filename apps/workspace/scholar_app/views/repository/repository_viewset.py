"""
ViewSet for managing available repositories.
"""

import logging
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import Repository

logger = logging.getLogger(__name__)


class RepositoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing available repositories"""

    queryset = Repository.objects.filter(status="active")
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List all available repositories"""
        repositories = self.get_queryset()

        data = []
        for repo in repositories:
            data.append(
                {
                    "id": str(repo.id),
                    "name": repo.name,
                    "type": repo.repository_type,
                    "description": repo.description,
                    "website_url": repo.website_url,
                    "supports_doi": repo.supports_doi,
                    "supports_versioning": repo.supports_versioning,
                    "supports_private_datasets": repo.supports_private_datasets,
                    "max_file_size_mb": repo.max_file_size_mb,
                    "is_default": repo.is_default,
                    "requires_authentication": repo.requires_authentication,
                    "license_options": repo.license_options,
                    "supported_file_formats": repo.supported_file_formats,
                }
            )

        return Response(data)
