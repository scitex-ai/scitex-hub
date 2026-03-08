#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Console App Service & On-site API URLs

REST API endpoints for:
- Project services (TensorBoard, Jupyter, etc.) — list, start, stop
- Paste/drag-drop file upload
- On-site agent capture (request, status, upload, permission)
"""

from django.urls import path

from .. import service_api_lifecycle, service_api_list
from ..views import on_site as on_site_views
from ..views import paste_upload as paste_upload_views

urlpatterns = [
    # Project Service API (TensorBoard, Jupyter, etc.)
    path(
        "api/service-types/",
        service_api_list.service_types_api,
        name="api_service_types",
    ),
    path(
        "api/services/<str:username>/<str:project_slug>/",
        service_api_list.ServiceListAPI.as_view(),
        name="api_service_list",
    ),
    path(
        "api/services/<str:username>/<str:project_slug>/start/",
        service_api_lifecycle.ServiceStartAPI.as_view(),
        name="api_service_start",
    ),
    path(
        "api/services/<str:service_id>/stop/",
        service_api_lifecycle.ServiceStopAPI.as_view(),
        name="api_service_stop",
    ),
    # Paste/drag-drop upload to project scitex/downloads/
    path(
        "api/paste-upload/",
        paste_upload_views.api_paste_upload,
        name="api_paste_upload",
    ),
    # On-site agent capture API
    path(
        "api/on-site/capture/",
        on_site_views.api_capture_request,
        name="api_capture_request",
    ),
    path(
        "api/on-site/capture/<uuid:request_id>/status/",
        on_site_views.api_capture_status,
        name="api_capture_status",
    ),
    path(
        "api/on-site/capture/upload/",
        on_site_views.api_capture_upload,
        name="api_capture_upload",
    ),
    path(
        "api/on-site/permission/",
        on_site_views.api_capture_permission,
        name="api_capture_permission",
    ),
    path(
        "api/on-site/permission/check/",
        on_site_views.api_capture_permission_check,
        name="api_capture_permission_check",
    ),
]

# EOF
