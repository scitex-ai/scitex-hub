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
        # Fall back to campaign mode if available
        from apps.llm_app.services.campaign_service import (
            get_campaign_config,
            is_campaign_enabled,
        )

        if is_campaign_enabled():
            config = get_campaign_config()
            return JsonResponse(
                {
                    "success": True,
                    "model": f"anthropic/{config['model']}",
                    "campaign": True,
                }
            )
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


@login_required
@require_http_methods(["POST"])
def api_tts_relay(request):
    """Relay TTS from container agent to user's browser via channel layer.

    Called by scitex MCP ``audio_speak`` inside Apptainer when it detects
    it's running in a container context (SCITEX_CONTAINER=1).  Pushes a
    ``tts_speak`` message to the user's terminal WebSocket group so the
    browser can call ``/llm/api/tts/`` and play audio through speakers.
    """
    import logging

    from channels.layers import get_channel_layer

    logger = logging.getLogger(__name__)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    text = data.get("text", "").strip()[:4096]
    if not text:
        return JsonResponse({"error": "text required"}, status=400)

    username = request.user.username
    group_name = f"speech_{username}"

    try:
        import asyncio

        channel_layer = get_channel_layer()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            channel_layer.group_send(
                group_name,
                {"type": "tts_speak", "text": text},
            )
        )
        loop.close()
        return JsonResponse({"success": True, "relayed_to": group_name})
    except Exception as e:
        logger.error("TTS relay failed: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


def _build_system_prompt(context: dict, user, sync_to_async=None) -> str:
    """Build system prompt with skill-aware context injection."""
    from apps.llm_app.skills import build_system_prompt, get_skill_for_page

    base_prompt = (
        "You are a scientific research assistant integrated into the SciTeX platform. "
        "You have access to tools for statistics, plotting, literature search, "
        "diagram creation, and manuscript writing. Use them when appropriate.\n"
        "When working with project files use the project_* tools "
        "(project_list_files, project_read_file, project_write_file, project_search_files). "
        "Always pass the exact root_path shown in this prompt.\n\n"
        "## Media Rendering\n"
        "When MCP tools create files (plt_plot, project_write_file, etc.), "
        "images and plots are automatically rendered inline in this chat. "
        "Supported: .png, .jpg, .svg, .gif (inline images), .csv/.tsv (interactive tables), "
        ".pdf (file links), .mmd (diagram links). "
        "Your response text is rendered as Markdown — use code blocks, headers, lists, "
        "and tables for clear formatting."
    )
    if context.get("project"):
        base_prompt += f"\nCurrent project: {context['project']}"
    if context.get("current_file"):
        base_prompt += f"\nUser is viewing: {context['current_file']}"

    # Skill-aware enhancement
    page = context.get("page", "")
    skill = get_skill_for_page(page) if page else None
    page_hints = context.get("page_hints", [])

    return build_system_prompt(skill, base_prompt, page_hints or None)


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


def _derive_app_name(context: dict) -> str:
    """Derive app_name from page context for accurate usage tracking."""
    from apps.llm_app.skills import get_skill_for_page

    page = context.get("page", "")
    if page:
        skill = get_skill_for_page(page)
        if skill:
            return f"{skill.app_name}_app"
    return "llm_app"


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

    # Derive app_name from page context for accurate usage tracking
    app_name = _derive_app_name(context)

    service = await sync_to_async(_ULS)(user=request.user)
    use_campaign = False
    if not service.connection:
        # Check campaign mode before returning error
        from apps.llm_app.services.campaign_service import (
            check_campaign_rate_limit,
            increment_campaign_usage,
            is_campaign_enabled,
        )

        if not is_campaign_enabled():
            return JsonResponse(
                {
                    "success": False,
                    "error": "No AI provider configured.",
                    "settings_url": "/accounts/settings/ai-providers/",
                },
                status=400,
            )
        allowed, remaining, err_msg = await sync_to_async(check_campaign_rate_limit)(
            request
        )
        if not allowed:
            return JsonResponse(
                {"success": False, "error": err_msg, "campaign": True},
                status=429,
            )
        use_campaign = True

    # Resolve project root for media detection in tool results
    project_slug = context.get("project_slug", "")
    project_root_str = None
    username = request.user.username
    if project_slug:
        try:
            from apps.project_app.models import Project
            from apps.project_app.services.filesystem.paths import (
                get_project_root_path,
            )

            project = await sync_to_async(
                lambda: Project.objects.filter(
                    owner=request.user, slug=project_slug
                ).first()
            )()
            if project:
                root = await sync_to_async(get_project_root_path)(request.user, project)
                if root:
                    project_root_str = str(root)
        except Exception:
            pass

    async def sse_generator():
        # Emit project context so frontend can build blob URLs for media
        if project_slug and username:
            yield (
                f"data: {_json.dumps({'type': 'context', 'username': username, 'slug': project_slug})}\n\n"
            )
        try:
            if use_campaign:
                from apps.llm_app.services.campaign_service import (
                    campaign_complete_streaming,
                )

                resp = await campaign_complete_streaming(messages)
                full_text = ""
                async for chunk in resp:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_text += delta.content
                        yield f"data: {_json.dumps({'type': 'chunk', 'text': delta.content})}\n\n"
                await sync_to_async(increment_campaign_usage)(request)
            else:
                async for event in service.complete_with_tools_streaming(
                    messages=messages,
                    app_name=app_name,
                    feature="ai_chat_stream",
                    project_root=project_root_str,
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

    app_name = _derive_app_name(context)

    service = await sync_to_async(UserLLMService)(user=request.user)
    if not service.connection:
        # Check campaign mode before returning error
        from apps.llm_app.services.campaign_service import (
            campaign_complete_streaming,
            check_campaign_rate_limit,
            increment_campaign_usage,
            is_campaign_enabled,
        )

        if not is_campaign_enabled():
            return JsonResponse(
                {
                    "success": False,
                    "error": "No AI provider configured.",
                    "settings_url": "/accounts/settings/ai-providers/",
                },
                status=400,
            )
        allowed, remaining, err_msg = await sync_to_async(check_campaign_rate_limit)(
            request
        )
        if not allowed:
            return JsonResponse(
                {"success": False, "error": err_msg, "campaign": True},
                status=429,
            )

        try:
            import time

            t0 = time.monotonic()
            resp = await campaign_complete_streaming(messages)
            full_text = ""
            async for chunk in resp:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
            elapsed = int((time.monotonic() - t0) * 1000)
            await sync_to_async(increment_campaign_usage)(request)
            return JsonResponse(
                {
                    "success": True,
                    "text": full_text,
                    "tools_used": [],
                    "response_time_ms": elapsed,
                    "campaign": True,
                }
            )
        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Campaign chat failed: {e}"},
                status=500,
            )

    try:
        result = await service.complete_with_tools(
            messages=messages,
            app_name=app_name,
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
