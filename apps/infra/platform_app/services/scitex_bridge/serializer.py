#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/platform_app/services/scitex_bridge/serializer.py
"""
Result serializer for ScitexBridge.

Converts scitex return values into JSON-safe Python dicts so that Django
views can pass them directly to ``JsonResponse``.

Handled types
-------------
- None / bool / int / float / str  — passed through as-is
- pathlib.Path                      — converted to posix string
- dict                              — recursively serialized
- list / tuple                      — recursively serialized
- pandas.DataFrame                  — orient="records" dict
- numpy.ndarray                     — nested list via .tolist()
- matplotlib Figure                 — base64-encoded PNG
- objects with __dict__             — serialized via __dict__
- everything else                   — str() fallback
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def serialize_result(result: Any) -> Any:
    """
    Recursively convert *result* into a JSON-safe value.

    Parameters
    ----------
    result:
        Raw return value from a scitex function call.

    Returns
    -------
    A JSON-serialisable Python object (dict / list / str / number / bool / None).
    """
    # --- Primitives ---------------------------------------------------------
    if result is None or isinstance(result, (bool, int, float, str)):
        return result

    # --- Path ---------------------------------------------------------------
    if isinstance(result, Path):
        return result.as_posix()

    # --- Dict ---------------------------------------------------------------
    if isinstance(result, dict):
        return {str(k): serialize_result(v) for k, v in result.items()}

    # --- List / tuple -------------------------------------------------------
    if isinstance(result, (list, tuple)):
        return [serialize_result(item) for item in result]

    # --- pandas DataFrame ---------------------------------------------------
    try:
        import pandas as pd

        if isinstance(result, pd.DataFrame):
            return _serialize_dataframe(result)
        if isinstance(result, pd.Series):
            return result.tolist()
    except ImportError:
        pass

    # --- numpy ndarray ------------------------------------------------------
    try:
        import numpy as np

        if isinstance(result, np.ndarray):
            return result.tolist()
        # numpy scalars
        if isinstance(result, np.generic):
            return result.item()
    except ImportError:
        pass

    # --- matplotlib Figure --------------------------------------------------
    try:
        import matplotlib.figure

        if isinstance(result, matplotlib.figure.Figure):
            return _serialize_figure(result)
    except ImportError:
        pass

    # --- objects with __dict__ ----------------------------------------------
    if hasattr(result, "__dict__") and not callable(result):
        try:
            return {
                "__type__": type(result).__name__,
                **{
                    k: serialize_result(v)
                    for k, v in vars(result).items()
                    if not k.startswith("_")
                },
            }
        except Exception:
            pass

    # --- Fallback -----------------------------------------------------------
    return str(result)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _serialize_dataframe(df) -> dict:
    """Convert a DataFrame to a records-oriented dict with column metadata."""
    try:
        records = df.where(df.notna(), None).to_dict(orient="records")
    except Exception:
        records = []

    return {
        "__type__": "DataFrame",
        "columns": list(df.columns),
        "records": records,
        "shape": list(df.shape),
    }


def _serialize_figure(fig) -> dict:
    """Encode a matplotlib Figure as a base64 PNG string."""
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=96)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return {
            "__type__": "Figure",
            "format": "png",
            "encoding": "base64",
            "data": encoded,
        }
    except Exception as exc:
        logger.warning("ScitexBridge serializer: could not encode figure: %s", exc)
        return {"__type__": "Figure", "error": str(exc)}
    finally:
        buf.close()


# EOF
