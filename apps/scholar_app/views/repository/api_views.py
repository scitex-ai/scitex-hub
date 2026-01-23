"""
API views for repository sync and statistics.
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import (
    Dataset,
    RepositoryConnection,
    RepositorySync,
)

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_status(request, sync_id):
    """Get sync operation status"""
    try:
        sync_record = get_object_or_404(RepositorySync, id=sync_id, user=request.user)

        return Response(
            {
                "id": str(sync_record.id),
                "sync_type": sync_record.sync_type,
                "status": sync_record.status,
                "progress_percentage": sync_record.get_progress_percentage(),
                "total_items": sync_record.total_items,
                "completed_items": sync_record.completed_items,
                "failed_items": sync_record.failed_items,
                "started_at": sync_record.started_at,
                "completed_at": sync_record.completed_at,
                "estimated_completion": sync_record.estimated_completion,
                "error_message": sync_record.error_message,
                "result_data": sync_record.result_data,
            }
        )

    except RepositorySync.DoesNotExist:
        return Response(
            {"error": "Sync record not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_repository_stats(request):
    """Get user's repository usage statistics"""
    user = request.user

    # Repository connections
    connections = RepositoryConnection.objects.filter(user=user)
    active_connections = connections.filter(status="active").count()

    # Datasets
    datasets = Dataset.objects.filter(owner=user)
    dataset_stats = {
        "total": datasets.count(),
        "by_status": {},
        "by_type": {},
        "by_repository": {},
        "total_size_bytes": 0,
    }

    for status_choice in Dataset.STATUS_CHOICES:
        count = datasets.filter(status=status_choice[0]).count()
        if count > 0:
            dataset_stats["by_status"][status_choice[0]] = count

    for type_choice in Dataset.DATASET_TYPES:
        count = datasets.filter(dataset_type=type_choice[0]).count()
        if count > 0:
            dataset_stats["by_type"][type_choice[0]] = count

    # Repository breakdown
    for connection in connections:
        repo_name = connection.repository.name
        count = datasets.filter(repository_connection=connection).count()
        if count > 0:
            dataset_stats["by_repository"][repo_name] = count

    # Total storage used
    dataset_stats["total_size_bytes"] = sum(
        dataset.total_size_bytes for dataset in datasets
    )

    # Recent activity
    recent_syncs = RepositorySync.objects.filter(user=user).order_by("-created_at")[:10]

    sync_data = []
    for sync in recent_syncs:
        sync_data.append(
            {
                "id": str(sync.id),
                "sync_type": sync.sync_type,
                "status": sync.status,
                "dataset_title": sync.dataset.title if sync.dataset else None,
                "repository_name": sync.repository_connection.repository.name,
                "created_at": sync.created_at,
                "completed_at": sync.completed_at,
            }
        )

    return Response(
        {
            "connections": {
                "total": connections.count(),
                "active": active_connections,
                "by_repository": {conn.repository.name: 1 for conn in connections},
            },
            "datasets": dataset_stats,
            "recent_syncs": sync_data,
        }
    )
