"""API endpoints for comment/annotation operations on manuscripts."""

import json
import logging
from difflib import SequenceMatcher

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
            anchor_text=data.get("anchor_text", ""),
            anchor_context_before=data.get("anchor_context_before", ""),
            anchor_context_after=data.get("anchor_context_after", ""),
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


def _find_anchor_position(content, anchor_text, context_before="", context_after=""):
    """Find the line range of anchor_text in content.

    Returns (line_start, line_end, confidence) or None if not found.
    Confidence: 1.0 = exact match, 0.7-0.99 = fuzzy match, 0 = not found.
    """
    if not anchor_text:
        return None

    # Step 1: Try exact substring match
    positions = []
    start = 0
    while True:
        idx = content.find(anchor_text, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1

    if len(positions) == 1:
        # Unique exact match
        char_pos = positions[0]
        line_start = content[:char_pos].count("\n") + 1
        line_end = content[: char_pos + len(anchor_text)].count("\n") + 1
        return (line_start, line_end, 1.0)

    if len(positions) > 1 and (context_before or context_after):
        # Step 2: Disambiguate using context
        best_pos = None
        best_score = 0
        for pos in positions:
            score = 0
            if context_before:
                before_text = content[max(0, pos - len(context_before)) : pos]
                score += SequenceMatcher(None, context_before, before_text).ratio()
            if context_after:
                after_end = pos + len(anchor_text)
                after_text = content[after_end : after_end + len(context_after)]
                score += SequenceMatcher(None, context_after, after_text).ratio()
            if score > best_score:
                best_score = score
                best_pos = pos
        if best_pos is not None:
            line_start = content[:best_pos].count("\n") + 1
            line_end = content[: best_pos + len(anchor_text)].count("\n") + 1
            return (line_start, line_end, 0.95)

    if positions:
        # Multiple matches, no context — use first
        char_pos = positions[0]
        line_start = content[:char_pos].count("\n") + 1
        line_end = content[: char_pos + len(anchor_text)].count("\n") + 1
        return (line_start, line_end, 0.9)

    # Step 3: Fuzzy matching via sliding window
    best_ratio = 0
    best_start = 0
    anchor_len = len(anchor_text)
    # Scan with windows of similar length (±30%)
    for window_size in [anchor_len, int(anchor_len * 0.8), int(anchor_len * 1.2)]:
        if window_size < 1:
            continue
        for i in range(len(content) - window_size + 1):
            window = content[i : i + window_size]
            ratio = SequenceMatcher(None, anchor_text, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i

    if best_ratio >= 0.7:
        line_start = content[:best_start].count("\n") + 1
        line_end = content[: best_start + anchor_len].count("\n") + 1
        return (line_start, line_end, best_ratio)

    return None


@login_required
@require_http_methods(["POST"])
def reanchor_comments(request, manuscript_id):
    """Re-anchor comments after a section edit.

    POST body:
        {
            "section_id": "manuscript/methods",
            "content": "<full section content after edit>"
        }

    Returns updated comments with new line positions.
    """
    try:
        manuscript, error = _get_manuscript_or_error(manuscript_id, request.user)
        if error:
            return error

        data = json.loads(request.body)
        section_id = data.get("section_id")
        content = data.get("content", "")

        if not section_id:
            return JsonResponse(
                {"success": False, "error": "section_id is required"}, status=400
            )

        comments = Comment.objects.filter(
            manuscript=manuscript,
            section_id=section_id,
            anchor_text__gt="",
        ).select_related("author")

        reanchored = 0
        lost = 0
        results = []

        for comment in comments:
            result = _find_anchor_position(
                content,
                comment.anchor_text,
                comment.anchor_context_before,
                comment.anchor_context_after,
            )

            if result:
                line_start, line_end, confidence = result
                comment.line_start = line_start
                comment.line_end = line_end
                comment.save(update_fields=["line_start", "line_end"])
                reanchored += 1
                d = comment.to_dict()
                d["anchor_confidence"] = round(confidence, 3)
                results.append(d)
            else:
                lost += 1
                d = comment.to_dict()
                d["anchor_confidence"] = 0
                d["anchor_lost"] = True
                results.append(d)

        return JsonResponse(
            {
                "success": True,
                "reanchored": reanchored,
                "lost": lost,
                "comments": results,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error re-anchoring comments: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
