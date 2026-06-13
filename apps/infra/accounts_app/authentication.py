#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DRF ``BaseAuthentication`` adapter for the ``scitex_xxxx`` APIKey.

Closes the Phase-1 gap operator-12909 surfaced: a user with a personal
access token generated via the UI (``https://scitex.ai/api-keys/``)
should be able to authenticate against every JWT-friendly endpoint —
``/api/project/create/``, ``/api/apps/submit/``, the project-scoped
``<u>/<slug>/api/*`` family — exactly like the JWT path that landed in
PR #268.

Before this class existed, ``APIKey`` rows only authenticated the
MCP-tool endpoints (via the custom ``HasToolAccess`` permission class).
DRF's ``IsAuthenticated``-permission views read ``request.user`` from
the global ``REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`` list, which
was ``[SessionAuthentication, JWTAuthentication]`` only. Adding this
class to that list extends APIKey acceptance to every DRF endpoint
without per-view edits — same impedance match the JWT middleware (PR
#268) provided for plain Django views.

Trust model: identical to the existing OK-tested
``apps.infra.accounts_app.auth.authenticate_api_key`` helper. This class
is a thin DRF-shaped wrapper around that helper — no new credential
mechanism, no new hash/format, no relaxation of the existing key
validity checks (active + non-expired).
"""

from __future__ import annotations

from rest_framework import authentication, exceptions

from .auth import authenticate_api_key


class APIKeyAuthentication(authentication.BaseAuthentication):
    """DRF authentication class for ``Authorization: Bearer scitex_xxxx``.

    Behaviour follows DRF's three-state ``authenticate`` contract:

    * **No relevant credentials** → return ``None``. Lets the next
      auth class in ``DEFAULT_AUTHENTICATION_CLASSES`` try (e.g. so a
      Bearer JWT still routes to ``JWTAuthentication``).
    * **Recognisable but invalid credential** → raise
      :exc:`AuthenticationFailed`. The token-prefix sniff
      (``Bearer scitex_``) is how we decide "this credential is meant
      for us" so failure here is a hard 401, not a fall-through.
    * **Valid credential** → return ``(user, api_key)`` where ``user``
      is the APIKey's owner. ``request.auth`` then carries the APIKey
      instance for views that want scope or last-used metadata.

    Scope semantics are NOT enforced here — they live in the
    permission class that the view's ``permission_classes`` declares.
    This class only proves identity. Same separation DRF uses elsewhere.
    """

    keyword_prefix = "Bearer scitex_"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(self.keyword_prefix):
            # Not a scitex_xxxx PAT — let the next auth class try.
            return None

        api_key = authenticate_api_key(request)
        if api_key is None:
            # Recognisable shape but the key is wrong / expired / inactive.
            # Hard 401 instead of fall-through so the client sees the
            # actual problem rather than a misleading "no auth" 401 from
            # whichever class last ran.
            raise exceptions.AuthenticationFailed("Invalid or expired scitex_ API key.")

        return (api_key.user, api_key)

    def authenticate_header(self, request):
        # Returned in the ``WWW-Authenticate`` header on 401 responses.
        # Same shape as DRF's JWT scheme so clients know which scheme(s)
        # are accepted.
        return 'Bearer realm="api"'


# EOF
