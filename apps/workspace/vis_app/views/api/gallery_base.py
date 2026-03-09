"""Gallery Base - Basic plot gallery API endpoints."""

import logging
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ...services.gallery_service import GalleryService

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def get_plot_galleries(request):
    """Get all available plot galleries."""
    try:
        galleries = GalleryService.get_plot_galleries()
        for gallery in galleries:
            if "path" in gallery:
                del gallery["path"]
        return JsonResponse(
            {
                "galleries": galleries,
                "total_plots": sum(len(g["plots"]) for g in galleries),
            }
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to load galleries: {str(e)}"}, status=500
        )


@require_http_methods(["GET"])
def get_plot_thumbnail(request, gallery_id: str, plot_id: str):
    """Get plot thumbnail as base64 or binary."""
    try:
        output_format = request.GET.get("format", "base64")
        result = GalleryService.find_plot_in_galleries(gallery_id, plot_id)
        if not result:
            return JsonResponse(
                {"error": f"Gallery or plot not found: {gallery_id}/{plot_id}"},
                status=404,
            )

        gallery, plot = result
        if not plot["files"]["png"]:
            return JsonResponse({"error": f"Plot not found: {plot_id}"}, status=404)

        png_path = Path(plot["files"]["png"])
        image_data = GalleryService.load_thumbnail(png_path)

        if output_format == "binary":
            response = HttpResponse(image_data, content_type="image/png")
            response["Content-Disposition"] = f'inline; filename="{png_path.name}"'
            return response
        else:
            return JsonResponse(
                {
                    "thumbnail": GalleryService.encode_thumbnail_base64(image_data),
                    "name": plot["name"],
                    "category": plot["category"],
                }
            )
    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_plot_template(request, gallery_id: str, plot_id: str):
    """Get plot JSON template for creating new plots."""
    try:
        result = GalleryService.find_plot_in_galleries(gallery_id, plot_id)
        if not result:
            return JsonResponse(
                {"error": f"Gallery or plot not found: {gallery_id}/{plot_id}"},
                status=404,
            )

        gallery, plot = result
        template_data = GalleryService.load_plot_template(plot)
        template_data["boilerplate_code"] = GalleryService.generate_boilerplate(
            plot, gallery_id
        )
        return JsonResponse(template_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_categories(request):
    """Get available plot categories."""
    try:
        category_counts = GalleryService.get_category_counts()
        categories = GalleryService.format_categories(category_counts)
        return JsonResponse({"categories": categories})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
