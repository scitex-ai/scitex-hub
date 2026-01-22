#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-28 22:56:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/visitor.py
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

from apps.project_app.models import VisitorAllocation
from apps.project_app.services.visitor_pool import VisitorPool

logger = logging.getLogger(__name__)


def visitor_status(request):
    """
    Redirect to server_status page.

    This view is deprecated. All visitor status information is now
    integrated into the server status page at /server-status/
    """
    return redirect('public_app:server_status', permanent=True)


def visitor_restart_session(request):
    """
    Restart visitor session - logs out current expired visitor and redirects back.

    This allows expired visitors to get a new 60-minute session.
    VisitorAutoLoginMiddleware will allocate them a new visitor slot.
    Redirects to the original page user wanted to visit (stored in session).
    """
    # Get the next URL before clearing session (default to landing page)
    next_url = request.session.get('visitor_next_url', '/')

    # Validate next_url to prevent open redirect attacks
    # Only allow relative URLs starting with /
    if not next_url or not next_url.startswith('/') or next_url.startswith('//'):
        next_url = '/'

    # Don't redirect back to visitor management pages
    skip_redirects = ('/visitor-expired/', '/visitor-restart/', '/visitor-pool-full/')
    if any(next_url.startswith(skip) for skip in skip_redirects):
        next_url = '/'

    # Clear visitor allocation from session
    request.session.pop(VisitorPool.SESSION_KEY_PROJECT_ID, None)
    request.session.pop(VisitorPool.SESSION_KEY_VISITOR_ID, None)
    request.session.pop(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN, None)
    request.session.pop('visitor_next_url', None)

    # Log out the current visitor user
    logout(request)

    logger.info(f"[Visitor] Session restarted, redirecting to: {next_url}")

    # Redirect to original page - VisitorAutoLoginMiddleware will allocate a new slot
    return redirect(next_url)


def visitor_pool_full(request):
    """
    Visitor pool full page.

    Shown when all visitor demo slots are currently in use.
    Provides clear explanation and options to sign up or wait.
    """
    from django.conf import settings

    # Get pool status
    pool_status = VisitorPool.get_pool_status()

    context = {
        'pool_size': pool_status.get('total', 4),
        'allocated': pool_status.get('allocated', 0),
        'free': pool_status.get('free', 0),
        'DEBUG': settings.DEBUG,
    }

    return render(request, 'public_app/visitor_pool_full.html', context)


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
        if username.startswith('visitor-'):
            try:
                # Extract visitor number from username (visitor-001 -> 1)
                visitor_number = int(username.replace('visitor-', ''))
            except (ValueError, AttributeError):
                pass

    context = {
        'visitor_number': visitor_number,
        'expired_at': expired_at,
        'expired_minutes_ago': expired_minutes_ago or 1,  # Default to 1 if unknown
    }

    return render(request, 'public_app/visitor_expired.html', context)


def visitor_heartbeat_api(request):
    """
    Activity heartbeat endpoint for visitor session management.

    GET /api/visitor/heartbeat/

    Called periodically by the frontend to indicate user activity.
    Updates the visitor's last_activity timestamp for idle detection.
    Returns remaining session time.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not request.user.username.startswith('visitor-'):
        return JsonResponse({'error': 'Not a visitor'}, status=400)

    allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
    if not allocation_token:
        return JsonResponse({'error': 'No allocation'}, status=400)

    try:
        allocation = VisitorAllocation.objects.get(
            allocation_token=allocation_token,
            is_active=True
        )

        # Update last activity timestamp
        allocation.last_activity = timezone.now()
        allocation.save(update_fields=['last_activity'])

        # Calculate remaining time
        remaining_seconds = max(0, (allocation.expires_at - timezone.now()).total_seconds())

        return JsonResponse({
            'status': 'active',
            'remaining_seconds': int(remaining_seconds),
            'expires_at': allocation.expires_at.isoformat(),
        })

    except VisitorAllocation.DoesNotExist:
        return JsonResponse({'error': 'Allocation not found', 'status': 'expired'}, status=404)


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
        return JsonResponse({
            'error': 'This endpoint is only available in development mode'
        }, status=403)

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

        return JsonResponse({
            'success': True,
            'created': created,
            'reset': reset_count,
            'total': pool_status.get('total', 0),
            'allocated': pool_status.get('allocated', 0),
            'free': pool_status.get('free', 0),
        })

    except Exception as e:
        logger.error(f"[VisitorPool] Failed to initialize pool: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


# EOF
