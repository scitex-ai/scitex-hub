"""
ViewSet for managing repository connections.
"""

import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import Repository, RepositoryConnection
from ...services.repository import RepositoryServiceFactory

logger = logging.getLogger(__name__)


class RepositoryConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing repository connections"""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RepositoryConnection.objects.filter(user=self.request.user)

    def list(self, request):
        """List user's repository connections"""
        connections = self.get_queryset()

        data = []
        for conn in connections:
            data.append(
                {
                    "id": str(conn.id),
                    "repository": {
                        "id": str(conn.repository.id),
                        "name": conn.repository.name,
                        "type": conn.repository.repository_type,
                    },
                    "connection_name": conn.connection_name,
                    "status": conn.status,
                    "is_default": conn.is_default,
                    "auto_sync_enabled": conn.auto_sync_enabled,
                    "last_verified": conn.last_verified,
                    "total_deposits": conn.total_deposits,
                    "created_at": conn.created_at,
                    "last_activity": conn.last_activity,
                }
            )

        return Response(data)

    def create(self, request):
        """Create a new repository connection"""
        try:
            data = request.data
            repository = get_object_or_404(Repository, id=data.get("repository_id"))

            # Create connection
            connection = RepositoryConnection.objects.create(
                user=request.user,
                repository=repository,
                connection_name=data.get(
                    "connection_name", f"{repository.name} Connection"
                ),
                api_token=data.get("api_token", ""),
                username=data.get("username", ""),
                is_default=data.get("is_default", False),
                auto_sync_enabled=data.get("auto_sync_enabled", True),
                notification_enabled=data.get("notification_enabled", True),
            )

            # Test the connection
            try:
                service = RepositoryServiceFactory.create_service(connection)
                if service.authenticate():
                    connection.status = "active"
                    connection.last_verified = timezone.now()
                else:
                    connection.status = "invalid"
                connection.save()
            except Exception as e:
                connection.status = "invalid"
                connection.last_error = str(e)
                connection.save()
                logger.error(f"Failed to authenticate repository connection: {e}")

            return Response(
                {
                    "id": str(connection.id),
                    "status": connection.status,
                    "message": "Connection created successfully"
                    if connection.status == "active"
                    else "Connection created but authentication failed",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        """Test a repository connection"""
        connection = self.get_object()

        try:
            service = RepositoryServiceFactory.create_service(connection)
            if service.authenticate():
                connection.status = "active"
                connection.last_verified = timezone.now()
                connection.error_count = 0
                connection.last_error = ""
                message = "Connection test successful"
                success = True
            else:
                connection.status = "invalid"
                message = "Authentication failed"
                success = False

            connection.save()

            return Response(
                {
                    "success": success,
                    "status": connection.status,
                    "message": message,
                    "last_verified": connection.last_verified,
                }
            )

        except Exception as e:
            connection.status = "invalid"
            connection.last_error = str(e)
            connection.error_count += 1
            connection.save()

            return Response(
                {
                    "success": False,
                    "status": connection.status,
                    "message": f"Connection test failed: {str(e)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def list_remote_datasets(self, request, pk=None):
        """List datasets in the remote repository"""
        connection = self.get_object()

        try:
            service = RepositoryServiceFactory.create_service(connection)

            # Get filter parameters
            filters = {}
            if request.GET.get("status"):
                filters["status"] = request.GET.get("status")
            if request.GET.get("page"):
                filters["page"] = int(request.GET.get("page", 1))
            if request.GET.get("size"):
                filters["size"] = int(request.GET.get("size", 20))

            datasets = service.list_datasets(filters)

            return Response({"datasets": datasets, "count": len(datasets)})

        except Exception as e:
            return Response(
                {"error": f"Failed to list remote datasets: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
