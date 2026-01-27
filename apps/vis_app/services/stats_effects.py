"""Stats Effects - Effect size computations and interpretations."""

from typing import List, Optional

import numpy as np


def compute_effect_size(
    effect_size_name: str, groups: List[np.ndarray]
) -> Optional[float]:
    """Compute effect size for given groups."""
    if len(groups) != 2:
        return None

    g1, g2 = groups[0], groups[1]

    if effect_size_name == "cohens_d":
        return _compute_cohens_d(g1, g2)
    elif effect_size_name == "cliffs_delta":
        return _compute_cliffs_delta(g1, g2)
    elif effect_size_name == "glass_delta":
        return _compute_glass_delta(g1, g2)
    return None


def _compute_cohens_d(g1: np.ndarray, g2: np.ndarray) -> float:
    """Compute Cohen's d effect size."""
    mean_diff = np.mean(g1) - np.mean(g2)
    pooled_std = np.sqrt((np.var(g1, ddof=1) + np.var(g2, ddof=1)) / 2)
    if pooled_std == 0:
        return 0.0
    return mean_diff / pooled_std


def _compute_cliffs_delta(g1: np.ndarray, g2: np.ndarray) -> float:
    """Compute Cliff's delta effect size."""
    n1, n2 = len(g1), len(g2)
    dominance = 0
    for x in g1:
        for y in g2:
            if x > y:
                dominance += 1
            elif x < y:
                dominance -= 1
    return dominance / (n1 * n2)


def _compute_glass_delta(g1: np.ndarray, g2: np.ndarray) -> float:
    """Compute Glass's delta (using control group std)."""
    mean_diff = np.mean(g1) - np.mean(g2)
    control_std = np.std(g2, ddof=1)
    if control_std == 0:
        return 0.0
    return mean_diff / control_std


def interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def interpret_cliffs_delta(delta: float) -> str:
    """Interpret Cliff's delta effect size."""
    abs_delta = abs(delta)
    if abs_delta < 0.147:
        return "negligible"
    elif abs_delta < 0.33:
        return "small"
    elif abs_delta < 0.474:
        return "medium"
    else:
        return "large"


def infer_outcome_type(groups: List[np.ndarray]) -> str:
    """Infer outcome type from data ('continuous', 'ordinal', or 'binary')."""
    all_values = np.concatenate(groups)
    unique = np.unique(all_values)
    if len(unique) <= 2:
        return "binary"
    if len(unique) <= 10:
        return "ordinal"
    return "continuous"
