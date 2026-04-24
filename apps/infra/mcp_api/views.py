# -*- coding: utf-8 -*-
# File: apps/infra/mcp_api/views.py
"""Generic MCP tool executor view and tool listing endpoint.

All MCP tools are dispatched through a single view class that:
1. Resolves the tool from the URL path
2. Validates parameters against the tool's JSON schema
3. Calls the tool function directly (no MCP protocol overhead)
4. Returns the result as JSON
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time

import jsonschema
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from .discovery import ToolInfo, get_tool_by_url_path, get_tool_registry
from .permissions import HasToolAccess

logger = logging.getLogger(__name__)


class ToolExecuteView(APIView):
    """Execute an MCP tool via REST API.

    POST /api/v1/tools/{namespace}/{action}/
    GET  /api/v1/tools/{namespace}/{action}/  (read-only tools only)

    Request body (POST): JSON object with tool parameters.
    Query params (GET):  key=value pairs for tool parameters.

    Response:
        {
            "success": true/false,
            "tool": "tool_name",
            "data": { ... },
            "elapsed_ms": 234
        }
    """

    permission_classes = [HasToolAccess]

    # Set by URL dispatch -- the ToolInfo for this endpoint
    _tool_info: ToolInfo = None

    def initial(self, request, *args, **kwargs):
        """Resolve tool info before permission checks."""
        url_path = kwargs.get("tool_path", "")
        self._tool_info = get_tool_by_url_path(url_path)
        super().initial(request, *args, **kwargs)

    def post(self, request: Request, tool_path: str = "") -> JsonResponse:
        return self._execute(request, tool_path)

    def get(self, request: Request, tool_path: str = "") -> JsonResponse:
        return self._execute(request, tool_path)

    def _execute(self, request: Request, tool_path: str) -> JsonResponse:
        """Core execution logic shared by GET and POST."""
        tool_info = self._tool_info
        if tool_info is None:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Unknown tool for path: {tool_path}",
                    "error_code": "NOT_FOUND",
                },
                status=404,
            )

        # Extract parameters
        params = self._extract_params(request, tool_info)

        # Inject project context if the tool requires root_path
        if "root_path" in (tool_info.parameters.get("properties") or {}):
            project_path = self._resolve_project_path(request)
            if project_path is not None:
                params.setdefault("root_path", str(project_path))

        # Validate parameters against JSON schema
        validation_error = self._validate_params(params, tool_info.parameters)
        if validation_error is not None:
            return JsonResponse(
                {
                    "success": False,
                    "tool": tool_info.name,
                    "error": validation_error,
                    "error_code": "VALIDATION_ERROR",
                },
                status=400,
            )

        # Execute the tool function
        start = time.monotonic()
        try:
            if inspect.iscoroutinefunction(tool_info.fn):
                # Run async tool function
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(tool_info.fn(**params))
                finally:
                    loop.close()
            else:
                result = tool_info.fn(**params)

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Ensure result is JSON-serializable
            data = self._make_serializable(result)

            return JsonResponse(
                {
                    "success": True,
                    "tool": tool_info.name,
                    "data": data,
                    "elapsed_ms": elapsed_ms,
                }
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "Tool execution failed: %s (elapsed=%dms)",
                tool_info.name,
                elapsed_ms,
                exc_info=True,
            )
            return JsonResponse(
                {
                    "success": False,
                    "tool": tool_info.name,
                    "error": str(exc),
                    "error_code": "EXECUTION_ERROR",
                    "elapsed_ms": elapsed_ms,
                },
                status=500,
            )

    def _extract_params(self, request: Request, tool_info: ToolInfo) -> dict:
        """Extract parameters from request body (POST) or query params (GET)."""
        if request.method == "POST":
            if request.content_type and "json" in request.content_type:
                try:
                    return json.loads(request.body) if request.body else {}
                except json.JSONDecodeError as exc:
                    # Return empty dict; validation will catch missing required params
                    logger.warning("Invalid JSON body: %s", exc)
                    return {}
            # DRF parsed data
            return dict(request.data) if request.data else {}
        else:
            # GET: convert query params, attempting type coercion from schema
            params = {}
            properties = tool_info.parameters.get("properties") or {}
            for key, value in request.query_params.items():
                prop_schema = properties.get(key, {})
                params[key] = self._coerce_query_param(value, prop_schema)
            return params

    def _coerce_query_param(self, value: str, prop_schema: dict):
        """Attempt to coerce a query parameter string to its schema type."""
        ptype = prop_schema.get("type")
        if ptype == "integer":
            try:
                return int(value)
            except ValueError:
                return value
        elif ptype == "number":
            try:
                return float(value)
            except ValueError:
                return value
        elif ptype == "boolean":
            return value.lower() in ("true", "1", "yes")
        elif ptype == "array" or ptype == "object":
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def _validate_params(self, params: dict, schema: dict) -> str | None:
        """Validate params against JSON schema. Return error string or None."""
        if not schema or not schema.get("properties"):
            return None
        try:
            jsonschema.validate(instance=params, schema=schema)
            return None
        except jsonschema.ValidationError as exc:
            return exc.message
        except jsonschema.SchemaError as exc:
            logger.error("Invalid tool schema: %s", exc)
            return f"Internal schema error: {exc.message}"

    def _resolve_project_path(self, request: Request):
        """Resolve the active project path for the authenticated user.

        Returns the filesystem path or None if not resolvable.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return None

        try:
            profile = user.profile
            project = profile.last_active_repository
            if project is None:
                return None

            from apps.infra.project_app.services.filesystem.paths import (
                get_project_root_path,
            )

            return get_project_root_path(user, project)
        except Exception as exc:
            logger.debug("Could not resolve project path: %s", exc)
            return None

    def _make_serializable(self, obj):
        """Ensure the result is JSON-serializable."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {str(k): self._make_serializable(v) for k, v in obj.items()}
        # Pydantic models
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        # Fallback: convert to string
        return str(obj)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_tools(request: Request) -> JsonResponse:
    """List all available MCP tool REST endpoints.

    GET /api/v1/tools/

    Returns a categorized list of all tools with their URL paths,
    descriptions, and parameter schemas.
    """
    registry = get_tool_registry()

    # Group by namespace
    namespaces: dict[str, list] = {}
    for tool_info in registry.values():
        ns = tool_info.namespace
        if ns not in namespaces:
            namespaces[ns] = []
        namespaces[ns].append(
            {
                "name": tool_info.name,
                "description": (
                    tool_info.description.split("\n")[0]
                    if tool_info.description
                    else ""
                ),
                "url": f"/api/v1/tools/{tool_info.url_path}/",
                "method": "POST",
                "parameters": tool_info.parameters,
                "is_public": tool_info.is_public,
            }
        )

    # Sort namespaces and tools within each
    categories = []
    for ns in sorted(namespaces.keys()):
        tools = sorted(namespaces[ns], key=lambda t: t["name"])
        categories.append(
            {
                "namespace": ns,
                "count": len(tools),
                "tools": tools,
            }
        )

    return JsonResponse(
        {
            "total": len(registry),
            "categories": len(categories),
            "namespaces": categories,
        }
    )


# EOF
