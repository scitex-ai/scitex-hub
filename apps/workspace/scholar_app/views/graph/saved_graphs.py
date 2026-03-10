"""Saved Graph CRUD API views."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ...models.graph import SavedGraph

logger = logging.getLogger(__name__)


@login_required
@require_GET
def api_list_saved_graphs(request):
    """List saved graphs (summary only, no graph_data)."""
    project_id = request.GET.get("project_id")
    qs = SavedGraph.objects.filter(user=request.user)
    if project_id:
        qs = qs.filter(project_id=project_id)

    graphs = list(
        qs.values(
            "id",
            "name",
            "source_type",
            "node_count",
            "edge_count",
            "created_at",
            "updated_at",
        )
    )
    for g in graphs:
        g["id"] = str(g["id"])
        g["created_at"] = g["created_at"].isoformat()
        g["updated_at"] = g["updated_at"].isoformat()

    return JsonResponse({"graphs": graphs})


@login_required
@require_POST
def api_save_graph(request):
    """Save current graph with name."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = body.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Name is required"}, status=400)

    graph_data = body.get("graph_data", {})
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    try:
        graph = SavedGraph.objects.create(
            user=request.user,
            project_id=body.get("project_id"),
            name=name,
            source_type=body.get("source_type", "dois"),
            seed_dois=body.get("seed_dois", []),
            query_text=body.get("query_text", ""),
            build_params=body.get("build_params", {}),
            graph_data=graph_data,
            node_positions=body.get("node_positions", {}),
            node_count=len(nodes),
            edge_count=len(edges),
        )
    except IntegrityError:
        return JsonResponse(
            {"error": f"A graph named '{name}' already exists"}, status=409
        )

    return JsonResponse(
        {
            "id": str(graph.id),
            "name": graph.name,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
        },
        status=201,
    )


@login_required
@require_GET
def api_load_graph(request, graph_id):
    """Load full graph data + positions for rendering."""
    try:
        graph = SavedGraph.objects.get(id=graph_id, user=request.user)
    except SavedGraph.DoesNotExist:
        return JsonResponse({"error": "Graph not found"}, status=404)

    return JsonResponse(
        {
            "id": str(graph.id),
            "name": graph.name,
            "source_type": graph.source_type,
            "seed_dois": graph.seed_dois,
            "query_text": graph.query_text,
            "build_params": graph.build_params,
            "graph_data": graph.graph_data,
            "node_positions": graph.node_positions,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "created_at": graph.created_at.isoformat(),
            "updated_at": graph.updated_at.isoformat(),
        }
    )


@login_required
@require_POST
def api_rename_graph(request, graph_id):
    """Rename a saved graph."""
    try:
        graph = SavedGraph.objects.get(id=graph_id, user=request.user)
    except SavedGraph.DoesNotExist:
        return JsonResponse({"error": "Graph not found"}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    new_name = body.get("name", "").strip()
    if not new_name:
        return JsonResponse({"error": "Name is required"}, status=400)

    try:
        graph.name = new_name
        graph.save(update_fields=["name", "updated_at"])
    except IntegrityError:
        return JsonResponse(
            {"error": f"A graph named '{new_name}' already exists"}, status=409
        )

    return JsonResponse({"id": str(graph.id), "name": graph.name})


@login_required
@require_POST
def api_delete_graph(request, graph_id):
    """Delete a saved graph."""
    deleted, _ = SavedGraph.objects.filter(id=graph_id, user=request.user).delete()
    if deleted == 0:
        return JsonResponse({"error": "Graph not found"}, status=404)
    return JsonResponse({"deleted": True})


@login_required
@require_POST
def api_refresh_graph(request, graph_id):
    """Re-build graph from its recipe and update the snapshot."""
    try:
        graph = SavedGraph.objects.get(id=graph_id, user=request.user)
    except SavedGraph.DoesNotExist:
        return JsonResponse({"error": "Graph not found"}, status=404)

    # Return the recipe so the frontend can re-build via existing build APIs
    return JsonResponse(
        {
            "id": str(graph.id),
            "source_type": graph.source_type,
            "seed_dois": graph.seed_dois,
            "query_text": graph.query_text,
            "build_params": graph.build_params,
        }
    )
