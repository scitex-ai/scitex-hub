"""
FileVault REST API views.

Endpoints:
    GET  /api/platform/files/<app>/              — list root directory
    GET  /api/platform/files/<app>/<file_path>   — read file
    POST /api/platform/files/<app>/<file_path>   — upload/write file
    DELETE /api/platform/files/<app>/<file_path> — delete file

All endpoints require:
    - login
    - ?project=<project_slug> query parameter
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.platform_app.services.filevault import FileVault
from apps.platform_app.services.filevault.storage import FileVaultError
from apps.project_app.models import Project


def _get_vault(request, app: str) -> FileVault:
    """Resolve project from query param and return a FileVault instance."""
    slug = request.GET.get("project") or request.POST.get("project")
    if not slug:
        raise ValueError("Missing required query parameter: project")
    project = get_object_or_404(Project, slug=slug, owner=request.user)
    return FileVault(app_name=app, project=project, user=request.user)


# ---------------------------------------------------------------------------
# Root listing
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def filevault_root(request, app: str) -> JsonResponse:
    """GET /api/platform/files/<app>/ — list root of the app vault.

    Query params:
        project  (required) project slug
        ext      (optional) comma-separated extension filter, e.g. ".csv,.json"
    """
    try:
        vault = _get_vault(request, app)
    except ValueError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    raw_ext = request.GET.get("ext", "").strip()
    extensions = [e.strip() for e in raw_ext.split(",") if e.strip()] or None

    entries = vault.list("/", extensions=extensions)
    return JsonResponse({"success": True, "entries": entries})


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------


@login_required
def filevault_file(request, app: str, file_path: str) -> HttpResponse:
    """Single-file endpoint: GET read, POST upload, DELETE delete.

    GET  returns raw file bytes with appropriate Content-Type.
    POST accepts either multipart (file field 'file') or raw body.
    DELETE removes the file and returns JSON confirmation.

    Query params (all methods):
        project  (required) project slug
    """
    try:
        vault = _get_vault(request, app)
    except ValueError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    if request.method == "GET":
        return _read_file(vault, file_path)
    if request.method == "POST":
        return _write_file(request, vault, file_path)
    if request.method == "DELETE":
        return _delete_file(vault, file_path)

    return JsonResponse(
        {"success": False, "error": "Method not allowed"},
        status=405,
    )


def _read_file(vault: FileVault, file_path: str) -> HttpResponse:
    """Read and stream a vault file."""
    try:
        meta = vault.info(file_path)
        content = vault.read(file_path, binary=True)
    except FileVaultError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=404)

    response = HttpResponse(content, content_type=meta["mimetype"])
    response["Content-Length"] = meta["size"]
    return response


def _write_file(request, vault: FileVault, file_path: str) -> JsonResponse:
    """Write uploaded content to a vault file.

    Supports two upload modes:
      1. Multipart form: field named 'file'.
      2. Raw request body (binary or text).
    """
    try:
        if request.FILES.get("file"):
            content: bytes = request.FILES["file"].read()
        elif request.body:
            content = request.body
        else:
            return JsonResponse(
                {"success": False, "error": "No content provided"}, status=400
            )

        abs_path = vault.save(file_path, content)
        meta = vault.info(file_path)
        return JsonResponse(
            {
                "success": True,
                "path": file_path,
                "size": meta["size"],
                "modified": meta["modified"],
                "mimetype": meta["mimetype"],
            },
            status=201,
        )
    except FileVaultError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _delete_file(vault: FileVault, file_path: str) -> JsonResponse:
    """Delete a vault file."""
    try:
        vault.delete(file_path)
        return JsonResponse({"success": True, "deleted": file_path})
    except FileVaultError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=404)
