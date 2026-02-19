"""
Path-Based Panel API Views.

Endpoints for figz panel operations using filesystem paths.
Uses scitex.plt (figrecipe) for rendering when figz/pltz is unavailable.
"""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from django.conf import settings
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


def _get_user_panels_dir(user_id: int, figure_name: str) -> Path:
    """Get directory for user panel images (fallback storage)."""
    panels_dir = (
        Path(settings.MEDIA_ROOT) / "vis" / "panels" / str(user_id) / figure_name
    )
    panels_dir.mkdir(parents=True, exist_ok=True)
    return panels_dir


def _render_panel_with_scitex_plt(
    gallery_category: str,
    gallery_plot_name: str,
    data_csv: str | None,
    output_path: Path,
) -> bool:
    """Render a panel using scitex.plt (figrecipe) gallery.

    Returns True on success, False on failure.
    """
    try:
        from apps.vis_app.services.gallery_generator import (
            get_template_gallery_path,
        )

        # First try to use the pre-rendered gallery image (fastest path)
        # Gallery images are stored as: {category}/{name}.pltz.d/exports/{name}.png
        gallery_path = get_template_gallery_path()
        png_path = (
            gallery_path
            / gallery_category
            / f"{gallery_plot_name}.pltz.d"
            / "exports"
            / f"{gallery_plot_name}.png"
        )
        if not png_path.exists():
            # Also try flat path as fallback
            for ext in [".png", ".jpg"]:
                candidate = (
                    gallery_path / gallery_category / f"{gallery_plot_name}{ext}"
                )
                if candidate.exists():
                    png_path = candidate
                    break

        if png_path.exists():
            import shutil

            shutil.copy2(png_path, output_path)
            logger.info(f"[path_panel] Used pre-rendered gallery image: {png_path}")
            return True

        # Fall back to rendering via scitex.plt / figrecipe
        logger.info(
            f"[path_panel] Gallery image not found, rendering via scitex.plt: "
            f"{gallery_category}/{gallery_plot_name}"
        )
        from apps.vis_app.services.plots_service import PlotsService

        csv_data: list = []
        if data_csv:
            import csv
            import io

            reader = csv.reader(io.StringIO(data_csv))
            csv_data = list(reader)

        result = PlotsService.render_gallery_plot(
            plot_type=gallery_plot_name,
            category=gallery_category,
            csv_data=csv_data,
            overrides={},
        )

        if result.get("success") and result.get("image"):
            import base64

            image_data = result["image"].split(",", 1)[-1]
            png_bytes = base64.b64decode(image_data)
            output_path.write_bytes(png_bytes)
            logger.info(f"[path_panel] Rendered panel via scitex.plt: {output_path}")
            return True

        logger.warning(
            f"[path_panel] scitex.plt render failed: {result.get('error', 'unknown')}"
        )
        return False

    except Exception as e:
        logger.exception(f"[path_panel] Failed to render panel: {e}")
        return False


def _try_figz_pltz_approach(
    project_owner: str,
    project_slug: str,
    figure_name: str,
    panel_label: str,
    gallery_category: str,
    gallery_plot_name: str,
    data_csv: str | None,
    position: dict,
    size: dict,
) -> dict | None:
    """Attempt to add panel using scitex.fig.Figz / scitex.plt.Pltz.

    Returns result dict on success, None if approach is unavailable.
    """
    try:
        from scitex.fig import Figz
        from scitex.plt import Pltz

        from apps.project_app.models import Project

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
            logger.info(
                f"[add_panel_to_figz] Added panel {panel_label} to {figz_path} via Figz/Pltz"
            )

            return {
                "success": True,
                "figz_path": str(figz_path),
                "panel_label": panel_label,
                "position": position,
                "size": size,
                "preview_url": (
                    f"/vis/api/bundles/figz/panel-preview/"
                    f"?path={figz_path}&panel={panel_label}"
                ),
            }
        finally:
            if temp_pltz_path.exists():
                temp_pltz_path.unlink()

    except ImportError:
        logger.info(
            "[add_panel_to_figz] scitex.fig.Figz / scitex.plt.Pltz not available, "
            "falling back to scitex.plt render"
        )
        return None
    except Exception as e:
        logger.warning(
            f"[add_panel_to_figz] Figz/Pltz approach failed: {e}, "
            "falling back to scitex.plt render"
        )
        return None


@login_required
@require_http_methods(["POST"])
def add_panel_to_figz(request):
    """Add a panel directly to figz bundle from gallery.

    Uses scitex.fig.Figz / scitex.plt.Pltz when available.
    Falls back to scitex.plt (figrecipe) rendering when not available
    or when no project context is provided.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    project_owner = data.get("project_owner", "")
    project_slug = data.get("project_slug", "")
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

    # Attempt 1: Use scitex.fig.Figz / scitex.plt.Pltz (requires project context)
    if project_owner and project_slug:
        result = _try_figz_pltz_approach(
            project_owner=project_owner,
            project_slug=project_slug,
            figure_name=figure_name,
            panel_label=panel_label,
            gallery_category=gallery_category,
            gallery_plot_name=gallery_plot_name,
            data_csv=data_csv,
            position=position,
            size=size,
        )
        if result is not None:
            return JsonResponse(result, status=201)

    # Attempt 2: Render using scitex.plt (figrecipe) and store in user media dir
    # This works without project context or when Figz/Pltz are unavailable.
    logger.info(
        f"[add_panel_to_figz] Using scitex.plt fallback for "
        f"{gallery_category}/{gallery_plot_name}"
    )
    try:
        panels_dir = _get_user_panels_dir(request.user.id, figure_name)
        panel_png_path = panels_dir / f"{panel_label}.png"

        success = _render_panel_with_scitex_plt(
            gallery_category=gallery_category,
            gallery_plot_name=gallery_plot_name,
            data_csv=data_csv,
            output_path=panel_png_path,
        )

        if not success:
            return JsonResponse(
                {
                    "error": (
                        f"Failed to render panel {gallery_category}/{gallery_plot_name}. "
                        "No gallery image found and scitex.plt render failed."
                    )
                },
                status=500,
            )

        # Use a virtual figz path that encodes the user panels directory
        virtual_figz_path = str(panels_dir)

        logger.info(
            f"[add_panel_to_figz] Panel {panel_label} rendered via scitex.plt: "
            f"{panel_png_path}"
        )

        return JsonResponse(
            {
                "success": True,
                "figz_path": virtual_figz_path,
                "panel_label": panel_label,
                "position": position,
                "size": size,
                "preview_url": (
                    f"/vis/api/bundles/figz/panel-preview/"
                    f"?path={virtual_figz_path}&panel={panel_label}"
                ),
            },
            status=201,
        )

    except Exception as e:
        logger.exception(f"[add_panel_to_figz] Failed to render panel: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_figz_panel_preview(request):
    """Get preview image for a specific panel inside figz bundle.

    Supports both real figz bundles (via scitex.fig.Figz) and
    virtual panel directories (from scitex.plt fallback rendering).
    """
    figz_path = request.GET.get("path")
    panel_label = request.GET.get("panel")

    if not figz_path or not panel_label:
        return JsonResponse({"error": "path and panel parameters required"}, status=400)

    logger.info(
        f"[get_figz_panel_preview] Getting preview for panel {panel_label} "
        f"from {figz_path}"
    )

    # Check if this is a virtual panel path (from scitex.plt fallback)
    panel_png = Path(figz_path) / f"{panel_label}.png"
    if panel_png.exists():
        logger.info(
            f"[get_figz_panel_preview] Serving from virtual panel dir: {panel_png}"
        )
        return HttpResponse(panel_png.read_bytes(), content_type="image/png")

    # Try resolving as a real figz bundle path
    resolved_path = resolve_bundle_path(
        figz_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )
    figz_path_resolved = str(resolved_path)
    logger.info(f"[get_figz_panel_preview] Resolved path: {figz_path_resolved}")

    # Also check virtual panel PNG at resolved path
    resolved_panel_png = Path(figz_path_resolved) / f"{panel_label}.png"
    if resolved_panel_png.exists():
        logger.info(
            f"[get_figz_panel_preview] Serving from resolved panel dir: "
            f"{resolved_panel_png}"
        )
        return HttpResponse(resolved_panel_png.read_bytes(), content_type="image/png")

    # Try real figz bundle approach
    try:
        from scitex.fig import Figz
        from scitex.plt import Pltz

        figz = Figz(figz_path_resolved)
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

    except ImportError:
        logger.warning(
            "[get_figz_panel_preview] scitex.fig.Figz not available "
            f"and no virtual panel found at {figz_path}"
        )
        return JsonResponse(
            {"error": f"Panel preview not available: {figz_path}/{panel_label}"},
            status=404,
        )
    except FileNotFoundError:
        return JsonResponse(
            {"error": f"Figz not found: {figz_path_resolved}"}, status=404
        )
    except Exception as e:
        logger.exception(f"Failed to get panel preview: {e}")
        return JsonResponse({"error": str(e)}, status=500)
