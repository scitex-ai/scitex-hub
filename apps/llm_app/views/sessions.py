"""Chat session CRUD API endpoints."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.llm_app.models import ChatMessage, ChatSession


def _session_to_dict(session, include_count=True):
    d = {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "is_archived": session.is_archived,
    }
    if include_count:
        d["message_count"] = session.messages.count()
    return d


@login_required
@require_http_methods(["GET", "POST"])
def api_sessions(request):
    """List or create chat sessions."""
    if request.method == "GET":
        qs = ChatSession.objects.filter(user=request.user, is_archived=False)
        sessions = [_session_to_dict(s) for s in qs[:50]]
        return JsonResponse({"sessions": sessions})

    # POST: create
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    title = body.get("title", "New chat").strip()[:200] or "New chat"
    session = ChatSession.objects.create(user=request.user, title=title)
    return JsonResponse(_session_to_dict(session, include_count=False), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def api_session_detail(request, session_id):
    """Get, update, or delete a specific session."""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(_session_to_dict(session))

    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        fields = []
        if "title" in body:
            session.title = body["title"].strip()[:200] or session.title
            fields.append("title")
        if "is_archived" in body:
            session.is_archived = bool(body["is_archived"])
            fields.append("is_archived")
        if fields:
            session.save(update_fields=fields + ["updated_at"])
        return JsonResponse(_session_to_dict(session))

    # DELETE
    session.delete()
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["GET"])
def api_session_messages(request, session_id):
    """Load messages for a session."""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    messages = session.messages.all().values(
        "id", "role", "text", "tools_used", "media", "created_at"
    )
    return JsonResponse(
        {
            "session_id": session.id,
            "title": session.title,
            "messages": list(messages),
        }
    )


@login_required
@require_http_methods(["POST"])
def api_session_add_message(request, session_id):
    """Add a message to a session (used by stream handler after completion)."""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    role = body.get("role", "").strip()
    if role not in ("user", "assistant", "error"):
        return JsonResponse({"error": "Invalid role"}, status=400)

    text = body.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "Text required"}, status=400)

    msg = ChatMessage.objects.create(
        session=session,
        role=role,
        text=text,
        tools_used=body.get("tools_used", []),
        media=body.get("media", []),
    )

    # Auto-title from first user message
    if role == "user" and session.title == "New chat":
        session.title = text[:50] + ("..." if len(text) > 50 else "")
        session.save(update_fields=["title", "updated_at"])
    else:
        session.save(update_fields=["updated_at"])

    return JsonResponse({"id": msg.id, "created_at": msg.created_at.isoformat()})
