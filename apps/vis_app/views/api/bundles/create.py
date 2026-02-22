"""
Bundle Creation API Views - Endpoints for creating new bundles.

These endpoints handle creating empty figz bundles and exporting bundles.
"""

import json
import logging
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ....services.figz import FigzService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def create_empty_figz(request):
    """
    Create an empty figz bundle using scitex package.

    This is called when a new figure tab is created in the UI.
    Django is a thin layer - actual logic is in scitex.fig.io.save_figz_bundle.

    Request body:
        project_owner: Project owner username
        project_slug: Project slug
        figure_name: Figure name (e.g., "Figure2")
        canvas_size: {width_mm, height_mm} (optional)

    Returns:
        Created bundle path
    """
    os.environ["MPLBACKEND"] = "Agg"

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    project_owner = data.get("project_owner")
    project_slug = data.get("project_slug")
    figure_name = data.get("figure_name")
    canvas_size = data.get("canvas_size", {"width_mm": 170, "height_mm": 120})

    if not figure_name:
        return JsonResponse({"error": "figure_name is required"}, status=400)

    # Determine output directory
    if project_owner and project_slug:
        from apps.project_app.models import Project

        try:
            project = Project.objects.get(
                owner__username=project_owner, slug=project_slug
            )
            project_root = project.get_local_path()
        except Project.DoesNotExist:
            return JsonResponse(
                {"error": f"Project not found: {project_owner}/{project_slug}"},
                status=404,
            )
        figures_dir = project_root / "scitex" / "vis" / "figures"
    else:
        figures_dir = (
            Path(settings.MEDIA_ROOT)
            / "vis"
            / "bundles"
            / "figz"
            / str(request.user.id)
        )

    figures_dir.mkdir(parents=True, exist_ok=True)
    zip_path = figures_dir / f"{figure_name}.fig.zip"

    # Return existing bundle if already created
    if zip_path.exists():
        return JsonResponse(
            {
                "success": True,
                "bundle_path": str(zip_path),
                "figure_name": figure_name,
                "already_exists": True,
            }
        )

    try:
        import figrecipe

        figrecipe.Figz.create(zip_path, figure_name, size_mm=canvas_size)

        logger.info(f"Created empty figz bundle: {zip_path}")

        return JsonResponse(
            {
                "success": True,
                "bundle_path": str(zip_path),
                "figure_name": figure_name,
            },
            status=201,
        )

    except Exception as e:
        logger.exception(f"Failed to create empty figz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def export_figz_bundle(request):
    """
    Export a figz bundle as a downloadable zip file.

    Request body:
        project_owner: Project owner username (optional)
        project_slug: Project slug (optional)
        figz_path: Direct path to figz bundle (optional)

    Returns:
        ZIP file download
    """

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    figz_path = data.get("figz_path")
    project_owner = data.get("project_owner")
    project_slug = data.get("project_slug")

    # Determine bundle path
    if figz_path:
        bundle_path = Path(figz_path)
    elif project_owner and project_slug:
        from apps.project_app.models import Project

        try:
            project = Project.objects.get(
                owner__username=project_owner, slug=project_slug
            )
            project_root = project.get_local_path()
        except Project.DoesNotExist:
            return JsonResponse(
                {"error": f"Project not found: {project_owner}/{project_slug}"},
                status=404,
            )
        figures_dir = project_root / "scitex" / "vis" / "figures"
        figz_files = list(figures_dir.glob("*.fig.zip"))
        if figz_files:
            bundle_path = figz_files[0]
        else:
            return JsonResponse(
                {"error": "No .fig.zip bundle found in project"}, status=404
            )
    else:
        bundle_base = FigzService.get_bundle_base_path(request.user.id)
        figz_files = list(bundle_base.glob("*.fig.zip"))
        if figz_files:
            bundle_path = figz_files[0]
        else:
            return JsonResponse({"error": "No .fig.zip bundle found"}, status=404)

    if not bundle_path.exists():
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)

    try:
        with open(bundle_path, "rb") as f:
            content = f.read()
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{bundle_path.name}"'
        return response

    except Exception as e:
        logger.exception(f"Failed to export figz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)
