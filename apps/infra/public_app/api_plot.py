#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public Plot API views.

GET  /api/plot/ — Quick plot from URL query parameters (browser-friendly).
POST /api/plot/ — Full figrecipe spec as JSON body (programmatic).
"""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from . import api_plot_helpers

logger = logging.getLogger("scitex")

__all__ = ["plot_endpoint"]


@csrf_exempt
def plot_endpoint(request):
    """Public plot API — GET for browser URLs, POST for full specs."""
    if request.method == "GET":
        return _handle_get(request)
    elif request.method == "POST":
        return _handle_post(request)
    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


def _handle_get(request):
    """GET /api/plot/?kind=line&x=1,2,3&y=1,4,9 — returns raw PNG."""
    try:
        try:
            import figrecipe  # noqa: F401
        except ImportError:
            return JsonResponse(
                {"success": False, "error": "figrecipe package not available"},
                status=503,
            )

        spec = api_plot_helpers.build_spec_from_query(request.GET)
        png_bytes = api_plot_helpers.render_figure(spec)
        return HttpResponse(png_bytes, content_type="image/png")

    except ValueError as e:
        logger.warning(f"Invalid input for plot GET: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in plot GET: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _handle_post(request):
    """POST /api/plot/ — accepts JSON spec or multipart CSV upload.

    JSON: Returns JSON with figure_base64, or raw PNG if figure_format="png".
    CSV:  Returns raw PNG from CSV columns + plot parameters.
    """
    content_type = request.content_type or ""
    if content_type.startswith("multipart/form-data"):
        return _handle_csv_post(request)
    return _handle_json_post(request)


def _handle_json_post(request):
    """POST with application/json — full figrecipe spec."""
    import base64

    try:
        try:
            import figrecipe  # noqa: F401
        except ImportError:
            return JsonResponse(
                {"success": False, "error": "figrecipe package not available"},
                status=503,
            )

        spec = json.loads(request.body)
        figure_format = spec.pop("figure_format", "").lower()

        png_bytes = api_plot_helpers.render_figure(spec)

        if figure_format == "png":
            return HttpResponse(png_bytes, content_type="image/png")

        b64 = base64.b64encode(png_bytes).decode("utf-8")
        return JsonResponse({"success": True, "figure_base64": b64})

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body"}, status=400
        )
    except ValueError as e:
        logger.warning(f"Invalid input for plot POST: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in plot POST: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _handle_csv_post(request):
    """POST with multipart/form-data — CSV file + column names.

    Form fields:
        csv_file: uploaded CSV/TSV file
        kind: plot type (line, scatter, bar, etc.)
        x_col: column name for x-axis
        y_col: column name for y-axis
        data_col: column name for distribution data (hist, box, violin)
        labels_col: column name for labels
        color, title, xlabel, ylabel: optional styling
    """
    from .api_csv_helpers import cleanup_csv_temp, parse_csv_upload

    csv_path = None
    try:
        try:
            import figrecipe  # noqa: F401
        except ImportError:
            return JsonResponse(
                {"success": False, "error": "figrecipe package not available"},
                status=503,
            )

        csv_path, params = parse_csv_upload(request)
        spec = api_plot_helpers.build_spec_from_csv(csv_path, params)
        png_bytes = api_plot_helpers.render_figure(spec)
        return HttpResponse(png_bytes, content_type="image/png")

    except ValueError as e:
        logger.warning(f"Invalid input for plot CSV: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in plot CSV: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    finally:
        if csv_path:
            cleanup_csv_temp(csv_path)


# EOF
