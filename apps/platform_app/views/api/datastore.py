"""
DataStore REST views.

Endpoints:
    GET/POST  /platform/api/data/<app>/<schema>/            list_create
    GET/PUT/DELETE  /platform/api/data/<app>/<schema>/<pk>/  detail
    POST      /platform/api/data/<app>/<schema>/search/     search

Project resolution order:
    1. ``project_id`` query-param (GET) / body key (POST)
    2. ``session['active_project_id']``

All endpoints require authentication.  Ownership / permission checks delegate
to the DataStore permission helpers.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.platform_app.models.app_data import AppData
from apps.platform_app.services.datastore import (
    PermissionDeniedError,
    check_create,
    check_read,
    check_write,
    get_engine,
)

logger = logging.getLogger(__name__)

# Default access mode when not specified by the client.
_DEFAULT_MODE = "owner_only"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_project(request, body: dict | None = None):
    """Return the Project ORM instance for this request, or None."""
    from apps.project_app.models import Project

    project_id = None

    # Prefer explicit param from body or query string.
    if body and "project_id" in body:
        project_id = body["project_id"]
    if not project_id:
        project_id = request.GET.get("project_id")
    if not project_id:
        project_id = request.session.get("active_project_id")

    if not project_id:
        return None

    return get_object_or_404(Project, pk=project_id, owner=request.user)


def _record_to_dict(record: AppData) -> dict:
    return {
        "id": str(record.id),
        "app_name": record.app_name,
        "schema_name": record.schema_name,
        "project_id": str(record.project_id),
        "owner_id": record.owner_id,
        "data": record.data,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _parse_body(request) -> dict:
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def datastore_list_create(request, app: str, schema: str):
    """List records (GET) or create a new record (POST).

    GET query params:
        project_id  — required (or set in session)
        order_by    — field name, optionally prefixed with ``-``
        limit       — integer, max records to return
        offset      — integer, skip N records

    POST body (JSON):
        project_id  — required (or set in session)
        data        — dict of field values
        mode        — access mode (default: owner_only)
    """
    if request.method == "GET":
        return _handle_list(request, app, schema)
    return _handle_create(request, app, schema)


def _handle_list(request, app: str, schema: str) -> JsonResponse:
    project = _resolve_project(request)
    if project is None:
        return JsonResponse({"error": "project_id is required"}, status=400)

    engine = get_engine(app, schema)
    mode = request.GET.get("mode", _DEFAULT_MODE)
    order_by = request.GET.get("order_by")
    limit = _int_param(request.GET.get("limit"))
    offset = _int_param(request.GET.get("offset"))

    qs = engine.filter(project, order_by=order_by, limit=limit, offset=offset)

    records = []
    for record in qs:
        try:
            check_read(record, request.user, mode)
            records.append(_record_to_dict(record))
        except PermissionDeniedError:
            pass  # silently skip inaccessible records

    return JsonResponse({"results": records, "count": len(records)})


def _handle_create(request, app: str, schema: str) -> JsonResponse:
    try:
        body = _parse_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    project = _resolve_project(request, body)
    if project is None:
        return JsonResponse({"error": "project_id is required"}, status=400)

    data = body.get("data", {})
    mode = body.get("mode", _DEFAULT_MODE)

    try:
        check_create(project, request.user, request.user, mode)
    except PermissionDeniedError as exc:
        return JsonResponse({"error": str(exc)}, status=403)

    engine = get_engine(app, schema)
    record = engine.create(project=project, owner=request.user, data=data)
    return JsonResponse({"result": _record_to_dict(record)}, status=201)


# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def datastore_detail(request, app: str, schema: str, pk):
    """Retrieve (GET), update (PUT), or delete (DELETE) a single record."""
    engine = get_engine(app, schema)

    try:
        record = engine.get(pk)
    except AppData.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    mode = request.GET.get("mode", _DEFAULT_MODE)

    if request.method == "GET":
        try:
            check_read(record, request.user, mode)
        except PermissionDeniedError as exc:
            return JsonResponse({"error": str(exc)}, status=403)
        return JsonResponse({"result": _record_to_dict(record)})

    if request.method == "PUT":
        try:
            check_write(record, request.user, mode)
        except PermissionDeniedError as exc:
            return JsonResponse({"error": str(exc)}, status=403)

        try:
            body = _parse_body(request)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        data = body.get("data", {})
        record = engine.update(pk, data)
        return JsonResponse({"result": _record_to_dict(record)})

    # DELETE
    try:
        check_write(record, request.user, mode)
    except PermissionDeniedError as exc:
        return JsonResponse({"error": str(exc)}, status=403)

    engine.delete(pk)
    return JsonResponse({"deleted": str(pk)}, status=200)


# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["POST"])
def datastore_search(request, app: str, schema: str):
    """Full-text search across specified fields.

    POST body (JSON):
        project_id  — required (or set in session)
        query       — search string
        fields      — list of field names to search
        mode        — access mode (default: owner_only)
    """
    try:
        body = _parse_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    project = _resolve_project(request, body)
    if project is None:
        return JsonResponse({"error": "project_id is required"}, status=400)

    query = body.get("query", "").strip()
    fields = body.get("fields", [])
    mode = body.get("mode", _DEFAULT_MODE)

    if not query:
        return JsonResponse({"error": "query is required"}, status=400)
    if not isinstance(fields, list) or not fields:
        return JsonResponse({"error": "fields must be a non-empty list"}, status=400)

    engine = get_engine(app, schema)
    qs = engine.search(project, query, fields)

    records = []
    for record in qs:
        try:
            check_read(record, request.user, mode)
            records.append(_record_to_dict(record))
        except PermissionDeniedError:
            pass

    return JsonResponse({"results": records, "count": len(records)})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _int_param(value) -> int | None:
    """Safely parse an optional integer query param."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
