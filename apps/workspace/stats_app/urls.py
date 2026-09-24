"""Authenticated Hub mount for scitex-stats' Django app.

The upstream package owns the statistics UI and its project-scoped file
contract. The Hub owns the public route and its login boundary, so every
upstream view is delegated through :mod:`apps.workspace.stats_app.views`
instead of mounting the package URLconf raw.

``app_name`` matches the upstream URLconf (``"stats"``) so the leaf's
application-namespaced reverses (notably ``stats:api_project_scope``) keep
resolving — now against the gated wrapper views. The explicit
``apps/stats/`` mount also makes ``plugin_urlpatterns`` skip the raw
upstream mount for the same route.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "stats"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/health", views.health, name="health"),
    path("api/project-scope", views.project_scope, name="api_project_scope"),
    path("api/project-files", views.project_files, name="project_files"),
    path("api/project-import", views.project_import, name="project_import"),
    path("api/project-save", views.project_save, name="project_save"),
    path("api/tests", views.tests, name="tests"),
    path("api/recommend", views.recommend, name="recommend"),
    path("api/recommend-test", views.recommend_test, name="recommend_test"),
    path("api/run-all", views.run_all, name="run_all"),
    path("api/run", views.run, name="run"),
    path("api/describe", views.describe, name="describe"),
    path("api/effect-size", views.effect_size, name="effect_size"),
    path("api/power", views.power, name="power"),
    path("api/posthoc", views.posthoc, name="posthoc"),
    path("api/correct", views.correct, name="correct"),
    path("api/plot", views.plot, name="plot"),
    path("api/integrations", views.integrations, name="integrations"),
    path(
        "api/report/capabilities",
        views.report_capabilities,
        name="report_capabilities",
    ),
    path("api/report/pdf", views.report_pdf, name="report_pdf"),
    path("api/report/save", views.report_save, name="report_save"),
]

__all__ = ["urlpatterns"]
