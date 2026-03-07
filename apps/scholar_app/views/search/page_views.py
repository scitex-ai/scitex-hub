#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/views/search/page_views.py
"""
Scholar App - Page Views Module

Template rendering views for main scholar pages.
Extracted from monolithic views.py for better modularity.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.project_app.services import get_current_project

from ...models import Collection, UserLibrary
from .search_core import simple_search_with_tab

logger = logging.getLogger(__name__)


def _check_visitor_pool_redirect(request):
    """Check if unauthenticated browser request should redirect to visitor-pool-full."""
    if not request.user.is_authenticated:
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        is_browser = any(
            browser in user_agent
            for browser in ["Mozilla", "Chrome", "Safari", "Firefox", "Edge", "Opera"]
        )
        if is_browser:
            logger.info(
                "[Scholar] Browser request not authenticated - redirecting to visitor-pool-full"
            )
            return redirect("public_app:visitor_pool_full")
    return None


def simple_search(request):
    """Advanced search interface with comprehensive filtering."""
    # Check for visitor pool redirect
    pool_redirect = _check_visitor_pool_redirect(request)
    if pool_redirect:
        return pool_redirect
    return simple_search_with_tab(request, active_tab="search")


def index(request):
    """Scholar app index/landing page."""
    # Check for visitor pool redirect
    pool_redirect = _check_visitor_pool_redirect(request)
    if pool_redirect:
        return pool_redirect

    # Simple landing page that shows both features
    context = {
        "active_tab": "overview",
    }
    return render(request, "scholar_app/index_landing.html", context)


def scholar_bibtex(request):
    """Dedicated BibTeX enrichment page - redirects to unified page."""
    # Redirect to unified page with bibtex hash
    return redirect("/scholar/#bibtex")


def scholar_search(request):
    """Dedicated literature search page - redirects to unified page."""
    # Redirect to unified page with search hash
    return redirect("/scholar/#search")


def scholar_graph(request):
    """Citation graph visualization page."""
    # Redirect to unified page with graph hash
    return redirect("/scholar/#graph")


def scholar_unified(request):
    """Unified scholar page with all tabs (search, bibtex, graph)."""
    # Check for visitor pool redirect
    pool_redirect = _check_visitor_pool_redirect(request)
    if pool_redirect:
        return pool_redirect

    from apps.project_app.models import Project
    from apps.project_app.services import get_current_project

    from ...models import BibTeXEnrichmentJob

    # Get user projects and current project
    user_projects = []
    current_project = None
    recent_jobs = []
    needs_scholar_init = False

    if request.user.is_authenticated:
        user_projects = Project.objects.filter(owner=request.user).order_by(
            "-created_at"
        )
        current_project = get_current_project(request, user=request.user)

        # Ensure scholar workspace exists on first access
        if current_project:
            try:
                from apps.project_app.services.project_filesystem import (
                    get_project_filesystem_manager,
                )

                mgr = get_project_filesystem_manager(request.user)
                project_root = mgr.get_project_root_path(current_project)
                if project_root and not (project_root / "scitex" / "scholar").exists():
                    # App projects: show init instruction instead of auto-creating
                    if getattr(current_project, "is_app", False):
                        needs_scholar_init = True
                    else:
                        from scitex.scholar import ensure_workspace

                        ensure_workspace(str(project_root))
                        logger.info(
                            f"Auto-initialized scholar workspace for: {current_project.slug}"
                        )
            except Exception as e:
                logger.warning(f"Failed to auto-initialize scholar: {e}")

        # Get user's recent enrichment jobs
        recent_jobs = (
            BibTeXEnrichmentJob.objects.filter(user=request.user)
            .select_related("project")
            .order_by("-created_at")[:10]
        )
    else:
        # For visitor users, get jobs by session key
        if request.session.session_key:
            recent_jobs = BibTeXEnrichmentJob.objects.filter(
                session_key=request.session.session_key
            ).order_by("-created_at")[:10]

    # Default filter ranges (used when no search results)
    filter_ranges = {
        "year_min": 1900,
        "year_max": 2025,
        "citations_min": 0,
        "citations_max": 128,
        "impact_factor_min": 0,
        "impact_factor_max": 50.0,
    }

    # Library stats for tab badge
    library_count = 0
    if request.user.is_authenticated:
        from ...models import UserLibrary

        library_count = UserLibrary.objects.filter(user=request.user).count()

    context = {
        "query": "",
        "results": [],
        "has_results": False,
        "user_projects": user_projects,
        "current_project": current_project,
        "recent_jobs": recent_jobs,
        "filter_ranges": filter_ranges,
        "library_count": library_count,
        "needs_scholar_init": needs_scholar_init,
    }

    return render(request, "scholar_app/scholar_unified.html", context)


def bibtex_enrichment_view(request, template_name="scholar_app/index.html"):
    """BibTeX Enrichment tab view."""
    from apps.project_app.models import Project
    from apps.scholar_app.models import BibTeXEnrichmentJob

    # Get user projects and current project using centralized getter
    user_projects = []
    current_project = None
    if request.user.is_authenticated:
        user_projects = Project.objects.filter(owner=request.user).order_by(
            "-created_at"
        )
        # Use centralized project getter
        current_project = get_current_project(request, user=request.user)

    # Get user's recent enrichment jobs
    if request.user.is_authenticated:
        recent_jobs = (
            BibTeXEnrichmentJob.objects.filter(user=request.user)
            .select_related("project")
            .order_by("-created_at")[:10]
        )
    else:
        # For visitor users, get jobs by session key
        recent_jobs = (
            BibTeXEnrichmentJob.objects.filter(
                session_key=request.session.session_key
            ).order_by("-created_at")[:10]
            if request.session.session_key
            else []
        )

    # Default filter ranges (used when no search results)
    filter_ranges = {
        "year_min": 1900,
        "year_max": 2025,
        "citations_min": 0,
        "citations_max": 128,
        "impact_factor_min": 0,
        "impact_factor_max": 50.0,
    }

    context = {
        "query": "",  # No search query for BibTeX tab
        "results": [],
        "has_results": False,
        "user_projects": user_projects,
        "current_project": current_project,
        "recent_jobs": recent_jobs,
        "active_tab": "bibtex",  # Indicate which tab is active
        "filter_ranges": filter_ranges,  # Add default filter ranges
    }

    return render(request, template_name, context)


def literature_search_view(request):
    """Literature Search tab view."""
    from . import simple_search_with_tab

    return simple_search_with_tab(request, active_tab="search")


def features(request):
    """Scholar features view."""
    return render(request, "scholar_app/features.html")


def pricing(request):
    """Scholar pricing view."""
    return render(request, "scholar_app/pricing.html")


@login_required
def personal_library(request):
    """Personal research library management interface."""
    # Get user's library papers with related data
    library_papers = (
        UserLibrary.objects.filter(user=request.user)
        .select_related("paper", "paper__journal")
        .prefetch_related("paper__authors", "collections")
        .order_by("-saved_at")
    )

    # Get user's collections
    collections = Collection.objects.filter(user=request.user).order_by("name")

    # Get reading status statistics
    status_stats = {}
    for status_code, status_name in UserLibrary.READING_STATUS_CHOICES:
        count = library_papers.filter(reading_status=status_code).count()
        status_stats[status_code] = {"name": status_name, "count": count}

    context = {
        "library_papers": library_papers,
        "collections": collections,
        "status_stats": status_stats,
        "total_papers": library_papers.count(),
    }

    return render(request, "scholar_app/personal_library.html", context)
