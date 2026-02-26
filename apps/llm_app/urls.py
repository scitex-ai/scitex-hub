from django.urls import path

from . import views

app_name = "llm_app"

urlpatterns = [
    # Available providers from litellm (public metadata, no auth needed for listing)
    path(
        "api/providers/available/",
        views.api_available_providers,
        name="api_available_providers",
    ),
    # Provider management
    path("api/providers/", views.api_list_providers, name="api_list_providers"),
    path("api/providers/add/", views.api_add_provider, name="api_add_provider"),
    path(
        "api/providers/<int:provider_id>/delete/",
        views.api_delete_provider,
        name="api_delete_provider",
    ),
    path(
        "api/providers/<int:provider_id>/test/",
        views.api_test_provider,
        name="api_test_provider",
    ),
    path(
        "api/providers/<int:provider_id>/key/",
        views.api_reveal_key,
        name="api_reveal_key",
    ),
    # Usage stats
    path("api/usage/", views.api_get_usage, name="api_get_usage"),
    # AI chat with MCP tools
    path("api/chat/", views.api_chat, name="api_chat"),
    path("api/chat/stream/", views.api_chat_stream, name="api_chat_stream"),
    path("api/model/", views.api_current_model, name="api_current_model"),
    # Text-to-speech: returns audio/mpeg bytes for browser playback
    path("api/tts/", views.api_tts, name="api_tts"),
    # TTS relay: container agent → channel layer → browser speakers
    path("api/tts/relay/", views.api_tts_relay, name="api_tts_relay"),
    # Bash exec: "!" prefix mode in AI chat
    path("api/bash/", views.api_bash_exec, name="api_bash_exec"),
    # Speech-to-text: accepts audio upload, returns transcribed text via whisper.cpp
    path("api/stt/", views.api_stt, name="api_stt"),
    # List available whisper models on disk
    path("api/stt/models/", views.api_stt_models, name="api_stt_models"),
    # Skills registry API
    path("api/skills/", views.api_list_skills, name="api_list_skills"),
    path("api/skills/<str:app_name>/", views.api_get_skill, name="api_get_skill"),
    # Agent context: full snapshot of what AI agents receive (downloadable)
    path("api/agent-context/", views.api_agent_context, name="api_agent_context"),
    # Cloud context API for MCP tools / AI agents
    path("api/context/", views.api_get_context, name="api_get_context"),
    path("api/eval-js/", views.api_eval_js, name="api_eval_js"),
    path("api/ui-action/", views.api_ui_action, name="api_ui_action"),
    # Usage dashboard
    path("usage/", views.usage_dashboard, name="usage_dashboard"),
    path(
        "api/usage/chart/<str:chart_type>/",
        views.api_usage_chart,
        name="api_usage_chart",
    ),
]
