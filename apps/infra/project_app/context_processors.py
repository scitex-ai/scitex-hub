"""
Context processors for making common variables available in all templates.
"""

import re

from django.conf import settings

from apps.infra.project_app.models import Project


def version_context(request):
    """Add SciTeX version to all templates."""
    return {
        "SCITEX_HUB_VERSION": getattr(settings, "SCITEX_HUB_VERSION", "0.1.0-alpha"),
    }


# The pool-occupancy projection (VISITOR_POOL_STATUS_KEYS /
# _visitor_pool_status_cached) was deleted 2026-09-11 with the visitor header
# badge (card drop-visitor-readonly-freemium-20260911): no template reads
# visitor_pool_status anymore — test_visitor_badge_projection.py now asserts
# that and fails if the badge (and its data source) is reintroduced.


def visitor_expiration_context(request):
    """
    Session-role context for all templates (post visitor retirement).

    Returns only what live templates still consume:
        dict: session_role — canonical session-role model
              (services.visitor_pool.get_session_role); read by
              global_base.html (data-session-role) and the JS role guards
              (readonly-visitor-guard.ts, visitor-heartbeat.ts). Still
              meaningful for PRE-retirement visitor-00N / readonly-visitor
              user rows, who can log in; for new sessions it is
              'registered' or 'anonymous'.
              visitor_username — the launcher guest CTA identity slice
              (Visitor #NNN).
              visitor_idle_timeout_minutes — the enforced PoolAllocator
              idle-reaper constant, quoted by the launcher CTA copy so the
              lifetime claim can't drift from the actual reaper.

    The former keys (is_visitor / is_readonly / visitor_expires_at /
    visitor_cpus / visitor_memory_gb / visitor_pool_status /
    readonly_visitor_notice* / readonly_visitor_reason*) are dropped: their
    only consumers were the visitor badge / menu / popover markup removed in
    the same retirement, and no template or live test reads them.
    """
    from apps.infra.project_app.services.visitor_pool import (
        ROLE_READONLY_VISITOR,
        ROLE_VISITOR,
        get_session_role,
    )
    from apps.infra.project_app.services.visitor_pool.pool_manager import (
        PoolAllocator,
    )

    role = get_session_role(request)
    context = {
        "session_role": role,
        "visitor_username": None,
        "visitor_idle_timeout_minutes": PoolAllocator.IDLE_TIMEOUT_MINUTES,
    }

    # A pre-retirement visitor / readonly-visitor row logging in still gets
    # the launcher guest-CTA identity slice.
    if role in (ROLE_VISITOR, ROLE_READONLY_VISITOR):
        context["visitor_username"] = request.user.username

    return context


def project_context(request):
    """
    Add current project to context if URL matches /<username>/<project-slug>/ pattern.

    This makes 'project' available in all templates for context-aware navigation.

    For visitor users (visitors), provides allocated project from visitor pool.
    """
    # Pattern: /<username>/<project-slug>/...
    pattern = r"^/([^/]+)/([^/]+)/"
    match = re.match(pattern, request.path)

    # Get guest project URL from middleware
    guest_project_url = getattr(request, "guest_project_url", "/guest/default")

    # Check for visitor project from session FIRST (for non-authenticated users)
    project = None
    if not request.user.is_authenticated:
        from apps.infra.project_app.services.visitor_pool import VisitorPool

        visitor_project_id = request.session.get(VisitorPool.SESSION_KEY_PROJECT_ID)
        if visitor_project_id:
            try:
                project = Project.objects.get(id=visitor_project_id)
            except Project.DoesNotExist:
                pass

    if match:
        username = match.group(1)
        project_slug = match.group(2)

        # Handle guest sessions (guest-<16chars>/default)
        if username.startswith("guest-") and project_slug == "default":
            # Guest session workspace
            return {
                "project": project,  # Use visitor project if available
                "guest_project_url": guest_project_url,
                "is_guest_session": True,
                "guest_username": username,
            }

        try:
            # Try to get real project from URL
            from django.contrib.auth.models import User

            user = User.objects.get(username=username)
            url_project = Project.objects.get(slug=project_slug, owner=user)
            return {
                "project": url_project,  # URL project takes precedence
                "guest_project_url": guest_project_url,
                "is_guest_session": False,
            }
        except (User.DoesNotExist, Project.DoesNotExist):
            pass

    # Provide default project URL
    # Logged-in users: /<username>/default
    # Visitor users: /guest-<session-id>/default
    if request.user.is_authenticated:
        default_project_url = f"/{request.user.username}/default"
    else:
        # Build from session ID
        if hasattr(request, "guest_session_id") and request.guest_session_id:
            default_project_url = f"/guest-{request.guest_session_id}/default"
        else:
            default_project_url = "/guest/default"

    return {
        "project": project,  # Include visitor project for visitor users
        "guest_project_url": default_project_url,
        "default_project_url": default_project_url,
        "is_guest_session": not request.user.is_authenticated,
    }
