#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stats API endpoint definitions."""

STATS_CATEGORY = {
    "name": "Stats API",
    "description": "Statistical testing, descriptive statistics, effect sizes, power analysis, and multiple comparison correction. Powered by scitex.stats.",
    "base_path": "/api",
    "auth_required": False,
    "endpoints": [
        {
            "method": "GET",
            "path": "/stats/plot/",
            "name": "Stats Quick Plot",
            "description": "Get a publication-ready statistical test figure by opening a URL in your browser. Returns raw PNG.",
            "params": [
                {
                    "name": "test_name",
                    "type": "string",
                    "required": True,
                    "desc": "Test: ttest_ind, ttest_paired, anova, mann_whitney, wilcoxon, kruskal, chi2",
                },
                {
                    "name": "data",
                    "type": "string",
                    "required": True,
                    "desc": "Comma-separated numbers",
                },
                {
                    "name": "data2",
                    "type": "string",
                    "required": False,
                    "desc": "Second group, comma-separated",
                },
                {
                    "name": "alternative",
                    "type": "string",
                    "required": False,
                    "desc": "two-sided (default), less, greater",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/calculate/",
            "name": "Run Statistical Tests",
            "description": "Execute statistical tests. Returns test statistics, p-values, effect sizes, and APA-formatted results. Supports JSON and CSV upload.",
            "params": [
                {
                    "name": "test_name",
                    "type": "string",
                    "required": True,
                    "desc": "Test: ttest_ind, ttest_paired, anova, mann_whitney, wilcoxon, kruskal, chi2",
                },
                {
                    "name": "data",
                    "type": "array",
                    "required": True,
                    "desc": "First data array",
                },
                {
                    "name": "data2",
                    "type": "array",
                    "required": False,
                    "desc": "Second data array for two-sample tests",
                },
                {
                    "name": "groups",
                    "type": "array",
                    "required": False,
                    "desc": "List of arrays for multi-group tests (ANOVA, Kruskal)",
                },
                {
                    "name": "alternative",
                    "type": "string",
                    "required": False,
                    "desc": "two-sided (default), less, greater",
                },
                {
                    "name": "plot",
                    "type": "bool",
                    "required": False,
                    "desc": "Set true to generate a publication-ready figure",
                },
                {
                    "name": "figure_format",
                    "type": "string",
                    "required": False,
                    "desc": "Set to 'png' for raw PNG image instead of JSON",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/describe/",
            "name": "Descriptive Statistics",
            "description": "Calculate mean, std, median, quartiles, skewness, kurtosis, and more.",
            "params": [
                {
                    "name": "data",
                    "type": "array",
                    "required": True,
                    "desc": "Array of numbers",
                },
                {
                    "name": "percentiles",
                    "type": "array",
                    "required": False,
                    "desc": "Custom percentiles, e.g., [25, 50, 75]",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/recommend/",
            "name": "Test Recommendations",
            "description": "Get recommendations for appropriate statistical tests based on data characteristics.",
            "params": [
                {
                    "name": "n_groups",
                    "type": "int",
                    "required": False,
                    "desc": "Number of groups (default: 2)",
                },
                {
                    "name": "sample_sizes",
                    "type": "array",
                    "required": False,
                    "desc": "List of sample sizes per group",
                },
                {
                    "name": "outcome_type",
                    "type": "string",
                    "required": False,
                    "desc": "continuous (default) or categorical",
                },
                {
                    "name": "design",
                    "type": "string",
                    "required": False,
                    "desc": "between (default) or within",
                },
                {
                    "name": "paired",
                    "type": "bool",
                    "required": False,
                    "desc": "Whether samples are paired",
                },
                {
                    "name": "has_control_group",
                    "type": "bool",
                    "required": False,
                    "desc": "Whether there is a control group",
                },
                {
                    "name": "top_k",
                    "type": "int",
                    "required": False,
                    "desc": "Number of recommendations (default: 3)",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/effect-size/",
            "name": "Effect Size",
            "description": "Calculate effect size: Cohen's d, eta-squared, epsilon-squared, Cliff's delta, probability of superiority.",
            "params": [
                {
                    "name": "measure",
                    "type": "string",
                    "required": True,
                    "desc": "cohens_d, eta_squared, epsilon_squared, cliffs_delta, prob_superiority",
                },
                {
                    "name": "group1",
                    "type": "array",
                    "required": True,
                    "desc": "First group data",
                },
                {
                    "name": "group2",
                    "type": "array",
                    "required": False,
                    "desc": "Second group data",
                },
                {
                    "name": "groups",
                    "type": "array",
                    "required": False,
                    "desc": "List of arrays for multi-group measures",
                },
                {
                    "name": "paired",
                    "type": "bool",
                    "required": False,
                    "desc": "Whether samples are paired (Cohen's d)",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/posthoc/",
            "name": "Post-hoc Tests",
            "description": "Pairwise post-hoc comparisons after significant ANOVA or Kruskal-Wallis.",
            "params": [
                {
                    "name": "method",
                    "type": "string",
                    "required": True,
                    "desc": "tukey, games_howell, dunnett",
                },
                {
                    "name": "groups",
                    "type": "array",
                    "required": True,
                    "desc": "List of group arrays",
                },
                {
                    "name": "group_names",
                    "type": "array",
                    "required": False,
                    "desc": "Names for each group",
                },
                {
                    "name": "alpha",
                    "type": "float",
                    "required": False,
                    "desc": "Significance level (default: 0.05)",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/power/",
            "name": "Power Analysis",
            "description": "Calculate statistical power or required sample size.",
            "params": [
                {
                    "name": "effect_size",
                    "type": "float",
                    "required": True,
                    "desc": "Expected effect size (Cohen's d)",
                },
                {
                    "name": "n",
                    "type": "int",
                    "required": False,
                    "desc": "Sample size (provide to calculate power)",
                },
                {
                    "name": "alpha",
                    "type": "float",
                    "required": False,
                    "desc": "Significance level (default: 0.05)",
                },
                {
                    "name": "power",
                    "type": "float",
                    "required": False,
                    "desc": "Desired power (default: 0.8). Used to calculate required n",
                },
                {
                    "name": "test_type",
                    "type": "string",
                    "required": False,
                    "desc": "one-sample, two-sample (default), paired",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/stats/correct/",
            "name": "Multiple Comparison Correction",
            "description": "Apply correction to p-values: Bonferroni, FDR (Benjamini-Hochberg), Holm, Sidak.",
            "params": [
                {
                    "name": "method",
                    "type": "string",
                    "required": True,
                    "desc": "bonferroni, fdr, holm, sidak",
                },
                {
                    "name": "pvalues",
                    "type": "array",
                    "required": True,
                    "desc": "Array of p-values",
                },
                {
                    "name": "alpha",
                    "type": "float",
                    "required": False,
                    "desc": "Significance level (default: 0.05)",
                },
            ],
        },
        {
            "method": "GET",
            "path": "/stats/flowchart/",
            "name": "Decision Flowchart",
            "description": "Statistical test decision tree as Mermaid diagram, JSON, or SVG.",
            "params": [
                {
                    "name": "format",
                    "type": "string",
                    "required": False,
                    "desc": "mermaid (default), json, svg",
                },
            ],
        },
    ],
}
