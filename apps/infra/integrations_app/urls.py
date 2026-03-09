from django.urls import path
from . import views

app_name = "integrations_app"

urlpatterns = [
    # Dashboard
    path("", views.integrations_dashboard, name="dashboard"),
    # ORCID
    path("orcid/connect/", views.orcid_connect, name="orcid_connect"),
    path("orcid/callback/", views.orcid_callback, name="orcid_callback"),
    path("orcid/disconnect/", views.orcid_disconnect, name="orcid_disconnect"),
    path("orcid/sync/", views.orcid_sync, name="orcid_sync"),
    # BibTeX Export
    path(
        "export/<int:project_id>/bib/",
        views.export_project_bib,
        name="export_project_bib",
    ),
    # Slack
    path("slack/configure/", views.slack_configure, name="slack_configure"),
    path("slack/<int:webhook_id>/test/", views.slack_test, name="slack_test"),
    path("slack/<int:webhook_id>/delete/", views.slack_delete, name="slack_delete"),
    # API endpoints
    path("api/status/", views.api_integration_status, name="api_status"),
    path("api/orcid/profile/", views.api_orcid_profile, name="api_orcid_profile"),
]
