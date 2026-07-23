#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/infra/project_app/middleware_onsite_auth.py
"""On-site (same-container MCP agent) request authentication.

Extracted from ``middleware.py`` so the trust decision lives in one small
auditable file. Re-exported from ``middleware`` for back-compat with the
``MIDDLEWARE`` setting path.
"""

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

logger = logging.getLogger(__name__)


def django_user_lookup(username):
    """Resolve a username to a Django user, or ``None`` if unknown."""
    from django.contrib.auth.models import User

    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


class OnSiteAuthMiddleware:
    """Authenticate MCP tool requests from on-site agents (same container).

    When the MCP server runs alongside Django (on-site), it SIGNS each
    request with the shared on-site secret and sends the triple
    ``X-SciTeX-OnSite`` / ``X-SciTeX-OnSite-Ts`` / ``X-SciTeX-OnSite-Sig``
    instead of Bearer-token auth.

    Trust comes from POSSESSION OF THE SHARED SECRET, and from nothing
    else.

    The previous implementation trusted a bare ``X-SciTeX-OnSite:
    <username>`` header whenever the request "looked internal", where
    "internal" was decided by ``X-Forwarded-For.split(",")[0]`` — the
    LEFTMOST entry, i.e. the value the CLIENT supplied (nginx *appends*
    the real peer via ``$proxy_add_x_forwarded_for``, so a forged entry
    stays first). Anyone on the internet could therefore send::

        curl -H 'X-Forwarded-For: 127.0.0.1' \\
             -H 'X-SciTeX-OnSite: <any-username>' https://<host>/<path>

    and be authenticated as that user — with CSRF checks disabled. The
    fallback branch was no better: behind the nginx container
    ``REMOTE_ADDR`` is always a 172.16/12 bridge address, which the old
    trusted-prefix list accepted. An IP-shaped signal is not an
    authenticator in this topology, so it is gone.

    Signature + replay-window verification lives in ``scitex_hub`` next to
    the signer (``scitex_hub._mcp_tools.api``) so signer and verifier
    cannot drift. Fails closed: with no ``ONSITE_AUTH_SECRET`` configured,
    no request is ever authenticated on-site.
    """

    sync_capable = True
    async_capable = True

    #: Injectable collaborator — ``callable(username) -> user | None``.
    #: Overridable per instance so the trust decision can be exercised
    #: (in tests, or by an alternative identity backend) without going
    #: through the ORM.
    user_lookup = staticmethod(django_user_lookup)

    def __init__(self, get_response, user_lookup=None):
        self.get_response = get_response
        if user_lookup is not None:
            self.user_lookup = user_lookup
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self._acall(request)
        self._sync_body(request)
        return self.get_response(request)

    async def _acall(self, request):
        await sync_to_async(self._sync_body, thread_sensitive=True)(request)
        return await self.get_response(request)

    @staticmethod
    def _secret() -> str:
        """Shared on-site secret; ``""`` disables on-site auth entirely."""
        from django.conf import settings

        return getattr(settings, "ONSITE_AUTH_SECRET", "") or ""

    def _sync_body(self, request):
        if request.user.is_authenticated:
            return

        claimed = request.META.get("HTTP_X_SCITEX_ONSITE")
        if not claimed:
            return

        from scitex_hub._mcp_tools.api import verify_onsite

        username = verify_onsite(request.META, self._secret())
        if not username:
            logger.warning(
                "OnSite auth REJECTED (bad/missing signature) for claimed "
                "user %r on %s",
                claimed,
                getattr(request, "path", "?"),
            )
            return

        user = self.user_lookup(username)
        if user is None:
            logger.warning("OnSite auth: user %s not found", username)
            return

        request.user = user
        request._on_site_auth = True
        # Exempt from CSRF — MCP tools don't have CSRF tokens
        request._dont_enforce_csrf_checks = True
