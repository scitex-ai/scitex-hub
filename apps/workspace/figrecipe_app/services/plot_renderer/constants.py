#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants and Unit Conversions for Plot Rendering
"""

# Unit conversion constants
MM_PER_INCH = 25.4
PT_PER_INCH = 72


def mm_to_inch(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / MM_PER_INCH


def mm_to_pt(mm: float) -> float:
    """Convert millimeters to points."""
    return mm * PT_PER_INCH / MM_PER_INCH


def pt_to_mm(pt: float) -> float:
    """Convert points to millimeters."""
    return pt * MM_PER_INCH / PT_PER_INCH


# EOF
