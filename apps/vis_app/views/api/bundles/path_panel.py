"""
Path-Based Panel API Views.

Endpoints for figz panel operations using filesystem paths.
"""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ._path_helpers import resolve_bundle_path

logger = logging.getLogger(__name__)

# Ensure scitex is importable
SCITEX_CODE_PATH = os.environ.get(
    "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


@login_required
@require_http_methods(["POST"])
def add_panel_to_figz(request):
    """Add a panel directly to figz bundle from gallery."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    project_owner = data.get("project_owner")
    project_slug = data.get("project_slug")
    figure_name = data.get("figure_name", "Figure1")
    panel_label = data.get("panel_label", "A")
    gallery_category = data.get("gallery_category")
    gallery_plot_name = data.get("gallery_plot_name")
    data_csv = data.get("data_csv")
    position = data.get("position", {"x_mm": 5, "y_mm": 5})
    size = data.get("size", {"width_mm": 80, "height_mm": 68})

    if not gallery_category or not gallery_plot_name:
        return JsonResponse(
            {"error": "gallery_category and gallery_plot_name required"}, status=400
        )

    try:
        from apps.project_app.models import Project
        from scitex.fig import Figz
        from scitex.plt import Pltz

        project = Project.objects.get(owner__username=project_owner, slug=project_slug)
        figures_dir = project.get_local_path() / "scitex" / "vis" / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        figz_path = figures_dir / f"{figure_name}.figz"

        figz = (
            Figz(figz_path)
            if figz_path.exists()
            else Figz.create(figz_path, figure_name)
        )

        with tempfile.NamedTemporaryFile(suffix=".pltz", delete=False) as f:
            temp_pltz_path = Path(f.name)

        try:
            pltz = Pltz.create_from_gallery(
                temp_pltz_path, gallery_category, gallery_plot_name
            )
            if data_csv:
                from io import StringIO

                import pandas as pd

                pltz.data = pd.read_csv(StringIO(data_csv))
                pltz.save()

            with open(temp_pltz_path, "rb") as f:
                pltz_bytes = f.read()

            figz.add_panel(panel_label, pltz_bytes, position, size)
            logger.info(f"[add_panel_to_figz] Added panel {panel_label} to {figz_path}")

            return JsonResponse(
                {
                    "success": True,
                    "figz_path": str(figz_path),
                    "panel_label": panel_label,
                    "position": position,
                    "size": size,
                    "preview_url": f"/vis/api/bundles/figz/panel-preview/?path={figz_path}&panel={panel_label}",
                },
                status=201,
            )
        finally:
            if temp_pltz_path.exists():
                temp_pltz_path.unlink()

    except Exception as e:
        logger.exception(f"Failed to add panel to figz: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_figz_panel_preview(request):
    """Get preview image for a specific panel inside figz bundle."""
    figz_path = request.GET.get("path")
    panel_label = request.GET.get("panel")

    if not figz_path or not panel_label:
        return JsonResponse({"error": "path and panel parameters required"}, status=400)

    logger.info(
        f"[get_figz_panel_preview] Getting preview for panel {panel_label} from {figz_path}"
    )

    resolved_path = resolve_bundle_path(
        figz_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )
    figz_path = str(resolved_path)
    logger.info(f"[get_figz_panel_preview] Resolved path: {figz_path}")

    try:
        from scitex.fig import Figz
        from scitex.plt import Pltz

        figz = Figz(figz_path)
        pltz_bytes = figz.get_panel_pltz(panel_label)

        if not pltz_bytes:
            return JsonResponse({"error": f"Panel {panel_label} not found"}, status=404)

        with tempfile.NamedTemporaryFile(suffix=".pltz", delete=False) as f:
            f.write(pltz_bytes)
            temp_path = Path(f.name)

        try:
            pltz = Pltz(temp_path)
            preview = pltz.get_preview() or pltz.render_preview()
            return HttpResponse(preview, content_type="image/png")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    except FileNotFoundError:
        return JsonResponse({"error": f"Figz not found: {figz_path}"}, status=404)
    except Exception as e:
        logger.exception(f"Failed to get panel preview: {e}")
        return JsonResponse({"error": str(e)}, status=500)
