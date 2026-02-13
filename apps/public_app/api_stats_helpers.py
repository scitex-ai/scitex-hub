#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statistical analysis helper functions.

Thin delegation layer to scitex.stats — no custom logic here.
"""

import base64
import io
import logging  # noqa: STX-I007 — Django context, no @stx.session

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Django views use standard logging, not @stx.session injection
logger = logging.getLogger("scitex")  # noqa: STX-I007


# ── Built-in datasets ────────────────────────────────────────────


def _load_builtin_dataset(name: str) -> pd.DataFrame:
    """Load a built-in dataset by name.

    Supported: "iris"
    """
    if name == "iris":
        from sklearn.datasets import load_iris

        iris = load_iris()
        df = pd.DataFrame(
            iris.data,
            columns=["sepal_length", "sepal_width", "petal_length", "petal_width"],
        )
        df["species"] = pd.Categorical([iris.target_names[t] for t in iris.target])
        return df
    raise ValueError(f"Unknown dataset: {name}. Available: iris")


def _resolve_data(body: dict) -> dict:
    """Resolve dataset+column spec into raw arrays, mutating body in-place.

    Supports two modes:
    1. Raw arrays: {"data": [...], "data2": [...], "groups": [[...], ...]}
    2. Dataset+columns: {"dataset": "iris", "data_column": "sepal_length",
                         "data2_column": "petal_length",
                         "group_column": "species",
                         "group_values": ["setosa", "versicolor"]}

    When dataset mode is used, populates body["data"], body["data2"],
    and/or body["groups"] from the dataset.
    """
    dataset_name = body.get("dataset")
    if not dataset_name:
        return body

    df = _load_builtin_dataset(dataset_name)
    data_col = body.get("data_column")
    data2_col = body.get("data2_column")
    group_col = body.get("group_column")
    group_values = body.get("group_values")

    if data_col and group_col and group_values:
        # Split data by group column
        groups = []
        for gv in group_values:
            mask = df[group_col] == gv
            groups.append(df.loc[mask, data_col].values.tolist())
        if len(groups) == 2:
            body["data"] = groups[0]
            body["data2"] = groups[1]
        body["groups"] = groups
    elif data_col and data2_col:
        # Two columns from same dataset
        if group_col and group_values:
            mask = df[group_col] == group_values[0]
            body["data"] = df.loc[mask, data_col].values.tolist()
            body["data2"] = df.loc[mask, data2_col].values.tolist()
        else:
            body["data"] = df[data_col].values.tolist()
            body["data2"] = df[data2_col].values.tolist()
    elif data_col:
        body["data"] = df[data_col].values.tolist()

    return body


__all__ = [
    "run_descriptive",
    "run_statistical_test",
    "run_effect_size",
    "run_posthoc",
    "run_power_analysis",
    "run_correction",
    "run_recommend",
]


def _capture_figure() -> str:
    """Capture current matplotlib figure as base64 PNG with scitex theme."""
    import scitex as stx  # noqa: STX-I001 — Django context, no @stx.session

    stx.plt.load_style()
    fig = stx.plt.gcf()
    if fig.get_axes():
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, facecolor="white")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        stx.plt.close(fig)
        return b64
    stx.plt.close(fig)
    return ""


def run_descriptive(body: dict) -> dict:
    """Compute descriptive statistics via scitex.stats."""
    import scitex as stx

    data = np.array(body.get("data", []), dtype=float)
    values, labels = stx.stats.describe(data)
    result = {label: float(v) for label, v in zip(labels, values)}
    result["count"] = len(data)
    result["min"] = float(np.nanmin(data))
    result["max"] = float(np.nanmax(data))
    # Rename for frontend clarity
    rename = {
        "nanmean": "mean",
        "nanstd": "std",
        "nanq25": "q25",
        "nanq50": "median",
        "nanq75": "q75",
    }
    return {rename.get(k, k): v for k, v in result.items()}


def run_statistical_test(body: dict) -> dict:
    """Route to scitex.stats public API and return result dict."""
    import scitex as stx

    # Resolve dataset+column spec into raw arrays
    body = _resolve_data(body)

    test_name = body.get("test_name")
    data = np.array(body.get("data", []), dtype=float)
    data2 = np.array(body["data2"], dtype=float) if body.get("data2") else None
    groups = (
        [np.array(g, dtype=float) for g in body["groups"]]
        if body.get("groups")
        else None
    )
    alternative = body.get("alternative", "two-sided")
    plot = body.get("plot", False)
    popmean = body.get("popmean", 0)

    router = {
        "ttest": lambda: stx.stats.test_ttest_ind(
            data, data2, alternative=alternative, plot=plot, return_as="dict"
        ),
        "ttest_ind": lambda: stx.stats.test_ttest_ind(
            data, data2, alternative=alternative, plot=plot, return_as="dict"
        ),
        "ttest_rel": lambda: stx.stats.test_ttest_rel(
            data, data2, plot=plot, return_as="dict"
        ),
        "ttest_paired": lambda: stx.stats.test_ttest_rel(
            data, data2, plot=plot, return_as="dict"
        ),
        "ttest_1samp": lambda: stx.stats.test_ttest_1samp(
            data, popmean=popmean, plot=plot, return_as="dict"
        ),
        "anova": lambda: stx.stats.test_anova(groups, plot=plot, return_as="dict"),
        "brunnermunzel": lambda: stx.stats.test_brunner_munzel(
            data, data2, alternative=alternative, plot=plot, return_as="dict"
        ),
        "mannwhitneyu": lambda: stx.stats.test_mannwhitneyu(
            data, data2, alternative=alternative, plot=plot, return_as="dict"
        ),
        "mann_whitney": lambda: stx.stats.test_mannwhitneyu(
            data, data2, alternative=alternative, plot=plot, return_as="dict"
        ),
        "wilcoxon": lambda: stx.stats.test_wilcoxon(
            data, data2, plot=plot, return_as="dict"
        ),
        "kruskal": lambda: stx.stats.test_kruskal(groups, plot=plot, return_as="dict"),
        "friedman": lambda: stx.stats.test_friedman(
            np.column_stack(groups), plot=plot, return_as="dict"
        ),
        "chi2": lambda: stx.stats.test_chi2(
            np.array(body["groups"], dtype=float)
            if body.get("groups")
            else np.vstack([data, data2]),
            plot=plot,
            return_as="dict",
        ),
        "fisher": lambda: stx.stats.test_fisher(
            np.array(body["groups"], dtype=float)
            if body.get("groups")
            else np.vstack([data, data2]),
            plot=plot,
            return_as="dict",
        ),
        "shapiro": lambda: stx.stats.test_shapiro(data, plot=plot, return_as="dict"),
        "ks_1samp": lambda: stx.stats.test_ks_1samp(data, plot=plot, return_as="dict"),
        "ks_2samp": lambda: stx.stats.test_ks_2samp(
            data, data2, plot=plot, return_as="dict"
        ),
        "pearson": lambda: stx.stats.test_pearson(
            data, data2, plot=plot, return_as="dict"
        ),
        "spearman": lambda: stx.stats.test_spearman(
            data, data2, plot=plot, return_as="dict"
        ),
        "kendall": lambda: stx.stats.test_kendall(
            data, data2, plot=plot, return_as="dict"
        ),
    }

    if test_name not in router:
        raise ValueError(f"Unknown test: {test_name}")

    result = router[test_name]()

    # Handle functions that return (result, fig) tuple
    if isinstance(result, tuple):
        result = result[0]

    # Normalize keys for frontend compatibility
    out = _normalize_result(result)

    # Capture figure if plotting was enabled
    if plot:
        figure_b64 = _capture_figure()
        if figure_b64:
            out["figure_base64"] = figure_b64

    return out


def run_effect_size(body: dict) -> dict:
    """Calculate effect size using scitex.stats.effect_sizes."""
    import scitex as stx

    measure = body["measure"]
    group1 = np.array(body["group1"], dtype=float)
    group2 = np.array(body.get("group2", []), dtype=float)
    groups = (
        [np.array(g, dtype=float) for g in body["groups"]]
        if body.get("groups")
        else None
    )
    paired = body.get("paired", False)

    dispatch = {
        "cohens_d": lambda: (
            float(stx.stats.effect_sizes.cohens_d(group1, group2, paired=paired)),
            stx.stats.effect_sizes.interpret_cohens_d,
        ),
        "eta_squared": lambda: (
            float(stx.stats.effect_sizes.eta_squared(groups or [group1, group2])),
            stx.stats.effect_sizes.interpret_eta_squared,
        ),
        "epsilon_squared": lambda: (
            float(stx.stats.effect_sizes.epsilon_squared(groups or [group1, group2])),
            stx.stats.effect_sizes.interpret_epsilon_squared,
        ),
        "cliffs_delta": lambda: (
            float(stx.stats.effect_sizes.cliffs_delta(group1, group2)),
            stx.stats.effect_sizes.interpret_cliffs_delta,
        ),
        "prob_superiority": lambda: (
            float(stx.stats.effect_sizes.prob_superiority(group1, group2)),
            stx.stats.effect_sizes.interpret_prob_superiority,
        ),
    }

    if measure not in dispatch:
        raise ValueError(f"Unknown effect size measure: {measure}")

    value, interpret_fn = dispatch[measure]()
    return {"measure": measure, "value": value, "interpretation": interpret_fn(value)}


def run_posthoc(body: dict) -> dict:
    """Run post-hoc test using scitex.stats.posthoc."""
    import scitex as stx

    method = body["method"]
    groups = [np.array(g, dtype=float) for g in body["groups"]]
    group_names = body.get("group_names")
    alpha = body.get("alpha", 0.05)

    if method == "tukey":
        result = stx.stats.posthoc.posthoc_tukey(
            groups, group_names=group_names, alpha=alpha, return_as="list"
        )
    elif method in ("games_howell", "games-howell"):
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
        kwargs = {"effect_size": effect_size, "alpha": alpha, "test_type": test_type}
        if test_type == "two-sample":
            kwargs["n1"] = n
            kwargs["n2"] = body.get("n2", n)
        else:
            kwargs["n"] = n
        computed_power = stx.stats.power.power_ttest(**kwargs)
        return {
            "power": float(computed_power),
            "n": n,
            "effect_size": effect_size,
            "alpha": alpha,
        }
    elif effect_size:
        n_required = stx.stats.power.sample_size_ttest(
            effect_size=effect_size, power=power, alpha=alpha, test_type=test_type
        )
        return {
            "n_required": int(n_required)
            if isinstance(n_required, (int, float))
            else n_required,
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

    results = [{"pvalue": p} for p in pvalues]

    func_map = {
        "bonferroni": stx.stats.correct.correct_bonferroni,
        "fdr_bh": stx.stats.correct.correct_fdr,
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

    ctx = stx.stats.StatContext(
        n_groups=body.get("n_groups", 2),
        sample_sizes=body.get("sample_sizes"),
        outcome_type=body.get("outcome_type", "continuous"),
        design=body.get("design", "between"),
        paired=body.get("paired", False),
        has_control_group=body.get("has_control_group", False),
    )
    recommendations = stx.stats.recommend_tests(ctx, top_k=body.get("top_k", 5))
    return {"recommendations": recommendations}


def _normalize_result(result: dict) -> dict:
    """Normalize scitex.stats result dict for frontend."""
    out = {}
    for k, v in result.items():
        if isinstance(v, np.bool_):
            out[k] = bool(v)
        elif isinstance(v, (np.floating, np.integer)):
            fv = float(v)
            out[k] = None if (np.isinf(fv) or np.isnan(fv)) else fv
        elif isinstance(v, float) and (np.isinf(v) or np.isnan(v)):
            out[k] = None
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
        else:
            out[k] = v

    # Map scitex keys to frontend-expected keys
    if "pvalue" in out and "p_value" not in out:
        out["p_value"] = out["pvalue"]
    if "test_method" in out and "test" not in out:
        out["test"] = out["test_method"]

    # Build formatted string if not present
    if "formatted" not in out and "statistic" in out and "p_value" in out:
        symbol = out.get("stat_symbol", "stat")
        stat_val = out["statistic"]
        p_val = out["p_value"]
        parts = [
            f"{symbol} = {stat_val:.3f}" if stat_val is not None else f"{symbol} = N/A",
            f"p = {p_val:.4f}" if p_val is not None else "p = N/A",
        ]
        if "effect_size" in out and out["effect_size"] is not None:
            metric = out.get("effect_size_metric", "d")
            parts.append(f"{metric} = {out['effect_size']:.3f}")
        if "stars" in out:
            parts.append(out["stars"])
        out["formatted"] = ", ".join(parts)

    return out


# EOF
