"""Gallery Project - Project-based gallery API endpoints."""

import json
import logging
import traceback

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.project_utils import get_current_project

from ...services.gallery_generator import (
    generate_gallery,
    get_gallery_contents,
    get_gallery_path,
    get_template_gallery_path,
    list_gallery_categories,
)
from ...services.gallery_service import GalleryService
from .gallery_utils import (
    add_metadata_to_result,
    find_image_in_gallery,
    find_png_path,
)

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def generate_project_gallery(request):
    """Generate gallery plots into project's scitex/vis/gallery directory."""
    try:
        project = get_current_project(request, user=request.user)
        if not project:
            return JsonResponse(
                {"error": "No project selected. Please select a project first."},
                status=400,
            )

        project_path = project.get_local_path()
        if not project_path.exists():
            return JsonResponse(
                {"error": f"Project workspace not found: {project_path}"}, status=404
            )

        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            body = {}

        result = generate_gallery(
            project_path=project_path,
            category=body.get("category"),
            plot_type=body.get("plot_type"),
            figsize=tuple(body.get("figsize", [4, 3])),
            dpi=body.get("dpi", 150),
            force=body.get("force", False),
        )
        return (
            JsonResponse(result)
            if result.get("success")
            else JsonResponse(result, status=500)
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_project_gallery(request):
    """Get contents of project's gallery."""
    try:
        project = (
            get_current_project(request, user=request.user)
            if request.user.is_authenticated
            else None
        )
        if project:
            project_path = project.get_local_path()
            result = get_gallery_contents(project_path, fallback_to_template=True)
        else:
            template_path = get_template_gallery_path()
            if template_path.exists():
                result = get_gallery_contents(
                    template_path.parent.parent.parent, fallback_to_template=False
                )
                result["using_template"] = True
            else:
                return JsonResponse(
                    {"success": False, "error": "No gallery available"}, status=404
                )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_project_gallery_image(request, category: str, plot_name: str):
    """Get a specific plot image from project gallery."""
    try:
        output_format = request.GET.get("format", "base64")
        image_type = request.GET.get("type", "svg" if output_format == "svg" else "png")

        project = (
            get_current_project(request) if request.user.is_authenticated else None
        )
        gallery_path = None

        if project:
            project_path = project.get_local_path()
            gallery_path = get_gallery_path(project_path)

        if image_type == "svg":
            svg_path = find_image_in_gallery(gallery_path, category, plot_name, "svg")
            if not svg_path:
                svg_path = find_image_in_gallery(
                    get_template_gallery_path(), category, plot_name, "svg"
                )
            if svg_path:
                with open(svg_path, "r") as f:
                    svg_content = f.read()
                response = HttpResponse(svg_content, content_type="image/svg+xml")
                response["Content-Disposition"] = f'inline; filename="{plot_name}.svg"'
                return response
            image_type = "png"

        png_path = find_png_path(project, category, plot_name)
        if not png_path:
            return JsonResponse(
                {"error": f"Image not found: {category}/{plot_name}"}, status=404
            )

        with open(png_path, "rb") as f:
            image_data = f.read()

        if output_format == "binary":
            response = HttpResponse(image_data, content_type="image/png")
            response["Content-Disposition"] = f'inline; filename="{png_path.name}"'
            return response
        else:
            result = {
                "image": GalleryService.encode_thumbnail_base64(image_data),
                "name": plot_name,
                "category": category,
            }
            add_metadata_to_result(result, png_path)
            return JsonResponse(result)

    except Exception as e:
        logger.error(
            f"get_project_gallery_image error for {category}/{plot_name}: "
            f"{e}\n{traceback.format_exc()}"
        )
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_project_gallery_csv(request, category: str, plot_name: str):
    """Get CSV data for a specific plot from project gallery."""
    try:
        csv_path = None
        project = (
            get_current_project(request) if request.user.is_authenticated else None
        )

        if project:
            gallery_path = get_gallery_path(project.get_local_path())
            csv_path = gallery_path / category / f"{plot_name}.csv"

        if not csv_path or not csv_path.exists():
            gallery_path = get_template_gallery_path()
            csv_path = gallery_path / category / f"{plot_name}.csv"
            if not csv_path.exists():
                return JsonResponse({"error": "CSV not found"}, status=404)

        with open(csv_path, "r") as f:
            csv_content = f.read()

        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = f'inline; filename="{csv_path.name}"'
        return response

    except Exception as e:
        logger.error(
            f"get_project_gallery_csv error for {category}/{plot_name}: "
            f"{e}\n{traceback.format_exc()}"
        )
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def list_gallery_categories_available(request):
    """List available categories from stx.plt.gallery."""
    try:
        result = list_gallery_categories()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_plot_metadata(request, category: str, plot_name: str):
    """Get axis metadata for a plot from gallery."""
    try:
        metadata = GalleryService.load_plot_metadata(category, plot_name)
        if not metadata:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Metadata not found for {category}/{plot_name}",
                },
                status=404,
            )
        return JsonResponse(metadata)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
