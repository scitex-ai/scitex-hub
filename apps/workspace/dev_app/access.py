"""Access gate for every /dev/ route.

The dev app is an internal toolbox: a design-system catalogue, an API test
monitor that makes the server fire HTTP requests at itself, a browser-console
log sink and a SLURM job canceller. None of it is for visitors.

When ``settings.DEBUG`` is True (local dev) everything stays open, as before.
Otherwise only instance admins (``is_staff`` or ``is_superuser``) get through;
everyone else receives the site's normal 404 so the pages are not advertised.

DEBUG is read per request, not at import time, so ``override_settings`` works.
"""

from functools import wraps

from django.conf import settings
from django.http import Http404


def is_instance_admin(user) -> bool:
    """True for staff or superusers."""
    return bool(
        getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
    )


def dev_admin_only(view_func):
    """Raise Http404 for non-admins unless DEBUG is on."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not settings.DEBUG and not is_instance_admin(request.user):
            raise Http404("Page not found")
        return view_func(request, *args, **kwargs)

    return _wrapped


# EOF
