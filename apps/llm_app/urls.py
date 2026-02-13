from django.urls import path

from . import views

app_name = "llm_app"

urlpatterns = [
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
    # Usage stats
    path("api/usage/", views.api_get_usage, name="api_get_usage"),
]
