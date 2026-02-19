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
    # Speech-to-text: accepts audio upload, returns transcribed text via whisper.cpp
    path("api/stt/", views.api_stt, name="api_stt"),
    # List available whisper models on disk
    path("api/stt/models/", views.api_stt_models, name="api_stt_models"),
]
