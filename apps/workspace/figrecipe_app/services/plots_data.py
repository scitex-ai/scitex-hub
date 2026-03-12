"""Plots Data - Data detection and preparation utilities."""

import re
from typing import List, Tuple

import pandas as pd


def detect_xy_column_pairs(cols: list) -> List[Tuple[str, str, str]]:
    """
    Detect paired X/Y columns from scitex gallery CSV format.
    Column naming convention: ax-row-X-col-Y_trace-id-NAME_variable-{x|y}
    """
    pairs = []
    y_cols = []
    x_cols = []

    for col in cols:
        if col.endswith("_variable-y") or col.endswith("variable_y"):
            y_cols.append(col)
        elif col.endswith("_variable-x") or col.endswith("variable_x"):
            x_cols.append(col)

    for y_col in y_cols:
        base = y_col.replace("_variable-y", "").replace("variable_y", "")

        x_col = None
        for xc in x_cols:
            xc_base = xc.replace("_variable-x", "").replace("variable_x", "")
            if xc_base == base:
                x_col = xc
                break

        if x_col is None and x_cols:
            x_col = x_cols[0]

        match = re.search(r"trace-id-([^_]+)", y_col)
        trace_name = match.group(1).replace("-", " ") if match else y_col

        if x_col:
            pairs.append((x_col, y_col, trace_name))

    return pairs


def prepare_dataframe(csv_data: List[List]) -> pd.DataFrame:
    """Convert CSV data to pandas DataFrame with numeric conversion."""
    if not csv_data or len(csv_data) < 2:
        raise ValueError("CSV data must have at least 2 rows (header + data)")

    headers = csv_data[0]
    rows = csv_data[1:]
    df = pd.DataFrame(rows, columns=headers)

    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass

    return df
