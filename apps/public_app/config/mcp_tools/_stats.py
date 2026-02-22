#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP tool data: stats category."""

_R = "required"

STATS_TOOLS = {
    "category": "Statistics",
    "prefix": "stats_*",
    "icon": "fa-chart-bar",
    "tools": [
        {
            "name": "stats_recommend_tests",
            "desc": "Recommend appropriate statistical tests based on data characteristics.",
            "params": [
                {"name": "n_groups", "type": "int", "default": "2"},
                {"name": "sample_sizes", "type": "list[int]", "default": "None"},
                {"name": "outcome_type", "type": "str", "default": "'continuous'"},
                {"name": "design", "type": "str", "default": "'between'"},
                {"name": "paired", "type": "bool", "default": "False"},
                {"name": "has_control_group", "type": "bool", "default": "False"},
                {"name": "top_k", "type": "int", "default": "3"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_run_test",
            "desc": "Execute a statistical test on provided data.",
            "params": [
                {"name": "test_name", "type": "str", "default": _R},
                {"name": "data", "type": "list[list[float]]", "default": "None"},
                {"name": "data_file", "type": "str", "default": "None"},
                {"name": "columns", "type": "list[str]", "default": "None"},
                {"name": "alternative", "type": "str", "default": "'two-sided'"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_format_results",
            "desc": "Format statistical results in journal style (APA, Nature, etc.).",
            "params": [
                {"name": "test_name", "type": "str", "default": _R},
                {"name": "statistic", "type": "float", "default": _R},
                {"name": "p_value", "type": "float", "default": _R},
                {"name": "df", "type": "float", "default": "None"},
                {"name": "effect_size", "type": "float", "default": "None"},
                {"name": "style", "type": "str", "default": "'apa'"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_power_analysis",
            "desc": "Calculate statistical power or required sample size.",
            "params": [
                {"name": "test_type", "type": "str", "default": "'ttest'"},
                {"name": "effect_size", "type": "float", "default": "None"},
                {"name": "alpha", "type": "float", "default": "0.05"},
                {"name": "power", "type": "float", "default": "0.8"},
                {"name": "n", "type": "int", "default": "None"},
                {"name": "n_groups", "type": "int", "default": "2"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_correct_pvalues",
            "desc": "Apply multiple comparison correction to p-values.",
            "params": [
                {"name": "pvalues", "type": "list[float]", "default": _R},
                {"name": "method", "type": "str", "default": "'fdr_bh'"},
                {"name": "alpha", "type": "float", "default": "0.05"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_describe",
            "desc": "Calculate descriptive statistics for data.",
            "params": [
                {"name": "data", "type": "list[float]", "default": _R},
                {"name": "percentiles", "type": "list[float]", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_effect_size",
            "desc": "Calculate effect size between groups.",
            "params": [
                {"name": "group1", "type": "list[float]", "default": _R},
                {"name": "group2", "type": "list[float]", "default": _R},
                {"name": "measure", "type": "str", "default": "'cohens_d'"},
                {"name": "pooled", "type": "bool", "default": "True"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_normality_test",
            "desc": "Test whether data follows a normal distribution.",
            "params": [
                {"name": "data", "type": "list[float]", "default": _R},
                {"name": "method", "type": "str", "default": "'shapiro'"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_posthoc_test",
            "desc": "Run post-hoc pairwise comparisons after significant ANOVA/Kruskal.",
            "params": [
                {"name": "groups", "type": "list[list[float]]", "default": _R},
                {"name": "group_names", "type": "list[str]", "default": "None"},
                {"name": "method", "type": "str", "default": "'tukey'"},
            ],
            "returns": "str (JSON)",
        },
        {
            "name": "stats_p_to_stars",
            "desc": "Convert p-value to significance stars (*, **, ***, ns).",
            "params": [
                {"name": "p_value", "type": "float", "default": _R},
                {"name": "thresholds", "type": "list[float]", "default": "None"},
            ],
            "returns": "str (JSON)",
        },
    ],
}

# EOF
