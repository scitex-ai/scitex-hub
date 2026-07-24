#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 22:56:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/visitor.py
# ----------------------------------------
from __future__ import annotations

__FILE__ = "./apps/public_app/views/status/visitor.py"
# ----------------------------------------

"""
Visitor Status Views

Views for visitor session management and status.
"""

import logging

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.infra.project_app.models import VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool

logger = logging.getLogger(__name__)


def visitor_status(request):
    """
    Redirect to server_status page.

    This view is deprecated. All visitor status information is now
    integrated into the server status page at /server-status/
    """
    return redirect("public_app:server_status", permanent=True)


def visitor_restart_session(request):
    """
    Restart visitor session - logs out current expired visitor and redirects back.

    This allows expired visitors to get a new 60-minute session.
    VisitorAutoLoginMiddleware will allocate them a new visitor slot.
    Redirects to the original page user wanted to visit (stored in session).
    """
    # Get the next URL before clearing session (default to landing page)
    next_url = request.session.get("visitor_next_url", "/")

    # Validate next_url to prevent open redirect attacks
    # Only allow relative URLs starting with /
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"

    # Don't redirect back to visitor management pages
    skip_redirects = ("/visitor-expired/", "/visitor-restart/", "/visitor-pool-full/")
    if any(next_url.startswith(skip) for skip in skip_redirects):
        next_url = "/"

    # Clear visitor allocation from session
    request.session.pop(VisitorPool.SESSION_KEY_PROJECT_ID, None)
    request.session.pop(VisitorPool.SESSION_KEY_VISITOR_ID, None)
    request.session.pop(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN, None)
    request.session.pop("visitor_next_url", None)

    # Log out the current visitor user
    logout(request)

    logger.info(f"[Visitor] Session restarted, redirecting to: {next_url}")

    # Redirect to original page - VisitorAutoLoginMiddleware will allocate a new slot
    return redirect(next_url)


def visitor_pool_full(request):
    """
    Visitor pool full page.

    Shown when:
    1. All visitor demo slots are currently in use (pool exhausted)
    2. User hasn't accepted cookies (can't allocate visitor session)

    Provides clear explanation and options to sign up or accept cookies.

    In DEBUG mode: Auto-resets pool when full (development convenience).
    """
    from django.conf import settings

    # Check if user has cookie consent
    has_cookie_consent = request.COOKIES.get("scitex_consent")

    # Get pool status
    pool_status = VisitorPool.get_pool_status()
    free_slots = pool_status.get("free", 0)

    # Determine reason for being here
    if not has_cookie_consent:
        # User hasn't accepted cookies - show cookies required message
        reason = "no_cookies"
    elif free_slots > 0:
        # Slots available and has cookies - redirect to home (middleware will allocate)
        return redirect("public_app:index")
    else:
        # Pool actually exhausted
        reason = "pool_full"

        # DEV MODE: Auto-reset pool when full for development convenience
        if settings.DEBUG:
            logger.info("[VisitorPool] DEV MODE: Auto-resetting full visitor pool")
            try:
                # Free all allocations (quick reset)
                freed = VisitorAllocation.objects.filter(is_active=True).update(
                    is_active=False
                )
                logger.info(f"[VisitorPool] DEV MODE: Freed {freed} allocations")

                # Redirect to home - middleware will allocate new slot
                return redirect("public_app:index")
            except Exception as e:
                logger.error(f"[VisitorPool] DEV MODE: Auto-reset failed: {e}")
                # Fall through to show pool full page

    context = {
        "pool_size": pool_status.get("total", 4),
        "allocated": pool_status.get("allocated", 0),
        "free": free_slots,
        "DEBUG": settings.DEBUG,
        "reason": reason,
        "has_cookie_consent": has_cookie_consent,
    }

    if reason == "no_cookies":
        # Pre-consent visitors have no session: the header logo's default
        # "/" would bounce straight back to this page (2026-07-08 iPhone
        # field report: logo read as a dead touch target). Point it at the
        # landing page, which always renders without a session.
        context["header_logo_href"] = "/landing/"

    return render(request, "public_app/visitor_pool_full.html", context)


def visitor_expired(request):
    """
    Visitor session expiration page.

    Shown when a visitor's 60-minute session expires.
    Provides clear explanation and options to sign up or start a new session.
    """
    # Try to get visitor allocation info from session or database
    visitor_number = None
    expired_at = None
    expired_minutes_ago = None

    # Check session for visitor allocation token
    allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
    if allocation_token:
        try:
            allocation = VisitorAllocation.objects.get(
                allocation_token=allocation_token
            )
            visitor_number = allocation.visitor_number
            expired_at = allocation.expires_at

            # Calculate how long ago it expired
            if expired_at:
                time_diff = timezone.now() - expired_at
                expired_minutes_ago = max(1, int(time_diff.total_seconds() / 60))
        except VisitorAllocation.DoesNotExist:
            pass

    # If no allocation found in session, check if user is logged in as visitor
    if not visitor_number and request.user.is_authenticated:
        username = request.user.username
        if username.startswith("visitor-"):
            try:
                # Extract visitor number from username (visitor-001 -> 1)
                visitor_number = int(username.replace("visitor-", ""))
            except (ValueError, AttributeError):
                pass

    context = {
        "visitor_number": visitor_number,
        "expired_at": expired_at,
        "expired_minutes_ago": expired_minutes_ago or 1,  # Default to 1 if unknown
    }

    return render(request, "public_app/visitor_expired.html", context)


@require_POST
def visitor_fill_slots_api(request):
    """
    Fill all visitor pool slots (Dev only).

    POST /api/visitor-pool/fill-slots/

    Marks all allocations as active to simulate pool-full state.
    Next anonymous visitor will get readonly-visitor mode.
    """
    if not settings.DEBUG:
        return JsonResponse({"error": "Only available in development mode"}, status=403)

    try:
        import secrets
        from datetime import timedelta

        freed_first = VisitorAllocation.objects.filter(is_active=True).update(
            is_active=False
        )
        filled = 0
        pool_size = VisitorPool.POOL_SIZE
        for i in range(1, pool_size + 1):
            VisitorAllocation.objects.update_or_create(
                visitor_number=i,
                defaults={
                    "session_key": f"dev-fill-{i}",
                    "allocation_token": secrets.token_hex(32),
                    "expires_at": timezone.now() + timedelta(hours=1),
                    "is_active": True,
                },
            )
            filled += 1

        # Log out current user so they get reassigned as readonly-visitor
        logout(request)

        return JsonResponse(
            {
                "success": True,
                "filled": filled,
                "message": "All slots filled. Reload to enter read-only mode.",
            }
        )
    except Exception as e:
        logger.error(f"[VisitorPool] Fill slots failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_POST
def visitor_free_slots_api(request):
    """
    Free all visitor pool slots (Dev only).

    POST /api/visitor-pool/free-slots/
    """
    if not settings.DEBUG:
        return JsonResponse({"error": "Only available in development mode"}, status=403)

    try:
        freed = VisitorAllocation.objects.filter(is_active=True).update(is_active=False)
        logout(request)
        return JsonResponse(
            {
                "success": True,
                "freed": freed,
                "message": "All slots freed. Reload to get a regular visitor slot.",
            }
        )
    except Exception as e:
        logger.error(f"[VisitorPool] Free slots failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def visitor_heartbeat_api(request):
    """
    Activity heartbeat endpoint for visitor session management.

    GET /api/visitor/heartbeat/

    Called periodically by the frontend to indicate user activity.
    Updates the visitor's last_activity timestamp for idle detection.
    Returns remaining session time.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)

    if not request.user.username.startswith("visitor-"):
        return JsonResponse({"error": "Not a visitor"}, status=400)

    allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
    if not allocation_token:
        return JsonResponse({"error": "No allocation"}, status=400)

    try:
        allocation = VisitorAllocation.objects.get(
            allocation_token=allocation_token, is_active=True
        )

        # Stamp activity AND extend the lease. Allocation only grants a
        # short probation lease (bot defense — see PoolAllocator); this
        # first heartbeat is what promotes a real browser to the full
        # session, and later beats keep an active visitor from hitting a
        # hard mid-work expiry.
        VisitorPool.extend_session_on_activity(allocation)

        # Calculate remaining time
        remaining_seconds = max(
            0, (allocation.expires_at - timezone.now()).total_seconds()
        )

        return JsonResponse(
            {
                "status": "active",
                "remaining_seconds": int(remaining_seconds),
                "expires_at": allocation.expires_at.isoformat(),
            }
        )

    except VisitorAllocation.DoesNotExist:
        return JsonResponse(
            {"error": "Allocation not found", "status": "expired"}, status=404
        )


@require_POST
def visitor_pool_initialize_api(request):
    """
    API endpoint to initialize/reset visitor pool (Dev only).

    POST /api/visitor-pool/initialize/

    This clears all allocations and re-initializes the visitor pool.
    Only available in DEBUG mode for development purposes.
    """
    # Only allow in DEBUG mode
    if not settings.DEBUG:
        return JsonResponse(
            {"error": "This endpoint is only available in development mode"}, status=403
        )

    try:
        # Clear all existing allocations
        VisitorAllocation.objects.all().delete()
        logger.info("[VisitorPool] Cleared all existing allocations")

        # Reset all project directories to default template
        reset_count = VisitorPool.reset_all_project_directories()
        logger.info(f"[VisitorPool] Reset {reset_count} project directories")

        # Initialize the pool (creates any missing users/projects)
        created = VisitorPool.initialize_pool()
        logger.info(f"[VisitorPool] Initialized pool with {created} visitors")

        # Get updated status
        pool_status = VisitorPool.get_pool_status()

        return JsonResponse(
            {
                "success": True,
                "created": created,
                "reset": reset_count,
                "total": pool_status.get("total", 0),
                "allocated": pool_status.get("allocated", 0),
                "free": pool_status.get("free", 0),
            }
        )

    except Exception as e:
        logger.error(f"[VisitorPool] Failed to initialize pool: {e}")
        return JsonResponse({"error": str(e)}, status=500)


# EOF
