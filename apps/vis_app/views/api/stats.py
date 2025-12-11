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
from typing import Any, Dict, List, Optional

import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

# Import from scitex.stats
try:
    from scitex.stats import (
        StatContext,
        StatResult,
        TEST_RULES,
        check_applicable,
        get_menu_items,
        p_to_stars,
        recommend_effect_sizes,
        recommend_posthoc,
        recommend_tests,
    )
    from scitex.stats.auto import (
        apply_multiple_correction,
        compute_summary_from_groups,
        format_for_inspector,
        format_test_line,
    )

    SCITEX_STATS_AVAILABLE = True
except ImportError:
    SCITEX_STATS_AVAILABLE = False

logger = logging.getLogger(__name__)


def _check_scitex_available() -> Optional[JsonResponse]:
    """Check if scitex.stats is available."""
    if not SCITEX_STATS_AVAILABLE:
        return JsonResponse(
            {
                "success": False,
                "error": "scitex.stats module not available",
            },
            status=500,
        )
    return None


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
        "items": [
            {
                "id": "brunner_munzel",
                "label": "Brunner-Munzel test (recommended)",
                "family": "nonparametric",
                "enabled": true,
                "tooltip": null,
                "priority": 110
            },
            ...
        ],
        "recommended": ["brunner_munzel", "ttest_ind", "mannwhitneyu"]
    }
    """
    if err := _check_scitex_available():
        return err

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON"}, status=400
        )

    # Build StatContext from request
    try:
        ctx = StatContext(
            n_groups=data.get("n_groups", 2),
            sample_sizes=data.get("sample_sizes", [10, 10]),
            outcome_type=data.get("outcome_type", "continuous"),
            design=data.get("design", "between"),
            paired=data.get("paired"),
            has_control_group=data.get("has_control_group", False),
            n_factors=data.get("n_factors", 1),
            normality_ok=data.get("normality_ok"),
            variance_homogeneity_ok=data.get("variance_homogeneity_ok"),
            group_names=data.get("group_names"),
            control_group_name=data.get("control_group_name"),
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Invalid context: {str(e)}"},
            status=400,
        )

    # Get menu items
    include_families = data.get("include_families")
    exclude_families = data.get("exclude_families")

    items = get_menu_items(
        ctx,
        include_families=include_families,
        exclude_families=exclude_families,
    )

    # Get recommendations
    recommended = recommend_tests(ctx, top_k=3)
    effect_sizes = recommend_effect_sizes(ctx, top_k=2)
    posthoc = recommend_posthoc(ctx, top_k=2) if ctx.n_groups >= 3 else []

    return JsonResponse(
        {
            "success": True,
            "items": items,
            "recommended": recommended,
            "effect_sizes": effect_sizes,
            "posthoc": posthoc,
            "context": ctx.to_dict(),
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
    if err := _check_scitex_available():
        return err

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON"}, status=400
        )

    test_name = data.get("test_name")
    groups_data = data.get("groups", [])
    paired = data.get("paired", False)
    correction_method = data.get("correction_method")

    if not test_name:
        return JsonResponse(
            {"success": False, "error": "test_name is required"}, status=400
        )

    if len(groups_data) < 2:
        return JsonResponse(
            {"success": False, "error": "At least 2 groups required"},
            status=400,
        )

    # Extract group names and values
    group_names = [g.get("name", f"Group_{i+1}") for i, g in enumerate(groups_data)]
    group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]

    # Compute summary statistics
    summary = compute_summary_from_groups(group_values, group_names)

    # Run the test
    result = _run_test(test_name, group_values, paired=paired)

    if result is None:
        return JsonResponse(
            {"success": False, "error": f"Test {test_name} not implemented"},
            status=400,
        )

    # Apply correction if needed
    if correction_method:
        results = apply_multiple_correction([result], method=correction_method)
        result = results[0]

    # Get stars
    p_value = result.get("p_adj") or result.get("p_raw")
    stars = p_to_stars(p_value)

    # Compute effect size
    effect_size = _compute_effect_size(test_name, group_values, paired=paired)

    # Format for display
    formatted = format_test_line(
        result,
        effects=[effect_size] if effect_size else None,
        summary=summary,
        style="plain",
        include_n=True,
    )

    # Build annotation object for canvas
    annotation = {
        "type": "stat_bracket",
        "groups": group_names,
        "stars": stars,
        "p_value": p_value,
        "test_name": test_name,
        "effect_size": effect_size,
        "formatted": formatted,
        "bracket_style": {
            "line_width": 1.0,
            "bracket_height": 5.0,
            "star_offset": 3.0,
        },
    }

    return JsonResponse(
        {
            "success": True,
            "result": {
                "test_name": test_name,
                "stat": result.get("stat"),
                "df": result.get("df"),
                "p_raw": result.get("p_raw"),
                "p_adj": result.get("p_adj"),
                "stars": stars,
                "effect_size": effect_size,
                "summary": summary,
                "formatted": formatted,
            },
            "annotation": annotation,
        }
    )


@require_POST
@csrf_exempt
def run_all_applicable(request) -> JsonResponse:
    """
    Run all applicable tests in parallel and return results.

    This is the "magic" mode: run every applicable test and show
    results in the Stats Inspector panel.

    Request body:
    {
        "groups": [...],
        "outcome_type": "continuous",
        "design": "between",
        "paired": false,
        "correction_method": "fdr_bh",
        "include_effect_sizes": true
    }

    Response:
    {
        "success": true,
        "results": {
            "tests": [...],
            "effects": [...],
            "recommended": "brunner_munzel"
        },
        "inspector_data": {...}
    }
    """
    if err := _check_scitex_available():
        return err

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON"}, status=400
        )

    groups_data = data.get("groups", [])
    outcome_type = data.get("outcome_type", "continuous")
    design = data.get("design", "between")
    paired = data.get("paired", False)
    correction_method = data.get("correction_method", "fdr_bh")
    include_effect_sizes = data.get("include_effect_sizes", True)

    if len(groups_data) < 2:
        return JsonResponse(
            {"success": False, "error": "At least 2 groups required"},
            status=400,
        )

    # Extract data
    group_names = [g.get("name", f"Group_{i+1}") for i, g in enumerate(groups_data)]
    group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]
    sample_sizes = [len(v) for v in group_values]

    # Build context
    ctx = StatContext(
        n_groups=len(group_values),
        sample_sizes=sample_sizes,
        outcome_type=outcome_type,
        design=design,
        paired=paired,
        has_control_group=data.get("has_control_group", False),
        n_factors=data.get("n_factors", 1),
        group_names=group_names,
    )

    # Get recommended tests
    recommended = recommend_tests(ctx, top_k=5)

    # Run all recommended tests
    test_results = []
    for test_name in recommended:
        result = _run_test(test_name, group_values, paired=paired)
        if result:
            test_results.append(result)

    # Apply correction
    if correction_method and test_results:
        test_results = apply_multiple_correction(
            test_results, method=correction_method
        )

    # Compute effect sizes if requested
    effect_results = []
    if include_effect_sizes:
        recommended_effects = recommend_effect_sizes(ctx, top_k=3)
        for effect_name in recommended_effects:
            effect = _compute_effect_size(
                effect_name, group_values, paired=paired
            )
            if effect:
                effect_results.append(effect)

    # Format for inspector panel
    inspector_data = format_for_inspector(test_results, effect_results)

    # Get top recommendation
    top_recommendation = recommended[0] if recommended else None

    return JsonResponse(
        {
            "success": True,
            "results": {
                "tests": test_results,
                "effects": effect_results,
                "recommended": top_recommendation,
            },
            "inspector_data": inspector_data,
            "context": ctx.to_dict(),
        }
    )


@require_POST
@csrf_exempt
def build_context_from_plot(request) -> JsonResponse:
    """
    Build StatContext from plot metadata.

    Extracts group information from plot data (e.g., boxplot groups)
    and returns the context for test selection.

    Request body:
    {
        "plot_type": "boxplot",
        "data": {
            "groups": [
                {"name": "A", "values": [...]},
                {"name": "B", "values": [...]}
            ]
        },
        "metadata": {
            "design": "between",
            "has_control_group": false
        }
    }

    Response:
    {
        "success": true,
        "context": {...},
        "applicable_tests": [...],
        "recommended": [...]
    }
    """
    if err := _check_scitex_available():
        return err

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON"}, status=400
        )

    plot_type = data.get("plot_type", "boxplot")
    plot_data = data.get("data", {})
    metadata = data.get("metadata", {})

    # Extract groups from plot data
    groups_data = plot_data.get("groups", [])

    if not groups_data:
        return JsonResponse(
            {"success": False, "error": "No groups found in plot data"},
            status=400,
        )

    group_names = [g.get("name", f"Group_{i+1}") for i, g in enumerate(groups_data)]
    group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]
    sample_sizes = [len(v) for v in group_values]

    # Infer outcome type from data
    outcome_type = _infer_outcome_type(group_values)

    # Build context
    ctx = StatContext(
        n_groups=len(group_values),
        sample_sizes=sample_sizes,
        outcome_type=outcome_type,
        design=metadata.get("design", "between"),
        paired=metadata.get("paired"),
        has_control_group=metadata.get("has_control_group", False),
        n_factors=metadata.get("n_factors", 1),
        group_names=group_names,
        control_group_name=metadata.get("control_group_name"),
    )

    # Get applicable tests
    items = get_menu_items(ctx)
    recommended = recommend_tests(ctx, top_k=3)

    return JsonResponse(
        {
            "success": True,
            "context": ctx.to_dict(),
            "applicable_tests": items,
            "recommended": recommended,
            "summary": compute_summary_from_groups(group_values, group_names),
        }
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _run_test(
    test_name: str,
    groups: List[np.ndarray],
    paired: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Run a specific statistical test.

    Returns a TestResultDict or None if test not implemented.
    """
    try:
        from scipy import stats
    except ImportError:
        logger.warning("scipy not available for statistical tests")
        return None

    if len(groups) < 2:
        return None

    g1, g2 = groups[0], groups[1]

    # Filter NaN
    g1 = g1[~np.isnan(g1)]
    g2 = g2[~np.isnan(g2)]

    result: Dict[str, Any] = {"test_name": test_name}

    try:
        if test_name == "ttest_ind":
            stat, p = stats.ttest_ind(g1, g2, equal_var=False)  # Welch
            result.update({"stat": float(stat), "p_raw": float(p), "df": None})

        elif test_name == "ttest_rel":
            if len(g1) != len(g2):
                return None
            stat, p = stats.ttest_rel(g1, g2)
            result.update({"stat": float(stat), "p_raw": float(p), "df": len(g1) - 1})

        elif test_name == "mannwhitneyu":
            stat, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
            result.update({"stat": float(stat), "p_raw": float(p)})

        elif test_name == "wilcoxon":
            if len(g1) != len(g2):
                return None
            stat, p = stats.wilcoxon(g1, g2)
            result.update({"stat": float(stat), "p_raw": float(p)})

        elif test_name == "brunner_munzel":
            stat, p = stats.brunnermunzel(g1, g2)
            result.update({"stat": float(stat), "p_raw": float(p)})

        elif test_name == "kruskal":
            stat, p = stats.kruskal(*groups)
            result.update({"stat": float(stat), "p_raw": float(p)})

        elif test_name == "anova_oneway":
            stat, p = stats.f_oneway(*groups)
            result.update({"stat": float(stat), "p_raw": float(p)})

        else:
            # Test not implemented
            return None

    except Exception as e:
        logger.warning(f"Error running test {test_name}: {e}")
        return None

    return result


def _compute_effect_size(
    effect_name: str,
    groups: List[np.ndarray],
    paired: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Compute effect size for the given groups.
    """
    if len(groups) < 2:
        return None

    g1, g2 = groups[0], groups[1]
    g1 = g1[~np.isnan(g1)]
    g2 = g2[~np.isnan(g2)]

    try:
        if effect_name in ("cohens_d_ind", "cohens_d_paired", "hedges_g"):
            # Cohen's d
            pooled_std = np.sqrt(
                ((len(g1) - 1) * np.var(g1, ddof=1) +
                 (len(g2) - 1) * np.var(g2, ddof=1)) /
                (len(g1) + len(g2) - 2)
            )
            if pooled_std == 0:
                return None
            d = (np.mean(g1) - np.mean(g2)) / pooled_std

            # Apply Hedges' correction if requested
            if effect_name == "hedges_g":
                n = len(g1) + len(g2)
                d = d * (1 - 3 / (4 * n - 9))

            return {
                "name": effect_name,
                "label": "Cohen's d" if "cohens" in effect_name else "Hedges' g",
                "value": float(d),
                "note": _interpret_cohens_d(abs(d)),
            }

        elif effect_name == "cliffs_delta":
            # Cliff's delta
            count = 0
            for x in g1:
                for y in g2:
                    if x > y:
                        count += 1
                    elif x < y:
                        count -= 1
            delta = count / (len(g1) * len(g2))
            return {
                "name": "cliffs_delta",
                "label": "Cliff's delta",
                "value": float(delta),
                "note": _interpret_cliffs_delta(abs(delta)),
            }

    except Exception as e:
        logger.warning(f"Error computing effect size {effect_name}: {e}")

    return None


def _interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d magnitude."""
    if d < 0.2:
        return "negligible"
    elif d < 0.5:
        return "small"
    elif d < 0.8:
        return "medium"
    else:
        return "large"


def _interpret_cliffs_delta(delta: float) -> str:
    """Interpret Cliff's delta magnitude."""
    if delta < 0.147:
        return "negligible"
    elif delta < 0.33:
        return "small"
    elif delta < 0.474:
        return "medium"
    else:
        return "large"


def _infer_outcome_type(groups: List[np.ndarray]) -> str:
    """Infer outcome type from data."""
    all_values = np.concatenate(groups)
    all_values = all_values[~np.isnan(all_values)]

    unique = np.unique(all_values)

    if len(unique) == 2 and set(unique).issubset({0, 1}):
        return "binary"
    elif len(unique) <= 10 and np.allclose(all_values, all_values.astype(int)):
        return "ordinal"
    else:
        return "continuous"
