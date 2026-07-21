"""URL configuration for scitex_agentic_journal_hub_app.

Exposes the agentic-journal UI inside the hub:

  /apps/agentic-journal/                — landing
  /apps/agentic-journal/<paper_id>/log/ — submission decision log
                                          (target of live-paper
                                          ReReviewBadge.log_url)

The badge resolver itself lives in scitex_agentic_journal (PR #32 +
the in-flight ``_hub_app_publisher`` PR); this hub app is the surface
that humans + the badge link to. See lead msg b3a51bec + publish-flow-
step-4 for path-B context.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "scitex_agentic_journal_hub_app"

urlpatterns = [
    path("", views.index_view, name="index"),
    path(
        "<paper_id>/log/",
        views.submission_log_view,
        name="submission_log",
    ),
]
