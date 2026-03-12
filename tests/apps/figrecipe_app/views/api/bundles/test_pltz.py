#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/figrecipe_app/views/api/bundles/pltz.py"""

import pytest

# from apps.workspace.figrecipe_app.views.api.bundles.pltz import ...


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
# Start of Source Code from: apps/figrecipe_app/views/api/bundles/pltz.py
# --------------------------------------------------------------------------------
# """
# PltzBundle API Views - CRUD endpoints for pltz bundle operations.
#
# Provides REST operations for individual plot bundles (.pltz).
# """
#
# import json
# import logging
#
# from django.contrib.auth.decorators import login_required
# from django.http import JsonResponse, HttpResponse
# from django.utils.text import slugify
# from django.views.decorators.http import require_http_methods
#
# from ....models import PltzBundle
# from ....services.pltz_service import PltzService
#
# logger = logging.getLogger(__name__)
#
#
# @login_required
# @require_http_methods(["GET"])
# def list_pltz_bundles(request):
#     """
#     List all pltz bundles for current user.
#
#     Query params:
#         category: Filter by category (line, scatter, bar, etc.)
#         search: Search in name/description
#
#     Returns:
#         JSON array of bundle summaries
#     """
#     bundles = PltzBundle.objects.filter(owner=request.user)
#
#     category = request.GET.get("category")
#     if category:
#         bundles = bundles.filter(category=category)
#
#     search = request.GET.get("search")
#     if search:
#         bundles = bundles.filter(name__icontains=search)
#
#     bundle_list = []
#     for bundle in bundles:
#         bundle_list.append({
#             "id": str(bundle.id),
#             "name": bundle.name,
#             "slug": bundle.slug,
#             "category": bundle.category,
#             "description": bundle.description,
#             "tags": bundle.tags,
#             "preview_url": f"/vis/api/bundles/pltz/{bundle.id}/preview/",
#             "created_at": bundle.created_at.isoformat(),
#             "updated_at": bundle.updated_at.isoformat(),
#         })
#
#     return JsonResponse({"bundles": bundle_list})
#
#
# @login_required
# @require_http_methods(["POST"])
# def create_pltz_bundle(request):
#     """
#     Create a new pltz bundle.
#
#     Request body:
#         name: Display name
#         spec: PltzSpec dictionary
#         style: PltzStyle dictionary
#         data_csv: CSV data string (optional)
#         category: Plot category (optional, auto-detected if not provided)
#         description: Description text (optional)
#         tags: List of tags (optional)
#
#     Returns:
#         Created bundle info
#     """
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#
#     name = data.get("name")
#     spec = data.get("spec", {})
#     style = data.get("style", {})
#
#     if not name:
#         return JsonResponse({"error": "name is required"}, status=400)
#
#     category = data.get("category")
#     if not category:
#         category = PltzService.categorize_plot(spec)
#
#     try:
#         result = PltzService.save_bundle(
#             spec=spec,
#             style=style,
#             data_csv=data.get("data_csv"),
#             user_id=request.user.id,
#             name=name,
#         )
#
#         bundle = PltzBundle.objects.create(
#             owner=request.user,
#             name=name,
#             slug=slugify(name),
#             bundle_path=result["path"],
#             is_zip=result.get("is_zip", False),
#             spec=spec,
#             style=style,
#             data_hash=result.get("data_hash", ""),
#             category=category,
#             description=data.get("description", ""),
#             tags=data.get("tags", []),
#         )
#
#         return JsonResponse({
#             "id": str(bundle.id),
#             "name": bundle.name,
#             "slug": bundle.slug,
#             "path": result["path"],
#             "category": bundle.category,
#         }, status=201)
#
#     except Exception as e:
#         logger.exception(f"Failed to create pltz bundle: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_bundle(request, bundle_id):
#     """Get pltz bundle details."""
#     try:
#         bundle = PltzBundle.objects.get(id=bundle_id, owner=request.user)
#     except PltzBundle.DoesNotExist:
#         return JsonResponse({"error": "Bundle not found"}, status=404)
#
#     try:
#         bundle_data = PltzService.load_bundle(bundle.bundle_path)
#     except Exception as e:
#         logger.warning(f"Failed to load bundle from disk: {e}")
#         bundle_data = {}
#
#     return JsonResponse({
#         "id": str(bundle.id),
#         "name": bundle.name,
#         "slug": bundle.slug,
#         "category": bundle.category,
#         "description": bundle.description,
#         "tags": bundle.tags,
#         "spec": bundle_data.get("spec", bundle.spec),
#         "style": bundle_data.get("style", bundle.style),
#         "data_hash": bundle.data_hash,
#         "geometry": bundle_data.get("geometry"),
#         "exports": bundle_data.get("exports"),
#         "created_at": bundle.created_at.isoformat(),
#         "updated_at": bundle.updated_at.isoformat(),
#     })
#
#
# @login_required
# @require_http_methods(["PUT", "PATCH"])
# def update_pltz_bundle(request, bundle_id):
#     """Update pltz bundle spec, style, or metadata."""
#     try:
#         bundle = PltzBundle.objects.get(id=bundle_id, owner=request.user)
#     except PltzBundle.DoesNotExist:
#         return JsonResponse({"error": "Bundle not found"}, status=404)
#
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#
#     if "spec" in data:
#         PltzService.update_spec(bundle.bundle_path, data["spec"])
#         bundle.spec = data["spec"]
#
#     if "style" in data:
#         PltzService.update_style(bundle.bundle_path, data["style"])
#         bundle.style = data["style"]
#
#     if "name" in data:
#         bundle.name = data["name"]
#         bundle.slug = slugify(data["name"])
#     if "description" in data:
#         bundle.description = data["description"]
#     if "tags" in data:
#         bundle.tags = data["tags"]
#     if "category" in data:
#         bundle.category = data["category"]
#
#     bundle.save()
#
#     return JsonResponse({
#         "id": str(bundle.id),
#         "name": bundle.name,
#         "updated": True,
#     })
#
#
# @login_required
# @require_http_methods(["DELETE"])
# def delete_pltz_bundle(request, bundle_id):
#     """Delete a pltz bundle."""
#     try:
#         bundle = PltzBundle.objects.get(id=bundle_id, owner=request.user)
#     except PltzBundle.DoesNotExist:
#         return JsonResponse({"error": "Bundle not found"}, status=404)
#
#     PltzService.delete_bundle(bundle.bundle_path)
#     bundle.delete()
#
#     return JsonResponse({"deleted": True})
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_preview(request, bundle_id):
#     """Get pltz bundle preview image."""
#     try:
#         bundle = PltzBundle.objects.get(id=bundle_id, owner=request.user)
#     except PltzBundle.DoesNotExist:
#         return JsonResponse({"error": "Bundle not found"}, status=404)
#
#     image_type = request.GET.get("type", "png")
#     image_data = PltzService.get_preview_image(bundle.bundle_path, image_type)
#
#     if image_data:
#         return HttpResponse(image_data, content_type="image/png")
#
#     return JsonResponse({"error": "Preview not found"}, status=404)
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_data(request, bundle_id):
#     """Get pltz bundle CSV data."""
#     try:
#         bundle = PltzBundle.objects.get(id=bundle_id, owner=request.user)
#     except PltzBundle.DoesNotExist:
#         return JsonResponse({"error": "Bundle not found"}, status=404)
#
#     csv_data = PltzService.get_data_csv(bundle.bundle_path)
#
#     if csv_data:
#         return HttpResponse(csv_data, content_type="text/csv")
#
#     return JsonResponse({"error": "Data not found"}, status=404)
#
#
# @login_required
# @require_http_methods(["GET"])
# def get_pltz_geometry(request, bundle_id):
#     """Get pltz bundle geometry cache for hit-testing."""
#     try:
#         bundle = PltzBundle.objects.get(id=bundle_id, owner=request.user)
#     except PltzBundle.DoesNotExist:
#         return JsonResponse({"error": "Bundle not found"}, status=404)
#
#     geometry = PltzService.get_geometry(bundle.bundle_path)
#
#     if geometry:
#         return JsonResponse(geometry)
#
#     return JsonResponse({"error": "Geometry not cached"}, status=404)

# --------------------------------------------------------------------------------
# End of Source Code from: apps/figrecipe_app/views/api/bundles/pltz.py
# --------------------------------------------------------------------------------
