#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trending and analytics views for Scholar App

This module handles research trends and analytics endpoints.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
import logging

from ...models import (
    SearchIndex as Paper,
    Author,
    Journal,
    UserLibrary,
    Topic,
)

logger = logging.getLogger(__name__)


def research_trends(request):
    """Display research trends page"""
    context = {
        "page_title": "Research Trends",
    }
    return render(request, "scholar_app/research_trends.html", context)


@login_required
@require_http_methods(["GET"])
def api_trending_papers(request):
    """API endpoint for trending papers"""
    try:
        days = int(request.GET.get("days", 30))
        limit = int(request.GET.get("limit", 10))

        cutoff_date = timezone.now() - timedelta(days=days)

        trending_papers = (
            Paper.objects.filter(created_at__gte=cutoff_date)
            .annotate(view_count=Count("id"), citation_count=Count("citations"))
            .order_by("-citation_count")[:limit]
        )

        papers_data = [
            {
                "id": str(p.id),
                "title": p.title,
                "authors": ", ".join(
                    [f"{a.first_name} {a.last_name}" for a in p.authors.all()]
                ),
                "journal": p.journal.name if p.journal else "Unknown",
                "year": p.publication_date.year if p.publication_date else "Unknown",
                "citations": p.citation_count,
                "impact_factor": p.journal.impact_factor if p.journal else None,
            }
            for p in trending_papers
        ]

        return JsonResponse(
            {"success": True, "papers": papers_data, "count": len(papers_data)}
        )
    except Exception as e:
        logger.error(f"Error getting trending papers: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_trending_topics(request):
    """API endpoint for trending research topics"""
    try:
        days = int(request.GET.get("days", 30))
        limit = int(request.GET.get("limit", 10))

        cutoff_date = timezone.now() - timedelta(days=days)

        trending_topics = (
            Topic.objects.filter(papers__created_at__gte=cutoff_date)
            .annotate(paper_count=Count("papers", distinct=True))
            .order_by("-paper_count")[:limit]
        )

        topics_data = [
            {"name": t.name, "paper_count": t.paper_count, "description": t.description}
            for t in trending_topics
        ]

        return JsonResponse(
            {"success": True, "topics": topics_data, "count": len(topics_data)}
        )
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_trending_authors(request):
    """API endpoint for trending authors"""
    try:
        days = int(request.GET.get("days", 30))
        limit = int(request.GET.get("limit", 10))

        cutoff_date = timezone.now() - timedelta(days=days)

        trending_authors = (
            Author.objects.filter(papers__created_at__gte=cutoff_date)
            .annotate(
                paper_count=Count("papers", distinct=True),
                avg_citations=Avg("papers__citation_count"),
            )
            .order_by("-paper_count")[:limit]
        )

        authors_data = [
            {
                "id": str(a.id),
                "name": f"{a.first_name} {a.last_name}",
                "paper_count": a.paper_count,
                "avg_citations": round(a.avg_citations or 0, 2),
                "affiliation": a.affiliation,
            }
            for a in trending_authors
        ]

        return JsonResponse(
            {"success": True, "authors": authors_data, "count": len(authors_data)}
        )
    except Exception as e:
        logger.error(f"Error getting trending authors: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_research_analytics(request):
    """API endpoint for research analytics and statistics"""
    try:
        # Overall statistics
        total_papers = Paper.objects.count()
        total_authors = Author.objects.count()
        total_journals = Journal.objects.count()

        # User-specific statistics
        user_papers = UserLibrary.objects.filter(user=request.user).count()

        # Average metrics
        avg_citations = Paper.objects.aggregate(avg=Avg("citation_count"))["avg"] or 0

        avg_impact_factor = (
            Journal.objects.aggregate(avg=Avg("impact_factor"))["avg"] or 0
        )

        # Papers per year (last 10 years)
        from django.db.models import Count

        papers_per_year = (
            Paper.objects.filter(publication_date__year__gte=timezone.now().year - 10)
            .extra(select={"year": "YEAR(publication_date)"})
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

        analytics = {
            "total_papers": total_papers,
            "total_authors": total_authors,
            "total_journals": total_journals,
            "user_papers": user_papers,
            "avg_citations": round(avg_citations, 2),
            "avg_impact_factor": round(avg_impact_factor, 2),
            "papers_per_year": list(papers_per_year),
        }

        return JsonResponse({"success": True, "analytics": analytics})
    except Exception as e:
        logger.error(f"Error getting research analytics: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# EOF
