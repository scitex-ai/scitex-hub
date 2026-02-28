#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arXiv categories data - official taxonomy.

DEPRECATED: arXiv integration moved to separate service.
This data is kept for reference only.

Category data is stored in arxiv_categories.json alongside this file.
"""

from __future__ import annotations

import json
import os

_DATA_FILE = os.path.join(os.path.dirname(__file__), "arxiv_categories.json")


def _load_categories():
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_categories():
    """Return all arXiv categories as a single list."""
    data = _load_categories()
    result = []
    for section in data.values():
        result.extend(section)
    return result


# Legacy named lists (loaded on demand to avoid startup cost)
def _get_section(key):
    return _load_categories()[key]


CS_CATEGORIES = None
MATH_CATEGORIES = None
PHYSICS_CATEGORIES = None
STAT_CATEGORIES = None
QBIO_CATEGORIES = None


def __getattr__(name):
    _map = {
        "CS_CATEGORIES": "cs",
        "MATH_CATEGORIES": "math",
        "PHYSICS_CATEGORIES": "physics",
        "STAT_CATEGORIES": "stat",
        "QBIO_CATEGORIES": "q-bio",
    }
    if name in _map:
        return _get_section(_map[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# EOF
