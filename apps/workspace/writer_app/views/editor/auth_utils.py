#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Authenticated project authorization utilities for Writer API views."""

import logging
from functools import wraps

from django.http import JsonResponse

from apps.infra.project_app.models import Project
from apps.security import safe_log_field

# Security-audit channel for auth denials involving untrusted input.
# Deliberately NOT under ``apps.workspace.writer_app``: that logger sets
# propagate=False (file routing), which would hide the record from the root
# handlers (console, and pytest's caplog). Auth-denial records must stay
# observable as one escaped physical line; auth_app's module loggers already
# work this way (unconfigured namespaces propagate to root).
audit_logger = logging.getLogger("apps.security.auth")

# Methods that cannot modify a project. Anything else needs write authority,
# which is what makes a read-only collaborator read-only.
_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


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
    """Require authentication and project access, read-wise and write-wise.

    The historical name is retained for import compatibility; login is no
    longer optional. Access is two gates, not one:

    - read  (GET/HEAD/OPTIONS): owner or collaborator;
    - write (anything else): owner, or a membership with write/admin
      permission — a read-only collaborator passes the read gate and must not
      pass this one.

    Both gates answer the same way a missing project does not: 401 for an
    anonymous caller, 404 for a project id that does not exist, and 403 for a
    caller who is authenticated but not allowed.
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

        if request.method not in _SAFE_METHODS and not user_can_write_project(
            request, project
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "You don't have write access to this project",
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


def user_can_write_project(request, project):
    """Return whether the caller may MODIFY a project.

    Read access is not write access. ``user_can_access_project`` above is
    read-shaped — any collaborator passes it — so a membership with
    ``permission_level == "read"`` used to be able to POST. The answer to "what
    does a write require" is the Hub's own model policy, so this delegates to
    ``Project.can_edit`` (owner, or a membership whose permission_level is
    write/admin) instead of restating it here.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    return project.can_edit(user)


def get_user_for_request(request, project_id):
    """Return the authenticated caller; anonymous sessions never imply identity.

    ``project_id`` is never trusted for identity; it is audit-logged through
    ``safe_log_field`` so a denied anonymous attempt stays traceable without
    allowing log injection.
    """
    if request.user.is_authenticated:
        return request.user, False
    audit_logger.warning(
        "[Auth] Anonymous request denied for project %s",
        safe_log_field(project_id),
    )
    return None, False
