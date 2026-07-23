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

import logging

from django.http import Http404
from django.shortcuts import render

from .pages_data import KEYBOARD_SHORTCUTS_DATA, OG_BASE_URL, VIDEO_CATALOG

logger = logging.getLogger(__name__)

__all__ = [
    "about",
    "setup_guide",
    "demos",
    "video_player",
    "publications",
    "fundraising",
    "pricing",
    "services",
    "keyboard_shortcuts",
    "contributors",
    "recruit",
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


def recruit(request):
    """Recruit page - open-source contributor recruitment (students welcome).

    Copy is legally reviewed (voluntary OSS contribution only; no
    direction/supervision by the company — never phrased as unpaid work).
    University-credit internships and paid roles appear only as future
    items under "Coming next".
    """
    return render(request, "public_app/pages/recruit.html")


def _notify_service_inquiry(inquiry):
    """Best-effort email of a services inquiry — ONLY if an address is set.

    Never falls back to recruit@ (the hiring inbox). The inquiry is already
    persisted (ServiceInquiry) before this runs, so if no address is
    configured, or if sending fails, nothing is lost — the DB (admin) is the
    source of truth. A send failure is LOGGED loudly, never swallowed.
    """
    from django.conf import settings

    to_addr = (getattr(settings, "SERVICES_INQUIRY_EMAIL", "") or "").strip()
    if not to_addr:
        return
    from django.core.mail import send_mail

    subject = f"[SciTeX services] お問い合わせ: {inquiry.name}"
    body = (
        f"お名前: {inquiry.name}\n"
        f"ご所属: {inquiry.affiliation or '-'}\n"
        f"ご予算感: {inquiry.budget or '-'}\n"
        f"受付日時: {inquiry.created_at:%Y-%m-%d %H:%M}\n\n"
        f"ご相談内容:\n{inquiry.request}\n"
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to_addr],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001 — email is best-effort; DB is the record
        logger.warning(
            "ServiceInquiry %s stored but email to %s failed",
            inquiry.pk,
            to_addr,
            exc_info=True,
        )


def services(request):
    """Services page (日本語) — services list + price bands + inquiry form.

    Cash-runway entry point: makes "what can I hire them for" visible and
    gives an inquiry path. Deliberately NOT a billing system — inquiries are
    persisted (ServiceInquiry) and, only when settings.SERVICES_INQUIRY_EMAIL
    is set, emailed (never to recruit@). The BYOK / 前受金 model stays a
    design memo until demand is visible (資金決済法 exposure otherwise).
    """
    submitted = False
    errors: dict[str, str] = {}
    form = {"name": "", "affiliation": "", "request": "", "budget": ""}

    if request.method == "POST":
        form = {
            "name": (request.POST.get("name") or "").strip(),
            "affiliation": (request.POST.get("affiliation") or "").strip(),
            "request": (request.POST.get("request") or "").strip(),
            "budget": (request.POST.get("budget") or "").strip(),
        }
        if not form["name"]:
            errors["name"] = "お名前をご記入ください。"
        if not form["request"]:
            errors["request"] = "ご相談内容をご記入ください。"
        if not errors:
            from ..models import ServiceInquiry

            inquiry = ServiceInquiry.objects.create(
                name=form["name"][:120],
                affiliation=form["affiliation"][:200],
                request=form["request"],
                budget=form["budget"][:120],
            )
            _notify_service_inquiry(inquiry)
            submitted = True
            form = {"name": "", "affiliation": "", "request": "", "budget": ""}

    return render(
        request,
        "public_app/pages/services.html",
        {"submitted": submitted, "errors": errors, "form": form},
    )


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
    """SciTeX pricing page - subscription plans and feature comparison.

    The rendered public state stays the truthful alpha-free framing.
    Underneath, the page is Stripe-ready: paid plans come from
    ``SCITEX_HUB_BILLING_PLANS`` (settings_commerce; prices are
    tax-inclusive 税込 per 総額表示義務) and are shown to staff only
    while billing is in testing (operator directive 2026-07-08).
    """
    from django.conf import settings

    return render(
        request,
        "public_app/pages/pricing.html",
        {
            "billing_plans": settings.BILLING_PLANS,
            "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
        },
    )


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
