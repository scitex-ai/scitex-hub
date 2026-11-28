"""Retired: shell commands from the AI chat "!" prefix.

This endpoint used to run the posted command with ``bash -c`` inside the web
application's container. User commands now run only where each user is
isolated: the project terminal and SLURM jobs. The route stays mounted so
old clients get a clear answer instead of a 404.
"""

from django.http import JsonResponse


def api_bash_exec(request, *args, **kwargs):
    """Answer 410 Gone without reading the request body."""
    return JsonResponse(
        {
            "success": False,
            "error": (
                "Running shell commands from chat has been retired. "
                "Use the project terminal."
            ),
        },
        status=410,
    )
