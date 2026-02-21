"""
Panel API Views - Add gallery panels to .fig.zip bundles and serve previews.

Thin Django wrapper — all bundle logic lives in figrecipe.Figz/Pltz.
"""

import io
import json
import logging
import zipfile  # used in get_figz_panel_preview to read .plt.zip bytes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ._path_helpers import resolve_bundle_path

logger = logging.getLogger(__name__)


def _get_figz_path(
    project_owner: str,
    project_slug: str,
    figure_name: str,
    user_id: int,
) -> Path:
    """Resolve .fig.zip bundle path from project context or user media dir."""
    if project_owner and project_slug:
        from apps.project_app.models import Project

        project = Project.objects.get(owner__username=project_owner, slug=project_slug)
        figures_dir = project.get_local_path() / "scitex" / "vis" / "figures"
    else:
        figures_dir = Path(settings.MEDIA_ROOT) / "vis" / "figures" / str(user_id)
    figures_dir.mkdir(parents=True, exist_ok=True)
    return figures_dir / f"{figure_name}.fig.zip"


@login_required
@require_http_methods(["POST"])
def add_panel_to_figz(request):
    """Add a gallery panel into a .fig.zip bundle.

    Request body:
        project_owner: Project owner username (optional)
        project_slug:  Project slug (optional)
        figure_name:   Figure name (default: "Figure1")
        panel_label:   Panel label A-H (default: "A")
        gallery_category:  Gallery category (required)
        gallery_plot_name: Gallery plot name (required)
        data_csv:      CSV data string (optional)
        position:      {x_mm, y_mm} (default: {5, 5})
        size:          {width_mm, height_mm} (default: {80, 68})

    Returns:
        figz_path and preview_url for the embedded panel.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    gallery_category = data.get("gallery_category")
    gallery_plot_name = data.get("gallery_plot_name")
    if not gallery_category or not gallery_plot_name:
        return JsonResponse(
            {"error": "gallery_category and gallery_plot_name required"},
            status=400,
        )

    project_owner = data.get("project_owner", "")
    project_slug = data.get("project_slug", "")
    figure_name = data.get("figure_name", "Figure1")
    panel_label = data.get("panel_label", "A")
    data_csv = data.get("data_csv")
    position = data.get("position", {"x_mm": 5, "y_mm": 5})
    size = data.get("size", {"width_mm": 80, "height_mm": 68})

    try:
        figz_path = _get_figz_path(
            project_owner, project_slug, figure_name, request.user.id
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)

    try:
        import base64
        import csv as _csv
        import io as _io

        import figrecipe

        from apps.vis_app.services.plots_service import PlotsService

        # Load or create .fig.zip bundle
        figz = (
            figrecipe.Figz(figz_path)
            if figz_path.exists()
            else figrecipe.Figz.create(figz_path, figure_name)
        )

        # Render gallery plot to PNG via PlotsService
        csv_data = list(_csv.reader(_io.StringIO(data_csv))) if data_csv else []
        result = PlotsService.render_gallery_plot(
            plot_type=gallery_plot_name,
            category=gallery_category,
            csv_data=csv_data,
            overrides={},
        )
        if not result.get("success") or not result.get("image"):
            return JsonResponse(
                {"error": (f"Gallery render failed: {result.get('error', 'unknown')}")},
                status=500,
            )

        png_bytes = base64.b64decode(result["image"].split(",", 1)[-1])

        # Delegate: figrecipe wraps PNG in .plt.zip and embeds in .fig.zip
        figz.add_panel_from_png(
            panel_label,
            png_bytes,
            plot_type=gallery_plot_name,
            position=position,
            size=size,
        )

        logger.info(f"[add_panel_to_figz] Panel {panel_label} added to {figz_path}")
        return JsonResponse(
            {
                "success": True,
                "figz_path": str(figz_path),
                "panel_label": panel_label,
                "position": position,
                "size": size,
                "preview_url": (
                    f"/vis/api/bundles/figz/panel-preview/"
                    f"?path={figz_path}&panel={panel_label}"
                ),
            },
            status=201,
        )

    except Exception as e:
        logger.exception(f"[add_panel_to_figz] Failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_figz_panel_preview(request):
    """Serve the preview PNG for a panel embedded in a .fig.zip bundle.

    Query params:
        path:           Path to .fig.zip bundle
        panel:          Panel label (e.g., "A")
        project_owner:  Optional project owner for path resolution
        project_slug:   Optional project slug for path resolution
    """
    figz_path = request.GET.get("path")
    panel_label = request.GET.get("panel")

    if not figz_path or not panel_label:
        return JsonResponse({"error": "path and panel parameters required"}, status=400)

    resolved_path = resolve_bundle_path(
        figz_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )

    try:
        import figrecipe

        figz = figrecipe.Figz(str(resolved_path))
        pltz_bytes = figz.get_panel_pltz(panel_label)

        if not pltz_bytes:
            return JsonResponse({"error": f"Panel {panel_label} not found"}, status=404)

        # Extract PNG directly from the .plt.zip bytes
        with zipfile.ZipFile(io.BytesIO(pltz_bytes)) as zf:
            for name in zf.namelist():
                if name.endswith(".png") and "hitmap" not in name:
                    return HttpResponse(zf.read(name), content_type="image/png")

        return JsonResponse({"error": "No preview image in panel bundle"}, status=404)

    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {resolved_path}"}, status=404)
    except Exception as e:
        logger.exception(f"[get_figz_panel_preview] Failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)
