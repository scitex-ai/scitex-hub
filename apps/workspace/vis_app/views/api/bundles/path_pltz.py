"""
Path-Based Pltz Bundle API Views.

Endpoints for pltz bundle operations using filesystem paths.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ....services.pltz_service import PltzService
from ._path_helpers import resolve_bundle_path

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def load_pltz_by_path(request):
    """Load a pltz bundle from filesystem path."""
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    try:
        bundle_data = PltzService.load_bundle(bundle_path)

        # Convert DataFrame to list of dicts for JSON serialization
        data = bundle_data.get("data")
        data_json = None
        if data is not None:
            try:
                data_json = {
                    "columns": list(data.columns),
                    "rows": data.to_dict(orient="records"),
                }
            except Exception as e:
                logger.warning(f"Failed to convert data to JSON: {e}")

        return JsonResponse(
            {
                "path": bundle_path,
                "spec": bundle_data.get("spec", {}),
                "style": bundle_data.get("style", {}),
                "data": data_json,
                "data_hash": bundle_data.get("data_hash"),
                "geometry": bundle_data.get("geometry"),
                "exports": bundle_data.get("exports"),
            }
        )
    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Failed to load pltz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_pltz_preview_by_path(request):
    """Get pltz bundle preview image from filesystem path."""
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    image_type = request.GET.get("type", "png")

    # Resolve relative paths using project context
    resolved_path = resolve_bundle_path(
        bundle_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )
    bundle_path = str(resolved_path)

    logger.info(f"[get_pltz_preview_by_path] Loading preview: {bundle_path}")

    try:
        image_data = PltzService.get_preview_image(bundle_path, image_type)

        if image_data:
            logger.info(
                f"[get_pltz_preview_by_path] Image found, size: {len(image_data)} bytes"
            )
            content_type = "image/svg+xml" if image_type == "svg" else "image/png"
            return HttpResponse(image_data, content_type=content_type)

        logger.warning(f"[get_pltz_preview_by_path] Preview not found: {bundle_path}")
        return JsonResponse({"error": "Preview not found"}, status=404)

    except FileNotFoundError:
        logger.error(f"[get_pltz_preview_by_path] Bundle not found: {bundle_path}")
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except Exception as e:
        logger.exception(f"Failed to get preview: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_pltz_geometry_by_path(request):
    """Get pltz bundle geometry_px.json from filesystem path."""
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    logger.info(f"[get_pltz_geometry_by_path] Loading geometry: {bundle_path}")

    try:
        geometry = PltzService.get_geometry(bundle_path)
        if geometry:
            return JsonResponse(geometry)
        return JsonResponse({"error": "Geometry not found"}, status=404)
    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except Exception as e:
        logger.exception(f"Failed to get geometry: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_pltz_data_by_path(request):
    """Get pltz bundle CSV data from filesystem path."""
    bundle_path = request.GET.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    # Resolve relative paths using project context
    resolved_path = resolve_bundle_path(
        bundle_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )
    bundle_path = str(resolved_path)

    logger.info(f"[get_pltz_data_by_path] Loading CSV data: {bundle_path}")

    try:
        csv_data = PltzService.get_data_csv(bundle_path)
        if csv_data:
            return HttpResponse(csv_data, content_type="text/csv")
        return JsonResponse({"error": "Data not found"}, status=404)
    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except Exception as e:
        logger.exception(f"Failed to get CSV data: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_pltz_by_path(request):
    """Update pltz bundle spec or style at filesystem path."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    bundle_path = data.get("path")
    if not bundle_path:
        return JsonResponse({"error": "path is required"}, status=400)

    try:
        result = {"path": bundle_path, "updated": []}
        if "spec" in data:
            PltzService.update_spec(bundle_path, data["spec"])
            result["updated"].append("spec")
        if "style" in data:
            PltzService.update_style(bundle_path, data["style"])
            result["updated"].append("style")
        return JsonResponse(result)
    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except Exception as e:
        logger.exception(f"Failed to update pltz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def render_pltz_by_path(request):
    """Re-render pltz bundle preview at filesystem path."""
    bundle_path = request.GET.get("path")
    if not bundle_path:
        try:
            data = json.loads(request.body)
            bundle_path = data.get("path")
        except json.JSONDecodeError:
            pass

    if not bundle_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    try:
        result = PltzService.render_preview(bundle_path)
        return JsonResponse(
            {
                "path": bundle_path,
                "rendered": True,
                "exports": result.get("exports", {}),
            }
        )
    except FileNotFoundError:
        return JsonResponse({"error": f"Bundle not found: {bundle_path}"}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Failed to render pltz bundle: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_project_file_content(request):
    """Serve raw content of a project file (CSV, TSV, TXT) by filesystem path.

    Query params:
        path:           Absolute or relative filesystem path
        project_owner:  Optional project owner for path resolution
        project_slug:   Optional project slug for path resolution
    """
    file_path = request.GET.get("path")
    if not file_path:
        return JsonResponse({"error": "path parameter required"}, status=400)

    resolved = resolve_bundle_path(
        file_path,
        project_owner=request.GET.get("project_owner"),
        project_slug=request.GET.get("project_slug"),
        user=request.user,
    )

    if not resolved.exists():
        return JsonResponse({"error": f"File not found: {resolved}"}, status=404)

    if not resolved.is_file():
        return JsonResponse({"error": "Path is not a file"}, status=400)

    allowed_suffixes = {
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        ".txt": "text/plain",
    }
    suffix = resolved.suffix.lower()
    if suffix not in allowed_suffixes:
        return JsonResponse({"error": f"Unsupported file type: {suffix}"}, status=400)

    try:
        content = resolved.read_text(encoding="utf-8")
        return HttpResponse(content, content_type=allowed_suffixes[suffix])
    except Exception as e:
        logger.exception(f"[get_project_file_content] Failed to read {resolved}: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_pltz_from_plot(request):
    """Create a pltz bundle from plot type and data."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    plot_type = data.get("plot_type")
    if not plot_type:
        return JsonResponse({"error": "plot_type is required"}, status=400)

    try:
        result = PltzService.create_from_plot(
            plot_type=plot_type,
            data_csv=data.get("data_csv"),
            data=data.get("data"),
            name=data.get("name"),
            output_dir=data.get("output_dir"),
            project_owner=data.get("project_owner"),
            project_slug=data.get("project_slug"),
            figure_name=data.get("figure_name"),
            panel_label=data.get("panel_label"),
            user=request.user,
            gallery_category=data.get("gallery_category"),
            gallery_plot_name=data.get("gallery_plot_name"),
        )
        bundle_path = result.get("bundle_path", result.get("path", ""))
        return JsonResponse(
            {
                "success": True,
                "bundle_path": bundle_path,
                "directory_path": result.get("directory_path"),
                "preview_url": f"/vis/api/bundles/pltz/preview/?path={bundle_path}",
                "hitmap_url": f"/vis/api/bundles/pltz/preview/?path={bundle_path}&type=hitmap",
                "spec": result.get("spec"),
                "style": result.get("style"),
                "geometry": result.get("geometry"),
            },
            status=201,
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Failed to create pltz from plot: {e}")
        return JsonResponse({"error": str(e)}, status=500)
