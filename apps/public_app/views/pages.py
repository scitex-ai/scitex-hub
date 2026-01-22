#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 21:31:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/pages.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/pages.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Information Pages Views

Handles about, publications, contributors, donate, and fundraising pages.
"""

from django.db import models
from django.shortcuts import render
from django.utils import timezone


def about(request):
    """SciTeX about page - purpose, mission, vision, and values."""
    return render(request, "public_app/pages/about.html")


def demos(request):
    """SciTeX demos page - architecture diagram, videos, and repository links."""
    return render(request, "public_app/pages/demos.html")


def video_player(request, video_id):
    """Video player page with 4x default speed."""
    videos = {
        "figrecipe": {
            "title": "Graphing by AI Agent (figrecipe v0.14.0)",
            "url": "/media/videos/figrecipe-v0.14.0-demo.mp4",
            "description": "scitex MCP enables AI agents to create publication-ready scientific figures. Reproducible recipes for automated plot generation.",
        },
        "crossref-local": {
            "title": "Literature Search by AI Agent (crossref-local v0.3.1)",
            "url": "/media/videos/crossref-local-v0.3.1-demo.mp4",
            "description": "scitex MCP enables AI agents to search 167M+ academic works via local database. No hallucinated citations — real literature data for reliable research.",
        },
        "scitex-writer": {
            "title": "Manuscript Writing by AI Agent (scitex-writer v2.2.0)",
            "url": "/media/videos/scitex-writer-v2.2.0-demo.mp4",
            "description": "scitex MCP enables AI agents to write scientific manuscripts. Automated literature integration, LaTeX compilation, and revision tracking.",
        },
        "scitex-automated-research": {
            "title": "Automated Research by AI Agent (scitex v2.10)",
            "url": "/media/videos/scitex-automated-research-demo.mp4",
            "description": "scitex MCP enables AI agents to conduct full research workflows: literature search, experiment, analysis, figure generation, manuscript writing, and revision.",
        },
    }
    video = videos.get(video_id)
    if not video:
        from django.http import Http404
        raise Http404("Video not found")
    return render(request, "public_app/pages/video_player.html", {
        "video_title": video["title"],
        "video_url": video["url"],
        "video_description": video["description"],
    })


def publications(request):
    """Publications page."""
    return render(request, "public_app/pages/publications.html")


def donate(request):
    """Donate page view with payment processing."""

    from django.contrib import messages

    from ..forms import DonationForm, EmailVerificationForm
    from ..models import Donation, DonationTier

    # Get donation tiers
    tiers = (
        DonationTier.objects.filter(is_active=True)
        if DonationTier.objects.exists()
        else []
    )

    if request.method == "POST":
        # Check if this is email verification request
        if "verify_email" in request.POST:
            email_form = EmailVerificationForm(request.POST)
            if email_form.is_valid():
                if email_form.send_verification_email():
                    messages.success(request, "Verification code sent to your email!")
                    request.session["verification_email"] = email_form.cleaned_data[
                        "email"
                    ]
                    from django.shortcuts import redirect
                    return redirect("cloud_app:verify-email")
                else:
                    messages.error(
                        request,
                        "Failed to send verification email. Please try again.",
                    )

        # Process donation
        elif "process_donation" in request.POST:
            form = DonationForm(request.POST)
            if form.is_valid():
                donation = form.save(commit=False)

                # If user is authenticated, link to user
                if request.user.is_authenticated:
                    donation.user = request.user

                # Save donation as pending
                donation.save()

                # Here you would integrate with payment processor
                # For now, we'll simulate successful payment
                if donation.payment_method == "credit_card":
                    # Simulate Stripe payment
                    transaction_id = f"STRIPE_{donation.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
                    donation.complete_donation(transaction_id)
                    messages.success(
                        request,
                        f"Thank you for your ${donation.amount} donation!",
                    )

                    # Send confirmation email
                    from .utils import send_donation_confirmation
                    send_donation_confirmation(donation)

                    from django.shortcuts import redirect
                    return redirect(
                        "cloud_app:donation-success", donation_id=donation.id
                    )

                elif donation.payment_method == "paypal":
                    # Redirect to PayPal
                    messages.info(request, "Redirecting to PayPal...")
                    from django.shortcuts import redirect
                    return redirect(
                        "cloud_app:donate"
                    )  # Would redirect to PayPal in production

                elif donation.payment_method == "github":
                    # Redirect to GitHub Sponsors
                    from django.shortcuts import redirect
                    return redirect("https://github.com/sponsors/SciTex-AI")

    else:
        form = DonationForm()

    # Get recent public donations
    recent_donations = (
        Donation.objects.filter(
            is_public=True, is_visitor=False, status="completed"
        ).select_related("user")[:10]
        if Donation.objects.exists()
        else []
    )

    # Calculate funding progress
    current_year = timezone.now().year
    year_donations = (
        Donation.objects.filter(
            status="completed", created_at__year=current_year
        ).aggregate(total=models.Sum("amount"))["total"]
        or 0
        if Donation.objects.exists()
        else 0
    )

    funding_goal = 75000  # $75,000 annual goal
    funding_percentage = min(100, int((year_donations / funding_goal) * 100))

    context = {
        "form": form,
        "tiers": tiers,
        "recent_donations": recent_donations,
        "year_donations": year_donations,
        "funding_goal": funding_goal,
        "funding_percentage": funding_percentage,
    }

    return render(request, "public_app/pages/donate.html", context)


def fundraising(request):
    """Fundraising and sustainability page."""
    return render(request, "public_app/pages/fundraising.html")


def pricing(request):
    """SciTeX pricing page - subscription plans and feature comparison."""
    return render(request, "public_app/pages/pricing.html")


def keyboard_shortcuts(request):
    """Keyboard shortcuts reference page with tabs by context and search."""
    # Define shortcuts organized by context with semantic sections
    contexts = [
        {
            "name": "Global",
            "slug": "global",
            "icon": "🌐",
            "description": "Available everywhere in SciTeX",
            "sections": [
                {
                    "title": "Global Navigation",
                    "shortcuts": [
                        {"keys": "Alt+F", "description": "Files"},
                        {"keys": "Alt+S", "description": "Scholar"},
                        {"keys": "Alt+C", "description": "Code"},
                        {"keys": "Alt+V", "description": "Vis"},
                        {"keys": "Alt+W", "description": "Writer"},
                        {"keys": "Alt+Z", "description": "Zen Mode"},
                    ],
                },
            ],
        },
        {
            "name": "Files",
            "slug": "files",
            "icon": "📁",
            "description": "File browser",
            "sections": [
                {
                    "title": "Navigation",
                    "shortcuts": [
                        {"keys": "Enter", "description": "Open item"},
                        {"keys": "Backspace", "description": "Parent folder"},
                        {"keys": "/", "description": "Focus search"},
                    ],
                },
                {
                    "title": "File Actions",
                    "shortcuts": [
                        {"keys": "Ctrl+N", "description": "New file"},
                        {"keys": "Ctrl+Shift+N", "description": "New folder"},
                        {"keys": "F2", "description": "Rename"},
                        {"keys": "Del", "description": "Delete"},
                    ],
                },
            ],
        },
        {
            "name": "Scholar",
            "slug": "scholar",
            "icon": "🎓",
            "description": "Literature search",
            "sections": [
                {
                    "title": "Search",
                    "shortcuts": [
                        {"keys": "Ctrl+F", "description": "Focus search"},
                        {"keys": "Enter", "description": "Search"},
                    ],
                },
                {
                    "title": "Citations",
                    "shortcuts": [
                        {"keys": "Ctrl+S", "description": "Save to library"},
                        {"keys": "Ctrl+C", "description": "Copy citation"},
                    ],
                },
            ],
        },
        {
            "name": "Code",
            "slug": "code",
            "icon": "💻",
            "description": "Code editor",
            "sections": [
                {
                    "title": "Files",
                    "shortcuts": [
                        {"keys": "Ctrl+S", "description": "Save file"},
                        {"keys": "Ctrl+N", "description": "New file"},
                        {"keys": "Ctrl+Tab", "description": "Next tab"},
                        {"keys": "Ctrl+Shift+Tab", "description": "Prev tab"},
                    ],
                },
                {
                    "title": "Terminal",
                    "shortcuts": [
                        {"keys": "Ctrl+Shift+T", "description": "New terminal"},
                        {"keys": "Ctrl+`", "description": "Toggle terminal"},
                    ],
                },
                {
                    "title": "View",
                    "shortcuts": [
                        {"keys": "Ctrl+B", "description": "Toggle sidebar"},
                    ],
                },
            ],
        },
        {
            "name": "Vis",
            "slug": "vis",
            "icon": "📊",
            "description": "Figure editor",
            "sections": [
                {
                    "title": "Basic",
                    "shortcuts": [
                        {"keys": "Ctrl+C", "description": "Copy object"},
                        {"keys": "Ctrl+V", "description": "Paste object"},
                        {"keys": "Ctrl+D", "description": "Duplicate"},
                        {"keys": "Ctrl+Z", "description": "Undo"},
                        {"keys": "Ctrl+Y", "description": "Redo"},
                        {"keys": "Del", "description": "Delete selected"},
                        {"keys": "Arrow", "description": "Move 1px"},
                        {"keys": "Shift+Arrow", "description": "Move 10px"},
                    ],
                },
                {
                    "title": "Align (Alt+A → ...)",
                    "shortcuts": [
                        {"keys": "L", "description": "Left"},
                        {"keys": "R", "description": "Right"},
                        {"keys": "T", "description": "Top"},
                        {"keys": "B", "description": "Bottom"},
                        {"keys": "H", "description": "Distribute H (equal)"},
                        {"keys": "V", "description": "Distribute V (equal)"},
                        {"keys": "C", "description": "Center horizontal"},
                        {"keys": "M", "description": "Center vertical"},
                    ],
                },
                {
                    "title": "Align by Axis (Alt+Shift+A → ...)",
                    "shortcuts": [
                        {"keys": "L", "description": "Y-Axis (Left edge)"},
                        {"keys": "R", "description": "Right edge"},
                        {"keys": "T", "description": "Top edge"},
                        {"keys": "B", "description": "X-Axis (Bottom edge)"},
                        {"keys": "C", "description": "Horizontal center"},
                        {"keys": "M", "description": "Vertical center"},
                        {"keys": "S", "description": "Stack vertically"},
                    ],
                },
                {
                    "title": "Size (Alt+Z → ...)",
                    "shortcuts": [
                        {"keys": "S", "description": "Match Size"},
                        {"keys": "W", "description": "Match Width"},
                        {"keys": "T", "description": "Match Height (Tall)"},
                        {"keys": "C", "description": "Multiple Crop"},
                    ],
                },
                {
                    "title": "Arrange",
                    "shortcuts": [
                        {"keys": "Alt+F", "description": "Bring to Front"},
                        {"keys": "Alt+B", "description": "Send to Back"},
                    ],
                },
                {
                    "title": "View",
                    "shortcuts": [
                        {"keys": "+", "description": "Zoom in"},
                        {"keys": "-", "description": "Zoom out"},
                        {"keys": "0", "description": "Fit to window"},
                        {"keys": "G", "description": "Toggle grid"},
                        {"keys": "Alt+T", "description": "Toggle theme"},
                    ],
                },
                {
                    "title": "Group",
                    "shortcuts": [
                        {"keys": "Ctrl+G", "description": "Group"},
                        {"keys": "Ctrl+Shift+G", "description": "Ungroup"},
                    ],
                },
            ],
        },
        {
            "name": "Writer",
            "slug": "writer",
            "icon": "✍️",
            "description": "Document editor",
            "sections": [
                {
                    "title": "Document",
                    "shortcuts": [
                        {"keys": "Ctrl+S", "description": "Save"},
                        {"keys": "Ctrl+B", "description": "Bold"},
                        {"keys": "Ctrl+I", "description": "Italic"},
                        {"keys": "Ctrl+K", "description": "Insert link"},
                    ],
                },
                {
                    "title": "Insert",
                    "shortcuts": [
                        {"keys": "Ctrl+Shift+C", "description": "Citation"},
                        {"keys": "Ctrl+Shift+E", "description": "Equation"},
                        {"keys": "Ctrl+Shift+F", "description": "Figure"},
                    ],
                },
            ],
        },
    ]

    # Calculate total shortcuts
    total_shortcuts = sum(
        len(s["shortcuts"]) for ctx in contexts for s in ctx["sections"]
    )

    context = {
        "contexts": contexts,
        "total_shortcuts": total_shortcuts,
    }

    return render(request, "public_app/pages/keyboard_shortcuts.html", context)


def contributors(request):
    """Contributors page - show SciTeX team and contributors."""
    from ..models import Contributor

    # Get core team members from database
    core_team_db = Contributor.objects.filter(is_core_team=True)

    # Get community contributors from database
    contributors_db = Contributor.objects.filter(is_core_team=False)

    # Convert to template-friendly format
    core_team = []
    for member in core_team_db:
        core_team.append(
            {
                "name": member.name,
                "username": member.github_username,
                "role": member.get_role_display(),
                "avatar_url": member.avatar_url,
                "github_url": member.github_url,
                "contributions": member.contributions_description
                or f"{member.contributions} contributions",
            }
        )

    contributors = []
    for contributor in contributors_db:
        contributors.append(
            {
                "name": contributor.name,
                "username": contributor.github_username,
                "role": (
                    contributor.get_role_display()
                    if contributor.role != "contributor"
                    else None
                ),
                "avatar_url": contributor.avatar_url,
                "github_url": contributor.github_url,
                "contributions": contributor.contributions_description
                or f"{contributor.contributions} contributions",
            }
        )

    context = {
        "core_team": core_team,
        "contributors": contributors,
    }

    return render(request, "public_app/pages/contributors.html", context)


# EOF
