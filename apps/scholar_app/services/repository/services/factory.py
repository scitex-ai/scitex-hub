"""Factory for creating repository service instances."""

import logging
from ....models import RepositoryConnection
from .exceptions import ValidationError, RepositoryServiceError
from .base_service import BaseRepositoryService
from .zenodo_service import ZenodoService

logger = logging.getLogger(__name__)


class RepositoryServiceFactory:
    """Factory for creating repository service instances"""

    _services = {
        "zenodo": ZenodoService,
    }

    @classmethod
    def create_service(
        cls, repository_connection: RepositoryConnection
    ) -> BaseRepositoryService:
        """Create a repository service instance"""
        repository_type = repository_connection.repository.repository_type

        if repository_type not in cls._services:
            raise RepositoryServiceError(
                f"Unsupported repository type: {repository_type}"
            )

        service_class = cls._services[repository_type]
        return service_class(repository_connection)

    @classmethod
    def register_service(cls, repository_type: str, service_class: type):
        """Register a new repository service"""
        cls._services[repository_type] = service_class



# EOF
