#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FigzBundle constants and lazy imports."""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

SCITEX_CODE_PATH = os.environ.get(
    "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


def get_figz_class():
    """Lazy import Figz class."""
    from scitex.fig import Figz

    return Figz


def get_bundle_module():
    """Lazy import bundle module."""
    import scitex.io.bundle as bundle

    return bundle


# Supported extensions (unified .stx + legacy)
STX_EXTENSION = ".stx"
FIGZ_EXTENSION = ".figz"
BUNDLE_EXTENSIONS = (STX_EXTENSION, FIGZ_EXTENSION)

# Constants for backward compatibility
SPEC_FILE = "spec.json"
STYLE_FILE = "style.json"
EXPORTS_DIR = "exports"
CACHE_DIR = "cache"
GEOMETRY_FILE = "geometry_px.json"
PANEL_LABELS = list("ABCDEFGH")


# EOF
