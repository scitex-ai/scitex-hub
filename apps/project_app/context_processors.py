"""
Context processors for making common variables available in all templates.
"""

import re
from django.conf import settings
from django.utils import timezone
from apps.project_app.models import Project


def version_context(request):
    """Add SciTeX version to all templates."""
    return {
        "SCITEX_CLOUD_VERSION": getattr(
            settings, "SCITEX_CLOUD_VERSION", "0.1.0-alpha"
        ),
    }


def visitor_expiration_context(request):
    """
    Add visitor session expiration time and username to context.

    Returns:
        dict: visitor_expires_at, visitor_username, and is_visitor flag
    """
    from apps.project_app.services.visitor_pool import VisitorPool
    from apps.project_app.models import VisitorAllocation
    from django.contrib.auth.models import User

    # Check if user is an authenticated visitor (username starts with "visitor-")
    is_visitor = False
    if request.user.is_authenticated:
        is_visitor = request.user.username.startswith("visitor-")

    # For authenticated visitors, get allocation from session
    if is_visitor:
        allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        if allocation_token:
            try:
                allocation = VisitorAllocation.objects.get(
                    allocation_token=allocation_token,
                    is_active=True,
                    expires_at__gt=timezone.now()
                )
                return {
                    "visitor_expires_at": allocation.expires_at,
                    "visitor_username": request.user.username,
                    "is_visitor": True,
                }
            except VisitorAllocation.DoesNotExist:
                pass

        # Authenticated visitor but no valid allocation
        return {
            "visitor_expires_at": None,
            "visitor_username": request.user.username,
            "is_visitor": True,
        }

    # For non-authenticated users
    if not request.user.is_authenticated:
        allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        if allocation_token:
            try:
                allocation = VisitorAllocation.objects.get(
                    allocation_token=allocation_token,
                    is_active=True,
                    expires_at__gt=timezone.now()
                )

                # Get visitor username
                visitor_user_id = request.session.get(VisitorPool.SESSION_KEY_VISITOR_ID)
                visitor_username = None
                if visitor_user_id:
                    try:
                        visitor_user = User.objects.get(id=visitor_user_id)
                        visitor_username = visitor_user.username
                    except User.DoesNotExist:
                        pass

                return {
                    "visitor_expires_at": allocation.expires_at,
                    "visitor_username": visitor_username,
                    "is_visitor": True,
                }
            except VisitorAllocation.DoesNotExist:
                pass

    # Not a visitor
    return {
        "visitor_expires_at": None,
        "visitor_username": None,
        "is_visitor": False,
    }


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
        from apps.project_app.services.visitor_pool import VisitorPool

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
