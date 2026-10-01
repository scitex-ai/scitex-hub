"""Render leaf-declared workspace content using the host's trusted mount."""

from django.http import HttpResponse
from django.shortcuts import render


def render_module_content(request, module, current_project):
    """Preserve SDK capability refusals without exposing their private details."""
    try:
        context = module.build_context(request, current_project)
    except Exception as error:
        # SDK is optional for Hub-owned panes. Import its exception classes
        # only when classifying a failed leaf context builder.
        try:
            from scitex_sdk.host import AccessError, CapabilityUnavailable
        except ImportError:
            raise error from None
        if isinstance(error, AccessError):
            status = error.status
            if type(status) is not int or not 400 <= status < 500:
                status = 403
            response = HttpResponse("Project access unavailable.", status=status)
        elif isinstance(error, CapabilityUnavailable):
            response = HttpResponse("This application is temporarily unavailable.", status=503)
        else:
            raise
        response["Cache-Control"] = "no-store"
        return response

    context["stx_mount"] = module.get_url().rstrip("/")
    return render(request, module.partial_template, context)
