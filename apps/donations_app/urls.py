#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-16 02:01:04 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/donations_app/urls.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/donations_app/urls.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------
from django.urls import path

from . import views

app_name = "donations_app"

urlpatterns = [
    # Pricing and subscription pages
    path("pricing/", views.pricing, name="pricing"),
    path("subscribe/", views.premium_subscription, name="subscribe"),
    path("donation/success/", views.donation_success, name="donation_success"),
    path("premium/", views.premium_subscription, name="premium"),
    path("fundraising/", views.fundraising, name="fundraising"),
    path(
        "donation-success/<int:donation_id>/",
        views.donation_success,
        name="donation_success_detail",
    ),
]

# EOF
