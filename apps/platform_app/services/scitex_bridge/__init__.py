#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/platform_app/services/scitex_bridge/__init__.py
"""
SciTeX Bridge — public API.

Provides per-user, per-project access to the scitex Python package
with context isolation, serialization, and guarded module access.

Usage:
    from apps.platform_app.services.scitex_bridge import ScitexBridge

    bridge = ScitexBridge(project=project, user=request.user)
    result = bridge.call("stats", "describe", data)
    io_proxy = bridge.get_module("io")
"""

from .bridge import ScitexBridge

__all__ = ["ScitexBridge"]

# EOF
