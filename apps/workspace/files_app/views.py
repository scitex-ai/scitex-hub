"""Files app views: one page plus a small JSON API over the user's root.

Every endpoint works on ``request.user``'s own root only; there is no way
to name another user's workspace.
"""

from __future__ import annotations

import json
import mimetypes
from functools import wraps
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from .services import workspace_fs as fs

# Served inline for the preview pane; anything else downloads as a file.
_INLINE_TYPES = ("image/", "video/", "audio/", "application/pdf")
_SCRIPTABLE_IMAGES = ("image/svg+xml",)
_TEXT_SUFFIXES = {
    ".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".py", ".r",
    ".m", ".tex", ".bib", ".log", ".sh", ".toml", ".ini", ".cfg", ".xml",
    ".html", ".css", ".js", ".ts", ".svg",
}  # fmt: skip


def _api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, fs.user_root(request.user), *args, **kwargs)
        except fs.WorkspacePathError:
            return JsonResponse({"error": "Invalid workspace path."}, status=400)
        except FileNotFoundError:
            return JsonResponse({"error": "not found"}, status=404)
        except FileExistsError:
            return JsonResponse({"error": "already exists"}, status=409)
        except (NotADirectoryError, IsADirectoryError):
            return JsonResponse({"error": "wrong kind of entry"}, status=400)

    return login_required(wrapped)


def _body(request) -> dict:
    try:
        data = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise fs.WorkspacePathError("invalid JSON body")
    if not isinstance(data, dict):
        raise fs.WorkspacePathError("invalid JSON body")
    return data


def _project_url(username: str, rel: str, is_dir: bool) -> str:
    parts = rel.split("/")
    if parts[0] != fs.PROJECTS or len(parts) < 2:
        return ""
    base = f"/{quote(username)}/{quote(parts[1])}/"
    if len(parts) == 2:
        return base
    if is_dir:
        return ""
    return base + "blob/" + quote("/".join(parts[2:]))


def _strings() -> dict:
    return {
        "home": _("Home"),
        "Downloads": _("Downloads"),
        "Recordings": _("Recordings"),
        "proj": _("Projects"),
        "empty": _("This folder is empty."),
        "open": _("Open"),
        "openInProject": _("Open in project"),
        "download": _("Download"),
        "rename": _("Rename"),
        "move": _("Move"),
        "delete": _("Delete"),
        "cancel": _("Cancel"),
        "newFolderPrompt": _("New folder name"),
        "renamePrompt": _("New name"),
        "movePrompt": _("Move to folder (path from Home, e.g. Downloads/figures)"),
        "deleteConfirm": _("Delete “%(name)s”? This cannot be undone."),
        "uploading": _("Uploading…"),
        "uploaded": _("Uploaded %(count)s file(s)."),
        "failed": _("Something went wrong: %(error)s"),
        "noPreview": _("No preview for this file type."),
        "actions": _("Actions"),
        "folder": _("Folder"),
    }


@login_required
@require_GET
def index(request):
    fs.user_root(request.user)
    return render(
        request,
        "files_app/index.html",
        {"files_strings": _strings(), "username": request.user.username},
    )


@require_GET
@_api
def api_list(request, root):
    rel = request.GET.get("path", "")
    username = request.user.username
    entries = [
        {
            "name": e.name,
            "path": e.path,
            "is_dir": e.is_dir,
            "size": e.size,
            "modified": e.modified,
            "project_url": _project_url(username, e.path, e.is_dir),
        }
        for e in fs.list_dir(root, rel)
    ]
    return JsonResponse({"path": fs.normalize(rel), "entries": entries})


def _file_response(root, rel: str, *, inline: bool):
    target = fs.resolve_path(root, rel)
    if not target.is_file():
        raise Http404("not a file")
    content_type, _enc = mimetypes.guess_type(target.name)
    content_type = content_type or "application/octet-stream"
    if inline and target.suffix.lower() in _TEXT_SUFFIXES:
        content_type = "text/plain; charset=utf-8"
    elif content_type in _SCRIPTABLE_IMAGES or not content_type.startswith(
        _INLINE_TYPES
    ):
        inline = False
    response = FileResponse(
        open(target, "rb"),
        as_attachment=not inline,
        filename=target.name,
        content_type=content_type,
    )
    response["X-Content-Type-Options"] = "nosniff"
    # Chrome's PDF viewer does not render under a sandbox CSP.
    if content_type != "application/pdf":
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


@require_GET
@_api
def download(request, root):
    try:
        return _file_response(root, request.GET.get("path", ""), inline=False)
    except Http404:
        return JsonResponse({"error": "not found"}, status=404)


@xframe_options_sameorigin
@require_GET
@_api
def raw(request, root):
    try:
        return _file_response(root, request.GET.get("path", ""), inline=True)
    except Http404:
        return JsonResponse({"error": "not found"}, status=404)


@require_POST
@_api
def api_upload(request, root):
    folder = request.POST.get("path", "")
    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"error": "no files"}, status=400)
    saved = [fs.save_upload(root, folder, f) for f in files]
    return JsonResponse({"saved": [fs.relative(root, p) for p in saved]})


@require_POST
@_api
def api_mkdir(request, root):
    data = _body(request)
    created = fs.make_dir(root, data.get("path", ""), data.get("name", ""))
    return JsonResponse({"path": fs.relative(root, created)})


@require_POST
@_api
def api_rename(request, root):
    data = _body(request)
    renamed = fs.rename(root, data.get("path", ""), data.get("name", ""))
    return JsonResponse({"path": fs.relative(root, renamed)})


@require_POST
@_api
def api_move(request, root):
    data = _body(request)
    moved = fs.move(root, data.get("path", ""), data.get("dest", ""))
    return JsonResponse({"path": fs.relative(root, moved)})


@require_POST
@_api
def api_delete(request, root):
    fs.delete(root, _body(request).get("path", ""))
    return JsonResponse({"ok": True})
