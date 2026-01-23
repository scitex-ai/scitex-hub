"""
Legacy view functions for backwards compatibility.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from ...models import Repository, RepositoryConnection

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def list_repositories(request):
    """List available repositories"""
    repositories = Repository.objects.filter(status="active")

    data = []
    for repo in repositories:
        data.append(
            {
                "id": str(repo.id),
                "name": repo.name,
                "type": repo.repository_type,
                "description": repo.description,
                "supports_doi": repo.supports_doi,
                "is_default": repo.is_default,
            }
        )

    return JsonResponse({"repositories": data})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_repository_connection(request):
    """Create a new repository connection"""
    try:
        data = json.loads(request.body)
        repository = get_object_or_404(Repository, id=data.get("repository_id"))

        connection = RepositoryConnection.objects.create(
            user=request.user,
            repository=repository,
            connection_name=data.get(
                "connection_name", f"{repository.name} Connection"
            ),
            api_token=data.get("api_token", ""),
            username=data.get("username", ""),
        )

        return JsonResponse(
            {"id": str(connection.id), "message": "Connection created successfully"}
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
