#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/legal.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/legal.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Legal Pages Views

Handles contact, privacy policy, terms of use, cookie policy, and the
特定商取引法に基づく表記 (Specified Commercial Transactions Act) pages.
"""

from django.conf import settings
from django.shortcuts import render
from ..pricing import published_price_rows


def donate(request):
    """Donate page - support SciTeX development."""
    return render(request, "public_app/legal/donate.html")


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


def tokushoho(request):
    """特定商取引法に基づく表記 (Specified Commercial Transactions Act).

    All values are config-driven (config/settings/settings_commerce.py,
    env keys SCITEX_HUB_COMPANY_*). Unfinalized values (public email)
    stay empty in the environment and the template renders an explicit
    準備中 notice — never a fake value.
    """
    context = {
        "company_name": settings.COMPANY_NAME,
        "company_representative": settings.COMPANY_REPRESENTATIVE,
        "company_address": settings.COMPANY_ADDRESS,
        "company_phone": settings.COMPANY_PHONE,
        "company_contact_email": settings.COMPANY_CONTACT_EMAIL,
        "billing_plans": settings.BILLING_PLANS,
        # Prices come from data/pricing.json, never from literals in the
        # template — test_pricing_ssot.py scans this app's templates and
        # views for hard-coded amounts. BILLING_PLANS stays empty on
        # purpose (checkout is shut); these are DISPLAY prices only, and
        # published_price_rows() already hides anything not yet for sale.
        "published_price_rows": published_price_rows(),
    }
    return render(request, "public_app/legal/tokushoho.html", context)


# EOF
