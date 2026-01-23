"""
Path-Based Figz Bundle API Views.

Endpoints for figz bundle operations using filesystem paths.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....services.figz import FigzService
from ._path_helpers import resolve_bundle_path

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def load_figz_by_path(request):
    """Load a figz bundle from filesystem path."""
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    logger.info(f"[load_figz_by_path] Loading figz bundle: {bundle_path}")

    # Resolve relative paths
    resolved_path = resolve_bundle_path(
        bundle_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )
    bundle_path = str(resolved_path)
    logger.info(f"[load_figz_by_path] Resolved path: {bundle_path}")

    try:
        bundle_data = FigzService.load_bundle(bundle_path)
        spec = bundle_data.get("spec") or {}
        style = bundle_data.get("style") or {}
        panels_spec = spec.get("panels") or []

        panels = []
        size_style = style.get("size") or {}
        figure_size_mm = {
            "width": size_style.get("width_mm", 170),
            "height": size_style.get("height_mm", 120),
        }

        if isinstance(panels_spec, list):
            for panel in panels_spec:
                panel_id = panel.get("id", panel.get("label", ""))
                size_raw = panel.get("size", {})
                panels.append({
                    "id": panel_id,
                    "label": panel.get("label", panel_id),
                    "plot": panel.get("plot", ""),
                    "position": panel.get("position", {"x_mm": 5, "y_mm": 5}),
                    "size": {
                        "width_mm": size_raw.get("width_mm") or 80,
                        "height_mm": size_raw.get("height_mm") or 68,
                    },
                    "caption": panel.get("caption", ""),
                })

        logger.info(f"[load_figz_by_path] Returning {len(panels)} panels")
        return JsonResponse({
            "path": bundle_path,
            "spec": spec,
            "style": style,
            "panels": panels,
            "size_mm": figure_size_mm,
        })

    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Failed to load figz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def save_figz_canvas(request):
    """Auto-save canvas state as a figz bundle."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    project_owner = data.get("project_owner")
    project_slug = data.get("project_slug")
    figure_name = data.get("figure_name", "Figure1")
    panels = data.get("panels", [])
    canvas_size = data.get("canvas_size", {"width_mm": 170, "height_mm": 120})
    theme = data.get("theme", "light")

    try:
        result = FigzService.save_canvas_as_bundle(
            project_owner=project_owner,
            project_slug=project_slug,
            figure_name=figure_name,
            panels=panels,
            canvas_size=canvas_size,
            theme=theme,
            user=request.user,
        )
        return JsonResponse({
            "success": True,
            "bundle_path": result.get("bundle_path", result.get("path", "")),
            "directory_path": result.get("directory_path"),
            "figure_name": figure_name,
            "panel_count": len(panels),
        })
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Failed to save figz canvas: {e}")
        return JsonResponse({"error": str(e)}, status=500)
