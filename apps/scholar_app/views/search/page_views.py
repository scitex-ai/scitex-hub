#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/views/search/page_views.py
"""
Scholar App - Page Views Module

Template rendering views for main scholar pages.
Extracted from monolithic views.py for better modularity.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ...models import UserLibrary, Collection
from .search_core import simple_search_with_tab
from apps.project_app.services import get_current_project

logger = logging.getLogger(__name__)


def _check_visitor_pool_redirect(request):
    """Check if unauthenticated browser request should redirect to visitor-pool-full."""
    if not request.user.is_authenticated:
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        is_browser = any(
            browser in user_agent
            for browser in ['Mozilla', 'Chrome', 'Safari', 'Firefox', 'Edge', 'Opera']
        )
        if is_browser:
            logger.info("[Scholar] Browser request not authenticated - redirecting to visitor-pool-full")
            return redirect('public_app:visitor_pool_full')
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
    """Dedicated BibTeX enrichment page."""
    # Check for visitor pool redirect
    pool_redirect = _check_visitor_pool_redirect(request)
    if pool_redirect:
        return pool_redirect

    from . import bibtex_enrichment_view

    return bibtex_enrichment_view(
        request, template_name="scholar_app/scholar_bibtex.html"
    )


def scholar_search(request):
    """Dedicated literature search page."""
    # Check for visitor pool redirect
    pool_redirect = _check_visitor_pool_redirect(request)
    if pool_redirect:
        return pool_redirect

    from . import simple_search_with_tab

    return simple_search_with_tab(
        request, active_tab="search", template_name="scholar_app/scholar_search.html"
    )


def scholar_graph(request):
    """Citation graph visualization page."""
    # Check for visitor pool redirect
    pool_redirect = _check_visitor_pool_redirect(request)
    if pool_redirect:
        return pool_redirect

    from apps.project_app.models import Project
    from apps.project_app.services import get_current_project

    # Get user projects and current project
    user_projects = []
    current_project = None
    if request.user.is_authenticated:
        user_projects = Project.objects.filter(owner=request.user).order_by(
            "-created_at"
        )
        current_project = get_current_project(request, user=request.user)

    context = {
        "active_tab": "graph",
        "user_projects": user_projects,
        "current_project": current_project,
    }

    return render(request, "scholar_app/scholar_graph.html", context)


def bibtex_enrichment_view(request, template_name="scholar_app/index.html"):
    """BibTeX Enrichment tab view."""
    from apps.scholar_app.models import BibTeXEnrichmentJob
    from apps.project_app.models import Project

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
