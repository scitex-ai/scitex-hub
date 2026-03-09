#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs - Repository management endpoints."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ..views import repository as repository_views

# Repository API Router
router = DefaultRouter()
router.register(
    r"repositories",
    repository_views.RepositoryViewSet,
    basename="repositories",
)
router.register(
    r"connections",
    repository_views.RepositoryConnectionViewSet,
    basename="connections",
)
router.register(
    r"datasets",
    repository_views.DatasetViewSet,
    basename="datasets",
)

# Repository Management API
urlpatterns = [
    path("api/repository/", include(router.urls)),
    path(
        "api/repository/sync/<uuid:sync_id>/status/",
        repository_views.sync_status,
        name="sync_status",
    ),
    path(
        "api/repository/stats/",
        repository_views.user_repository_stats,
        name="user_repository_stats",
    ),
    # Legacy repository endpoints
    path(
        "api/repositories/",
        repository_views.list_repositories,
        name="list_repositories",
    ),
    path(
        "api/repository-connections/create/",
        repository_views.create_repository_connection,
        name="create_repository_connection",
    ),
]


# EOF
