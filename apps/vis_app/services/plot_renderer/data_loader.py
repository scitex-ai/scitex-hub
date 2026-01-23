#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Loading for Plot Rendering
"""

import os
import pandas as pd


def load_data_from_spec(plot_spec):
    """
    Load data from plot specification.

    Args:
        plot_spec: Dictionary with either 'data' (inline) or 'csv_path' (file)

    Returns:
        DataFrame with plot data
    """
    csv_path = plot_spec.get('csv_path')
    inline_data = plot_spec.get('data')

    if inline_data:
        # Convert inline data array to DataFrame
        # Supports [[x1, y1], [x2, y2], ...] format
        df = pd.DataFrame(inline_data, columns=['x', 'y'])
    elif csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        raise ValueError(
            f"No data provided. Specify either 'data' (inline array) or 'csv_path' (file path)"
        )

    return df


# EOF
