"""Access gate for every /dev/ route.

The dev app is an internal toolbox: a design-system catalogue, an API test
monitor that makes the server fire HTTP requests at itself, a browser-console
log sink and a SLURM job canceller. None of it is for visitors.

Two independent conditions, both required:

1. ``settings.DEV_TOOLS_ENABLED`` must be True. It is off by default on every
   deployment (DEBUG does not turn it on) and production settings force it
   off. ``config.urls`` only mounts ``/dev/`` when it is on; this gate checks
   it again per request so a stale mount still answers 404.
2. The user must be an instance admin (``is_staff`` or ``is_superuser``).
   Everyone else, anonymous visitors included, gets 403.

Settings are read per request, not at import time, so ``override_settings``
works.
"""

from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404


def is_instance_admin(user) -> bool:
    """True for staff or superusers."""
    return bool(
        getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
    )


def dev_tools_enabled() -> bool:
    """True when this deployment explicitly enabled the /dev/ toolbox."""
    return bool(getattr(settings, "DEV_TOOLS_ENABLED", False))


def dev_admin_only(view_func):
    """404 unless dev tools are enabled; 403 unless the user is an admin."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not dev_tools_enabled():
            raise Http404("Page not found")
        if not is_instance_admin(request.user):
            raise PermissionDenied("Developer tools are restricted to staff")
        return view_func(request, *args, **kwargs)

    return _wrapped


# EOF
