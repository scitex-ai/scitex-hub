#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layout helpers for FigzBundle."""

from __future__ import annotations

from typing import Dict


def get_layout_positions(layout: str) -> Dict[str, Dict]:
    """Get default panel positions for a layout."""
    layouts = {
        "1x1": {"A": {"x": 0, "y": 0, "width": 1, "height": 1}},
        "2x1": {
            "A": {"x": 0, "y": 0, "width": 0.5, "height": 1},
            "B": {"x": 0.5, "y": 0, "width": 0.5, "height": 1},
        },
        "1x2": {
            "A": {"x": 0, "y": 0, "width": 1, "height": 0.5},
            "B": {"x": 0, "y": 0.5, "width": 1, "height": 0.5},
        },
        "2x2": {
            "A": {"x": 0, "y": 0, "width": 0.5, "height": 0.5},
            "B": {"x": 0.5, "y": 0, "width": 0.5, "height": 0.5},
            "C": {"x": 0, "y": 0.5, "width": 0.5, "height": 0.5},
            "D": {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5},
        },
    }
    return layouts.get(layout, layouts["1x1"])


# EOF
