#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical analysis API views — core endpoints.

Calculate, plot, describe, and recommend.
Advanced endpoints (effect_size, posthoc, power, correct, flowchart)
are in api_stats_advanced.py.
"""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import api_stats_helpers

# Django views use standard logging, not @stx.session injection
logger = logging.getLogger("scitex")  # noqa: STX-I007

__all__ = [
    "stats_calculate",
    "stats_plot",
    "stats_describe",
    "stats_recommend",
]


def _parse_body(request) -> dict:
    """Parse request body — JSON or multipart CSV upload."""
    ct = request.content_type or ""
    if ct.startswith("multipart/"):
        return api_stats_helpers.parse_csv_body(request)
    return json.loads(request.body)


@csrf_exempt
@require_POST
def stats_calculate(request) -> JsonResponse:
    """Run statistical test via scitex.stats backend.

    Accepts JSON body or multipart CSV with column names.
    """
    try:
        body = _parse_body(request)
        test_name = body.get("test_name")

        if not test_name:
            return JsonResponse(
                {"success": False, "error": "test_name is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "scitex package not available",
                    "fallback": True,
                },
                status=503,
            )

        result = api_stats_helpers.run_statistical_test(body)

        # Return raw PNG if requested
        figure_format = body.get("figure_format", "").lower()
        if figure_format == "png" and result.get("figure_base64"):
            import base64

            png_bytes = base64.b64decode(result["figure_base64"])
            return HttpResponse(png_bytes, content_type="image/png")

        return JsonResponse(
            {
                "success": True,
                "result": result,
                "formatted": result.get("formatted", ""),
            }
        )

    except ValueError as e:
        logger.warning(f"Invalid input for stats_calculate: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_calculate: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def stats_plot(request):
    """GET endpoint returning a PNG figure for a statistical test.

    Designed for non-technical users — just paste the URL in a browser.

    Query parameters:
        test_name: str   - e.g., "ttest_ind", "anova", "mann_whitney"
        data: str        - Comma-separated numbers (e.g., "1,2,3,4,5")
        data2: str       - Optional second group (e.g., "2,3,4,5,6")
        alternative: str - "two-sided" (default), "less", "greater"

    Example:
        /api/stats/plot/?test_name=ttest_ind&data=1,2,3,4,5&data2=2,3,4,5,6
    """
    import base64

    try:
        test_name = request.GET.get("test_name")
        if not test_name:
            return JsonResponse(
                {"success": False, "error": "test_name is required"}, status=400
            )

        data_str = request.GET.get("data", "")
        if not data_str:
            return JsonResponse(
                {"success": False, "error": "data is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        body = {
            "test_name": test_name,
            "data": [float(x.strip()) for x in data_str.split(",")],
            "plot": True,
            "alternative": request.GET.get("alternative", "two-sided"),
        }

        data2_str = request.GET.get("data2", "")
        if data2_str:
            body["data2"] = [float(x.strip()) for x in data2_str.split(",")]

        result = api_stats_helpers.run_statistical_test(body)

        if result.get("figure_base64"):
            png_bytes = base64.b64decode(result["figure_base64"])
            return HttpResponse(png_bytes, content_type="image/png")

        return JsonResponse(
            {"success": False, "error": "No figure generated"}, status=500
        )

    except ValueError as e:
        logger.warning(f"Invalid input for stats_plot: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_plot: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_describe(request) -> JsonResponse:
    """Calculate descriptive statistics.

    Accepts JSON body or multipart CSV with data_col.
    """
    try:
        body = _parse_body(request)
        data = body.get("data", [])

        if not data:
            return JsonResponse(
                {"success": False, "error": "data is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "scitex package not available",
                    "fallback": True,
                },
                status=503,
            )

        result = api_stats_helpers.run_descriptive(body)
        return JsonResponse({"success": True, "result": result})

    except Exception as e:
        logger.error(f"Error in stats_describe: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_recommend(request) -> JsonResponse:
    """Recommend statistical tests based on data characteristics.

    JSON-only — no CSV needed (parameter-based, no data arrays).
    """
    try:
        body = json.loads(request.body)

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        result = api_stats_helpers.run_recommend(body)

        return JsonResponse(
            {"success": True, "recommendations": result["recommendations"]}
        )

    except Exception as e:
        logger.error(f"Error in stats_recommend: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
