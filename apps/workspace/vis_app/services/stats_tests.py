"""Stats Tests - Delegates to scitex.stats.

Thin wrapper maintaining the same API surface while delegating
all statistical computations to the scitex package.
"""

from typing import Dict, List, Optional

import numpy as np


def run_test(
    test_name: str, groups: List[np.ndarray], paired: bool = False
) -> Optional[Dict]:
    """Run a statistical test via scitex.stats."""
    from scitex.stats import (
        test_anova,
        test_brunner_munzel,
        test_kruskal,
        test_mannwhitneyu,
        test_ttest_1samp,
        test_ttest_ind,
        test_ttest_rel,
        test_wilcoxon,
    )

    test_map = {
        "ttest_ind": lambda: test_ttest_ind(groups[0], groups[1], return_as="dict"),
        "ttest_rel": lambda: test_ttest_rel(groups[0], groups[1], return_as="dict"),
        "ttest_1samp": lambda: test_ttest_1samp(groups[0], return_as="dict"),
        "mannwhitneyu": lambda: test_mannwhitneyu(
            groups[0], groups[1], return_as="dict"
        ),
        "wilcoxon": lambda: test_wilcoxon(groups[0], groups[1], return_as="dict"),
        "brunner_munzel": lambda: test_brunner_munzel(
            groups[0], groups[1], return_as="dict"
        ),
        "anova_oneway": lambda: test_anova(groups=list(groups), return_as="dict"),
        "kruskal": lambda: test_kruskal(groups=list(groups), return_as="dict"),
    }

    if test_name not in test_map:
        return None

    needs_two = {"ttest_ind", "ttest_rel", "mannwhitneyu", "wilcoxon", "brunner_munzel"}
    if test_name in needs_two and len(groups) != 2:
        return None
    if test_name == "ttest_1samp" and len(groups) != 1:
        return None

    result = test_map[test_name]()

    # Normalize keys for callers expecting: stat, p_raw, test_name, df
    return {
        "test_name": test_name,
        "stat": float(result.get("statistic", 0)),
        "p_raw": float(result.get("pvalue", 1)),
        "df": result.get("df"),
        "effect_size": result.get("effect_size"),
        "effect_size_metric": result.get("effect_size_metric"),
        "stars": result.get("stars", ""),
    }
