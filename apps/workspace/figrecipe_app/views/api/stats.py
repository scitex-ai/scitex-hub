"""
Statistical Testing API for SciTeX Vis.

This module provides API endpoints for the "magic" statistical testing feature:
- Get applicable tests for a given context (right-click menu)
- Get recommended tests
- Run statistical tests and return results with stars/brackets
- Build StatContext from plot metadata

The vision: "When users draw plots, statistical tests automatically run
and significance markers (stars) appear."
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ...services.stats_service import StatsService

logger = logging.getLogger(__name__)


@require_POST
@csrf_exempt
def get_applicable_tests(request) -> JsonResponse:
    """
    Get menu items for right-click context menu.

    Returns all tests with enabled/disabled status and tooltips
    explaining why each test is or isn't applicable.

    Request body:
    {
        "n_groups": 2,
        "sample_sizes": [30, 32],
        "outcome_type": "continuous",
        "design": "between",
        "paired": false,
        "has_control_group": false,
        "n_factors": 1,
        "normality_ok": null,
        "variance_homogeneity_ok": null,
        "include_families": ["parametric", "nonparametric"],
        "exclude_families": ["normality"]
    }

    Response:
    {
        "success": true,
        "items": [...],
        "recommended": ["brunner_munzel", "ttest_ind", "mannwhitneyu"]
    }
    """
    if not StatsService.is_scitex_stats_available():
        return JsonResponse(
            {"success": False, "error": "scitex.stats module not available"},
            status=500,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    # Build StatContext from request
    try:
        ctx = StatsService.build_stat_context(data)
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    # Get menu items
    include_families = data.get("include_families")
    exclude_families = data.get("exclude_families")

    result = StatsService.get_applicable_tests_menu(
        ctx,
        include_families=include_families,
        exclude_families=exclude_families,
    )

    return JsonResponse(
        {
            "success": True,
            **result,
        }
    )


@require_POST
@csrf_exempt
def run_statistical_test(request) -> JsonResponse:
    """
    Run a statistical test on provided data.

    Request body:
    {
        "test_name": "brunner_munzel",
        "groups": [
            {"name": "Control", "values": [1.2, 2.3, ...]},
            {"name": "Treatment", "values": [3.4, 4.5, ...]}
        ],
        "paired": false,
        "correction_method": "fdr_bh"
    }

    Response:
    {
        "success": true,
        "result": {
            "test_name": "brunner_munzel",
            "stat": 2.34,
            "p_raw": 0.023,
            "p_adj": 0.023,
            "stars": "*",
            "effect_size": {"name": "cliffs_delta", "value": 0.45},
            "summary": [...],
            "formatted": "BM = 2.34, p = 0.023, delta = 0.45"
        },
        "annotation": {
            "type": "stat_bracket",
            "groups": ["Control", "Treatment"],
            "stars": "*",
            "p_value": 0.023,
            ...
        }
    }
    """
    if not StatsService.is_scitex_stats_available():
        return JsonResponse(
            {"success": False, "error": "scitex.stats module not available"},
            status=500,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    test_name = data.get("test_name")
    groups_data = data.get("groups", [])
    paired = data.get("paired", False)
    correction_method = data.get("correction_method")

    if not test_name:
        return JsonResponse(
            {"success": False, "error": "test_name is required"}, status=400
        )

    # Run test using service
    try:
        result = StatsService.run_statistical_test_with_context(
            test_name=test_name,
            groups_data=groups_data,
            paired=paired,
            correction_method=correction_method,
        )
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Statistical test error: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse(
        {
            "success": True,
            **result,
        }
    )


@require_POST
@csrf_exempt
def run_all_applicable(request) -> JsonResponse:
    """
    Run all applicable statistical tests on provided data.

    Request body:
    {
        "groups": [
            {"name": "Control", "values": [1.2, 2.3, ...]},
            {"name": "Treatment", "values": [3.4, 4.5, ...]}
        ],
        "correction_method": "fdr_bh",
        "max_tests": 5
    }

    Response:
    {
        "success": true,
        "results": [
            {
                "result": {...},
                "annotation": {...}
            },
            ...
        ]
    }
    """
    if not StatsService.is_scitex_stats_available():
        return JsonResponse(
            {"success": False, "error": "scitex.stats module not available"},
            status=500,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    groups_data = data.get("groups", [])
    correction_method = data.get("correction_method", "fdr_bh")
    max_tests = data.get("max_tests", 5)

    if len(groups_data) < 2:
        return JsonResponse(
            {"success": False, "error": "At least 2 groups required"},
            status=400,
        )

    # Run all applicable tests
    try:
        results = StatsService.run_all_applicable_tests(
            groups_data=groups_data,
            correction_method=correction_method,
            max_tests=max_tests,
        )
    except Exception as e:
        logger.error(f"Run all applicable tests error: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse(
        {
            "success": True,
            "results": results,
        }
    )


@require_POST
@csrf_exempt
def build_context_from_plot(request) -> JsonResponse:
    """
    Build StatContext from plot metadata and CSV data.

    Request body:
    {
        "element_bboxes": {...},
        "column_mapping": {"line_0": "Group_A", ...},
        "csv_data": [[...], ...]
    }

    Response:
    {
        "success": true,
        "context": {
            "n_groups": 2,
            "sample_sizes": [30, 32],
            "outcome_type": "continuous",
            ...
        },
        "recommended_tests": ["brunner_munzel", "ttest_ind"],
        "effect_sizes": ["cliffs_delta", "cohens_d"]
    }
    """
    if not StatsService.is_scitex_stats_available():
        return JsonResponse(
            {"success": False, "error": "scitex.stats module not available"},
            status=500,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    element_bboxes = data.get("element_bboxes", {})
    column_mapping = data.get("column_mapping", {})
    csv_data = data.get("csv_data", [])

    # Build context from plot metadata
    ctx = StatsService.build_context_from_plot_metadata(
        element_bboxes=element_bboxes,
        column_mapping=column_mapping,
        csv_data=csv_data,
    )

    if ctx is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Could not infer statistical context from plot",
            },
            status=400,
        )

    # Get recommendations
    from scitex.stats import recommend_tests, recommend_effect_sizes

    recommended_tests = recommend_tests(ctx, top_k=3)
    effect_sizes = recommend_effect_sizes(ctx, top_k=2)

    return JsonResponse(
        {
            "success": True,
            "context": ctx.to_dict(),
            "recommended_tests": recommended_tests,
            "effect_sizes": effect_sizes,
        }
    )
