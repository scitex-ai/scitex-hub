#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/views/search/recommendations.py
"""
Scholar App - Recommendations Module

Paper and user recommendation functions based on similarity algorithms.
Extracted from monolithic views.py for better modularity.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from scitex import logging
from ...models import SearchIndex

# Set up logger
logger = logging.getLogger(__name__)


# TODO: These helper functions need to be implemented or imported
def _calculate_paper_similarity(paper, limit=10):
    """
    Calculate similarity between papers.
    TODO: Implement similarity algorithm (e.g., TF-IDF, embeddings)
    """
    # Placeholder implementation
    return []


def _get_similar_papers_recommendations(user, recent_views):
    """
    Generate personalized recommendations based on user activity.
    TODO: Implement recommendation algorithm
    """
    # Placeholder implementation
    return []


@require_http_methods(["GET"])
def paper_recommendations(request, paper_id):
    """Get similarity recommendations for a specific paper."""
    try:
        from . import get_paper_authors

        # Get the source paper
        paper = SearchIndex.objects.get(id=paper_id, status="active")

        # Get similarity recommendations
        similar_papers = _calculate_paper_similarity(paper, limit=10)

        # Format recommendations for API response
        recommendations = []
        for sim_paper, score, reason in similar_papers:
            recommendations.append(
                {
                    "id": sim_paper.id,
                    "title": sim_paper.title,
                    "authors": get_paper_authors(sim_paper),
                    "publication_date": sim_paper.publication_date.isoformat()
                    if sim_paper.publication_date
                    else None,
                    "journal": sim_paper.journal.name if sim_paper.journal else None,
                    "abstract": sim_paper.abstract[:200] + "..."
                    if sim_paper.abstract and len(sim_paper.abstract) > 200
                    else sim_paper.abstract,
                    "citation_count": sim_paper.citation_count,
                    "similarity_score": round(score, 3),
                    "similarity_reason": reason,
                    "pdf_url": sim_paper.pdf_url,
                    "doi": sim_paper.doi,
                }
            )

        return JsonResponse(
            {
                "status": "success",
                "paper_id": paper_id,
                "paper_title": paper.title,
                "recommendations": recommendations,
                "count": len(recommendations),
            }
        )

    except SearchIndex.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Paper not found"}, status=404
        )
    except Exception as e:
        logger.error(
            f"Error generating paper recommendations for paper {paper_id}: {e}"
        )
        return JsonResponse(
            {"status": "error", "message": "Failed to generate recommendations"},
            status=500,
        )


@login_required
@require_http_methods(["GET"])
def user_recommendations(request):
    """Get personalized recommendations based on user's recent activity."""
    try:
        from . import get_paper_authors
        from ...models import RecommendationLog

        # Get user's recent views for recommendations
        recent_views = (
            RecommendationLog.objects.filter(user=request.user, clicked=True)
            .select_related("source_paper")
            .order_by("-created_at")[:10]
        )

        # Generate recommendations
        recommendations = _get_similar_papers_recommendations(
            request.user, recent_views
        )

        # Format for API response
        formatted_recommendations = []
        for rec in recommendations:
            paper = rec["paper"]
            formatted_recommendations.append(
                {
                    "id": paper.id,
                    "title": paper.title,
                    "authors": get_paper_authors(paper),
                    "publication_date": paper.publication_date.isoformat()
                    if paper.publication_date
                    else None,
                    "journal": paper.journal.name if paper.journal else None,
                    "abstract": paper.abstract[:200] + "..."
                    if paper.abstract and len(paper.abstract) > 200
                    else paper.abstract,
                    "citation_count": paper.citation_count,
                    "similarity_score": round(rec["score"], 3),
                    "similarity_reason": rec["reason"],
                    "recommendation_type": rec["type"],
                    "pdf_url": paper.pdf_url,
                    "doi": paper.doi,
                }
            )

        return JsonResponse(
            {
                "status": "success",
                "recommendations": formatted_recommendations,
                "count": len(formatted_recommendations),
            }
        )

    except Exception as e:
        logger.error(
            f"Error generating user recommendations for user {request.user.id}: {e}"
        )
        return JsonResponse(
            {
                "status": "error",
                "message": "Failed to generate personalized recommendations",
            },
            status=500,
        )
