#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical analysis API views — advanced endpoints.

Effect size, post-hoc, power analysis, p-value correction, and flowchart.
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
    "stats_effect_size",
    "stats_posthoc",
    "stats_power",
    "stats_correct",
    "stats_flowchart",
]


def _parse_body(request) -> dict:
    """Parse request body — JSON or multipart CSV upload."""
    ct = request.content_type or ""
    if ct.startswith("multipart/"):
        return api_stats_helpers.parse_csv_body(request)
    return json.loads(request.body)


@csrf_exempt
@require_POST
def stats_effect_size(request) -> JsonResponse:
    """Calculate effect size measures.

    Accepts JSON body or multipart CSV with column names.
    """
    try:
        body = _parse_body(request)
        measure = body.get("measure")

        if not measure:
            return JsonResponse(
                {"success": False, "error": "measure is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        result = api_stats_helpers.run_effect_size(body)
        return JsonResponse({"success": True, "result": result})

    except ValueError as e:
        logger.warning(f"Invalid input for stats_effect_size: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_effect_size: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_posthoc(request) -> JsonResponse:
    """Run post-hoc pairwise comparisons.

    Accepts JSON body or multipart CSV with column names.
    """
    try:
        body = _parse_body(request)
        method = body.get("method")

        if not method:
            return JsonResponse(
                {"success": False, "error": "method is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        result = api_stats_helpers.run_posthoc(body)
        return JsonResponse({"success": True, "result": result})

    except ValueError as e:
        logger.warning(f"Invalid input for stats_posthoc: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_posthoc: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_power(request) -> JsonResponse:
    """Run power analysis for sample size or power calculation.

    JSON-only — no CSV needed (parameter-based, no data arrays).
    """
    try:
        body = json.loads(request.body)
        effect_size = body.get("effect_size")

        if not effect_size:
            return JsonResponse(
                {"success": False, "error": "effect_size is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        result = api_stats_helpers.run_power_analysis(body)
        return JsonResponse({"success": True, "result": result})

    except ValueError as e:
        logger.warning(f"Invalid input for stats_power: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_power: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_correct(request) -> JsonResponse:
    """Apply multiple comparison correction to p-values.

    Accepts JSON body or multipart CSV with pvalues_col.
    """
    try:
        body = _parse_body(request)
        method = body.get("method")
        pvalues = body.get("pvalues")

        if not method:
            return JsonResponse(
                {"success": False, "error": "method is required"}, status=400
            )
        if not pvalues:
            return JsonResponse(
                {"success": False, "error": "pvalues is required"}, status=400
            )

        try:
            import scitex as stx  # noqa: F401
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        result = api_stats_helpers.run_correction(body)
        return JsonResponse({"success": True, "result": result})

    except ValueError as e:
        logger.warning(f"Invalid input for stats_correct: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_correct: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def stats_flowchart(request):
    """Return statistical test decision flowchart as Mermaid text or JSON.

    GET parameters:
        format: "mermaid" (default), "json", or "svg"
    """
    try:
        from scitex.stats.auto import (
            get_decision_tree,
            render_flowchart_mermaid,
            render_flowchart_svg,
        )
    except ImportError as e:
        logger.error(f"Failed to import scitex: {e}")
        return JsonResponse(
            {"success": False, "error": "scitex package not available"}, status=503
        )

    try:
        fmt = request.GET.get("format", "mermaid")
        if fmt == "json":
            return JsonResponse({"success": True, "tree": get_decision_tree()})
        if fmt == "svg":
            svg = render_flowchart_svg()
            return HttpResponse(svg, content_type="image/svg+xml")
        mermaid_text = render_flowchart_mermaid()
        return HttpResponse(mermaid_text, content_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"Error in stats_flowchart: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
