#!/usr/bin/env python3
"""Test all scitex.stats plot functions using the Iris dataset.

Usage:
    python scripts/test_stats_plots.py
    # Output: /tmp/stats_plots_test/*.png
"""

import os
import sys
import traceback

import numpy as np
import pandas as pd
from sklearn.datasets import load_iris

# Ensure scitex-python is importable
sys.path.insert(0, os.path.expanduser("~/proj/scitex-python/src"))
import scitex as stx

OUT = "/tmp/stats_plots_test"
os.makedirs(OUT, exist_ok=True)

# ── Load Iris dataset ──────────────────────────────────────────
iris = load_iris()
setosa_sl = iris.data[iris.target == 0, 0]  # sepal length
versicolor_sl = iris.data[iris.target == 1, 0]
virginica_sl = iris.data[iris.target == 2, 0]
setosa_pl = iris.data[iris.target == 0, 2]  # petal length
versicolor_pl = iris.data[iris.target == 1, 2]
all_sl = iris.data[:, 0]
all_pl = iris.data[:, 2]

n_pass = 0
n_fail = 0


def save(name, fig=None):
    """Save figure and close."""
    if fig is None:
        fig = stx.plt.gcf()
    path = os.path.join(OUT, f"{name}.png")
    stx.io.save(fig, path, dpi=300)
    stx.plt.close(fig)
    print(f"  OK    {name}")


def run(name, fn, has_plot=True):
    """Run a test function, print pass/fail."""
    global n_pass, n_fail
    try:
        result = fn()
        if has_plot:
            # Some tests return (result, fig) tuple
            fig = result[1] if isinstance(result, tuple) else None
            save(name, fig=fig)
        else:
            print(f"  OK    {name} (no plot)")
        n_pass += 1
    except Exception:
        print(f"  FAIL  {name}")
        traceback.print_exc()
        stx.plt.close("all")
        n_fail += 1


# ── Tests ──────────────────────────────────────────────────────
print("=== scitex.stats Plot Tests (Iris dataset) ===\n")

# 1. Two-group parametric
print("Parametric (2-group):")
run(
    "ttest_ind",
    lambda: stx.stats.test_ttest_ind(
        setosa_sl,
        versicolor_sl,
        var_x="Setosa SL",
        var_y="Versicolor SL",
        plot=True,
        return_as="dict",
    ),
)
run(
    "ttest_rel",
    lambda: stx.stats.test_ttest_rel(
        setosa_sl,
        setosa_pl,
        var_x="Sepal Length",
        var_y="Petal Length",
        plot=True,
        return_as="dict",
    ),
)
run(
    "ttest_1samp",
    lambda: stx.stats.test_ttest_1samp(
        setosa_sl,
        popmean=5.0,
        var_x="Setosa Sepal Length",
        plot=True,
        return_as="dict",
    ),
)

# 2. Multi-group parametric
print("\nParametric (multi-group):")
run(
    "anova",
    lambda: stx.stats.test_anova(
        [setosa_sl, versicolor_sl, virginica_sl],
        var_names=["Setosa", "Versicolor", "Virginica"],
        plot=True,
        return_as="dict",
    ),
)

# 2b. Repeated measures ANOVA (wide format: each column = condition)
rm_data = np.column_stack([setosa_sl, versicolor_sl, virginica_sl])
run(
    "anova_rm",
    lambda: stx.stats.test_anova_rm(
        rm_data,
        condition_names=["Setosa", "Versicolor", "Virginica"],
        plot=True,
        return_as="dict",
    ),
)

# 2c. Two-way ANOVA (DataFrame with factor columns)
df_2way = pd.DataFrame(
    {
        "value": np.concatenate(
            [
                setosa_sl,
                versicolor_sl,
                virginica_sl,
                setosa_pl,
                versicolor_pl,
                iris.data[iris.target == 2, 2],
            ]
        ),
        "species": (["setosa"] * 50 + ["versicolor"] * 50 + ["virginica"] * 50) * 2,
        "measure": ["sepal"] * 150 + ["petal"] * 150,
    }
)
run(
    "anova_2way",
    lambda: stx.stats.test_anova_2way(
        df_2way,
        factor_a="species",
        factor_b="measure",
        value="value",
        factor_a_name="Species",
        factor_b_name="Measure",
        plot=True,
        return_as="dict",
    ),
)

# 3. Two-group nonparametric
print("\nNonparametric (2-group):")
run(
    "mannwhitneyu",
    lambda: stx.stats.test_mannwhitneyu(
        setosa_sl,
        versicolor_sl,
        var_x="Setosa SL",
        var_y="Versicolor SL",
        plot=True,
        return_as="dict",
    ),
)
run(
    "wilcoxon",
    lambda: stx.stats.test_wilcoxon(
        setosa_sl,
        setosa_pl,
        var_x="Sepal Length",
        var_y="Petal Length",
        plot=True,
        return_as="dict",
    ),
)
run(
    "brunnermunzel",
    lambda: stx.stats.test_brunner_munzel(
        setosa_sl,
        versicolor_sl,
        var_x="Setosa SL",
        var_y="Versicolor SL",
        plot=True,
        return_as="dict",
    ),
)

# 4. Multi-group nonparametric
print("\nNonparametric (multi-group):")
run(
    "kruskal",
    lambda: stx.stats.test_kruskal(
        [setosa_sl, versicolor_sl, virginica_sl],
        var_names=["Setosa", "Versicolor", "Virginica"],
        plot=True,
        return_as="dict",
    ),
)

# 4b. Friedman test (wide format)
run(
    "friedman",
    lambda: stx.stats.test_friedman(
        rm_data,
        condition_names=["Setosa SL", "Versicolor SL", "Virginica SL"],
        plot=True,
        return_as="dict",
    ),
)

# 5. Correlation
print("\nCorrelation:")
run(
    "pearson",
    lambda: stx.stats.test_pearson(
        setosa_sl,
        setosa_pl,
        var_x="Sepal Length",
        var_y="Petal Length",
        plot=True,
        return_as="dict",
    ),
)
run(
    "spearman",
    lambda: stx.stats.test_spearman(
        setosa_sl,
        setosa_pl,
        var_x="Sepal Length",
        var_y="Petal Length",
        plot=True,
        return_as="dict",
    ),
)
run(
    "kendall",
    lambda: stx.stats.test_kendall(
        setosa_sl,
        setosa_pl,
        var_x="Sepal Length",
        var_y="Petal Length",
        plot=True,
        return_as="dict",
    ),
)

# 5b. Theil-Sen (no plot parameter)
run(
    "theilsen",
    lambda: stx.stats.test_theilsen(
        setosa_sl,
        setosa_pl,
        var_x="Sepal Length",
        var_y="Petal Length",
        return_as="dict",
    ),
    has_plot=False,
)

# 6. Normality
print("\nNormality:")
run(
    "shapiro",
    lambda: stx.stats.test_shapiro(
        setosa_sl,
        var_x="Setosa Sepal Length",
        plot=True,
        return_as="dict",
    ),
)
run(
    "ks_1samp",
    lambda: stx.stats.test_ks_1samp(
        setosa_sl,
        var_x="Setosa Sepal Length",
        plot=True,
        return_as="dict",
    ),
)
run(
    "ks_2samp",
    lambda: stx.stats.test_ks_2samp(
        setosa_sl,
        versicolor_sl,
        var_x="Setosa SL",
        var_y="Versicolor SL",
        plot=True,
        return_as="dict",
    ),
)

# 7. Categorical
print("\nCategorical:")
run(
    "chi2",
    lambda: stx.stats.test_chi2(
        np.array([[30, 20], [15, 35], [10, 40]]),
        var_row="Species",
        var_col="Size",
        plot=True,
        return_as="dict",
    ),
)
run(
    "fisher",
    lambda: stx.stats.test_fisher(
        np.array([[28, 22], [15, 35]]),
        var_row="Treatment",
        var_col="Outcome",
        plot=True,
        return_as="dict",
    ),
)
run(
    "mcnemar",
    lambda: stx.stats.test_mcnemar(
        np.array([[40, 5], [10, 45]]),
        var_before="Before",
        var_after="After",
        plot=True,
        return_as="dict",
    ),
)

# 7b. Cochran's Q (binary repeated measures, wide format)
cochran_data = np.array(
    [
        [1, 1, 0],
        [1, 0, 0],
        [1, 1, 1],
        [0, 0, 0],
        [1, 1, 0],
        [1, 0, 1],
        [0, 1, 0],
        [1, 1, 1],
        [1, 0, 0],
        [0, 0, 0],
        [1, 1, 0],
        [1, 1, 1],
        [0, 0, 0],
        [1, 0, 0],
        [1, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
        [1, 0, 0],
        [1, 1, 0],
        [0, 0, 0],
    ]
)
run(
    "cochran_q",
    lambda: stx.stats.test_cochran_q(
        cochran_data,
        condition_names=["Method A", "Method B", "Method C"],
        plot=True,
        return_as="dict",
    ),
)

# ── Summary ──────────────────────────────────────────────────────
print(f"\n=== Results: {n_pass} passed, {n_fail} failed ===")
print(f"Figures in {OUT}/")
