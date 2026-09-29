"""Authentication and project authorization decorators for Writer."""

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


def writer_auth_required(view_func):
    """Require a real authenticated user and expose it as ``effective_user``."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _authentication_required()
        request.effective_user = request.user
        return view_func(request, *args, **kwargs)

    return wrapper


def writer_project_access_required(view_func):
    """Require the authenticated caller to have edit access to the project."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        project_id = kwargs.get("project_id")
        if not project_id:
            return JsonResponse(
                {"success": False, "error": "No project specified"}, status=400
            )
        if not request.user.is_authenticated:
            return _authentication_required()

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Project not found"}, status=404
            )

        if not project.can_edit(request.user):
            return JsonResponse(
                {"success": False, "error": "You don't have access to this project"},
                status=403,
            )

        request.effective_user = request.user
        request.project = project
        return view_func(request, *args, **kwargs)

    return wrapper
