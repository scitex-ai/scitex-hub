#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/utils.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/utils.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Utility Views

Helper views and shared functionality.
"""

import logging

from django.shortcuts import render

logger = logging.getLogger("scitex")


def demo(request):
    """Demo page."""
    return render(request, "public_app/demo.html")


# EOF
