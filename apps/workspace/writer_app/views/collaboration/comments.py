"""API endpoints for comment/annotation operations on manuscripts."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...models import Comment, Manuscript

logger = logging.getLogger(__name__)


def _get_manuscript_or_error(manuscript_id, user):
    """Retrieve manuscript and verify access. Returns (manuscript, error_response)."""
    try:
        manuscript = Manuscript.objects.select_related("owner", "project").get(
            id=manuscript_id
        )
    except Manuscript.DoesNotExist:
        return None, JsonResponse(
            {"success": False, "error": "Manuscript not found"}, status=404
        )
    # Access check: owner or project collaborator
    if manuscript.owner_id != user.id:
        if manuscript.project and hasattr(manuscript.project, "collaborators"):
            if not manuscript.project.collaborators.filter(id=user.id).exists():
                return None, JsonResponse(
                    {"success": False, "error": "Access denied"}, status=403
                )
        # Allow access if no project-level restrictions are enforced
    return manuscript, None


@login_required
@require_http_methods(["GET"])
def list_comments(request, manuscript_id):
    """List comments for a manuscript.

    Query params:
        section_id (optional): Filter by section
        status (optional): Filter by status (open/resolved/closed)
        parent_only (optional): If "true", only return top-level comments
    """
    try:
        manuscript, error = _get_manuscript_or_error(manuscript_id, request.user)
        if error:
            return error

        comments = Comment.objects.filter(manuscript=manuscript).select_related(
            "author"
        )

        # Optional filters
        section_id = request.GET.get("section_id")
        if section_id:
            comments = comments.filter(section_id=section_id)

        status = request.GET.get("status")
        if status in ("open", "resolved", "closed"):
            comments = comments.filter(status=status)

        parent_only = request.GET.get("parent_only")
        if parent_only == "true":
            comments = comments.filter(parent__isnull=True)

        return JsonResponse(
            {
                "success": True,
                "comments": [c.to_dict() for c in comments],
            }
        )

    except Exception as e:
        logger.error(f"Error listing comments: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_comment(request, manuscript_id):
    """Create a new comment on a manuscript.

    POST body:
        {
            "section_id": "manuscript/methods",
            "line_start": 10,
            "line_end": 15,
            "text": "This paragraph needs a citation.",
            "parent_id": null  (optional, for replies)
        }
    """
    try:
        manuscript, error = _get_manuscript_or_error(manuscript_id, request.user)
        if error:
            return error

        data = json.loads(request.body)

        # Validate required fields
        required = ["section_id", "line_start", "line_end", "text"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return JsonResponse(
                {"success": False, "error": f"Missing fields: {', '.join(missing)}"},
                status=400,
            )

        # Validate parent exists and belongs to same manuscript
        parent_id = data.get("parent_id")
        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, manuscript=manuscript)
            except Comment.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Parent comment not found"},
                    status=404,
                )

        comment = Comment.objects.create(
            manuscript=manuscript,
            author=request.user,
            section_id=data["section_id"],
            line_start=int(data["line_start"]),
            line_end=int(data["line_end"]),
            text=data["text"],
            parent=parent,
        )

        return JsonResponse(
            {
                "success": True,
                "comment": comment.to_dict(),
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error creating comment: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["PATCH"])
def update_comment(request, manuscript_id, comment_id):
    """Update a comment's text.

    PATCH body:
        {
            "text": "Updated comment content"
        }

    Only the comment author can update it.
    """
    try:
        manuscript, error = _get_manuscript_or_error(manuscript_id, request.user)
        if error:
            return error

        try:
            comment = Comment.objects.get(id=comment_id, manuscript=manuscript)
        except Comment.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Comment not found"}, status=404
            )

        if comment.author_id != request.user.id:
            return JsonResponse(
                {"success": False, "error": "Only the author can edit this comment"},
                status=403,
            )

        data = json.loads(request.body)
        text = data.get("text")
        if not text:
            return JsonResponse(
                {"success": False, "error": "text is required"}, status=400
            )

        comment.text = text
        comment.save(update_fields=["text", "updated_at"])

        return JsonResponse(
            {
                "success": True,
                "comment": comment.to_dict(),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error updating comment: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def resolve_comment(request, manuscript_id, comment_id):
    """Resolve a comment thread.

    Sets status to 'resolved'. Any collaborator on the manuscript can resolve.
    """
    try:
        manuscript, error = _get_manuscript_or_error(manuscript_id, request.user)
        if error:
            return error

        try:
            comment = Comment.objects.get(
                id=comment_id, manuscript=manuscript, parent__isnull=True
            )
        except Comment.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Top-level comment not found"},
                status=404,
            )

        comment.status = "resolved"
        comment.save(update_fields=["status", "updated_at"])

        return JsonResponse(
            {
                "success": True,
                "comment": comment.to_dict(),
            }
        )

    except Exception as e:
        logger.error(f"Error resolving comment: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_comment(request, manuscript_id, comment_id):
    """Delete a comment.

    Only the comment author or manuscript owner can delete.
    Deleting a parent comment cascades to all replies.
    """
    try:
        manuscript, error = _get_manuscript_or_error(manuscript_id, request.user)
        if error:
            return error

        try:
            comment = Comment.objects.get(id=comment_id, manuscript=manuscript)
        except Comment.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Comment not found"}, status=404
            )

        # Only author or manuscript owner can delete
        if (
            comment.author_id != request.user.id
            and manuscript.owner_id != request.user.id
        ):
            return JsonResponse(
                {"success": False, "error": "Permission denied"},
                status=403,
            )

        comment.delete()

        return JsonResponse({"success": True})

    except Exception as e:
        logger.error(f"Error deleting comment: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
