#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical analysis helper functions.

Implementation logic for stats API endpoints. Delegates to scitex.stats where
possible, falling back to scipy for tests not directly wrapped.
"""

import logging

import numpy as np

logger = logging.getLogger("scitex")

__all__ = [
    "run_descriptive",
    "run_statistical_test",
    "run_effect_size",
    "run_posthoc",
    "run_power_analysis",
    "run_correction",
    "run_recommend",
]


def run_descriptive(body: dict) -> dict:
    """Compute descriptive statistics via scitex.stats."""
    import scitex as stx

    data = body.get("data", [])
    percentiles = body.get("percentiles")
    if percentiles:
        return stx.stats.descriptive(data, percentiles=percentiles)
    return stx.stats.descriptive(data)


def run_statistical_test(body: dict) -> dict:
    """Route to appropriate statistical test."""
    test_name = body.get("test_name")
    data = np.array(body.get("data", []))
    data2 = np.array(body["data2"]) if body.get("data2") else None
    groups = [np.array(g) for g in body["groups"]] if body.get("groups") else None
    alternative = body.get("alternative", "two-sided")

    router = {
        "ttest": lambda: _ttest_ind(data, data2, alternative),
        "ttest_ind": lambda: _ttest_ind(data, data2, alternative),
        "ttest_paired": lambda: _ttest_paired(data, data2),
        "anova": lambda: _anova(groups),
        "mann_whitney": lambda: _mann_whitney(data, data2, alternative),
        "wilcoxon": lambda: _wilcoxon(data, data2),
        "kruskal": lambda: _kruskal(groups),
        "chi2": lambda: _chi2(data, data2),
        "shapiro": lambda: _shapiro(data),
        "pearson": lambda: _correlation(data, data2, "pearson"),
        "correlation": lambda: _correlation(data, data2, "pearson"),
        "spearman": lambda: _correlation(data, data2, "spearman"),
    }
    if test_name not in router:
        raise ValueError(f"Unknown test: {test_name}")
    return router[test_name]()


def run_effect_size(body: dict) -> dict:
    """Calculate effect size using scitex.stats.effect_sizes."""
    import scitex as stx

    measure = body["measure"]
    group1 = np.array(body["group1"])
    group2 = np.array(body.get("group2", []))
    groups = [np.array(g) for g in body["groups"]] if body.get("groups") else None
    paired = body.get("paired", False)

    # Calculate value
    if measure == "cohens_d":
        value = float(stx.stats.effect_sizes.cohens_d(group1, group2, paired=paired))
        interpretation = stx.stats.effect_sizes.interpret_cohens_d(value)
    elif measure == "eta_squared":
        value = float(stx.stats.effect_sizes.eta_squared(groups or [group1, group2]))
        interpretation = stx.stats.effect_sizes.interpret_eta_squared(value)
    elif measure == "epsilon_squared":
        value = float(
            stx.stats.effect_sizes.epsilon_squared(groups or [group1, group2])
        )
        interpretation = stx.stats.effect_sizes.interpret_epsilon_squared(value)
    elif measure == "cliffs_delta":
        value = float(stx.stats.effect_sizes.cliffs_delta(group1, group2))
        interpretation = stx.stats.effect_sizes.interpret_cliffs_delta(value)
    elif measure == "prob_superiority":
        value = float(stx.stats.effect_sizes.prob_superiority(group1, group2))
        interpretation = stx.stats.effect_sizes.interpret_prob_superiority(value)
    else:
        raise ValueError(f"Unknown effect size measure: {measure}")

    return {"measure": measure, "value": value, "interpretation": interpretation}


def run_posthoc(body: dict) -> dict:
    """Run post-hoc test using scitex.stats.posthoc."""
    import scitex as stx

    method = body["method"]
    groups = [np.array(g) for g in body["groups"]]
    group_names = body.get("group_names")
    alpha = body.get("alpha", 0.05)

    if method == "tukey":
        result = stx.stats.posthoc.posthoc_tukey(
            groups, group_names=group_names, alpha=alpha, return_as="list"
        )
    elif method == "games_howell":
        result = stx.stats.posthoc.posthoc_games_howell(
            groups, group_names=group_names, alpha=alpha, return_as="list"
        )
    elif method == "dunnett":
        control = groups[0]
        treatments = groups[1:]
        t_names = group_names[1:] if group_names else None
        c_name = group_names[0] if group_names else "Control"
        result = stx.stats.posthoc.posthoc_dunnett(
            control,
            treatments,
            treatment_names=t_names,
            control_name=c_name,
            alpha=alpha,
            return_as="list",
        )
    else:
        raise ValueError(f"Unknown post-hoc method: {method}")

    return {"method": method, "comparisons": result}


def run_power_analysis(body: dict) -> dict:
    """Run power analysis using scitex.stats.power."""
    import scitex as stx

    effect_size = body.get("effect_size")
    n = body.get("n")
    alpha = body.get("alpha", 0.05)
    power = body.get("power", 0.8)
    test_type = body.get("test_type", "two-sample")

    if n and effect_size:
        # Calculate power given n and effect size
        computed_power = stx.stats.power.power_ttest(
            effect_size=effect_size, n=n, alpha=alpha, test_type=test_type
        )
        return {
            "power": float(computed_power),
            "n": n,
            "effect_size": effect_size,
            "alpha": alpha,
        }
    elif effect_size:
        # Calculate required n given effect size and desired power
        n_required = stx.stats.power.sample_size_ttest(
            effect_size=effect_size, power=power, alpha=alpha, test_type=test_type
        )
        return {
            "n_required": (
                int(n_required) if isinstance(n_required, (int, float)) else n_required
            ),
            "effect_size": effect_size,
            "alpha": alpha,
            "power": power,
        }
    else:
        raise ValueError("effect_size is required for power analysis")


def run_correction(body: dict) -> dict:
    """Apply multiple comparison correction using scitex.stats.correct."""
    import scitex as stx

    method = body["method"]
    pvalues = body["pvalues"]
    alpha = body.get("alpha", 0.05)

    # scitex correction functions accept results as dicts with p_value keys
    results = [{"p_value": p} for p in pvalues]

    func_map = {
        "bonferroni": stx.stats.correct.correct_bonferroni,
        "fdr": stx.stats.correct.correct_fdr,
        "holm": stx.stats.correct.correct_holm,
        "sidak": stx.stats.correct.correct_sidak,
    }
    if method not in func_map:
        raise ValueError(f"Unknown correction method: {method}")

    corrected = func_map[method](
        results, alpha=alpha, return_as="list", verbose=False, plot=False
    )
    return {"method": method, "corrected": corrected, "alpha": alpha}


def run_recommend(body: dict) -> dict:
    """Recommend tests using scitex.stats.recommend_tests."""
    import scitex as stx

    recommendations = stx.stats.recommend_tests(
        n_groups=body.get("n_groups", 2),
        sample_sizes=body.get("sample_sizes"),
        outcome_type=body.get("outcome_type", "continuous"),
        design=body.get("design", "between"),
        paired=body.get("paired", False),
        has_control_group=body.get("has_control_group", False),
        top_k=body.get("top_k", 5),
    )
    return {"recommendations": recommendations}


# Private helper functions for individual tests
def _ttest_ind(data1, data2, alternative):
    """Run independent samples t-test."""
    import scitex as stx
    from scipy import stats as sp_stats

    result = sp_stats.ttest_ind(data1, data2, alternative=alternative)
    df = len(data1) + len(data2) - 2

    # Use scitex for effect size
    cohens_d = float(stx.stats.effect_sizes.cohens_d(data1, data2))

    return {
        "test": "Independent Samples t-test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "mean1": float(data1.mean()),
        "mean2": float(data2.mean()),
        "cohens_d": cohens_d,
        "formatted": f"t({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, d = {cohens_d:.3f}",
    }


def _ttest_paired(data1, data2):
    """Run paired samples t-test."""
    import scitex as stx
    from scipy import stats as sp_stats

    result = sp_stats.ttest_rel(data1, data2)

    # Calculate effect size using scitex
    cohens_d = float(stx.stats.effect_sizes.cohens_d(data1, data2, paired=True))
    diff = data1 - data2
    df = len(data1) - 1

    return {
        "test": "Paired Samples t-test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "mean_diff": float(diff.mean()),
        "cohens_d": cohens_d,
        "formatted": f"t({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, d = {cohens_d:.3f}",
    }


def _anova(groups):
    """Run one-way ANOVA."""
    import scitex as stx
    from scipy import stats as sp_stats

    result = sp_stats.f_oneway(*groups)

    # Calculate eta squared using scitex
    eta_squared = float(stx.stats.effect_sizes.eta_squared(groups))

    df_between = len(groups) - 1
    df_within = sum(len(g) for g in groups) - len(groups)

    return {
        "test": "One-Way ANOVA",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df_between": df_between,
        "df_within": df_within,
        "eta_squared": eta_squared,
        "formatted": f"F({df_between}, {df_within}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, η² = {eta_squared:.3f}",
    }


def _mann_whitney(data1, data2, alternative):
    """Run Mann-Whitney U test."""
    from scipy import stats as sp_stats

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


def _wilcoxon(data1, data2):
    """Run Wilcoxon signed-rank test."""
    from scipy import stats as sp_stats

    result = sp_stats.wilcoxon(data1, data2)

    return {
        "test": "Wilcoxon Signed-Rank Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "formatted": f"W = {result.statistic:.1f}, p = {result.pvalue:.4f}",
    }


def _kruskal(groups):
    """Run Kruskal-Wallis H test."""
    import scitex as stx
    from scipy import stats as sp_stats

    result = sp_stats.kruskal(*groups)

    # Calculate epsilon squared using scitex
    epsilon_squared = float(stx.stats.effect_sizes.epsilon_squared(groups))
    df = len(groups) - 1

    return {
        "test": "Kruskal-Wallis H Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "df": df,
        "epsilon_squared": epsilon_squared,
        "formatted": f"H({df}) = {result.statistic:.3f}, p = {result.pvalue:.4f}, ε² = {epsilon_squared:.3f}",
    }


def _chi2(observed, expected=None):
    """Run Chi-square test."""
    from scipy import stats as sp_stats

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


def _shapiro(data):
    """Run Shapiro-Wilk normality test."""
    from scipy import stats as sp_stats

    result = sp_stats.shapiro(data)

    return {
        "test": "Shapiro-Wilk Normality Test",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "normal": result.pvalue > 0.05,
        "formatted": f"W = {result.statistic:.4f}, p = {result.pvalue:.4f} ({'normal' if result.pvalue > 0.05 else 'not normal'})",
    }


def _correlation(data1, data2, method="pearson"):
    """Run correlation test."""
    from scipy import stats as sp_stats

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
        "formatted": f"r = {r:.3f}, p = {p:.4f}, n = {n}",
    }


# EOF
