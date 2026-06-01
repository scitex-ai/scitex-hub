#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``scitex-hub app *`` command surface.

This module is a thin re-export of the :mod:`._app` subpackage. The actual
verb implementations live in focused per-theme files under ``_app/`` to keep
each module well under the 512-line cap. External callers (``main.py``,
``tests``) import ``app`` from here unchanged.
"""

from __future__ import annotations

from ._app import app

__all__ = ["app"]

# EOF
