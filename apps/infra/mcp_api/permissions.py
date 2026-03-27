# -*- coding: utf-8 -*-
# File: apps/infra/mcp_api/permissions.py
"""DRF permission classes for MCP REST API tool access.

Supports three auth tiers:
1. API Key (Bearer scitex_xxxx) -- requires "api" or "*" scope
2. JWT (Bearer <jwt>) -- session-based for logged-in users
3. Public (no auth) -- only for tools marked is_public=True
"""

from __future__ import annotations

import logging

from rest_framework.permissions import BasePermission

from apps.infra.accounts_app.auth import authenticate_api_key

logger = logging.getLogger(__name__)


class HasToolAccess(BasePermission):
    """Check that the request has permission to call the requested MCP tool.

    For public tools (introspect_*, docs_*, scholar_search*), anonymous
    access is allowed.

    For all other tools, a valid API key (with "api" or "*" scope) or
    an authenticated session/JWT is required.
    """

    def has_permission(self, request, view) -> bool:
        tool_info = getattr(view, "_tool_info", None)

        # If the tool is marked public, allow anonymous access
        if tool_info and tool_info.is_public:
            return True

        # Try API key authentication
        api_key = authenticate_api_key(request)
        if api_key is not None:
            if api_key.has_scope("api") or api_key.has_scope("*"):
                # Attach user from API key to request for downstream use
                request.user = api_key.user
                request._api_key = api_key
                return True
            logger.warning(
                "API key %s lacks 'api' scope for tool access", api_key.key_prefix
            )
            return False

        # Fall back to session/JWT authentication (handled by DRF)
        if request.user and request.user.is_authenticated:
            return True

        return False


# EOF
