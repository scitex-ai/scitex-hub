import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.llm_app.services import UserLLMService
from apps.llm_app.utils import litellm_model_string


@login_required
@require_http_methods(["GET"])
def api_current_model(request):
    """Return the model name that will be used for the next chat request."""
    service = UserLLMService(request.user)
    if not service.connection or not service.llm_connection:
        return JsonResponse({"success": False, "model": None})
    model = litellm_model_string(
        service.connection.service, service.llm_connection.default_model
    )
    return JsonResponse(
        {"success": True, "model": model or service.llm_connection.default_model}
    )


@login_required
@require_http_methods(["POST"])
def api_tts(request):
    """Generate TTS audio bytes for browser playback.

    Delegates to scitex.audio.generate_bytes() — backends tried in order:
    elevenlabs (if ELEVENLABS_API_KEY set) → gtts (free, internet) → pyttsx3.
    Returns audio/mpeg; browser creates a Blob URL and plays via Web Audio API.
    Returns 503 when no backend is available so frontend falls back to
    window.speechSynthesis.
    """
    import scitex.audio as _audio

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    text = data.get("text", "").strip()[:4096]
    if not text:
        return JsonResponse({"error": "text required"}, status=400)

    voice = data.get("voice", None)
    backend = data.get("backend", None)

    try:
        audio_bytes = _audio.generate_bytes(text, backend=backend, voice=voice)
        return HttpResponse(audio_bytes, content_type="audio/mpeg")
    except ValueError as e:
        # No backend available (missing packages / API keys)
        return JsonResponse({"error": str(e)}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _build_system_prompt(context: dict, user, sync_to_async=None) -> str:
    """Build base system prompt (sync portion — call before async context injection)."""
    prompt = (
        "You are a scientific research assistant integrated into the SciTeX platform. "
        "You have access to tools for statistics, plotting, literature search, "
        "diagram creation, and manuscript writing. Use them when appropriate.\n"
        "When working with project files use the project_* tools "
        "(project_list_files, project_read_file, project_write_file, project_search_files). "
        "Always pass the exact root_path shown in this prompt."
    )
    if context.get("page"):
        prompt += f"\nUser is on page: {context['page']}"
    if context.get("project"):
        prompt += f"\nCurrent project: {context['project']}"
    if context.get("current_file"):
        prompt += f"\nUser is viewing: {context['current_file']}"
    return prompt


async def _inject_project_root(prompt: str, user, project_slug: str) -> str:
    """Resolve project root path server-side and append to system prompt."""
    from asgiref.sync import sync_to_async

    if not project_slug:
        return prompt
    try:
        from apps.project_app.models import Project
        from apps.project_app.services.filesystem.paths import get_project_root_path

        project = await sync_to_async(
            lambda: Project.objects.filter(owner=user, slug=project_slug).first()
        )()
        if project:
            root = await sync_to_async(get_project_root_path)(user, project)
            if root:
                prompt += (
                    f"\nProject root path: {root}"
                    "\nUse this exact root_path when calling project_* file tools."
                )
    except Exception:
        pass  # project context is optional
    return prompt


@transaction.non_atomic_requests
@login_required
@require_http_methods(["POST"])
async def api_chat_stream(request):
    """Streaming AI chat endpoint using Server-Sent Events."""
    import json as _json

    from asgiref.sync import sync_to_async
    from django.http import StreamingHttpResponse

    from apps.llm_app.services.llm_service import UserLLMService as _ULS

    try:
        data = _json.loads(request.body)
    except _json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return JsonResponse(
            {"success": False, "error": "prompt is required"}, status=400
        )

    context = data.get("context", {})
    system_prompt = _build_system_prompt(context, request.user)
    system_prompt = await _inject_project_root(
        system_prompt, request.user, context.get("project_slug", "")
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    service = await sync_to_async(_ULS)(user=request.user)
    if not service.connection:
        return JsonResponse(
            {
                "success": False,
                "error": "No AI provider configured. Go to Settings > AI Providers to add one.",
            },
            status=400,
        )

    async def sse_generator():
        try:
            async for event in service.complete_with_tools_streaming(
                messages=messages,
                app_name="console_app",
                feature="ai_chat_stream",
            ):
                yield f"data: {_json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    response = StreamingHttpResponse(sse_generator(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@transaction.non_atomic_requests
@login_required
@require_http_methods(["POST"])
async def api_chat(request):
    """Non-streaming AI chat endpoint with MCP tool access."""
    from asgiref.sync import sync_to_async

    from apps.llm_app.services.llm_service import LLMProviderError, RateLimitError

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return JsonResponse(
            {"success": False, "error": "prompt is required"}, status=400
        )

    context = data.get("context", {})
    system_prompt = _build_system_prompt(context, request.user)
    system_prompt = await _inject_project_root(
        system_prompt, request.user, context.get("project_slug", "")
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    service = await sync_to_async(UserLLMService)(user=request.user)
    if not service.connection:
        return JsonResponse(
            {
                "success": False,
                "error": "No AI provider configured. Go to Settings > AI Providers to add one.",
            },
            status=400,
        )

    try:
        result = await service.complete_with_tools(
            messages=messages,
            app_name="console_app",
            feature="ai_chat",
        )
        return JsonResponse(
            {
                "success": True,
                "text": result["text"],
                "tools_used": result["tools_used"],
                "response_time_ms": result["response_time_ms"],
            }
        )

    except RateLimitError as e:
        return JsonResponse(
            {"success": False, "error": f"Rate limit exceeded: {e}"},
            status=429,
        )
    except LLMProviderError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"AI request failed: {e}"},
            status=500,
        )
