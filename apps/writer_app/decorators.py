"""
Writer app decorators for handling authentication including visitor users.
"""

from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.models import User
from apps.project_app.models import VisitorAllocation, Project
from apps.project_app.services.visitor_pool import VisitorPool
import logging

logger = logging.getLogger(__name__)


def writer_auth_required(view_func):
    """
    Decorator that allows both authenticated users and visitors.

    For authenticated users: Uses request.user
    For visitors: Gets visitor user from session allocation

    Sets:
        - request.effective_user: The user to use (either authenticated or visitor)
        - request.is_visitor: Boolean indicating if this is a visitor
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if request.user.is_authenticated:
            request.effective_user = request.user
            request.is_visitor = False
            return view_func(request, *args, **kwargs)

        # Check for visitor allocation
        allocation_token = request.session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        visitor_user_id = request.session.get(VisitorPool.SESSION_KEY_VISITOR_ID)

        if not allocation_token or not visitor_user_id:
            return JsonResponse({
                "success": False,
                "error": "Authentication required. Please log in or wait for a visitor slot."
            }, status=401)

        # Verify visitor allocation is still valid
        try:
            visitor_user = User.objects.get(id=visitor_user_id)

            # Check if allocation is still active
            allocation = VisitorAllocation.objects.filter(
                allocation_token=allocation_token,
                is_active=True
            ).first()

            if not allocation:
                return JsonResponse({
                    "success": False,
                    "error": "Visitor session expired. Please refresh the page."
                }, status=401)

            # Set effective user for the view
            request.effective_user = visitor_user
            request.is_visitor = True
            request.visitor_allocation = allocation

            return view_func(request, *args, **kwargs)

        except User.DoesNotExist:
            logger.error(f"Visitor user {visitor_user_id} not found")
            return JsonResponse({
                "success": False,
                "error": "Invalid visitor session"
            }, status=401)

    return wrapper


def writer_project_access_required(view_func):
    """
    Decorator that ensures user has access to the requested project.
    Must be used after writer_auth_required.

    Checks project_id from URL kwargs and verifies:
    - For authenticated users: User owns the project
    - For visitors: Project matches their allocated default-project
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        project_id = kwargs.get('project_id')

        if not project_id:
            return JsonResponse({
                "success": False,
                "error": "No project specified"
            }, status=400)

        # Check if effective_user was set by writer_auth_required
        if not hasattr(request, 'effective_user'):
            return JsonResponse({
                "success": False,
                "error": "Authentication required"
            }, status=401)

        # Get project
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Project not found"
            }, status=404)

        # Check access based on user type
        if hasattr(request, 'is_visitor') and request.is_visitor:
            # Visitor must access their own default project
            visitor_project_id = request.session.get(VisitorPool.SESSION_KEY_PROJECT_ID)
            if project.id != visitor_project_id:
                return JsonResponse({
                    "success": False,
                    "error": "Visitors can only access their default project"
                }, status=403)
        else:
            # Authenticated user must own the project
            if project.owner != request.effective_user:
                return JsonResponse({
                    "success": False,
                    "error": "You don't have access to this project"
                }, status=403)

        # Add project to request
        request.project = project
        return view_func(request, *args, **kwargs)

    return wrapper
