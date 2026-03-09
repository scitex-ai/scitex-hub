"""Stats Context - Context building from plot metadata."""

from typing import Dict, List, Optional

import numpy as np

from .stats_effects import infer_outcome_type

try:
    from scitex.stats import StatContext

    SCITEX_STATS_AVAILABLE = True
except ImportError:
    SCITEX_STATS_AVAILABLE = False
    StatContext = Dict


def build_stat_context(data: Dict):
    """Build StatContext from request data."""
    if not SCITEX_STATS_AVAILABLE:
        raise ImportError("scitex.stats not available")
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


def build_context_from_plot_metadata(
    element_bboxes: Dict, column_mapping: Dict, csv_data: List[List]
) -> Optional[StatContext]:
    """Build StatContext from plot metadata and CSV data."""
    if not SCITEX_STATS_AVAILABLE:
        return None
    if not csv_data or len(csv_data) < 2:
        return None

    headers = csv_data[0]
    rows = csv_data[1:]
    y_columns = list(set(column_mapping.values()))

    if not y_columns:
        return None

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

    n_groups = len(groups)
    sample_sizes = [len(g) for g in groups]
    outcome_type = infer_outcome_type(groups)

    return StatContext(
        n_groups=n_groups,
        sample_sizes=sample_sizes,
        outcome_type=outcome_type,
        design="between",
        paired=False,
        has_control_group=False,
        n_factors=1,
        group_names=group_names,
    )
