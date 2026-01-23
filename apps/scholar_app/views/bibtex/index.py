#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/index.py

"""
BibTeX Enrichment Index View

Main landing page for BibTeX enrichment functionality.
"""

from django.shortcuts import render


def bibtex_enrichment(request):
    """BibTeX enrichment landing page - upload and manage enrichment jobs (visitor allowed)."""
    from apps.project_app.models import Project
    from ...models import BibTeXEnrichmentJob

    # Get user's recent enrichment jobs
    if request.user.is_authenticated:
        recent_jobs = (
            BibTeXEnrichmentJob.objects.filter(user=request.user)
            .select_related("project")
            .order_by("-created_at")[:10]
        )

        # Get user's projects for project selection
        user_projects = Project.objects.filter(owner=request.user).order_by(
            "-created_at"
        )
        current_project = user_projects.first() if user_projects.exists() else None
    else:
        # For visitor users, get jobs by session key
        recent_jobs = (
            BibTeXEnrichmentJob.objects.filter(
                session_key=request.session.session_key
            ).order_by("-created_at")[:10]
            if request.session.session_key
            else []
        )

        # For visitor users, get their assigned project from the visitor pool
        from apps.project_app.services.visitor_pool import VisitorPool

        visitor_project_id = request.session.get(VisitorPool.SESSION_KEY_PROJECT_ID)
        current_project = None
        user_projects = []

        if visitor_project_id:
            try:
                current_project = Project.objects.get(id=visitor_project_id)
                user_projects = [current_project]
            except Project.DoesNotExist:
                pass

    context = {
        "recent_jobs": recent_jobs,
        "user_projects": user_projects,
        "current_project": current_project,
        "is_visitor": not request.user.is_authenticated,
        "show_save_prompt": not request.user.is_authenticated,
    }

    return render(request, "scholar_app/bibtex_enrichment.html", context)


# EOF
