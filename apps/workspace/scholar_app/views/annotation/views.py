#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Annotation views for Scholar App

This module handles collaborative annotations and paper discussions.
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count
import json
import logging
from uuid import UUID

from ...models import (
    SearchIndex as Paper,
    Annotation,
    CollaborationGroup,
)

logger = logging.getLogger(__name__)


@login_required
def paper_annotations(request, paper_id):
    """Display annotations for a paper"""
    paper_id = UUID(str(paper_id))
    paper = get_object_or_404(Paper, id=paper_id)

    # Check if user has access to this paper
    has_access = paper.collections.filter(user=request.user).exists()

    if not has_access and not request.user.is_superuser:
        return JsonResponse(
            {"success": False, "error": "You do not have access to this paper"},
            status=403,
        )

    annotations = Annotation.objects.filter(paper=paper).prefetch_related(
        "user", "replies", "votes"
    )

    context = {
        "paper": paper,
        "annotations": annotations,
        "has_access": has_access,
    }

    return render(request, "scholar_app/paper_annotations.html", context)


@login_required
@require_http_methods(["GET"])
def api_paper_annotations(request, paper_id):
    """API endpoint to get annotations for a paper"""
    try:
        paper_id = UUID(str(paper_id))
        paper = Paper.objects.get(id=paper_id)

        # Check access
        has_access = paper.collections.filter(user=request.user).exists()
        if not has_access and not request.user.is_superuser:
            return JsonResponse(
                {"success": False, "error": "Access denied"}, status=403
            )

        annotations = (
            Annotation.objects.filter(paper=paper)
            .values("id", "user__username", "text", "tag", "created_at")
            .annotate(vote_count=Count("votes"), reply_count=Count("replies"))
        )

        return JsonResponse(
            {
                "success": True,
                "annotations": list(annotations),
                "count": annotations.count(),
            }
        )
    except Paper.DoesNotExist:
        return JsonResponse({"success": False, "error": "Paper not found"}, status=404)
    except Exception as e:
        logger.error(f"Error fetching annotations: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_create_annotation(request):
    """API endpoint to create an annotation"""
    try:
        data = json.loads(request.body)
        paper_id = data.get("paper_id")
        text = data.get("text")
        tag = data.get("tag")

        if not paper_id or not text:
            return JsonResponse(
                {"success": False, "error": "paper_id and text are required"},
                status=400,
            )

        paper_id = UUID(str(paper_id))
        paper = Paper.objects.get(id=paper_id)

        # Check access
        has_access = paper.collections.filter(user=request.user).exists()
        if not has_access and not request.user.is_superuser:
            return JsonResponse(
                {"success": False, "error": "Access denied"}, status=403
            )

        annotation = Annotation.objects.create(
            paper=paper, user=request.user, text=text, tag=tag
        )

        return JsonResponse(
            {
                "success": True,
                "annotation_id": str(annotation.id),
                "created_at": annotation.created_at.isoformat(),
            }
        )
    except Paper.DoesNotExist:
        return JsonResponse({"success": False, "error": "Paper not found"}, status=404)
    except Exception as e:
        logger.error(f"Error creating annotation: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_update_annotation(request, annotation_id):
    """API endpoint to update an annotation"""
    try:
        annotation_id = UUID(str(annotation_id))
        annotation = Annotation.objects.get(id=annotation_id)

        # Check ownership
        if annotation.user != request.user:
            return JsonResponse(
                {"success": False, "error": "You can only edit your own annotations"},
                status=403,
            )

        data = json.loads(request.body)

        if "text" in data:
            annotation.text = data["text"]
        if "tag" in data:
            annotation.tag = data["tag"]

        annotation.save()

        return JsonResponse(
            {"success": True, "message": "Annotation updated successfully"}
        )
    except Annotation.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Annotation not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error updating annotation: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def api_delete_annotation(request, annotation_id):
    """API endpoint to delete an annotation"""
    try:
        annotation_id = UUID(str(annotation_id))
        annotation = Annotation.objects.get(id=annotation_id)

        # Check ownership
        if annotation.user != request.user:
            return JsonResponse(
                {"success": False, "error": "You can only delete your own annotations"},
                status=403,
            )

        annotation.delete()

        return JsonResponse(
            {"success": True, "message": "Annotation deleted successfully"}
        )
    except Annotation.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Annotation not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error deleting annotation: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_vote_annotation(request, annotation_id):
    """API endpoint to vote on an annotation"""
    try:
        annotation_id = UUID(str(annotation_id))
        annotation = Annotation.objects.get(id=annotation_id)

        data = json.loads(request.body)
        vote_type = data.get("vote_type")  # 'up' or 'down'

        if vote_type not in ["up", "down"]:
            return JsonResponse(
                {"success": False, "error": 'vote_type must be "up" or "down"'},
                status=400,
            )

        vote, created = annotation.votes.get_or_create(
            user=request.user, defaults={"vote_type": vote_type}
        )

        if not created:
            vote.vote_type = vote_type
            vote.save()

        vote_count = annotation.votes.filter(vote_type="up").count()

        return JsonResponse(
            {"success": True, "created": created, "vote_count": vote_count}
        )
    except Annotation.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Annotation not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error voting on annotation: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_collaboration_groups(request):
    """API endpoint to get user's collaboration groups"""
    try:
        groups = CollaborationGroup.objects.filter(members=request.user).values(
            "id", "name", "description"
        )

        return JsonResponse(
            {"success": True, "groups": list(groups), "count": groups.count()}
        )
    except Exception as e:
        logger.error(f"Error fetching collaboration groups: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def paper_recommendations(request, paper_id):
    """Get similar papers recommendations"""
    try:
        paper_id = UUID(str(paper_id))
        paper = Paper.objects.get(id=paper_id)

        # Find similar papers based on tags/keywords
        similar_papers = Paper.objects.filter(
            keywords__icontains=paper.keywords
        ).exclude(id=paper_id)[:5]

        return JsonResponse(
            {
                "success": True,
                "recommendations": [
                    {
                        "id": str(p.id),
                        "title": p.title,
                        "authors": ", ".join(
                            [f"{a.first_name} {a.last_name}" for a in p.authors.all()]
                        ),
                        "year": (
                            p.publication_date.year if p.publication_date else "Unknown"
                        ),
                    }
                    for p in similar_papers
                ],
            }
        )
    except Paper.DoesNotExist:
        return JsonResponse({"success": False, "error": "Paper not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def user_recommendations(request):
    """Get personalized paper recommendations for user"""
    try:
        # Get user's saved papers
        from ...models import UserLibrary

        user_papers = UserLibrary.objects.filter(user=request.user).values_list(
            "paper_id", flat=True
        )

        # Find similar papers
        recommendations = Paper.objects.filter(
            keywords__icontains=(
                Paper.objects.filter(id__in=user_papers).first().keywords
                if user_papers
                else ""
            )
        ).exclude(id__in=user_papers)[:10]

        return JsonResponse(
            {
                "success": True,
                "recommendations": [
                    {
                        "id": str(p.id),
                        "title": p.title,
                        "authors": ", ".join(
                            [f"{a.first_name} {a.last_name}" for a in p.authors.all()]
                        ),
                        "year": (
                            p.publication_date.year if p.publication_date else "Unknown"
                        ),
                    }
                    for p in recommendations
                ],
            }
        )
    except Exception as e:
        logger.error(f"Error getting user recommendations: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# EOF
