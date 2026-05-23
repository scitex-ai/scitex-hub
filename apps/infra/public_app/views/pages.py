#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Information Pages Views

Handles about, publications, contributors, donate, and fundraising pages.

Re-exports from specialized submodules:
- pages_data: Static data (videos, keyboard shortcuts)
- pages_donate: Donation processing
"""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import render

from .pages_data import KEYBOARD_SHORTCUTS_DATA, OG_BASE_URL, VIDEO_CATALOG

__all__ = [
    "about",
    "setup_guide",
    "demos",
    "video_player",
    "publications",
    "fundraising",
    "pricing",
    "keyboard_shortcuts",
    "contributors",
]


def setup_guide(request):
    """Setup guide - how to deploy SciTeX Hub anywhere."""
    return render(request, "public_app/pages/setup.html")


def about(request):
    """SciTeX about page - purpose, mission, vision, and values."""
    return render(request, "public_app/pages/about.html")


def open_source(request):
    """Why open source matters for SciTeX and scientific research."""
    return render(request, "public_app/pages/open_source.html")


def demos(request):
    """SciTeX demos page - architecture diagram, videos, and repository links."""
    return render(request, "public_app/pages/demos.html")


def video_player(request, video_id):
    """Video player page with 4x default speed and Open Graph meta tags."""
    video = VIDEO_CATALOG.get(video_id)
    if not video:
        raise Http404("Video not found")

    # Build absolute URL for current page
    page_url = f"{OG_BASE_URL}/demos/watch/{video_id}/"

    # Build absolute thumbnail URL (use video-specific or default)
    thumbnail = video.get("thumbnail")
    if thumbnail:
        og_image = f"{OG_BASE_URL}{thumbnail}"
    else:
        og_image = f"{OG_BASE_URL}/static/shared/images/scitex-og-image.png"

    return render(
        request,
        "public_app/pages/video_player.html",
        {
            "video_title": video["title"],
            "video_url": video["url"],
            "video_description": video["description"],
            "video_id": video_id,
            "og_url": page_url,
            "og_image": og_image,
        },
    )


def publications(request):
    """Publications page - display publications from database.

    Data is populated via: python manage.py sync_publications
    """
    from ..models import Publication

    publications_qs = Publication.objects.filter(is_active=True)

    # Build stats
    stats = {
        "publication_count": publications_qs.count(),
        "institutions": "3+",
        "countries": 2,
    }

    # Convert to template-friendly format
    papers = [
        {
            "title": pub.title,
            "authors": pub.authors,
            "journal": pub.journal_citation,
            "abstract": pub.abstract_display,
            "paper_url": pub.paper_url,
            "code_url": pub.code_url,
        }
        for pub in publications_qs
    ]

    return render(
        request,
        "public_app/pages/publications.html",
        {
            "stats": stats,
            "papers": papers,
        },
    )


def fundraising(request):
    """Fundraising and sustainability page."""
    return render(request, "public_app/pages/fundraising.html")


def pricing(request):
    """SciTeX pricing page - subscription plans and feature comparison."""
    return render(request, "public_app/pages/pricing.html")


def keyboard_shortcuts(request):
    """Keyboard shortcuts reference page with tabs by context and search."""
    # Calculate total shortcuts
    total_shortcuts = sum(
        len(s["shortcuts"]) for ctx in KEYBOARD_SHORTCUTS_DATA for s in ctx["sections"]
    )

    context = {
        "contexts": KEYBOARD_SHORTCUTS_DATA,
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
    core_team = [
        {
            "name": member.name,
            "username": member.github_username,
            "role": member.get_role_display(),
            "avatar_url": member.avatar_url,
            "github_url": member.github_url,
            "contributions": member.contributions_description
            or f"{member.contributions} contributions",
        }
        for member in core_team_db
    ]

    contributors_list = [
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
        for contributor in contributors_db
    ]

    context = {
        "core_team": core_team,
        "contributors": contributors_list,
    }

    return render(request, "public_app/pages/contributors.html", context)


# EOF
