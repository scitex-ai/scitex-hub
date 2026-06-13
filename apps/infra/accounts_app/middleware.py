#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Middleware for resolving non-session authentication into ``request.user``.

This module hosts the JWT-bearer → request.user shim that lets plain Django
views (``@require_http_methods`` etc.) accept SimpleJWT access tokens
without each view having to convert to DRF (``@api_view +
IsAuthenticated``). The motivating use case is the agent-programmatic
publish flow (operator-12880): every project-scoped operation lives behind
endpoints in ``apps/infra/project_app/views/repository/api/`` that check
``request.user.is_authenticated`` — and ``request.user`` is normally
populated by Django's ``AuthenticationMiddleware`` from a session cookie.
A CLI client holding only a Bearer JWT would be silently anonymous on
those endpoints. This middleware closes that gap.

Trust model: the same one already used by the workspace console's
``terminal_broker/shell.py:_make_short_lived_jwt`` —
``RefreshToken.for_user(user).access_token`` mints a JWT that
authenticates AS the user. SimpleJWT's ``JWTAuthentication`` validates
that token's signature, expiry, and user_id claim against the database;
nothing here weakens those checks.

Pattern follows ``apps.infra.project_app.middleware.OnSiteAuthMiddleware``:
hybrid sync/async, mutates ``request.user`` only when the existing
authentication slot is empty, sets ``request._dont_enforce_csrf_checks``
when (and only when) the JWT successfully resolves — Bearer authentication
is the trust signal, mirroring the existing OnSite carve-out.
"""

from __future__ import annotations

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

logger = logging.getLogger(__name__)


class JWTBearerToSessionMiddleware:
    """Resolve ``Authorization: Bearer <jwt>`` → ``request.user``.

    Runs only when the upstream ``AuthenticationMiddleware`` left
    ``request.user`` anonymous AND the request carries a ``Bearer`` header.
    Browser flows (cookie sessions) are unaffected — the middleware
    short-circuits on the ``is_authenticated`` check before touching the
    Authorization header.

    Fail-closed semantics: a malformed / expired / forged token leaves the
    request anonymous (downstream permission checks then return 401/403).
    Only narrow SimpleJWT / DRF auth exceptions are swallowed; any other
    exception propagates per the project's crash-loud doctrine.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
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

    def _sync_body(self, request):
        # Browser session already authenticated this request — leave it
        # entirely alone (do not even inspect the Bearer header).
        if request.user.is_authenticated:
            return

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return

        # `Bearer scitex_xxxx` is the UI-PAT shape — routed by
        # `APIKeyAuthentication` (DRF auth class), NOT JWTAuthentication.
        # Calling JWTAuthentication on it would emit a misleading
        # "rejected token" INFO log and leave the request anonymous; DRF
        # then resolves identity via APIKeyAuthentication anyway. Skip
        # the wasted decode + log noise.
        if auth_header.startswith("Bearer scitex_"):
            return

        # Local imports keep this middleware importable even in test setups
        # that don't have DRF wired (e.g. minimal `manage.py check`).
        from rest_framework.exceptions import AuthenticationFailed
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        try:
            result = JWTAuthentication().authenticate(request)
        except (InvalidToken, TokenError, AuthenticationFailed) as exc:
            # Fail closed — leave the request anonymous so the view's own
            # permission check returns the correct 401/403. Log at INFO
            # because a bad token is a normal client error, not a server
            # bug.
            logger.info("JWTBearerToSessionMiddleware: rejected token (%s)", exc)
            return
        # Any other exception (e.g. DB connection error, mis-configured
        # SECRET_KEY) is a real bug and MUST propagate so the surrounding
        # request-level error handlers / crash-loud doctrine see it.
        # Intentionally not caught here.

        if result is None:
            # No token usable for auth (e.g. header wasn't actually a JWT —
            # could be a stale scitex_xxxx API key for the MCP path).
            return

        user, validated_token = result
        request.user = user
        request._jwt_auth = validated_token
        # Bearer auth is the trust signal — mirrors OnSiteAuthMiddleware's
        # CSRF carve-out. The token's signature already proves the
        # request's intent.
        request._dont_enforce_csrf_checks = True


# EOF
