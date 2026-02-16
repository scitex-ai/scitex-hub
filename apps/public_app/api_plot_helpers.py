#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot API helpers — thin wrapper around scitex.plt spec builders and renderer."""

import logging

from scitex.plt import build_spec, build_spec_from_csv, render_spec_to_bytes

logger = logging.getLogger("scitex")

__all__ = ["build_spec_from_query", "build_spec_from_csv", "render_figure"]


def build_spec_from_query(params: dict) -> dict:
    """Convert GET query parameters to a figrecipe spec dict.

    Delegates to ``scitex.plt.build_spec``.
    """
    return build_spec(params)


def render_figure(spec: dict) -> bytes:
    """Render a figrecipe spec to PNG bytes.

    Delegates to ``scitex.plt.render_spec_to_bytes``.
    """
    return render_spec_to_bytes(spec)


# EOF
