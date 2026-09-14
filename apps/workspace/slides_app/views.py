#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Slides views: the editor page and a small JSON API over project decks."""

from __future__ import annotations

import json
import mimetypes

from django.http import FileResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

from . import services


def _denied(message: str, status: int) -> JsonResponse:
    return JsonResponse({"success": False, "error": message}, status=status)


def _project_or_error(request, ref=None, *, write: bool = False):
    project = services.resolve_project(request, ref)
    # A project the user may not see answers exactly like a missing one.
    if project is None or not project.can_view(request.user):
        return None, _denied("project not found", 404)
    if write and not project.can_edit(request.user):
        return None, _denied("you cannot edit this project", 403)
    return project, None


def _project_ref(project) -> str:
    return f"{project.owner.username}/{project.slug}"


def build_slides_context(request, current_project=None):
    project = services.resolve_project(request)
    if project is not None and not project.can_view(request.user):
        project = None
    owned = []
    if project is None and request.user.is_authenticated:
        owned = Project.objects.filter(owner=request.user).select_related("owner")
        owned = list(owned.order_by("-updated_at")[:50])
    return {
        "slides_projects": owned,
        "slides_project": project,
        "slides_project_ref": _project_ref(project) if project else "",
        "slides_can_edit": bool(project and project.can_edit(request.user)),
        "current_project": current_project or project,
    }


@require_http_methods(["GET"])
def slides_index(request):
    return render(request, "slides_app/index.html", build_slides_context(request))


@require_http_methods(["GET"])
def api_decks(request):
    project, error = _project_or_error(request)
    if error:
        return error
    return JsonResponse(
        {
            "success": True,
            "project": _project_ref(project),
            "can_edit": project.can_edit(request.user),
            "decks": services.list_decks(project),
            "figures": services.list_figures(project),
        }
    )


def _payload(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except ValueError:
        return {}


@require_http_methods(["GET", "POST"])
def api_deck(request):
    if request.method == "GET":
        project, error = _project_or_error(request)
        if error:
            return error
        try:
            content = services.read_deck(project, request.GET.get("name", ""))
        except services.DeckError as exc:
            return _denied(str(exc), 404)
        return JsonResponse({"success": True, "content": content})

    data = _payload(request)
    project, error = _project_or_error(request, data.get("project", ""), write=True)
    if error:
        return error
    try:
        path = services.write_deck(project, data.get("name", ""), data.get("content", ""))
    except services.DeckError as exc:
        return _denied(str(exc), 400)
    return JsonResponse({"success": True, "name": path.stem})


@require_http_methods(["POST"])
def api_deck_from_project(request):
    data = _payload(request)
    project, error = _project_or_error(request, data.get("project", ""), write=True)
    if error:
        return error
    name = data.get("name") or f"{project.slug}-overview"
    try:
        content = services.starter_deck(project)
        path = services.write_deck(project, name, content)
    except services.DeckError as exc:
        return _denied(str(exc), 400)
    return JsonResponse({"success": True, "name": path.stem, "content": content})


@require_http_methods(["GET"])
def api_file(request):
    project, error = _project_or_error(request)
    if error:
        return error
    rel_path = request.GET.get("path", "")
    if not rel_path.lower().endswith(services.FIGURE_EXTENSIONS):
        return HttpResponseNotFound()
    try:
        path = services.resolve_project_file(project, rel_path)
    except services.DeckError:
        return HttpResponseNotFound()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    response = FileResponse(path.open("rb"), content_type=content_type)
    # SVGs from a project may carry script; never let them run on the hub origin.
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    response["X-Content-Type-Options"] = "nosniff"
    return response


# EOF
