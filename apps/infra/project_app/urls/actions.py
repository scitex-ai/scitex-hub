"""
Actions Feature URLs

Handles social interactions (watch, star, fork) and project statistics.
API-only endpoints for project interactions.
"""

from django.urls import path
from ..api_views_module.api_views import (
    api_project_watch,
    api_project_star,
    api_project_fork,
    api_project_stats,
)

# No app_name here - namespace is provided by parent (project_app)

urlpatterns = [
    # Social interaction API endpoints (Watch, Star, Fork)
    path("watch/", api_project_watch, name="watch"),
    path("star/", api_project_star, name="star"),
    path("fork/", api_project_fork, name="fork"),
    path("stats/", api_project_stats, name="stats"),
]
