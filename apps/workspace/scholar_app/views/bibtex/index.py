#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BibTeX enrichment index for authenticated users."""

from django.shortcuts import redirect, render


def bibtex_enrichment(request):
    """Render the caller's BibTeX jobs and owned projects."""
    if not request.user.is_authenticated:
        return redirect("auth_app:signup")

    from apps.infra.project_app.models import Project

    from ...models import BibTeXEnrichmentJob

    recent_jobs = (
        BibTeXEnrichmentJob.objects.filter(user=request.user)
        .select_related("project")
        .order_by("-created_at")[:10]
    )
    user_projects = Project.objects.filter(owner=request.user).order_by("-created_at")
    current_project = user_projects.first()

    return render(
        request,
        "scholar_app/bibtex_enrichment.html",
        {
            "recent_jobs": recent_jobs,
            "user_projects": user_projects,
            "current_project": current_project,
            "show_save_prompt": False,
        },
    )


# EOF
