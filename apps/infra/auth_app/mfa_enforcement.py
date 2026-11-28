"""Two-factor authentication: available to everyone, required for staff.

TOTP and recovery codes come from ``allauth.mfa``. The hub sign-in form runs
allauth's login stages, so any account with an authenticator is asked for
its code there. Staff and superusers must have one:

- a staff session without an authenticator is sent to the TOTP setup page
  and can reach nothing else until it is set up;
- a staff session that never passed a second factor (for example one opened
  through the Django admin login form) is signed out and sent to sign in.

Only cookie sessions are checked. API keys, bearer tokens and on-site agent
signatures carry their own credentials and never reach these pages.
"""

from __future__ import annotations

from allauth.account.internal.flows.login import (
    get_authentication_records,
    record_authentication,
)
from allauth.mfa.models import Authenticator
from allauth.mfa.signals import authenticator_added
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import SESSION_KEY, logout
from django.dispatch import receiver
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

#: Paths a staff session may use before its second factor is in place.
EXEMPT_PREFIXES = (
    "/static/",
    "/media/",
    "/favicon",
    "/healthz",
    "/auth/social/2fa/",
    "/auth/social/reauthenticate/",
    "/auth/social/logout/",
    "/auth/logout/",
    "/auth/signout/",
    "/auth/signin/",
    "/auth/login/",
)

_SECOND_FACTOR_TYPES = (Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN)


def has_second_factor(user) -> bool:
    return Authenticator.objects.filter(
        user=user, type__in=_SECOND_FACTOR_TYPES
    ).exists()


def passed_second_factor(request, user) -> bool:
    return any(
        r.get("method") == "mfa" for r in get_authentication_records(request, user)
    )


def requires_second_factor(user) -> bool:
    return bool(user.is_staff or user.is_superuser)


class StaffMFAMiddleware:
    """Holds staff cookie sessions to a second factor (see module docstring)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._enforce(request)
        return response if response is not None else self.get_response(request)

    def _enforce(self, request):
        if not getattr(settings, "MFA_REQUIRED_FOR_STAFF", True):
            return None
        user = getattr(request, "user", None)
        if (
            user is None
            or not user.is_authenticated
            or not requires_second_factor(user)
        ):
            return None
        session = getattr(request, "session", None)
        if session is None or session.get(SESSION_KEY) != str(user.pk):
            return None  # not a cookie session
        if request.path.startswith(EXEMPT_PREFIXES):
            return None
        if not has_second_factor(user):
            messages.warning(
                request,
                "Staff accounts must turn on two-factor authentication before continuing.",
            )
            return redirect(reverse("mfa_activate_totp"))
        if not passed_second_factor(request, user):
            logout(request)
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{reverse('auth_app:signin')}?{query}")
        return None


@receiver(authenticator_added, dispatch_uid="auth_app.mfa_enforcement.added")
def _record_setup_as_second_factor(sender, request, user, authenticator, **kwargs):
    """Activating TOTP proves possession of the device; count it for this session."""
    if request is not None and authenticator.type in _SECOND_FACTOR_TYPES:
        record_authentication(
            request, user, "mfa", id=authenticator.pk, type=authenticator.type
        )
