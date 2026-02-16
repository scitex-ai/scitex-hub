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
    "parse_csv_body",
    "run_descriptive",
    "run_statistical_test",
    "run_effect_size",
    "run_posthoc",
    "run_power_analysis",
    "run_correction",
    "run_recommend",
]


def parse_csv_body(request) -> dict:
    """Parse multipart CSV upload into a body dict matching JSON format.

    Reads csv_file + form fields, extracts columns, returns dict with
    data/data2/groups arrays that existing helper functions expect.
    """
    from .api_csv_helpers import cleanup_csv_temp, extract_columns, parse_csv_upload

    csv_path, params = parse_csv_upload(request)
    try:
        body = dict(params)

        # Extract columns specified by form fields
        data_col = params.get("data_col", "")
        data2_col = params.get("data2_col", "")
        group1_col = params.get("group1_col", "")
        group2_col = params.get("group2_col", "")
        group_col = params.get("group_col", "")
        group_values_str = params.get("group_values", "")
        pvalues_col = params.get("pvalues_col", "")

        if group_col and group_values_str and data_col:
            # Split data by group column
            group_values = [v.strip() for v in group_values_str.split(",")]
            cols = extract_columns(csv_path, [data_col, group_col])
            import pandas as pd  # noqa: STX-IO003

            df = pd.DataFrame(cols)
            groups = []
            for gv in group_values:
                mask = df[group_col] == gv
                groups.append(df.loc[mask, data_col].tolist())
            body["groups"] = groups
            if len(groups) == 2:
                body["data"] = groups[0]
                body["data2"] = groups[1]
        else:
            if data_col:
                cols = extract_columns(csv_path, [data_col])
                body["data"] = cols[data_col]
            if data2_col:
                cols = extract_columns(csv_path, [data2_col])
                body["data2"] = cols[data2_col]
            if group1_col:
                cols = extract_columns(csv_path, [group1_col])
                body["group1"] = cols[group1_col]
            if group2_col:
                cols = extract_columns(csv_path, [group2_col])
                body["group2"] = cols[group2_col]
            if pvalues_col:
                cols = extract_columns(csv_path, [pvalues_col])
                body["pvalues"] = cols[pvalues_col]

        return body
    finally:
        cleanup_csv_temp(csv_path)


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
    return result


def run_statistical_test(body: dict) -> dict:
    """Route to scitex.stats.run_test() and return result dict."""
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
    plot = body.get("plot", False)

    out = stx.stats.run_test(
        test_name,
        data=data,
        data2=data2,
        groups=groups,
        alternative=body.get("alternative", "two-sided"),
        plot=plot,
        popmean=body.get("popmean", 0),
    )

    # Capture figure if plotting was enabled
    if plot:
        figure_b64 = _capture_figure()
        if figure_b64:
            out["figure_base64"] = figure_b64

    return out


def run_effect_size(body: dict) -> dict:
    """Calculate effect size using scitex.stats.effect_sizes."""
    import numpy as np
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


# EOF
