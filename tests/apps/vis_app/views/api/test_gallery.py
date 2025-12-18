#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/vis_app/views/api/gallery.py"""

import pytest

# from apps.vis_app.views.api.gallery import ...


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
# Start of Source Code from: apps/vis_app/views/api/gallery.py
# --------------------------------------------------------------------------------
# """
# Plot Type Gallery API - Serves plot templates and thumbnails from scitex examples.
# 
# Provides:
# - List of available plot types with thumbnails
# - Template JSON for creating new plots
# - Categorized plot types (matplotlib, scitex, seaborn)
# """
# 
# import base64
# import json
# import logging
# import traceback
# from pathlib import Path
# 
# from django.http import JsonResponse, HttpResponse
# from django.views.decorators.http import require_http_methods
# 
# from ...services.gallery_service import GalleryService
# from ...services.gallery_generator import (
#     generate_gallery,
#     get_gallery_contents,
#     get_template_gallery_path,
#     list_gallery_categories,
#     get_gallery_path,
# )
# from apps.project_app.services.project_utils import get_current_project
# 
# logger = logging.getLogger(__name__)
# 
# 
# @require_http_methods(["GET"])
# def get_plot_galleries(request):
#     """
#     Get all available plot galleries.
# 
#     GET /vis/api/gallery/
# 
#     Response:
#     {
#         "galleries": [
#             {
#                 "id": "matplotlib",
#                 "name": "Matplotlib",
#                 "description": "...",
#                 "plots": [...]
#             },
#             ...
#         ]
#     }
#     """
#     try:
#         galleries = GalleryService.get_plot_galleries()
# 
#         # Remove file paths from response (for security)
#         for gallery in galleries:
#             if 'path' in gallery:
#                 del gallery['path']
# 
#         return JsonResponse({
#             'galleries': galleries,
#             'total_plots': sum(len(g['plots']) for g in galleries)
#         })
# 
#     except Exception as e:
#         return JsonResponse({
#             'error': f'Failed to load galleries: {str(e)}'
#         }, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_plot_thumbnail(request, gallery_id: str, plot_id: str):
#     """
#     Get plot thumbnail as base64 or binary.
# 
#     GET /vis/api/gallery/<gallery_id>/<plot_id>/thumbnail/
# 
#     Query params:
#     - format: 'base64' (default) or 'binary'
#     - size: 'small' (64px), 'medium' (128px), 'large' (256px)
# 
#     Response (base64):
#     {
#         "thumbnail": "data:image/png;base64,..."
#     }
# 
#     Response (binary):
#     Binary PNG image
#     """
#     try:
#         output_format = request.GET.get('format', 'base64')
# 
#         result = GalleryService.find_plot_in_galleries(gallery_id, plot_id)
#         if not result:
#             return JsonResponse({'error': f'Gallery or plot not found: {gallery_id}/{plot_id}'}, status=404)
# 
#         gallery, plot = result
# 
#         if not plot['files']['png']:
#             return JsonResponse({'error': f'Plot not found: {plot_id}'}, status=404)
# 
#         png_path = Path(plot['files']['png'])
#         image_data = GalleryService.load_thumbnail(png_path)
# 
#         if output_format == 'binary':
#             response = HttpResponse(image_data, content_type='image/png')
#             response['Content-Disposition'] = f'inline; filename="{png_path.name}"'
#             return response
#         else:
#             # Base64
#             return JsonResponse({
#                 'thumbnail': GalleryService.encode_thumbnail_base64(image_data),
#                 'name': plot['name'],
#                 'category': plot['category']
#             })
# 
#     except FileNotFoundError as e:
#         return JsonResponse({'error': str(e)}, status=404)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_plot_template(request, gallery_id: str, plot_id: str):
#     """
#     Get plot JSON template for creating new plots.
# 
#     GET /vis/api/gallery/<gallery_id>/<plot_id>/template/
# 
#     Response:
#     {
#         "metadata": {...},
#         "csv_columns": [...],
#         "boilerplate_code": "..."
#     }
#     """
#     try:
#         result = GalleryService.find_plot_in_galleries(gallery_id, plot_id)
#         if not result:
#             return JsonResponse({'error': f'Gallery or plot not found: {gallery_id}/{plot_id}'}, status=404)
# 
#         gallery, plot = result
# 
#         # Load template data
#         template_data = GalleryService.load_plot_template(plot)
# 
#         # Generate boilerplate code
#         template_data['boilerplate_code'] = GalleryService.generate_boilerplate(plot, gallery_id)
# 
#         return JsonResponse(template_data)
# 
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_categories(request):
#     """
#     Get available plot categories.
# 
#     GET /vis/api/gallery/categories/
# 
#     Response:
#     {
#         "categories": [
#             {"id": "line", "name": "Line Plots", "count": 8},
#             ...
#         ]
#     }
#     """
#     try:
#         category_counts = GalleryService.get_category_counts()
#         categories = GalleryService.format_categories(category_counts)
# 
#         return JsonResponse({'categories': categories})
# 
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
# 
# 
# # =============================================================================
# # Project-Based Gallery API (uses stx.plt.gallery.generate)
# # =============================================================================
# 
# @require_http_methods(["POST"])
# def generate_project_gallery(request):
#     """
#     Generate gallery plots into project's scitex/vis/gallery directory.
# 
#     POST /vis/api/gallery/generate/
# 
#     Request body:
#     {
#         "category": "line",  // optional: generate specific category
#         "plot_type": "scatter",  // optional: generate specific plot
#         "force": false,  // optional: regenerate even if exists
#         "figsize": [4, 3],  // optional
#         "dpi": 150  // optional
#     }
# 
#     Response:
#     {
#         "success": true,
#         "path": "/path/to/gallery",
#         "png": [...],
#         "csv": [...],
#         "json": [...]
#     }
#     """
#     try:
#         # Get current project
#         project = get_current_project(request, user=request.user)
#         if not project:
#             return JsonResponse({
#                 'error': 'No project selected. Please select a project first.'
#             }, status=400)
# 
#         # Get project path
#         project_path = project.get_local_path()
#         if not project_path.exists():
#             return JsonResponse({
#                 'error': f'Project workspace not found: {project_path}'
#             }, status=404)
# 
#         # Parse request body
#         try:
#             body = json.loads(request.body) if request.body else {}
#         except json.JSONDecodeError:
#             body = {}
# 
#         category = body.get('category')
#         plot_type = body.get('plot_type')
#         force = body.get('force', False)
#         figsize = tuple(body.get('figsize', [4, 3]))
#         dpi = body.get('dpi', 150)
# 
#         # Generate gallery
#         result = generate_gallery(
#             project_path=project_path,
#             category=category,
#             plot_type=plot_type,
#             figsize=figsize,
#             dpi=dpi,
#             force=force,
#         )
# 
#         if result.get('success'):
#             return JsonResponse(result)
#         else:
#             return JsonResponse(result, status=500)
# 
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_project_gallery(request):
#     """
#     Get contents of project's gallery.
# 
#     GET /vis/api/gallery/project/
# 
#     Response:
#     {
#         "success": true,
#         "exists": true,
#         "path": "/path/to/gallery",
#         "categories": {
#             "line": {
#                 "name": "Line",
#                 "plots": [...],
#                 "count": 4
#             },
#             ...
#         },
#         "total_plots": 46
#     }
#     """
#     try:
#         project = get_current_project(request, user=request.user) if request.user.is_authenticated else None
#         if project:
#             project_path = project.get_local_path()
#             result = get_gallery_contents(project_path, fallback_to_template=True)
#         else:
#             # No project - use template gallery directly
#             template_path = get_template_gallery_path()
#             if template_path.exists():
#                 result = get_gallery_contents(template_path.parent.parent.parent, fallback_to_template=False)
#                 result['using_template'] = True
#             else:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'No gallery available'
#                 }, status=404)
# 
#         return JsonResponse(result)
# 
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_project_gallery_image(request, category: str, plot_name: str):
#     """
#     Get a specific plot image from project gallery.
# 
#     GET /vis/api/gallery/project/<category>/<plot_name>/image/
# 
#     Query params:
#     - format: 'base64' (default), 'binary', or 'svg'
#     - type: 'png' (default) or 'svg'
# 
#     Response (base64):
#     {
#         "image": "data:image/png;base64,...",
#         "name": "plot",
#         "category": "line"
#     }
# 
#     Response (binary):
#     Binary PNG image
# 
#     Response (svg):
#     SVG XML content
#     """
#     try:
#         output_format = request.GET.get('format', 'base64')
#         image_type = request.GET.get('type', 'svg' if output_format == 'svg' else 'png')
# 
#         project = get_current_project(request) if request.user.is_authenticated else None
#         gallery_path = None
# 
#         if project:
#             project_path = project.get_local_path()
#             gallery_path = get_gallery_path(project_path)
# 
#         # Helper to find SVG in gallery (bundle or flat format)
#         def find_svg_in_gallery(gallery_base: Path) -> Path | None:
#             """Find SVG in gallery, checking both new bundle format and old flat format."""
#             # New format: inside .pltz.d bundle
#             bundle_svg = gallery_base / category / f"{plot_name}.pltz.d" / "exports" / f"{plot_name}.svg"
#             if bundle_svg.exists():
#                 return bundle_svg
#             # Old format: flat file
#             flat_svg = gallery_base / category / f"{plot_name}.svg"
#             if flat_svg.exists():
#                 return flat_svg
#             return None
# 
#         # For SVG, try SVG file first
#         if image_type == 'svg':
#             svg_path = None
#             if gallery_path:
#                 svg_path = find_svg_in_gallery(gallery_path)
#             if not svg_path:
#                 gallery_path = get_template_gallery_path()
#                 svg_path = find_svg_in_gallery(gallery_path)
#             if svg_path:
#                 with open(svg_path, 'r') as f:
#                     svg_content = f.read()
#                 response = HttpResponse(svg_content, content_type='image/svg+xml')
#                 response['Content-Disposition'] = f'inline; filename="{plot_name}.svg"'
#                 return response
#             # Fall back to PNG if SVG doesn't exist
#             image_type = 'png'
# 
#         # PNG path - check multiple locations
#         # New format: gallery/{category}/{plot_name}.pltz.d/exports/{plot_name}.png
#         # Old format: gallery/{category}/{plot_name}.png
#         png_path = None
# 
#         def find_png_in_gallery(gallery_base: Path) -> Path | None:
#             """Find PNG in gallery, checking both new bundle format and old flat format."""
#             # New format: inside .pltz.d bundle
#             bundle_png = gallery_base / category / f"{plot_name}.pltz.d" / "exports" / f"{plot_name}.png"
#             if bundle_png.exists():
#                 return bundle_png
#             # Old format: flat file
#             flat_png = gallery_base / category / f"{plot_name}.png"
#             if flat_png.exists():
#                 return flat_png
#             return None
# 
#         # Try project gallery first
#         if project:
#             project_path = project.get_local_path()
#             gallery_path = get_gallery_path(project_path)
#             png_path = find_png_in_gallery(gallery_path)
# 
#         # Try temp gallery with hitmap
#         if not png_path:
#             temp_gallery_path = Path('/tmp/scitex_gallery_with_bboxes')
#             png_path = find_png_in_gallery(temp_gallery_path)
# 
#         # Fallback to static template gallery
#         if not png_path:
#             gallery_path = get_template_gallery_path()
#             png_path = find_png_in_gallery(gallery_path)
#             if not png_path:
#                 return JsonResponse({'error': f'Image not found: {category}/{plot_name}'}, status=404)
# 
#         with open(png_path, 'rb') as f:
#             image_data = f.read()
# 
#         if output_format == 'binary':
#             response = HttpResponse(image_data, content_type='image/png')
#             response['Content-Disposition'] = f'inline; filename="{png_path.name}"'
#             return response
#         else:
#             result = {
#                 'image': GalleryService.encode_thumbnail_base64(image_data),
#                 'name': plot_name,
#                 'category': category
#             }
#             # Try to load metadata from companion JSON
#             # New format: spec.json in bundle root (../spec.json from exports/)
#             # Old format: {plot_name}.json next to PNG
#             json_path = png_path.parent.parent / 'spec.json'  # New bundle format
#             if not json_path.exists():
#                 json_path = png_path.with_suffix('.json')  # Old flat format
#             if json_path.exists():
#                 try:
#                     with open(json_path, 'r') as f:
#                         metadata = json.load(f)
#                     if 'axes_bbox_px' in metadata:
#                         result['axes_bbox_px'] = metadata['axes_bbox_px']
#                     if 'element_bboxes' in metadata:
#                         result['element_bboxes'] = metadata['element_bboxes']
#                     if 'dimensions' in metadata:
#                         dims = metadata['dimensions']
#                         if 'figure_size_px' in dims:
#                             result['figure_size_px'] = dims['figure_size_px']
#                     # Add hitmap for fast element picking
#                     if 'hitmap_color_map' in metadata:
#                         result['hitmap_color_map'] = metadata['hitmap_color_map']
#                     if 'hitmap_file' in metadata:
#                         hitmap_path = png_path.parent / metadata['hitmap_file']
#                         if hitmap_path.exists():
#                             with open(hitmap_path, 'rb') as f:
#                                 hitmap_data = f.read()
#                             result['hitmap'] = f'data:image/png;base64,{base64.b64encode(hitmap_data).decode("utf-8")}'
#                 except Exception as e:
#                     logger.warning(f"Failed to load metadata: {e}")
#             return JsonResponse(result)
# 
#     except Exception as e:
#         logger.error(f"get_project_gallery_image error for {category}/{plot_name}: {e}\n{traceback.format_exc()}")
#         return JsonResponse({'error': str(e)}, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_project_gallery_csv(request, category: str, plot_name: str):
#     """
#     Get CSV data for a specific plot from project gallery.
# 
#     GET /vis/api/gallery/project/<category>/<plot_name>/csv/
# 
#     Response:
#     CSV text content
#     """
#     try:
#         csv_path = None
#         project = get_current_project(request) if request.user.is_authenticated else None
# 
#         if project:
#             project_path = project.get_local_path()
#             gallery_path = get_gallery_path(project_path)
#             csv_path = gallery_path / category / f"{plot_name}.csv"
# 
#         # Fallback to template gallery
#         if not csv_path or not csv_path.exists():
#             gallery_path = get_template_gallery_path()
#             csv_path = gallery_path / category / f"{plot_name}.csv"
#             if not csv_path.exists():
#                 return JsonResponse({'error': 'CSV not found'}, status=404)
# 
#         with open(csv_path, 'r') as f:
#             csv_content = f.read()
# 
#         response = HttpResponse(csv_content, content_type='text/csv')
#         response['Content-Disposition'] = f'inline; filename="{csv_path.name}"'
#         return response
# 
#     except Exception as e:
#         logger.error(f"get_project_gallery_csv error for {category}/{plot_name}: {e}\n{traceback.format_exc()}")
#         return JsonResponse({'error': str(e)}, status=500)
# 
# 
# @require_http_methods(["GET"])
# def list_gallery_categories_available(request):
#     """
#     List available categories from stx.plt.gallery (not project-specific).
# 
#     GET /vis/api/gallery/available/
# 
#     Response:
#     {
#         "success": true,
#         "categories": {
#             "line": {"name": "Line Plots", "plots": [...], "description": "..."},
#             ...
#         },
#         "total_plots": 46
#     }
#     """
#     try:
#         result = list_gallery_categories()
#         return JsonResponse(result)
# 
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)
# 
# 
# @require_http_methods(["GET"])
# def get_plot_metadata(request, category: str, plot_name: str):
#     """
#     Get axis metadata (axes_bbox_px) for a plot from gallery.
#     Used for snap/align by axis position.
# 
#     GET /vis/api/gallery/metadata/<category>/<plot_name>/
# 
#     Response:
#     {
#         "success": true,
#         "axes_bbox_px": {"x0": 236, "y0": 236, "x1": 708, "y1": 566, ...},
#         "figure_size_px": {"width": 944, "height": 803}
#     }
#     """
#     try:
#         metadata = GalleryService.load_plot_metadata(category, plot_name)
# 
#         if not metadata:
#             return JsonResponse({
#                 'success': False,
#                 'error': f'Metadata not found for {category}/{plot_name}'
#             }, status=404)
# 
#         return JsonResponse(metadata)
# 
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)

# --------------------------------------------------------------------------------
# End of Source Code from: apps/vis_app/views/api/gallery.py
# --------------------------------------------------------------------------------
