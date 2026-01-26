"""
Stats Service - Business logic for statistical testing operations.

Re-exports from specialized submodules:
- stats_tests: Individual test implementations
- stats_effects: Effect size computations
- stats_context: Context building from data
"""

import logging
from typing import Dict, List, Optional

import numpy as np

from .stats_context import build_context_from_plot_metadata, build_stat_context
from .stats_effects import (
    compute_effect_size,
    infer_outcome_type,
    interpret_cliffs_delta,
    interpret_cohens_d,
)
from .stats_tests import run_test

logger = logging.getLogger(__name__)

try:
    from scitex.stats import (
        StatContext,
        get_menu_items,
        p_to_stars,
        recommend_effect_sizes,
        recommend_posthoc,
        recommend_tests,
    )
    from scitex.stats.auto import (
        apply_multiple_correction,
        compute_summary_from_groups,
        format_test_line,
    )

    SCITEX_STATS_AVAILABLE = True
except ImportError:
    SCITEX_STATS_AVAILABLE = False
    StatContext = Dict
    get_menu_items = lambda *args, **kwargs: []
    p_to_stars = lambda p: ""
    recommend_effect_sizes = lambda *args, **kwargs: []
    recommend_posthoc = lambda *args, **kwargs: []
    recommend_tests = lambda *args, **kwargs: []
    apply_multiple_correction = lambda *args, **kwargs: []
    compute_summary_from_groups = lambda *args, **kwargs: {}
    format_test_line = lambda *args, **kwargs: ""


class StatsService:
    """Service for statistical testing operations."""

    is_scitex_stats_available = staticmethod(lambda: SCITEX_STATS_AVAILABLE)
    build_stat_context = staticmethod(build_stat_context)
    run_test = staticmethod(run_test)
    compute_effect_size = staticmethod(compute_effect_size)
    interpret_cohens_d = staticmethod(interpret_cohens_d)
    interpret_cliffs_delta = staticmethod(interpret_cliffs_delta)
    infer_outcome_type = staticmethod(infer_outcome_type)
    build_context_from_plot_metadata = staticmethod(build_context_from_plot_metadata)

    @staticmethod
    def get_applicable_tests_menu(
        ctx,
        include_families: Optional[List[str]] = None,
        exclude_families: Optional[List[str]] = None,
    ) -> Dict:
        """Get menu items for right-click context menu."""
        items = get_menu_items(
            ctx, include_families=include_families, exclude_families=exclude_families
        )
        recommended = recommend_tests(ctx, top_k=3)
        effect_sizes = recommend_effect_sizes(ctx, top_k=2)
        posthoc = recommend_posthoc(ctx, top_k=2) if ctx.n_groups >= 3 else []
        return {
            "items": items,
            "recommended": recommended,
            "effect_sizes": effect_sizes,
            "posthoc": posthoc,
            "context": ctx.to_dict(),
        }

    @staticmethod
    def run_statistical_test_with_context(
        test_name: str,
        groups_data: List[Dict],
        paired: bool = False,
        correction_method: Optional[str] = None,
    ) -> Dict:
        """Run statistical test with full context and formatting."""
        if len(groups_data) < 2:
            raise ValueError("At least 2 groups required")

        group_names = [
            g.get("name", f"Group_{i + 1}") for i, g in enumerate(groups_data)
        ]
        group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]

        summary = compute_summary_from_groups(group_values, group_names)
        result = run_test(test_name, group_values, paired=paired)

        if result is None:
            raise ValueError(f"Test {test_name} not implemented")

        if correction_method:
            results = apply_multiple_correction([result], method=correction_method)
            result = results[0]

        p_value = result.get("p_adj") or result.get("p_raw")
        stars = p_to_stars(p_value) if p_value is not None else ""

        effect_size = None
        if len(group_values) == 2:
            delta = compute_effect_size("cliffs_delta", group_values)
            if delta is not None:
                effect_size = {
                    "name": "cliffs_delta",
                    "value": float(delta),
                    "interpretation": interpret_cliffs_delta(delta),
                }

        formatted = format_test_line(result, effect_size=effect_size)
        annotation = {
            "type": "stat_bracket",
            "groups": group_names,
            "stars": stars,
            "p_value": p_value,
            "test_name": test_name,
        }

        return {
            "result": {
                **result,
                "stars": stars,
                "effect_size": effect_size,
                "summary": summary,
                "formatted": formatted,
            },
            "annotation": annotation,
        }

    @staticmethod
    def run_all_applicable_tests(
        groups_data: List[Dict],
        correction_method: str = "fdr_bh",
        max_tests: int = 5,
    ) -> List[Dict]:
        """Run all applicable tests for given data."""
        group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]
        group_names = [
            g.get("name", f"Group_{i + 1}") for i, g in enumerate(groups_data)
        ]

        n_groups = len(group_values)
        sample_sizes = [len(g) for g in group_values]
        outcome_type = infer_outcome_type(group_values)

        ctx = StatContext(
            n_groups=n_groups,
            sample_sizes=sample_sizes,
            outcome_type=outcome_type,
            design="between",
            paired=False,
            group_names=group_names,
        )

        recommended_tests = recommend_tests(ctx, top_k=max_tests)
        results = []

        for test_name in recommended_tests:
            try:
                result = StatsService.run_statistical_test_with_context(
                    test_name=test_name,
                    groups_data=groups_data,
                    paired=False,
                    correction_method=correction_method,
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to run test {test_name}: {e}")
                continue

        return results


__all__ = [
    "StatsService",
    "run_test",
    "compute_effect_size",
    "interpret_cohens_d",
    "interpret_cliffs_delta",
    "infer_outcome_type",
    "build_stat_context",
    "build_context_from_plot_metadata",
]
