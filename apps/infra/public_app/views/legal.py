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
    env keys SCITEX_HUB_COMPANY_*). Unfinalized values (address, phone,
    public email) stay empty in the environment and the template renders
    an explicit 準備中 notice — never a fake value.

    ``page_title_override`` / ``page_meta_description`` are consumed by
    global_base_partials/page_title.html and global_head_meta.html.
    These MUST be plain context variables, not template {% block %}
    overrides in tokushoho.html: global_base.html reaches both partials
    via {% include %}, and Django's block/extends inheritance does not
    cross an {% include %} boundary, so a {% block title %} /
    {% block meta_description %} in the page template would silently
    never take effect (caught by
    tests/apps/public_app/views/test_commerce.py::TestTokushohoRealDefaults).
    """
    page_meta_description = (
        f"{settings.COMPANY_NAME}の特定商取引法に基づく表記"
        "(販売業者、運営統括責任者、所在地、支払方法、返品・キャンセル等)。"
    )
    context = {
        "company_name": settings.COMPANY_NAME,
        "company_representative": settings.COMPANY_REPRESENTATIVE,
        "company_address": settings.COMPANY_ADDRESS,
        "company_phone": settings.COMPANY_PHONE,
        "company_contact_email": settings.COMPANY_CONTACT_EMAIL,
        "billing_plans": settings.BILLING_PLANS,
        "page_title_override": "特定商取引法に基づく表記 - SciTeX",
        "page_meta_description": page_meta_description,
    }
    return render(request, "public_app/legal/tokushoho.html", context)


# EOF
