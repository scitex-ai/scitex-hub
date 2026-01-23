"""
Scientific Figure Editor - Version Management API Views
REST API endpoints for figure version control and Original/Edited comparison
"""

import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from apps.vis_app.models import ScientificFigure, FigureVersion


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def create_version_snapshot(request, figure_id):
    """Create a version snapshot for Original | Edited comparison"""
    figure = get_object_or_404(ScientificFigure, id=figure_id, owner=request.user)

    try:
        data = json.loads(request.body)
        version_type = data.get("version_type", "snapshot")
        label = data.get("label", "")
        canvas_state = data.get("canvas_state", {})

        # Get next version number
        last_version = (
            FigureVersion.objects.filter(figure=figure).order_by("-version_number").first()
        )
        version_number = (last_version.version_number + 1) if last_version else 1

        # Create version snapshot
        version = FigureVersion.objects.create(
            figure=figure,
            version_type=version_type,
            version_number=version_number,
            label=label,
            canvas_state=canvas_state,
            created_by=request.user,
        )

        return JsonResponse(
            {
                "success": True,
                "version_id": str(version.id),
                "version_number": version.version_number,
                "label": version.label,
                "created_at": version.created_at.isoformat(),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )


@login_required
@require_http_methods(["GET"])
def get_figure_versions(request, figure_id):
    """Get all versions for a figure"""
    figure = get_object_or_404(ScientificFigure, id=figure_id, owner=request.user)

    versions = FigureVersion.objects.filter(figure=figure).order_by("-created_at")

    versions_data = [
        {
            "id": str(version.id),
            "version_number": version.version_number,
            "version_type": version.version_type,
            "label": version.label or f"v{version.version_number}",
            "created_at": version.created_at.isoformat(),
            "created_by": version.created_by.username,
        }
        for version in versions
    ]

    return JsonResponse({"success": True, "versions": versions_data})


@login_required
@require_http_methods(["GET"])
def load_version_state(request, figure_id, version_id):
    """Load canvas state from a specific version"""
    figure = get_object_or_404(ScientificFigure, id=figure_id, owner=request.user)
    version = get_object_or_404(FigureVersion, id=version_id, figure=figure)

    return JsonResponse(
        {
            "success": True,
            "version_id": str(version.id),
            "version_number": version.version_number,
            "label": version.label,
            "canvas_state": version.canvas_state,
            "created_at": version.created_at.isoformat(),
        }
    )


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def set_original_version(request, figure_id):
    """Mark a specific version as 'original' for comparison"""
    figure = get_object_or_404(ScientificFigure, id=figure_id, owner=request.user)

    try:
        data = json.loads(request.body)
        version_id = data.get("version_id")

        if not version_id:
            return JsonResponse(
                {"success": False, "error": "version_id required"}, status=400
            )

        # Clear existing 'original' versions
        FigureVersion.objects.filter(figure=figure, version_type="original").update(
            version_type="snapshot"
        )

        # Set new original
        version = get_object_or_404(FigureVersion, id=version_id, figure=figure)
        version.version_type = "original"
        version.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Original version set successfully",
                "version_id": str(version.id),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )


@login_required
@require_http_methods(["GET"])
def get_original_version(request, figure_id):
    """Get the original version for comparison"""
    figure = get_object_or_404(ScientificFigure, id=figure_id, owner=request.user)

    original = FigureVersion.objects.filter(
        figure=figure, version_type="original"
    ).first()

    if not original:
        return JsonResponse(
            {"success": False, "error": "No original version set"}, status=404
        )

    return JsonResponse(
        {
            "success": True,
            "version_id": str(original.id),
            "version_number": original.version_number,
            "label": original.label,
            "canvas_state": original.canvas_state,
            "created_at": original.created_at.isoformat(),
        }
    )
