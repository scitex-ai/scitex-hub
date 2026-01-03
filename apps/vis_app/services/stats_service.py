"""
Stats Service - Business logic for statistical testing operations.

Handles:
- Building statistical contexts from plot metadata
- Running statistical tests on data
- Computing effect sizes
- Interpreting test results
- Generating test annotations
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Import from scitex.stats
try:
    from scitex.stats import (
        StatContext,
        StatResult,
        TEST_RULES,
        check_applicable,
        get_menu_items,
        p_to_stars,
        recommend_effect_sizes,
        recommend_posthoc,
        recommend_tests,
    )
    from scitex.stats.auto import (
        apply_multiple_correction,
        compute_summary_from_groups,
        format_for_inspector,
        format_test_line,
    )

    SCITEX_STATS_AVAILABLE = True
except ImportError:
    SCITEX_STATS_AVAILABLE = False
    # Define placeholder types for type hints when scitex.stats unavailable
    StatContext = Dict
    StatResult = Dict
    TEST_RULES = {}
    check_applicable = lambda *args, **kwargs: False
    get_menu_items = lambda *args, **kwargs: []
    p_to_stars = lambda p: ''
    recommend_effect_sizes = lambda *args, **kwargs: []
    recommend_posthoc = lambda *args, **kwargs: []
    recommend_tests = lambda *args, **kwargs: []
    apply_multiple_correction = lambda *args, **kwargs: []
    compute_summary_from_groups = lambda *args, **kwargs: {}
    format_for_inspector = lambda *args, **kwargs: {}
    format_test_line = lambda *args, **kwargs: ''


class StatsService:
    """Service for statistical testing operations."""

    @staticmethod
    def is_scitex_stats_available() -> bool:
        """Check if scitex.stats module is available."""
        return SCITEX_STATS_AVAILABLE

    @staticmethod
    def build_stat_context(data: Dict) -> StatContext:
        """
        Build StatContext from request data.

        Args:
            data: Dictionary with context parameters

        Returns:
            StatContext object

        Raises:
            ValueError: If context parameters are invalid
        """
        try:
            return StatContext(
                n_groups=data.get("n_groups", 2),
                sample_sizes=data.get("sample_sizes", [10, 10]),
                outcome_type=data.get("outcome_type", "continuous"),
                design=data.get("design", "between"),
                paired=data.get("paired"),
                has_control_group=data.get("has_control_group", False),
                n_factors=data.get("n_factors", 1),
                normality_ok=data.get("normality_ok"),
                variance_homogeneity_ok=data.get("variance_homogeneity_ok"),
                group_names=data.get("group_names"),
                control_group_name=data.get("control_group_name"),
            )
        except Exception as e:
            raise ValueError(f"Invalid context: {str(e)}")

    @staticmethod
    def get_applicable_tests_menu(
        ctx: StatContext,
        include_families: Optional[List[str]] = None,
        exclude_families: Optional[List[str]] = None
    ) -> Dict:
        """
        Get menu items for right-click context menu.

        Args:
            ctx: Statistical context
            include_families: Families to include
            exclude_families: Families to exclude

        Returns:
            Dictionary with items, recommended tests, effect sizes, and posthoc tests
        """
        items = get_menu_items(
            ctx,
            include_families=include_families,
            exclude_families=exclude_families,
        )

        # Get recommendations
        recommended = recommend_tests(ctx, top_k=3)
        effect_sizes = recommend_effect_sizes(ctx, top_k=2)
        posthoc = recommend_posthoc(ctx, top_k=2) if ctx.n_groups >= 3 else []

        return {
            'items': items,
            'recommended': recommended,
            'effect_sizes': effect_sizes,
            'posthoc': posthoc,
            'context': ctx.to_dict(),
        }

    @staticmethod
    def run_test(
        test_name: str,
        groups: List[np.ndarray],
        paired: bool = False
    ) -> Optional[Dict]:
        """
        Run a statistical test on data.

        Args:
            test_name: Name of the test
            groups: List of data arrays for each group
            paired: Whether the test is paired

        Returns:
            Dictionary with test results or None if test not implemented
        """
        from scipy import stats

        # T-tests
        if test_name == "ttest_ind":
            if len(groups) != 2:
                return None
            stat, pval = stats.ttest_ind(groups[0], groups[1])
            return {
                "test_name": "ttest_ind",
                "stat": float(stat),
                "p_raw": float(pval),
                "df": len(groups[0]) + len(groups[1]) - 2,
            }

        elif test_name == "ttest_rel":
            if len(groups) != 2:
                return None
            stat, pval = stats.ttest_rel(groups[0], groups[1])
            return {
                "test_name": "ttest_rel",
                "stat": float(stat),
                "p_raw": float(pval),
                "df": len(groups[0]) - 1,
            }

        elif test_name == "ttest_1samp":
            if len(groups) != 1:
                return None
            stat, pval = stats.ttest_1samp(groups[0], popmean=0)
            return {
                "test_name": "ttest_1samp",
                "stat": float(stat),
                "p_raw": float(pval),
                "df": len(groups[0]) - 1,
            }

        # Mann-Whitney U
        elif test_name == "mannwhitneyu":
            if len(groups) != 2:
                return None
            stat, pval = stats.mannwhitneyu(groups[0], groups[1], alternative='two-sided')
            return {
                "test_name": "mannwhitneyu",
                "stat": float(stat),
                "p_raw": float(pval),
            }

        # Wilcoxon signed-rank
        elif test_name == "wilcoxon":
            if len(groups) != 2:
                return None
            stat, pval = stats.wilcoxon(groups[0], groups[1])
            return {
                "test_name": "wilcoxon",
                "stat": float(stat),
                "p_raw": float(pval),
            }

        # Brunner-Munzel
        elif test_name == "brunner_munzel":
            if len(groups) != 2:
                return None
            stat, pval = stats.brunnermunzel(groups[0], groups[1])
            return {
                "test_name": "brunner_munzel",
                "stat": float(stat),
                "p_raw": float(pval),
            }

        # ANOVA
        elif test_name == "anova_oneway":
            stat, pval = stats.f_oneway(*groups)
            return {
                "test_name": "anova_oneway",
                "stat": float(stat),
                "p_raw": float(pval),
            }

        # Kruskal-Wallis
        elif test_name == "kruskal":
            stat, pval = stats.kruskal(*groups)
            return {
                "test_name": "kruskal",
                "stat": float(stat),
                "p_raw": float(pval),
            }

        # Chi-square test
        elif test_name == "chi2":
            # Requires different input format
            return None

        return None

    @staticmethod
    def compute_effect_size(
        effect_size_name: str,
        groups: List[np.ndarray]
    ) -> Optional[float]:
        """
        Compute effect size for given groups.

        Args:
            effect_size_name: Name of effect size (cohens_d, cliffs_delta, etc.)
            groups: List of data arrays

        Returns:
            Effect size value or None if not computable
        """
        if len(groups) != 2:
            return None

        g1, g2 = groups[0], groups[1]

        if effect_size_name == "cohens_d":
            # Cohen's d
            mean_diff = np.mean(g1) - np.mean(g2)
            pooled_std = np.sqrt((np.var(g1, ddof=1) + np.var(g2, ddof=1)) / 2)
            if pooled_std == 0:
                return 0.0
            return mean_diff / pooled_std

        elif effect_size_name == "cliffs_delta":
            # Cliff's delta
            n1, n2 = len(g1), len(g2)
            dominance = 0
            for x in g1:
                for y in g2:
                    if x > y:
                        dominance += 1
                    elif x < y:
                        dominance -= 1
            return dominance / (n1 * n2)

        elif effect_size_name == "glass_delta":
            # Glass's delta (using control group std)
            mean_diff = np.mean(g1) - np.mean(g2)
            control_std = np.std(g2, ddof=1)
            if control_std == 0:
                return 0.0
            return mean_diff / control_std

        return None

    @staticmethod
    def interpret_cohens_d(d: float) -> str:
        """
        Interpret Cohen's d effect size.

        Args:
            d: Cohen's d value

        Returns:
            Interpretation string
        """
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    @staticmethod
    def interpret_cliffs_delta(delta: float) -> str:
        """
        Interpret Cliff's delta effect size.

        Args:
            delta: Cliff's delta value

        Returns:
            Interpretation string
        """
        abs_delta = abs(delta)
        if abs_delta < 0.147:
            return "negligible"
        elif abs_delta < 0.33:
            return "small"
        elif abs_delta < 0.474:
            return "medium"
        else:
            return "large"

    @staticmethod
    def infer_outcome_type(groups: List[np.ndarray]) -> str:
        """
        Infer outcome type from data.

        Args:
            groups: List of data arrays

        Returns:
            'continuous', 'ordinal', or 'binary'
        """
        # Combine all groups
        all_values = np.concatenate(groups)

        # Check for binary
        unique = np.unique(all_values)
        if len(unique) <= 2:
            return "binary"

        # Check for ordinal (small number of unique values)
        if len(unique) <= 10:
            return "ordinal"

        return "continuous"

    @staticmethod
    def run_statistical_test_with_context(
        test_name: str,
        groups_data: List[Dict],
        paired: bool = False,
        correction_method: Optional[str] = None
    ) -> Dict:
        """
        Run statistical test with full context and formatting.

        Args:
            test_name: Name of the test
            groups_data: List of group dictionaries with 'name' and 'values'
            paired: Whether the test is paired
            correction_method: Multiple comparison correction method

        Returns:
            Dictionary with test results, summary, annotation, etc.

        Raises:
            ValueError: If invalid input
        """
        if len(groups_data) < 2:
            raise ValueError("At least 2 groups required")

        # Extract group names and values
        group_names = [g.get("name", f"Group_{i+1}") for i, g in enumerate(groups_data)]
        group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]

        # Compute summary statistics
        summary = compute_summary_from_groups(group_values, group_names)

        # Run the test
        result = StatsService.run_test(test_name, group_values, paired=paired)

        if result is None:
            raise ValueError(f"Test {test_name} not implemented")

        # Apply correction if needed
        if correction_method:
            results = apply_multiple_correction([result], method=correction_method)
            result = results[0]

        # Get stars
        p_value = result.get("p_adj") or result.get("p_raw")
        stars = p_to_stars(p_value) if p_value is not None else ""

        # Compute effect size
        effect_size = None
        if len(group_values) == 2:
            # For two groups, compute Cliff's delta by default
            delta = StatsService.compute_effect_size("cliffs_delta", group_values)
            if delta is not None:
                effect_size = {
                    "name": "cliffs_delta",
                    "value": float(delta),
                    "interpretation": StatsService.interpret_cliffs_delta(delta),
                }

        # Format result
        formatted = format_test_line(result, effect_size=effect_size)

        # Create annotation for plot
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
    def build_context_from_plot_metadata(
        element_bboxes: Dict,
        column_mapping: Dict,
        csv_data: List[List]
    ) -> Optional[StatContext]:
        """
        Build StatContext from plot metadata and CSV data.

        Args:
            element_bboxes: Element bounding boxes from plot
            column_mapping: Mapping of elements to CSV columns
            csv_data: CSV data with header and rows

        Returns:
            StatContext or None if cannot be inferred
        """
        if not csv_data or len(csv_data) < 2:
            return None

        # Parse CSV
        headers = csv_data[0]
        rows = csv_data[1:]

        # Get unique Y columns from column_mapping
        y_columns = list(set(column_mapping.values()))

        if not y_columns:
            return None

        # Extract data for each group
        groups = []
        group_names = []

        for y_col in y_columns:
            if y_col not in headers:
                continue

            col_idx = headers.index(y_col)
            values = [float(row[col_idx]) for row in rows if row[col_idx]]
            groups.append(np.array(values))
            group_names.append(y_col)

        if len(groups) < 2:
            return None

        # Infer properties
        n_groups = len(groups)
        sample_sizes = [len(g) for g in groups]
        outcome_type = StatsService.infer_outcome_type(groups)
        design = "between"  # Default assumption
        paired = False  # Default assumption

        return StatContext(
            n_groups=n_groups,
            sample_sizes=sample_sizes,
            outcome_type=outcome_type,
            design=design,
            paired=paired,
            has_control_group=False,
            n_factors=1,
            group_names=group_names,
        )

    @staticmethod
    def run_all_applicable_tests(
        groups_data: List[Dict],
        correction_method: str = "fdr_bh",
        max_tests: int = 5
    ) -> List[Dict]:
        """
        Run all applicable tests for given data.

        Args:
            groups_data: List of group dictionaries
            correction_method: Multiple comparison correction method
            max_tests: Maximum number of tests to run

        Returns:
            List of test result dictionaries
        """
        # Extract data
        group_values = [np.array(g.get("values", []), dtype=float) for g in groups_data]
        group_names = [g.get("name", f"Group_{i+1}") for i, g in enumerate(groups_data)]

        # Build context
        n_groups = len(group_values)
        sample_sizes = [len(g) for g in group_values]
        outcome_type = StatsService.infer_outcome_type(group_values)

        ctx = StatContext(
            n_groups=n_groups,
            sample_sizes=sample_sizes,
            outcome_type=outcome_type,
            design="between",
            paired=False,
            group_names=group_names,
        )

        # Get recommended tests
        recommended_tests = recommend_tests(ctx, top_k=max_tests)

        # Run each test
        results = []
        for test_name in recommended_tests:
            try:
                result = StatsService.run_statistical_test_with_context(
                    test_name=test_name,
                    groups_data=groups_data,
                    paired=False,
                    correction_method=correction_method
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to run test {test_name}: {e}")
                continue

        return results
