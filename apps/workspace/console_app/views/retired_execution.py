"""Code-execution endpoints that used to run user code inside the web server.

The console's early "execute code / run analysis / run notebook / set up
environment / run workflow" endpoints ran user-supplied Python, pip installs
and notebook kernels in the web application's own process, with its
privileges, filesystem and environment. User code now runs only where it is
isolated per user: the project terminal and SLURM jobs (Apptainer, per-user
accounts). These routes stay mounted so old clients get a clear answer.
"""

from __future__ import annotations

from django.http import JsonResponse


def retired_execution(request, *args, **kwargs):
    """Answer 410 Gone without touching the request body."""
    return JsonResponse(
        {
            "success": False,
            "error": (
                "This endpoint has been retired. Run code in the project "
                "terminal or submit it as a job."
            ),
        },
        status=410,
    )
