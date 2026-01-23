"""
Pull Request Review

Handles PR review submission and comments.
"""

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import logging

from apps.project_app.models import (
    Project,
    PullRequest,
    PullRequestReview,
    PullRequestComment,
    PullRequestEvent,
)

logger = logging.getLogger(__name__)


@login_required
@require_POST
def pr_review_submit(request, username, slug, pr_number):
    """
    Submit review (approve, request changes, comment).

    URL: /<username>/<slug>/pull/<pr_number>/review/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    # Check permissions
    if not project.can_view(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Get review data
    review_state = request.POST.get(
        "state", "commented"
    )  # approved, changes_requested, commented
    content = request.POST.get("content", "").strip()

    # Validation
    if review_state not in ["approved", "changes_requested", "commented"]:
        return JsonResponse({"error": "Invalid review state"}, status=400)

    if not content and review_state != "approved":
        return JsonResponse({"error": "Review content is required"}, status=400)

    try:
        # Create review
        review = PullRequestReview.objects.create(
            pull_request=pr,
            reviewer=request.user,
            state=review_state,
            content=content,
        )

        # Create event
        PullRequestEvent.objects.create(
            pull_request=pr,
            event_type="reviewed",
            actor=request.user,
            metadata={"state": review_state},
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Review submitted successfully",
                "review_id": review.id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to submit review: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@login_required
@require_POST
def pr_comment_create(request, username, slug, pr_number):
    """
    Add comment (general or inline).

    URL: /<username>/<slug>/pull/<pr_number>/comment/
    """
    project = get_object_or_404(Project, owner__username=username, slug=slug)
    pr = get_object_or_404(PullRequest, project=project, number=pr_number)

    # Check permissions
    if not project.can_view(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Get comment data
    content = request.POST.get("content", "").strip()
    file_path = request.POST.get("file_path", "")
    line_number = request.POST.get("line_number", "")
    commit_sha = request.POST.get("commit_sha", "")
    parent_id = request.POST.get("parent_id", "")

    # Validation
    if not content:
        return JsonResponse({"error": "Comment content is required"}, status=400)

    try:
        # Create comment
        comment_data = {
            "pull_request": pr,
            "author": request.user,
            "content": content,
        }

        # Add inline comment fields if provided
        if file_path and line_number:
            comment_data["file_path"] = file_path
            comment_data["line_number"] = int(line_number)
            comment_data["commit_sha"] = commit_sha

        # Add parent for threaded comments
        if parent_id:
            parent_comment = PullRequestComment.objects.get(
                id=parent_id, pull_request=pr
            )
            comment_data["parent_comment"] = parent_comment

        comment = PullRequestComment.objects.create(**comment_data)

        # Create event
        PullRequestEvent.objects.create(
            pull_request=pr,
            event_type="comment",
            actor=request.user,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Comment added successfully",
                "comment_id": comment.id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to create comment: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )
