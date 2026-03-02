#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/landing.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/landing.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Landing and Marketing Views

Handles landing page and premium subscription pricing.
"""

import importlib.metadata

from django.db import connection, transaction
from django.shortcuts import render

# Pip package names for ecosystem table (scitex-cloud uses SCITEX_CLOUD_VERSION from context processor)
_ECOSYSTEM_PACKAGES = [
    "scitex",
    "figrecipe",
    "scitex-writer",
    "scitex-dataset",
    "scitex-linter",
    "crossref-local",
    "openalex-local",
]


def _get_ecosystem_versions():
    """Get installed versions of ecosystem packages.

    Returns dict with underscored keys (Django templates can't handle hyphens).
    e.g. {"scitex": "2.17.7", "figrecipe": "1.2.0", ...}
    """
    versions = {}
    for pkg in _ECOSYSTEM_PACKAGES:
        key = pkg.replace("-", "_")
        try:
            versions[key] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[key] = ""
    return versions


@transaction.non_atomic_requests
def index(request):
    """
    Cloud app index view - Landing page for all users.

    Shows the landing page to all visitors, including authenticated users.
    Visitor auto-login is handled by VisitorAutoLoginMiddleware.

    non_atomic_requests: Disables ATOMIC_REQUESTS for this read-only view.
    In ASGI mode (Daphne), middleware and views run in different threads,
    so the middleware's visitor-allocation DB operations can leave the
    thread-local connection dirty via PgBouncer (transaction pool mode).
    Without the atomic wrapper, individual template queries can succeed
    even if earlier ones fail, preventing cascading 500 errors on startup.
    """
    # Ensure a clean DB connection for this thread.  In ASGI mode, the
    # thread pool may hand us a thread whose connection was dirtied by a
    # previous request's middleware (PgBouncer transaction pool mode).
    connection.close()
    context = {
        "ecosystem_versions": _get_ecosystem_versions(),
    }
    return render(request, "public_app/landing.html", context)


def premium_subscription(request):
    """Premium subscription and pricing details view."""

    # Define the comprehensive pricing structure based on the premium strategy
    individual_plans = [
        {
            "name": "Free",
            "price": 0,
            "gpu_hours": "5/month",
            "literature_searches": "50/month",
            "figure_generation": "25/month",
            "storage": "500MB",
            "scientific_validation": "Basic methodology checks",
            "agent_prompts": "Basic templates",
            "collaboration": "None",
            "language_support": "English",
            "support_level": "Community",
            "key_features": [
                "Basic LaTeX compilation",
                "Git integration",
                "Methodology validation",
                "File organization & project structure",
                "Simple data visualization",
            ],
            "cta_text": "Get Started Free",
            "cta_url": "/signup/",
            "popular": False,
        },
        {
            "name": "Standard",
            "price": 29,
            "gpu_hours": "50/month",
            "literature_searches": "500/month",
            "figure_generation": "200/month",
            "storage": "5GB",
            "scientific_validation": "Statistical rigor checking",
            "agent_prompts": "Standard library",
            "collaboration": "Basic sharing",
            "language_support": "English",
            "support_level": "Email",
            "key_features": [
                "AI literature reviews",
                "Grant templates (NSF/NIH)",
                "Peer review basics",
                "Advanced bibliography management",
                "Statistical validation tools",
            ],
            "cta_text": "Start Free Trial",
            "cta_url": "/signup/?plan=standard",
            "popular": False,
        },
        {
            "name": "Professional",
            "price": 99,
            "gpu_hours": "200/month",
            "literature_searches": "Unlimited",
            "figure_generation": "1000/month",
            "storage": "25GB",
            "scientific_validation": "Advanced validation",
            "agent_prompts": "Full library",
            "collaboration": "Project workspaces",
            "language_support": "English + Japanese",
            "support_level": "Priority",
            "key_features": [
                "Full scientific writing suite",
                "VisPlot integration",
                "Agent orchestration",
                "JST/MEXT grant optimization",
                "Advanced statistical analysis",
            ],
            "cta_text": "Start Free Trial",
            "cta_url": "/signup/?plan=professional",
            "popular": True,
        },
        {
            "name": "Researcher Plus",
            "price": 199,
            "gpu_hours": "500/month",
            "literature_searches": "Unlimited",
            "figure_generation": "Unlimited",
            "storage": "100GB",
            "scientific_validation": "Expert validation",
            "agent_prompts": "Custom prompts",
            "collaboration": "Advanced collaboration",
            "language_support": "English + Japanese",
            "support_level": "Dedicated + Monthly consult",
            "key_features": [
                "Co-authorship validation",
                "Grant optimization",
                "Peer review assistant",
                "Expert consultation included",
                "Custom prompt development",
            ],
            "cta_text": "Contact Sales",
            "cta_url": "/contact/",
            "popular": False,
        },
    ]

    institutional_plans = [
        {
            "name": "Lab License",
            "price": 299,
            "users": "5-10 users",
            "gpu_hours": "1000 shared",
            "storage": "500GB",
            "features": [
                "Admin dashboard",
                "Quarterly training",
                "Role-based permissions",
                "Advanced validation",
                "Priority support",
            ],
        },
        {
            "name": "Department",
            "price": 999,
            "users": "25-50 users",
            "gpu_hours": "3000 shared",
            "storage": "2TB",
            "features": [
                "Custom prompts",
                "Monthly training",
                "Enterprise collaboration",
                "Expert validation",
                "Dedicated support",
            ],
        },
        {
            "name": "University Enterprise",
            "price": "Custom",
            "users": "Unlimited",
            "gpu_hours": "Unlimited",
            "storage": "Unlimited",
            "features": [
                "On-premise deployment",
                "Unlimited users",
                "Dedicated support manager",
                "Co-authorship eligible",
                "Fully customized",
            ],
        },
    ]

    japanese_specials = [
        {
            "name": "Pilot Program",
            "price": "Free (6 months)",
            "description": "Professional tier features for up to 10 researchers",
            "features": [
                "Success tracking",
                "Japanese language focus",
                "Priority support",
                "Full library access",
            ],
        },
        {
            "name": "MEXT Partnership",
            "price": "50% off all plans",
            "description": "For government-funded research institutions",
            "features": [
                "Compliance certification",
                "Custom JST/MEXT templates",
                "Enterprise collaboration",
                "Dedicated support",
            ],
        },
    ]

    add_on_services = [
        {
            "name": "Custom Prompt Development",
            "price": "$2,000/project",
            "description": "Tailored AI prompts for specific research domains",
            "available_for": "Professional+",
        },
        {
            "name": "On-Premise Setup",
            "price": "$10,000 + $2,000/month",
            "description": "Local deployment with maintenance",
            "available_for": "Enterprise only",
        },
        {
            "name": "Training Workshop",
            "price": "$5,000/session",
            "description": "Emacs + SciTeX training for teams",
            "available_for": "All institutional",
        },
        {
            "name": "Scientific Validation Consultation",
            "price": "$200/hour",
            "description": "Expert consultation on research quality",
            "available_for": "Standard+",
        },
        {
            "name": "Co-authorship Review",
            "price": "$500/paper",
            "description": "Publication-ready validation with co-author eligibility",
            "available_for": "Professional+",
        },
    ]

    context = {
        "individual_plans": individual_plans,
        "institutional_plans": institutional_plans,
        "japanese_specials": japanese_specials,
        "add_on_services": add_on_services,
    }

    return render(request, "public_app/premium_subscription.html", context)


# EOF
