"""Chat session CRUD API endpoints."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.infra.llm_app.models import ChatMessage, ChatSession


def _session_to_dict(session, include_count=True):
    d = {
        "id": session.id,
        "title": session.title,
        "share_token": str(session.share_token),
        "is_shared": session.is_shared,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "is_archived": session.is_archived,
    }
    if include_count:
        d["message_count"] = session.messages.count()
    # Preview: first sentence of first user message (for tooltip)
    first_msg = session.messages.filter(role="user").order_by("id").first()
    if first_msg:
        text = first_msg.text.strip()
        # Extract first sentence (up to 120 chars)
        for sep in (".", "!", "?", "\n"):
            idx = text.find(sep)
            if 0 < idx < 120:
                text = text[: idx + 1]
                break
        d["preview"] = text[:120]
    else:
        d["preview"] = ""
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
        if "is_shared" in body:
            session.is_shared = bool(body["is_shared"])
            fields.append("is_shared")
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


# --- Public shared session endpoints (no auth required) ---


@require_http_methods(["GET"])
def api_shared_session(request, token):
    """Public read-only API for a shared chat session."""
    session = get_object_or_404(ChatSession, share_token=token, is_shared=True)
    messages = list(
        session.messages.all().values(
            "role", "text", "tools_used", "media", "created_at"
        )
    )
    return JsonResponse(
        {
            "title": session.title,
            "owner": session.user.username,
            "created_at": session.created_at.isoformat(),
            "messages": messages,
        }
    )


@require_http_methods(["GET"])
def shared_session_page(request, token):
    """Public read-only HTML page for a shared chat session."""
    session = get_object_or_404(ChatSession, share_token=token, is_shared=True)
    messages = list(
        session.messages.all().values(
            "role", "text", "tools_used", "media", "created_at"
        )
    )
    return render(
        request,
        "llm_app/shared_session.html",
        {
            "session": session,
            "chat_messages": messages,
        },
    )
