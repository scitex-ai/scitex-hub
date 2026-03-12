#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/figrecipe_app/views/api/bundles/path_api.py"""

import pytest

# from apps.workspace.figrecipe_app.views.api.bundles.path_api import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/figrecipe_app/views/api/bundles/path_api.py
# --------------------------------------------------------------------------------
# """
# Path-Based Bundle API Views - Endpoints for canvas integration.
#
# These endpoints operate on filesystem paths directly, supporting the
# canvas editor workflow where bundles are accessed by path rather than ID.
# """
#
# import json
# import logging
# from pathlib import Path
#
# from django.conf import settings
# from django.contrib.auth.decorators import login_required
# from django.http import JsonResponse, HttpResponse
# from django.views.decorators.http import require_http_methods
#
# from ....services.pltz_service import PltzService
# from ....services.figz import FigzService
#
# logger = logging.getLogger(__name__)
#
#
# @login_required
# @require_http_methods(["GET"])
# def load_figz_by_path(request):
#     """
#     Load a figz bundle from filesystem path.
#
#     Query params:
#         path: Filesystem path to .figz.d directory or .figz file
#
#     Returns:
#         JSON with spec, style, and panel info
#     """
#     bundle_path = request.GET.get("path")
#     if not bundle_path:
#         return JsonResponse({"error": "path parameter required"}, status=400)
#
#     logger.info(f"[load_figz_by_path] Loading figz bundle: {bundle_path}")
#
#     try:
#         bundle_data = FigzService.load_bundle(bundle_path)
#
#         spec = bundle_data.get("spec", {})
#         style = bundle_data.get("style", {})
#         panels_spec = spec.get("panels", [])
#
#         panels = []
#         figure_size_mm = {
#             "width": style.get("size", {}).get("width_mm", 170),
#             "height": style.get("size", {}).get("height_mm", 120),
#         }
#
#         if isinstance(panels_spec, list):
#             for idx, panel in enumerate(panels_spec):
#                 panel_id = panel.get("id", panel.get("label", ""))
#                 plot_ref = panel.get("plot", "")
#                 position = panel.get("position", {"x_mm": 5, "y_mm": 5})
#                 size_raw = panel.get("size", {})
#
#                 size = {
#                     "width_mm": size_raw.get("width_mm") if size_raw.get("width_mm") else 80,
#                     "height_mm": size_raw.get("height_mm") if size_raw.get("height_mm") else 68,
#                 }
#
#                 panels.append({
#                     "id": panel_id,
#                     "label": panel.get("label", panel_id),
#                     "plot": plot_ref,
#                     "position": position,
#                     "size": size,
#                     "caption": panel.get("caption", ""),
#                 })
#
#         logger.info(f"[load_figz_by_path] Returning {len(panels)} panels")
#
#         return JsonResponse({
#             "path": bundle_path,
#             "spec": spec,
#             "style": style,
#             "panels": panels,
#             "size_mm": figure_size_mm,
#         })
#
#     except FileNotFoundError:
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except ValueError as e:
#         return JsonResponse({"error": str(e)}, status=400)
#     except Exception as e:
#         logger.exception(f"Failed to load figz bundle: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["GET"])
# def load_pltz_by_path(request):
#     """
#     Load a pltz bundle from filesystem path.
#
#     Query params:
#         path: Filesystem path to .pltz.d directory or .pltz file
#
#     Returns:
#         JSON with spec, style, data info, and geometry
#     """
#     bundle_path = request.GET.get("path")
#     if not bundle_path:
#         return JsonResponse({"error": "path parameter required"}, status=400)
#
#     try:
#         bundle_data = PltzService.load_bundle(bundle_path)
#
#         return JsonResponse({
#             "path": bundle_path,
#             "spec": bundle_data.get("spec", {}),
#             "style": bundle_data.get("style", {}),
#             "data_hash": bundle_data.get("data_hash"),
#             "geometry": bundle_data.get("geometry"),
#             "exports": bundle_data.get("exports"),
#         })
#
#     except FileNotFoundError:
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except ValueError as e:
#         return JsonResponse({"error": str(e)}, status=400)
#     except Exception as e:
#         logger.exception(f"Failed to load pltz bundle: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_preview_by_path(request):
#     """
#     Get pltz bundle preview image from filesystem path.
#
#     Query params:
#         path: Filesystem path to .pltz.d directory or .pltz file
#         type: Image type (png, svg, hitmap, overview) - default: png
#
#     Returns:
#         Image binary (PNG or SVG)
#     """
#     bundle_path = request.GET.get("path")
#     if not bundle_path:
#         return JsonResponse({"error": "path parameter required"}, status=400)
#
#     image_type = request.GET.get("type", "png")
#
#     logger.info(f"[get_pltz_preview_by_path] Loading preview: {bundle_path}")
#
#     try:
#         image_data = PltzService.get_preview_image(bundle_path, image_type)
#
#         if image_data:
#             logger.info(f"[get_pltz_preview_by_path] Image found, size: {len(image_data)} bytes")
#
#             if image_type == "svg":
#                 content_type = "image/svg+xml"
#             else:
#                 content_type = "image/png"
#
#             return HttpResponse(image_data, content_type=content_type)
#
#         logger.warning(f"[get_pltz_preview_by_path] Preview not found: {bundle_path}")
#         return JsonResponse({"error": "Preview not found"}, status=404)
#
#     except FileNotFoundError:
#         logger.error(f"[get_pltz_preview_by_path] Bundle not found: {bundle_path}")
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except Exception as e:
#         logger.exception(f"Failed to get preview: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_geometry_by_path(request):
#     """Get pltz bundle geometry_px.json from filesystem path."""
#     bundle_path = request.GET.get("path")
#     if not bundle_path:
#         return JsonResponse({"error": "path parameter required"}, status=400)
#
#     logger.info(f"[get_pltz_geometry_by_path] Loading geometry: {bundle_path}")
#
#     try:
#         geometry = PltzService.get_geometry(bundle_path)
#
#         if geometry:
#             return JsonResponse(geometry)
#
#         return JsonResponse({"error": "Geometry not found"}, status=404)
#
#     except FileNotFoundError:
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except Exception as e:
#         logger.exception(f"Failed to get geometry: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_data_by_path(request):
#     """Get pltz bundle CSV data from filesystem path."""
#     bundle_path = request.GET.get("path")
#     if not bundle_path:
#         return JsonResponse({"error": "path parameter required"}, status=400)
#
#     try:
#         csv_data = PltzService.get_data_csv(bundle_path)
#
#         if csv_data:
#             return HttpResponse(csv_data, content_type="text/csv")
#
#         return JsonResponse({"error": "Data not found"}, status=404)
#
#     except FileNotFoundError:
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except Exception as e:
#         logger.exception(f"Failed to get CSV data: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["POST"])
# def update_pltz_by_path(request):
#     """Update pltz bundle spec or style at filesystem path."""
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#
#     bundle_path = data.get("path")
#     if not bundle_path:
#         return JsonResponse({"error": "path is required"}, status=400)
#
#     try:
#         result = {"path": bundle_path, "updated": []}
#
#         if "spec" in data:
#             PltzService.update_spec(bundle_path, data["spec"])
#             result["updated"].append("spec")
#
#         if "style" in data:
#             PltzService.update_style(bundle_path, data["style"])
#             result["updated"].append("style")
#
#         return JsonResponse(result)
#
#     except FileNotFoundError:
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except Exception as e:
#         logger.exception(f"Failed to update pltz bundle: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["POST"])
# def render_pltz_by_path(request):
#     """Re-render pltz bundle preview at filesystem path."""
#     bundle_path = request.GET.get("path")
#     if not bundle_path:
#         try:
#             data = json.loads(request.body)
#             bundle_path = data.get("path")
#         except json.JSONDecodeError:
#             pass
#
#     if not bundle_path:
#         return JsonResponse({"error": "path parameter required"}, status=400)
#
#     try:
#         result = PltzService.render_preview(bundle_path)
#
#         return JsonResponse({
#             "path": bundle_path,
#             "rendered": True,
#             "exports": result.get("exports", {}),
#         })
#
#     except FileNotFoundError:
#         return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
#     except ValueError as e:
#         return JsonResponse({"error": str(e)}, status=400)
#     except Exception as e:
#         logger.exception(f"Failed to render pltz bundle: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["POST"])
# def create_pltz_from_plot(request):
#     """
#     Create a pltz bundle from plot type and data.
#
#     This is the primary endpoint for the gallery -> canvas flow.
#     """
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#
#     plot_type = data.get("plot_type")
#     if not plot_type:
#         return JsonResponse({"error": "plot_type is required"}, status=400)
#
#     try:
#         result = PltzService.create_from_plot(
#             plot_type=plot_type,
#             data_csv=data.get("data_csv"),
#             data=data.get("data"),
#             name=data.get("name"),
#             output_dir=data.get("output_dir"),
#             project_owner=data.get("project_owner"),
#             project_slug=data.get("project_slug"),
#             figure_name=data.get("figure_name"),
#             panel_label=data.get("panel_label"),
#             user=request.user,
#             gallery_category=data.get("gallery_category"),
#             gallery_plot_name=data.get("gallery_plot_name"),
#         )
#
#         bundle_path = result.get("bundle_path", result.get("path", ""))
#         # Use bundle_path for preview (scitex handles ZIP transparently)
#         preview_path = bundle_path
#
#         return JsonResponse({
#             "success": True,
#             "bundle_path": bundle_path,
#             "directory_path": result.get("directory_path"),
#             "preview_url": f"/vis/api/bundles/pltz/preview/?path={preview_path}",
#             "hitmap_url": f"/vis/api/bundles/pltz/preview/?path={preview_path}&type=hitmap",
#             "spec": result.get("spec"),
#             "style": result.get("style"),
#             "geometry": result.get("geometry"),
#         }, status=201)
#
#     except ValueError as e:
#         return JsonResponse({"error": str(e)}, status=400)
#     except Exception as e:
#         logger.exception(f"Failed to create pltz from plot: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["POST"])
# def save_figz_canvas(request):
#     """
#     Auto-save canvas state as a figz bundle.
#
#     Request body:
#         project_owner: Project owner username
#         project_slug: Project slug
#         figure_name: Figure name (e.g., "Figure1")
#         panels: List of panel specs with positions
#         canvas_size: {width_mm, height_mm}
#         theme: "light" or "dark"
#
#     Returns:
#         Saved figz bundle info
#     """
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#
#     project_owner = data.get("project_owner")
#     project_slug = data.get("project_slug")
#     figure_name = data.get("figure_name", "Figure1")
#     panels = data.get("panels", [])
#     canvas_size = data.get("canvas_size", {"width_mm": 170, "height_mm": 120})
#     theme = data.get("theme", "light")
#
#     try:
#         result = FigzService.save_canvas_as_bundle(
#             project_owner=project_owner,
#             project_slug=project_slug,
#             figure_name=figure_name,
#             panels=panels,
#             canvas_size=canvas_size,
#             theme=theme,
#             user=request.user,
#         )
#
#         return JsonResponse({
#             "success": True,
#             "bundle_path": result.get("bundle_path", result.get("path", "")),
#             "directory_path": result.get("directory_path"),
#             "figure_name": figure_name,
#             "panel_count": len(panels),
#         })
#
#     except ValueError as e:
#         return JsonResponse({"error": str(e)}, status=400)
#     except Exception as e:
#         logger.exception(f"Failed to save figz canvas: {e}")
#         return JsonResponse({"error": str(e)}, status=500)

# --------------------------------------------------------------------------------
# End of Source Code from: apps/figrecipe_app/views/api/bundles/path_api.py
# --------------------------------------------------------------------------------
