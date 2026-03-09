#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/legal.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/legal.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Legal Pages Views

Handles contact, privacy policy, terms of use, and cookie policy pages.
"""

from django.shortcuts import render


def contact(request):
    """Contact page."""
    return render(request, "public_app/legal/contact.html")


def privacy_policy(request):
    """Privacy policy page."""
    return render(request, "public_app/legal/privacy_policy.html")


def terms_of_use(request):
    """Terms of use page."""
    return render(request, "public_app/legal/terms_of_use.html")


def cookie_policy(request):
    """Cookie policy page."""
    return render(request, "public_app/legal/cookie_policy.html")


# EOF
