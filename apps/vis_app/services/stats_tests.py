"""Stats Tests - Individual statistical test implementations."""

from typing import Dict, List, Optional

import numpy as np


def run_test(
    test_name: str, groups: List[np.ndarray], paired: bool = False
) -> Optional[Dict]:
    """Run a statistical test on data."""
    from scipy import stats

    if test_name == "ttest_ind":
        return _run_ttest_ind(groups, stats)
    elif test_name == "ttest_rel":
        return _run_ttest_rel(groups, stats)
    elif test_name == "ttest_1samp":
        return _run_ttest_1samp(groups, stats)
    elif test_name == "mannwhitneyu":
        return _run_mannwhitneyu(groups, stats)
    elif test_name == "wilcoxon":
        return _run_wilcoxon(groups, stats)
    elif test_name == "brunner_munzel":
        return _run_brunner_munzel(groups, stats)
    elif test_name == "anova_oneway":
        return _run_anova_oneway(groups, stats)
    elif test_name == "kruskal":
        return _run_kruskal(groups, stats)
    elif test_name == "chi2":
        return None
    return None


def _run_ttest_ind(groups, stats) -> Optional[Dict]:
    """Independent samples t-test."""
    if len(groups) != 2:
        return None
    stat, pval = stats.ttest_ind(groups[0], groups[1])
    return {
        "test_name": "ttest_ind",
        "stat": float(stat),
        "p_raw": float(pval),
        "df": len(groups[0]) + len(groups[1]) - 2,
    }


def _run_ttest_rel(groups, stats) -> Optional[Dict]:
    """Paired samples t-test."""
    if len(groups) != 2:
        return None
    stat, pval = stats.ttest_rel(groups[0], groups[1])
    return {
        "test_name": "ttest_rel",
        "stat": float(stat),
        "p_raw": float(pval),
        "df": len(groups[0]) - 1,
    }


def _run_ttest_1samp(groups, stats) -> Optional[Dict]:
    """One-sample t-test."""
    if len(groups) != 1:
        return None
    stat, pval = stats.ttest_1samp(groups[0], popmean=0)
    return {
        "test_name": "ttest_1samp",
        "stat": float(stat),
        "p_raw": float(pval),
        "df": len(groups[0]) - 1,
    }


def _run_mannwhitneyu(groups, stats) -> Optional[Dict]:
    """Mann-Whitney U test."""
    if len(groups) != 2:
        return None
    stat, pval = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
    return {"test_name": "mannwhitneyu", "stat": float(stat), "p_raw": float(pval)}


def _run_wilcoxon(groups, stats) -> Optional[Dict]:
    """Wilcoxon signed-rank test."""
    if len(groups) != 2:
        return None
    stat, pval = stats.wilcoxon(groups[0], groups[1])
    return {"test_name": "wilcoxon", "stat": float(stat), "p_raw": float(pval)}


def _run_brunner_munzel(groups, stats) -> Optional[Dict]:
    """Brunner-Munzel test."""
    if len(groups) != 2:
        return None
    stat, pval = stats.brunnermunzel(groups[0], groups[1])
    return {"test_name": "brunner_munzel", "stat": float(stat), "p_raw": float(pval)}


def _run_anova_oneway(groups, stats) -> Optional[Dict]:
    """One-way ANOVA."""
    stat, pval = stats.f_oneway(*groups)
    return {"test_name": "anova_oneway", "stat": float(stat), "p_raw": float(pval)}


def _run_kruskal(groups, stats) -> Optional[Dict]:
    """Kruskal-Wallis H-test."""
    stat, pval = stats.kruskal(*groups)
    return {"test_name": "kruskal", "stat": float(stat), "p_raw": float(pval)}
