import json
import uuid

from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.llm_app.funded_chat.config import (
    FundedChatConfigurationError,
    load_funded_chat_config,
)
from apps.infra.llm_app.funded_chat.errors import provider_error_payload
from apps.infra.llm_app.funded_chat.provider import litellm_provider_call
from apps.infra.llm_app.funded_chat.service import FundedChatDenied, FundedChatService
from apps.infra.llm_app.services import UserLLMService
from apps.infra.llm_app.utils import LLM_PROVIDERS, litellm_model_string
from apps.infra.llm_app.views.sse_utils import build_multimodal_user_msg, with_keepalive

MAX_CHAT_HTTP_BODY_BYTES = 131_072


def _request_idempotency_key(request) -> str:
    value = request.headers.get("Idempotency-Key")
    if value is None:
        return uuid.uuid4().hex
    if value != value.strip() or not 1 <= len(value) <= 200:
        raise ValueError("invalid Idempotency-Key")
    return value


def _execute_funded_chat(user, messages: list[dict], idempotency_key: str):
    """The sole executor for every no-BYOK provider request."""

    config = load_funded_chat_config()
    request_body = json.dumps(
        {"messages": messages}, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if config.tools_enabled:
        from apps.infra.llm_app.funded_chat.provider import litellm_tool_loop_call

        def _loop_call(cfg, body, key=""):
            return litellm_tool_loop_call(
                cfg, body, key, user=user, max_rounds=config.tool_max_rounds
            )

        provider_call = _loop_call
    else:
        provider_call = litellm_provider_call
    return FundedChatService(config=config).execute(
        user,
        idempotency_key=idempotency_key,
        request_body=request_body,
        provider_call=provider_call,
    )


def _funded_error_payload(exc: FundedChatDenied, *, model: str) -> dict:
    return {
        "category": exc.category,
        "remaining": None,
        "reset_at": "",
        "model": model,
        "error": "AI provider request failed",
        "retry_after": exc.retry_after_seconds,
        "support_id": exc.support_id,
    }


def _model_display_name(service_id: str, model_id: str) -> str:
    """Derive a human-friendly model name from provider + model ID.

    Strips provider prefix and date suffixes dynamically — no hardcoding.
    """
    import re

    provider = LLM_PROVIDERS.get(service_id, {})
    provider_display = provider.get("display", service_id).split("(")[0].strip()
    # Strip provider prefix (e.g. "gemini/" from "gemini/gemini-2.0-flash")
    prefix = provider.get("model_prefix", "")
    base = model_id
    if prefix and base.startswith(prefix):
        base = base[len(prefix) :]
    # Strip date suffix (e.g. "-20241022")
    base = re.sub(r"-\d{8}$", "", base)
    return f"{provider_display} · {base}"


def _sanitized_provider_payload(exc: BaseException, *, model: str = "") -> dict:
    """Build the browser contract without retaining provider exception text."""

    return provider_error_payload(
        exc,
        remaining=None,
        reset_at="",
        model=model,
    )


def _service_model(service: UserLLMService) -> str:
    if not service.connection or not service.llm_connection:
        return ""
    return litellm_model_string(
        service.connection.service,
        service.llm_connection.default_model,
    )


@login_required
@require_http_methods(["GET"])
def api_current_model(request):
    """Return the model name that will be used for the next chat request."""
    service = UserLLMService(request.user)
    if not service.connection or not service.llm_connection:
        try:
            config = load_funded_chat_config()
        except FundedChatConfigurationError:
            return JsonResponse({"success": False, "model": None}, status=503)
        if config.enabled:
            return JsonResponse(
                {
                    "success": True,
                    "model": config.litellm_model,
                    "display": _model_display_name(config.provider, config.model),
                    "funded": True,
                }
            )
        return JsonResponse({"success": False, "model": None})
    model = litellm_model_string(
        service.connection.service, service.llm_connection.default_model
    )
    display = _model_display_name(
        service.connection.service, service.llm_connection.default_model
    )
    return JsonResponse(
        {
            "success": True,
            "model": model or service.llm_connection.default_model,
            "display": display,
        }
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
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        # Use async_to_sync (not a throwaway new_event_loop) so the send runs
        # on the same event loop the in-memory/Redis channel layer is bound to.
        # InMemoryChannelLayer keys its queues to the running loop, so sending
        # on an isolated loop would silently drop the message for any reader on
        # the request's loop.
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "tts_speak", "text": text},
        )
        return JsonResponse({"success": True, "relayed_to": group_name})
    except Exception as e:
        logger.error("TTS relay failed: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


def _build_system_prompt(context: dict, user, sync_to_async=None) -> str:
    """Build system prompt with skill-aware context injection.

    Uses the rich base prompt from export_chat_prompt() which includes
    web app structure, all skills, key patterns, and MCP tool groups —
    matching the depth that terminal agents receive via SKILL.md.
    """
    from apps.infra.llm_app.skills import build_system_prompt, get_skill_for_page
    from apps.infra.llm_app.skills.export import export_chat_prompt

    base_prompt = export_chat_prompt()

    # Append project file guidance — tool list is auto-discovered from MCP
    base_prompt += (
        "When working with project files use the project_* tools. "
        "Always pass the exact root_path shown in this prompt.\n"
    )

    if context.get("project"):
        base_prompt += f"\nCurrent project: {context['project']}"
    if context.get("current_file"):
        base_prompt += f"\nUser is viewing: {context['current_file']}"

    # Skill-aware enhancement (active skill for current page)
    page = context.get("page", "")
    skill = get_skill_for_page(page) if page else None
    page_hints = context.get("page_hints", [])

    from apps.infra.llm_app.page_context import page_context_prompt

    return page_context_prompt(context) + build_system_prompt(
        skill, base_prompt, page_hints or None
    )


async def _inject_project_root(prompt: str, user, project_slug: str) -> str:
    """Resolve project root path server-side and append to system prompt."""
    from asgiref.sync import sync_to_async

    if not project_slug:
        return prompt
    try:
        from apps.infra.project_app.models import Project
        from apps.infra.project_app.services.filesystem.paths import (
            get_project_root_path,
        )

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
    from apps.infra.llm_app.skills import get_skill_for_page

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

    from apps.infra.llm_app.services.llm_service import UserLLMService as _ULS

    if len(request.body) > MAX_CHAT_HTTP_BODY_BYTES:
        return JsonResponse(
            {"success": False, "error": "Request too large"}, status=413
        )
    try:
        idempotency_key = _request_idempotency_key(request)
    except ValueError:
        return JsonResponse(
            {"success": False, "error": "Invalid Idempotency-Key"}, status=400
        )
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

    user_msg = build_multimodal_user_msg(prompt, data.get("attachments", []))
    messages = [
        {"role": "system", "content": system_prompt},
        user_msg,
    ]

    # Derive app_name from page context for accurate usage tracking
    app_name = _derive_app_name(context)

    service = await sync_to_async(_ULS)(user=request.user)
    use_funded = not service.connection
    funded_model = ""
    if use_funded:
        try:
            funded_config = load_funded_chat_config()
        except FundedChatConfigurationError:
            return JsonResponse(
                {"success": False, "error": "AI provider unavailable"}, status=503
            )
        if not funded_config.enabled:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No AI provider configured.",
                    "settings_url": "/accounts/settings/ai-providers/",
                },
                status=400,
            )
        funded_model = funded_config.litellm_model

    # Resolve project root for media detection in tool results
    project_slug = context.get("project_slug", "")
    project_root_str = None
    username = request.user.username
    if project_slug:
        try:
            from apps.infra.project_app.models import Project
            from apps.infra.project_app.services.filesystem.paths import (
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
            if use_funded:
                result = await sync_to_async(
                    _execute_funded_chat, thread_sensitive=True
                )(request.user, messages, idempotency_key)
                yield f"data: {_json.dumps({'type': 'chunk', 'text': result.text})}\n\n"
            else:
                async for event in with_keepalive(
                    service.complete_with_tools_streaming(
                        messages=messages,
                        app_name=app_name,
                        feature="ai_chat_stream",
                        project_root=project_root_str,
                    )
                ):
                    yield event
        except FundedChatDenied as exc:
            payload = {
                "type": "error",
                **_funded_error_payload(exc, model=funded_model),
            }
            yield f"data: {_json.dumps(payload)}\n\n"
        except Exception as exc:
            model = funded_model if use_funded else _service_model(service)
            payload = {"type": "error", **_sanitized_provider_payload(exc, model=model)}
            yield f"data: {_json.dumps(payload)}\n\n"
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

    from apps.infra.llm_app.services.llm_service import LLMProviderError, RateLimitError

    if len(request.body) > MAX_CHAT_HTTP_BODY_BYTES:
        return JsonResponse(
            {"success": False, "error": "Request too large"}, status=413
        )
    try:
        idempotency_key = _request_idempotency_key(request)
    except ValueError:
        return JsonResponse(
            {"success": False, "error": "Invalid Idempotency-Key"}, status=400
        )
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

    user_msg = build_multimodal_user_msg(prompt, data.get("attachments", []))
    messages = [
        {"role": "system", "content": system_prompt},
        user_msg,
    ]

    app_name = _derive_app_name(context)

    service = await sync_to_async(UserLLMService)(user=request.user)
    if not service.connection:
        try:
            funded_config = load_funded_chat_config()
        except FundedChatConfigurationError:
            return JsonResponse(
                {"success": False, "error": "AI provider unavailable"}, status=503
            )
        if not funded_config.enabled:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No AI provider configured.",
                    "settings_url": "/accounts/settings/ai-providers/",
                },
                status=400,
            )
        try:
            import time

            t0 = time.monotonic()
            result = await sync_to_async(_execute_funded_chat, thread_sensitive=True)(
                request.user, messages, idempotency_key
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            return JsonResponse(
                {
                    "success": True,
                    "text": result.text,
                    "tools_used": [],
                    "response_time_ms": elapsed,
                    "funded": True,
                }
            )
        except FundedChatDenied as exc:
            payload = _funded_error_payload(exc, model=funded_config.litellm_model)
            status = 429 if exc.category in {"quota_reached", "rate_limit"} else 502
            return JsonResponse({"success": False, **payload}, status=status)
        except Exception as exc:
            payload = _sanitized_provider_payload(
                exc, model=funded_config.litellm_model
            )
            return JsonResponse({"success": False, **payload}, status=502)

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

    except RateLimitError as exc:
        payload = _sanitized_provider_payload(exc, model=_service_model(service))
        return JsonResponse({"success": False, **payload}, status=429)
    except LLMProviderError as exc:
        payload = _sanitized_provider_payload(exc, model=_service_model(service))
        return JsonResponse({"success": False, **payload}, status=502)
    except Exception as exc:
        payload = _sanitized_provider_payload(exc, model=_service_model(service))
        return JsonResponse({"success": False, **payload}, status=502)
