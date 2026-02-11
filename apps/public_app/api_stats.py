#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical analysis API views.

Provides backend functionality for the Statistics Calculator tool using scitex.stats.
"""

import json
import logging
from typing import Any, Dict

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Django views use standard logging, not @stx.session injection
logger = logging.getLogger("scitex")  # noqa: STX-I007

__all__ = ["stats_calculate", "stats_recommend", "stats_describe"]


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
        data = body.get("data", [])
        data2 = body.get("data2")
        groups = body.get("groups")
        alternative = body.get("alternative", "two-sided")

        if not test_name:
            return JsonResponse(
                {"success": False, "error": "test_name is required"}, status=400
            )

        # Import scitex stats module
        try:
            import scitex as stx
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

        # Route to appropriate test function
        result = _run_statistical_test(stx, test_name, data, data2, groups, alternative)

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
        percentiles = body.get("percentiles")

        if not data:
            return JsonResponse(
                {"success": False, "error": "data is required"}, status=400
            )

        try:
            import scitex as stx
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

        # Call scitex.stats.descriptive
        if percentiles:
            result = stx.stats.descriptive(data, percentiles=percentiles)
        else:
            result = stx.stats.descriptive(data)

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

        n_groups = body.get("n_groups", 2)
        sample_sizes = body.get("sample_sizes")
        outcome_type = body.get("outcome_type", "continuous")
        design = body.get("design", "between")
        paired = body.get("paired", False)
        has_control_group = body.get("has_control_group", False)
        top_k = body.get("top_k", 3)

        try:
            import scitex as stx
        except ImportError as e:
            logger.error(f"Failed to import scitex: {e}")
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )

        # Call scitex.stats.recommend_tests
        recommendations = stx.stats.recommend_tests(
            n_groups=n_groups,
            sample_sizes=sample_sizes,
            outcome_type=outcome_type,
            design=design,
            paired=paired,
            has_control_group=has_control_group,
            top_k=top_k,
        )

        return JsonResponse({"success": True, "recommendations": recommendations})

    except Exception as e:
        logger.error(f"Error in stats_recommend: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _run_statistical_test(
    stx, test_name: str, data, data2, groups, alternative: str
) -> Dict[str, Any]:
    """
    Route to appropriate statistical test function.

    Returns dict with test results.
    """
    import numpy as np

    # Convert to numpy arrays
    data = np.array(data)
    if data2 is not None:
        data2 = np.array(data2)
    if groups is not None:
        groups = [np.array(g) for g in groups]

    # Map test names to scitex functions
    test_mapping = {
        "ttest": lambda: _run_ttest(stx, data, data2, alternative),
        "ttest_ind": lambda: _run_ttest(stx, data, data2, alternative),
        "ttest_paired": lambda: _run_ttest_paired(stx, data, data2),
        "anova": lambda: _run_anova(stx, groups),
        "mann_whitney": lambda: _run_mann_whitney(stx, data, data2, alternative),
        "wilcoxon": lambda: _run_wilcoxon(stx, data, data2),
        "kruskal": lambda: _run_kruskal(stx, groups),
        "chi2": lambda: _run_chi2(stx, data, data2),
        "shapiro": lambda: _run_shapiro(stx, data),
        "correlation": lambda: _run_correlation(stx, data, data2),
        "pearson": lambda: _run_correlation(stx, data, data2, method="pearson"),
        "spearman": lambda: _run_correlation(stx, data, data2, method="spearman"),
    }

    if test_name not in test_mapping:
        raise ValueError(f"Unknown test: {test_name}")

    return test_mapping[test_name]()


def _run_ttest(stx, data1, data2, alternative):
    """Run independent samples t-test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.ttest_ind(data1, data2, alternative=alternative)

    # Calculate effect size (Cohen's d)
    mean1, mean2 = data1.mean(), data2.mean()
    pooled_std = np.sqrt(
        (
            (len(data1) - 1) * data1.std(ddof=1) ** 2
            + (len(data2) - 1) * data2.std(ddof=1) ** 2
        )
        / (len(data1) + len(data2) - 2)
    )
    cohens_d = (mean1 - mean2) / pooled_std

    # Format APA style
    df = len(data1) + len(data2) - 2
    formatted = (
        stx.stats.get_stat_style().format_test(
            "t-test",
            statistic=result.statistic,
            p_value=result.pvalue,
            df=df,
            effect_size=cohens_d,
            effect_size_name="d",
        )
        if hasattr(stx.stats, "get_stat_style")
        else ""
    )

    return {
        "test": "Independent Samples t-test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "mean1": float(mean1),
        "mean2": float(mean2),
        "cohens_d": float(cohens_d),
        "formatted": formatted
        or f"t({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, d = {cohens_d:.3f}",
    }


def _run_ttest_paired(stx, data1, data2):
    """Run paired samples t-test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.ttest_rel(data1, data2)

    # Calculate effect size
    diff = data1 - data2
    cohens_d = diff.mean() / diff.std(ddof=1)

    df = len(data1) - 1

    return {
        "test": "Paired Samples t-test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "mean_diff": float(diff.mean()),
        "cohens_d": float(cohens_d),
        "formatted": f"t({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, d = {cohens_d:.3f}",
    }


def _run_anova(stx, groups):
    """Run one-way ANOVA."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.f_oneway(*groups)

    # Calculate eta squared
    grand_mean = np.concatenate(groups).mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = sum(((g - grand_mean) ** 2).sum() for g in groups)
    eta_squared = ss_between / ss_total

    df_between = len(groups) - 1
    df_within = sum(len(g) for g in groups) - len(groups)

    return {
        "test": "One-Way ANOVA",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df_between": df_between,
        "df_within": df_within,
        "eta_squared": float(eta_squared),
        "formatted": f"F({df_between}, {df_within}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, η² = {eta_squared:.3f}",
    }


def _run_mann_whitney(stx, data1, data2, alternative):
    """Run Mann-Whitney U test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.mannwhitneyu(data1, data2, alternative=alternative)

    # Calculate rank biserial correlation
    n1, n2 = len(data1), len(data2)
    r = 1 - (2 * result.statistic) / (n1 * n2)

    return {
        "test": "Mann-Whitney U Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "rank_biserial": float(r),
        "formatted": f"U = {result.statistic:.1f}, p = {result.pvalue:.4f}, r = {r:.3f}",
    }


def _run_wilcoxon(stx, data1, data2):
    """Run Wilcoxon signed-rank test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.wilcoxon(data1, data2)

    return {
        "test": "Wilcoxon Signed-Rank Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "formatted": f"W = {result.statistic:.1f}, p = {result.pvalue:.4f}",
    }


def _run_kruskal(stx, groups):
    """Run Kruskal-Wallis H test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.kruskal(*groups)

    # Calculate epsilon squared
    n = sum(len(g) for g in groups)
    eta_squared = (result.statistic - len(groups) + 1) / (n - len(groups))

    df = len(groups) - 1

    return {
        "test": "Kruskal-Wallis H Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "epsilon_squared": float(eta_squared),
        "formatted": f"H({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, ε² = {eta_squared:.3f}",
    }


def _run_chi2(stx, observed, expected=None):
    """Run Chi-square test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    if expected is None:
        # Chi-square goodness of fit with uniform distribution
        expected = np.full_like(observed, observed.mean())

    result = sp_stats.chisquare(observed, expected)

    df = len(observed) - 1

    return {
        "test": "Chi-Square Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "formatted": f"χ²({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}",
    }


def _run_shapiro(stx, data):
    """Run Shapiro-Wilk normality test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    result = sp_stats.shapiro(data)

    return {
        "test": "Shapiro-Wilk Normality Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "normal": result.pvalue > 0.05,
        "formatted": f"W = {result.statistic:.4f}, p = {result.pvalue:.4f} ({'normal' if result.pvalue > 0.05 else 'not normal'})",
    }


def _run_correlation(stx, data1, data2, method="pearson"):
    """Run correlation test."""
    from scipy import stats as sp_stats  # noqa: STX-I002

    if method == "pearson":
        r, p = sp_stats.pearsonr(data1, data2)
        test_name = "Pearson Correlation"
    elif method == "spearman":
        r, p = sp_stats.spearmanr(data1, data2)
        test_name = "Spearman Correlation"
    else:
        raise ValueError(f"Unknown correlation method: {method}")

    n = len(data1)

    return {
        "test": test_name,
        "correlation": float(r),
        "p_value": float(p),
        "n": n,
        "r_squared": float(r**2),
        "formatted": f"r = {r:.3f}, p = {r.pvalue:.4f}, n = {n}"
        if hasattr(r, "pvalue")
        else f"r = {r:.3f}, p = {p:.4f}, n = {n}",
    }


# EOF
