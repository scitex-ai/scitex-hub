#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Authenticated project authorization utilities for Writer API views."""

from functools import wraps

from django.http import JsonResponse

from apps.infra.project_app.models import Project


def _authentication_required():
    return JsonResponse(
        {
            "success": False,
            "error": "Authentication required. Sign up or log in.",
            "signup_url": "/auth/signup/",
            "login_url": "/auth/login/",
        },
        status=401,
    )


def api_login_optional(view_func):
    """Require authentication and owner/collaborator access to ``project_id``.

    The historical name is retained for import compatibility; login is no
    longer optional.
    """

    @wraps(view_func)
    def wrapper(request, project_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return _authentication_required()

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": f"Project {project_id} not found"},
                status=404,
            )

        if not user_can_access_project(request, project):
            return JsonResponse(
                {
                    "success": False,
                    "error": "You don't have access to this project",
                },
                status=403,
            )

        return view_func(request, project_id, *args, **kwargs)

    return wrapper


def user_can_access_project(request, project):
    """Return whether an authenticated owner or collaborator may read a project."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    if project.owner_id == user.id:
        return True
    return project.collaborators.filter(id=user.id).exists()


def get_user_for_request(request, project_id):
    """Return the authenticated caller; anonymous sessions never imply identity."""
    del project_id  # retained in the signature for existing call sites
    if request.user.is_authenticated:
        return request.user, False
    return None, False
