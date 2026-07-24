"""
Context processors for making common variables available in all templates.
"""

import re

from django.conf import settings
from django.utils import timezone

from apps.infra.project_app.models import Project


def version_context(request):
    """Add SciTeX version to all templates."""
    return {
        "SCITEX_HUB_VERSION": getattr(settings, "SCITEX_HUB_VERSION", "0.1.0-alpha"),
    }


#: Pool-occupancy cache (requirement 4, card hub-visitor-ux-allapps):
#: cheap enough for the header on every page — one query per minute.
VISITOR_POOL_STATUS_CACHE_KEY = "visitor_pool_status"
VISITOR_POOL_STATUS_CACHE_SECONDS = 60


def _visitor_pool_status_cached():
    """{"total", "allocated"} for the header badge, cached 60s.

    Returns None (badge hides occupancy) when the pool tables are not
    migrated yet — logged loudly, never masked as fake numbers.
    """
    import logging

    from django.core.cache import cache

    from apps.infra.project_app.services.visitor_pool import VisitorPool

    def _load():
        status = VisitorPool.get_pool_status()
        return {"total": status["total"], "allocated": status["allocated"]}

    try:
        return cache.get_or_set(
            VISITOR_POOL_STATUS_CACHE_KEY, _load, VISITOR_POOL_STATUS_CACHE_SECONDS
        )
    except Exception as exc:
        logging.getLogger(__name__).error(
            "[VisitorPool] pool-status query failed (occupancy hidden): %s", exc
        )
        return None


def visitor_expiration_context(request):
    """
    Visitor-session context for all templates (card hub-visitor-ux-allapps).

    Role handling is delegated to the canonical session-role model
    (services.visitor_pool.get_session_role) — no username checks here.

    Returns:
        dict: session_role, visitor_expires_at, visitor_username,
              is_visitor, is_readonly, visitor_cpus, visitor_memory_gb,
              visitor_idle_timeout_minutes (idle-reaper threshold — banner
              copy quotes the enforced constant, never hardcoded prose),
              readonly_visitor_notice (one-shot downgrade reason code),
              readonly_visitor_notice_detail (its user-facing copy),
              readonly_visitor_reason (persistent downgrade reason code),
              readonly_visitor_reason_detail (its user-facing copy),
              visitor_pool_status ({total, allocated} — readonly sessions)
    """
    from django.contrib.auth.models import User

    from apps.infra.project_app.models import VisitorAllocation
    from apps.infra.project_app.services.visitor_pool import (
        ROLE_ANONYMOUS,
        ROLE_READONLY_VISITOR,
        ROLE_VISITOR,
        SESSION_KEY_READONLY_NOTICE,
        VisitorPool,
        get_readonly_reason,
        get_session_role,
        readonly_reason_detail,
    )
    from apps.infra.project_app.services.visitor_pool.pool_manager import (
        PoolAllocator,
    )
    from config.settings.quotas import SLURM_QUOTAS

    role = get_session_role(request)
    context = {
        "session_role": role,
        "visitor_expires_at": None,
        "visitor_username": None,
        "is_visitor": role in (ROLE_VISITOR, ROLE_READONLY_VISITOR),
        "is_readonly": role == ROLE_READONLY_VISITOR,
        "visitor_cpus": SLURM_QUOTAS.get("interactive_cpus", 2),
        "visitor_memory_gb": SLURM_QUOTAS.get("interactive_memory_gb", 4),
        # A visitor session is NOT a fixed lifetime: activity heartbeats
        # keep extending it; the idle reaper reclaims after this many
        # minutes of inactivity (see PoolAllocator.extend_session_on_activity).
        "visitor_idle_timeout_minutes": PoolAllocator.IDLE_TIMEOUT_MINUTES,
        "readonly_visitor_notice": "",
        "readonly_visitor_notice_detail": "",
        "readonly_visitor_reason": "",
        "readonly_visitor_reason_detail": "",
        "visitor_pool_status": None,
    }

    # Shared read-only visitor (no writable slot at allocation time)
    if role == ROLE_READONLY_VISITOR:
        context["visitor_username"] = request.user.username
        # Fail-loud: one-shot explanation of WHY this session is read-only
        # (reason code set by VisitorAutoLoginMiddleware on downgrade,
        # shown once by the banner).
        notice = request.session.pop(SESSION_KEY_READONLY_NOTICE, "")
        context["readonly_visitor_notice"] = notice
        if notice:
            context["readonly_visitor_notice_detail"] = readonly_reason_detail(notice)
        # Persistent reason for the header badge popover/dropdown — the
        # state (and its truthful explanation) outlives the one-shot banner.
        reason = get_readonly_reason(request.session)
        context["readonly_visitor_reason"] = reason
        context["readonly_visitor_reason_detail"] = readonly_reason_detail(reason)
        context["visitor_pool_status"] = _visitor_pool_status_cached()
        return context

    # Writable pool visitor — expose allocation expiry when valid
    if role == ROLE_VISITOR:
        context["visitor_username"] = request.user.username
        allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        if allocation_token:
            try:
                allocation = VisitorAllocation.objects.get(
                    allocation_token=allocation_token,
                    is_active=True,
                    expires_at__gt=timezone.now(),
                )
                context["visitor_expires_at"] = allocation.expires_at
            except VisitorAllocation.DoesNotExist:
                pass
        return context

    # Anonymous with a leftover allocation in the session (pre-login edge)
    if role == ROLE_ANONYMOUS:
        allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        if allocation_token:
            try:
                allocation = VisitorAllocation.objects.get(
                    allocation_token=allocation_token,
                    is_active=True,
                    expires_at__gt=timezone.now(),
                )
                visitor_user_id = request.session.get(
                    VisitorPool.SESSION_KEY_VISITOR_ID
                )
                if visitor_user_id:
                    try:
                        context["visitor_username"] = User.objects.get(
                            id=visitor_user_id
                        ).username
                    except User.DoesNotExist:
                        pass
                context["visitor_expires_at"] = allocation.expires_at
                context["is_visitor"] = True
            except VisitorAllocation.DoesNotExist:
                pass

    # Registered user or plain anonymous
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
