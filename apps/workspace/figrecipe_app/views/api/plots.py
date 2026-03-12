"""
Scientific Figure Editor - Plot Rendering API Views
REST API endpoints for backend plot rendering using matplotlib/scitex.plt
"""

import json
import logging
import traceback

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from apps.workspace.figrecipe_app.plot_renderer import render_plot_from_spec
from ...services.plots_service import PlotsService

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@csrf_exempt
def render_plot(request):
    """
    Render a scientific plot from JSON specification.

    POST /api/vis/plot/

    Request body (JSON):
    {
      "figure": {"width_mm": 35, "height_mm": 24.5, "dpi": 300},
      "style": {"tick_length_mm": 0.8, ...},
      "plot": {"kind": "line", "csv_path": "...", ...}
    }

    Response:
    - Success: SVG image (Content-Type: image/svg+xml)
    - Error: JSON with error details
    """
    try:
        spec = json.loads(request.body)

        # Validate required fields
        if "figure" not in spec:
            return JsonResponse(
                {"error": "Missing required field: figure is required"}, status=400
            )

        if "plot" not in spec and "panels" not in spec:
            return JsonResponse(
                {"error": "Missing required field: either plot or panels is required"},
                status=400,
            )

        # Render plot using matplotlib backend
        svg_buffer = render_plot_from_spec(spec)

        # Return SVG
        return HttpResponse(svg_buffer.getvalue(), content_type="image/svg+xml")

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def render_gallery_plot(request):
    """
    Render a plot from gallery template with CSV data.

    POST /vis/api/plot/gallery/

    Request body (JSON):
    {
        "plot_type": "plot",           # e.g., plot, scatter, bar, hist
        "category": "line",            # e.g., line, scatter, categorical
        "csv_data": [[...], ...],      # 2D array of data
        "overrides": {                 # Optional style overrides
            "title": "My Plot",
            "xlabel": "X",
            "ylabel": "Y",
            "linewidth": 1.0,
            ...
        }
    }

    Response (success):
    {
        "success": true,
        "image": "data:image/png;base64,...",
        "width": 800,
        "height": 600
    }
    """
    try:
        data = json.loads(request.body)
        plot_type = data.get("plot_type", "plot")
        category = data.get("category", "line")
        csv_data = data.get("csv_data", [])
        overrides = data.get("overrides", {})

        # Render plot using service
        result = PlotsService.render_gallery_plot(
            plot_type=plot_type,
            category=category,
            csv_data=csv_data,
            overrides=overrides,
        )

        return JsonResponse(result)

    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    except ImportError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    except Exception as e:
        logger.error(f"render_gallery_plot error: {e}\n{traceback.format_exc()}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def upload_plot_data(request):
    """
    Upload CSV or Excel file for plot rendering.

    POST /api/vis/upload-plot-data/

    Request: multipart/form-data with 'file' field

    Response:
    - Success: JSON with file_path
    - Error: JSON with error details
    """
    try:
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        uploaded_file = request.FILES["file"]

        # Save file using service
        result = PlotsService.save_uploaded_file(uploaded_file)

        return JsonResponse(result)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse({"error": f"Upload failed: {str(e)}"}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def extract_image_metadata(request):
    """
    Extract scitex metadata embedded in a PNG image.

    POST /vis/api/plot/metadata/

    Request body (JSON):
    {
        "image": "data:image/png;base64,..." or base64 string
    }

    Response (success):
    {
        "success": true,
        "has_metadata": true,
        "metadata": {...},
        "axes_bbox_px": {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    }
    """
    try:
        data = json.loads(request.body)
        image_data = data.get("image", "")

        # Extract metadata using service
        result = PlotsService.extract_image_metadata_from_base64(image_data)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )

    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    except Exception as e:
        logger.error(f"extract_image_metadata error: {e}\n{traceback.format_exc()}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
