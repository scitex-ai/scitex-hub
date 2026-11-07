# -*- coding: utf-8 -*-
# File: apps/infra/mcp_api/permissions.py
"""DRF permission classes for MCP REST API tool access.

Generic tools require an active platform superuser. Their MCP schemas
do not convey the leaf Web APIs' project authorization or filesystem scope.
API keys additionally require "api" or "*" scope. Public metadata remains
readable; tool execution uses this operator boundary regardless of its name.
"""

from __future__ import annotations

import logging

from rest_framework.permissions import BasePermission

from apps.infra.accounts_app.auth import authenticate_api_key

logger = logging.getLogger(__name__)


class HasToolAccess(BasePermission):
    """Check that the request has permission to call the requested MCP tool.

    Tools require an active superuser session/JWT or an API key
    belonging to an active superuser with "api" or "*" scope.
    """

    message = "Generic MCP tools require an active platform operator. Use the app's scoped Web API for project operations."

    @staticmethod
    def _is_operator(user) -> bool:
        return all(
            getattr(user, field, False)
            for field in ("is_authenticated", "is_active", "is_superuser")
        )

    def has_permission(self, request, view) -> bool:
        # Try API key authentication
        api_key = authenticate_api_key(request)
        if api_key is not None:
            if self._is_operator(api_key.user) and (
                api_key.has_scope("api") or api_key.has_scope("*")
            ):
                # Attach user from API key to request for downstream use
                request.user = api_key.user
                request._api_key = api_key
                return True
            logger.warning(
                "API key %s lacks operator identity or 'api' scope", api_key.key_prefix
            )
            return False

        # Fall back to session/JWT authentication (handled by DRF)
        return self._is_operator(request.user)


# EOF
