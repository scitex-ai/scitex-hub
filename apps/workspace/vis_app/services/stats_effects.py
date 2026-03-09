"""Stats Effects - Delegates to scitex.stats.effect_sizes.

Thin wrapper maintaining the same API surface while delegating
effect size computations to the scitex package.
"""

from typing import List, Optional

import numpy as np


def compute_effect_size(
    effect_size_name: str, groups: List[np.ndarray]
) -> Optional[float]:
    """Compute effect size via scitex.stats.effect_sizes."""
    if len(groups) != 2:
        return None

    from scitex.stats.effect_sizes import cliffs_delta, cohens_d

    g1, g2 = groups[0], groups[1]

    if effect_size_name == "cohens_d":
        return cohens_d(g1, g2)
    elif effect_size_name == "cliffs_delta":
        return cliffs_delta(g1, g2)
    elif effect_size_name == "glass_delta":
        mean_diff = np.mean(g1) - np.mean(g2)
        ctrl_std = np.std(g2, ddof=1)
        return mean_diff / ctrl_std if ctrl_std != 0 else 0.0
    return None


def interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d via scitex."""
    from scitex.stats.effect_sizes import interpret_cohens_d as _interpret

    return _interpret(d)


def interpret_cliffs_delta(delta: float) -> str:
    """Interpret Cliff's delta via scitex."""
    from scitex.stats.effect_sizes import interpret_cliffs_delta as _interpret

    return _interpret(delta)


def infer_outcome_type(groups: List[np.ndarray]) -> str:
    """Infer outcome type from data ('continuous', 'ordinal', or 'binary')."""
    all_values = np.concatenate(groups)
    unique = np.unique(all_values)
    if len(unique) <= 2:
        return "binary"
    if len(unique) <= 10:
        return "ordinal"
    return "continuous"
