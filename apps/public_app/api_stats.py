#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical analysis API views.

Provides backend functionality for the Statistics Calculator tool using scitex.stats.
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import api_stats_helpers

# Django views use standard logging, not @stx.session injection
logger = logging.getLogger("scitex")  # noqa: STX-I007

__all__ = [
    "stats_calculate",
    "stats_recommend",
    "stats_describe",
    "stats_effect_size",
    "stats_posthoc",
    "stats_power",
    "stats_correct",
]


@csrf_exempt
@require_POST
def stats_calculate(request) -> JsonResponse:
    """
    Run statistical test via scitex.stats backend.

    Expected POST body:
    {
        "test_name": str,  # e.g., "ttest", "anova", "mann_whitney"
        "data": list,      # Single array for one-sample tests
        "data2": list,     # Optional second array for two-sample tests
        "groups": list,    # Optional list of arrays for multi-group tests
        "alternative": str # "two-sided" (default), "less", "greater"
    }

    Returns:
    {
        "success": bool,
        "result": dict,    # Test results with statistics, p-values, effect sizes
        "formatted": str   # APA-style formatted result string
    }
    """
    try:
        body = json.loads(request.body)
        test_name = body.get("test_name")

        if not test_name:
            return JsonResponse(
                {"success": False, "error": "test_name is required"}, status=400
            )

        # Import scitex stats module
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

        # Delegate to helper
        result = api_stats_helpers.run_statistical_test(body)

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


@csrf_exempt
@require_POST
def stats_describe(request) -> JsonResponse:
    """
    Calculate descriptive statistics.

    Expected POST body:
    {
        "data": list,          # Array of numbers
        "percentiles": list    # Optional, e.g., [25, 50, 75]
    }

    Returns:
    {
        "success": bool,
        "result": dict  # Contains mean, std, median, quartiles, etc.
    }
    """
    try:
        body = json.loads(request.body)
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

        # Delegate to helper
        result = api_stats_helpers.run_descriptive(body)

        return JsonResponse({"success": True, "result": result})

    except Exception as e:
        logger.error(f"Error in stats_describe: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_recommend(request) -> JsonResponse:
    """
    Recommend statistical tests based on data characteristics.

    Expected POST body:
    {
        "n_groups": int,              # Number of groups to compare
        "sample_sizes": list,         # Optional list of sample sizes
        "outcome_type": str,          # "continuous" or "categorical"
        "design": str,                # "between" or "within"
        "paired": bool,               # Whether samples are paired
        "has_control_group": bool,    # Whether there's a control group
        "top_k": int                  # Number of recommendations to return (default: 3)
    }

    Returns:
    {
        "success": bool,
        "recommendations": list  # List of recommended tests with rationale
    }
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

        # Delegate to helper
        result = api_stats_helpers.run_recommend(body)

        return JsonResponse(
            {"success": True, "recommendations": result["recommendations"]}
        )

    except Exception as e:
        logger.error(f"Error in stats_recommend: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def stats_effect_size(request) -> JsonResponse:
    """
    Calculate effect size measures.

    Expected POST body:
    {
        "measure": str,       # "cohens_d", "eta_squared", "epsilon_squared", "cliffs_delta", "prob_superiority"
        "group1": list,       # First group data
        "group2": list,       # Optional second group data
        "groups": list,       # Optional list of groups for multi-group measures
        "paired": bool        # Whether samples are paired (for Cohen's d)
    }

    Returns:
    {
        "success": bool,
        "result": dict  # Contains measure name, value, and interpretation
    }
    """
    try:
        body = json.loads(request.body)
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

        # Delegate to helper
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
    """
    Run post-hoc pairwise comparisons.

    Expected POST body:
    {
        "method": str,        # "tukey", "games_howell", "dunnett"
        "groups": list,       # List of group arrays
        "group_names": list,  # Optional list of group names
        "alpha": float        # Significance level (default: 0.05)
    }

    Returns:
    {
        "success": bool,
        "result": dict  # Contains method and list of comparisons
    }
    """
    try:
        body = json.loads(request.body)
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

        # Delegate to helper
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
    """
    Run power analysis for sample size or power calculation.

    Expected POST body:
    {
        "effect_size": float,  # Required
        "n": int,              # Optional - provide to calculate power
        "alpha": float,        # Significance level (default: 0.05)
        "power": float,        # Desired power (default: 0.8) - used when n not provided
        "test_type": str       # "one-sample", "two-sample" (default), "paired"
    }

    Returns:
    {
        "success": bool,
        "result": dict  # Contains power and n (or n_required)
    }
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

        # Delegate to helper
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
    """
    Apply multiple comparison correction to p-values.

    Expected POST body:
    {
        "method": str,      # "bonferroni", "fdr", "holm", "sidak"
        "pvalues": list,    # List of p-values
        "alpha": float      # Significance level (default: 0.05)
    }

    Returns:
    {
        "success": bool,
        "result": dict  # Contains method, corrected p-values, and alpha
    }
    """
    try:
        body = json.loads(request.body)
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

        # Delegate to helper
        result = api_stats_helpers.run_correction(body)

        return JsonResponse({"success": True, "result": result})

    except ValueError as e:
        logger.warning(f"Invalid input for stats_correct: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in stats_correct: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
