#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Public App Page URLs

Template-serving and page views:
- SEO files (robots.txt)
- Landing and concept pages
- Documentation pages
- Status and visitor pages
- API key management
- Release notes
"""

from django.shortcuts import redirect
from django.urls import path

from .. import views

urlpatterns = [
    # SEO files
    path("robots.txt", views.robots_txt, name="robots_txt"),
    # Landing
    path("", views.index, name="index"),
    path("landing/", views.index, name="landing"),
    path("cloud/", lambda request: redirect("public_app:index"), name="cloud"),
    # Concept and vision pages
    path("about/", views.about, name="about"),
    path("setup/", views.setup_guide, name="setup"),
    path("open-source/", views.open_source, name="open_source"),
    path("demos/", views.demos, name="demos"),
    path("demos/watch/<str:video_id>/", views.video_player, name="video_player"),
    # path("vision/", views.vision, name="vision"),
    path("publications/", views.publications, name="publications"),
    path("contributors/", views.contributors, name="contributors"),
    path("recruit/", views.recruit, name="recruit"),
    path("pricing/", views.pricing, name="pricing"),
    # Reference pages
    path("keyboard-shortcuts/", views.keyboard_shortcuts, name="keyboard_shortcuts"),
    # Legal and contact pages
    path("contact/", views.contact, name="contact"),
    path("donate/", views.donate, name="donate"),
    path("privacy/", views.privacy_policy, name="privacy"),
    path("terms/", views.terms_of_use, name="terms"),
    path("cookies/", views.cookie_policy, name="cookies"),
    # 特定商取引法に基づく表記 (legally required before charging JP customers)
    path("tokushoho/", views.tokushoho, name="tokushoho"),
    # Billing (Stripe scaffold; checkout is staff-only while testing,
    # webhook is CSRF-exempt but signature-verified)
    path("billing/checkout/", views.billing_checkout, name="billing_checkout"),
    path("billing/webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
    # Demo page
    path("demo/", views.demo, name="demo"),
    # Web API documentation
    path("docs/web-api/", views.api_docs, name="api_docs"),
    path(
        "docs/web-api/<str:section>/",
        views.api_docs_section,
        name="api_docs_section",
    ),
    path(
        "docs/web-api/scitex-hub-api-docs.<str:fmt>",
        views.api_docs_download,
        name="api_docs_download",
    ),
    # Legacy redirects
    path(
        "api-docs/", lambda r: redirect("public_app:api_docs"), name="api_docs_legacy"
    ),
    path(
        "api-docs/<str:section>/",
        lambda r, section: redirect("public_app:api_docs_section", section=section),
        name="api_docs_section_legacy",
    ),
    # Status pages
    path("status/", views.public_status_view, name="public-status"),
    path("server-status/", views.server_status, name="server_status"),
    path("healthz/", views.healthz, name="healthz"),
    path("visitor-status/", views.visitor_status, name="visitor_status"),
    path("visitor-expired/", views.visitor_expired, name="visitor_expired"),
    path("visitor-restart/", views.visitor_restart_session, name="visitor_restart"),
    path("visitor-pool-full/", views.visitor_pool_full, name="visitor_pool_full"),
    # SciTeX API Key Management
    path("api-keys/", views.scitex_api_keys, name="scitex_api_keys"),
    # Release Notes
    path("releases/", views.releases_view, name="releases"),
]

# EOF
