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

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path
from django.views.generic import RedirectView

from .. import views


def _visitor_retired_410(request):
    """410 Gone for a retired visitor-session surface.

    The visitor pool was retired 2026-09-10 (operator ruling: "drop visitor
    entirely"), so the anonymous states these routes served — status,
    expired, restart, pool-full — have no source. 410 (not 404) tells an old
    link or client "this existed and was retired on purpose" rather than
    "we don't know what you meant"; the body says what to do instead.
    """
    return HttpResponse(
        "The visitor sandbox was retired (2026-09-10). Sign up or sign in to "
        "continue — signup starts a 30-day free trial.",
        status=410,
        content_type="text/plain",
    )


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
    # Services + inquiry (cash-runway entry point; JP-first)
    path("services/", views.services, name="services"),
    # Public security / trust page (implemented protections + live test count)
    path("security/", views.security, name="security"),
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
    # English reference version (supplementary; the JA page stays the
    # legally binding disclosure for Japanese consumers)
    path("tokushoho-en/", views.tokushoho_en, name="tokushoho_en"),
    # Billing (Stripe scaffold; checkout is staff-only while testing,
    # webhook is CSRF-exempt but signature-verified)
    path("billing/checkout/", views.billing_checkout, name="billing_checkout"),
    path("billing/start-setup/", views.start_card_setup, name="billing_start_setup"),
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
    # Visitor entry — RETIRED 2026-09-10 (operator ruling: "drop visitor
    # entirely", compass-impl-visitor-pool-retirement-20260910). The old
    # /enter/ target of the landing hero's "Enter as visitor" CTA now 301s
    # to the signup-first entry point; the hero itself already points at
    # /auth/signup/ (leader commit 6811bbd9a). Anyone with the old link in
    # a bookmark or the old deploy lands on signup, not a dead shell.
    path(
        "enter/",
        RedirectView.as_view(url="/auth/signup/", permanent=True),
        name="visitor_enter",
    ),
    # Status pages
    path("status/", views.public_status_view, name="public-status"),
    path("server-status/", views.server_status, name="server_status"),
    path("healthz/", views.healthz, name="healthz"),
    # Visitor session surfaces — RETIRED 2026-09-10 with the pool. No
    # anonymous browser is provisioned any more, so the visitor
    # status/expired/restart/pool-full states have no source; each returns
    # 410 Gone so an old link or client gets a clear "retired" signal
    # rather than a dead shell (compass L658).
    path("visitor-status/", _visitor_retired_410, name="visitor_status"),
    path("visitor-expired/", _visitor_retired_410, name="visitor_expired"),
    path("visitor-restart/", _visitor_retired_410, name="visitor_restart"),
    path("visitor-pool-full/", _visitor_retired_410, name="visitor_pool_full"),
    # SciTeX API Key Management
    path("api-keys/", views.scitex_api_keys, name="scitex_api_keys"),
    # Release Notes
    path("releases/", views.releases_view, name="releases"),
]

# EOF
