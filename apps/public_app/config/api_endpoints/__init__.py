#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API endpoint definitions by category."""

from .plot import PLOT_CATEGORY
from .project import PROJECT_CATEGORY
from .public import PUBLIC_CATEGORY
from .scholar import SCHOLAR_CATEGORY
from .stats import STATS_CATEGORY
from .writer import WRITER_CATEGORY

__all__ = [
    "PUBLIC_CATEGORY",
    "SCHOLAR_CATEGORY",
    "WRITER_CATEGORY",
    "PROJECT_CATEGORY",
    "PLOT_CATEGORY",
    "STATS_CATEGORY",
]
