#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Creator: the create page, the app workspace and its three actions."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from ..services.app_create import (
    DEFAULT_STARTER,
    STARTERS,
    AppCreateError,
    create_app_project,
)
from ..services.app_workspace import (
    EditRefused,
    apply_file_edit,
    dev_tab_url,
    list_app_files,
    owned_app_project,
    project_dir_for,
    run_privately,
)

logger = logging.getLogger(__name__)

_MAX_HISTORY = 10


def _planned_brief(params) -> str:
    """The starter brief of the planned app named by ``brief`` (an id), if any."""
    from ..planned_apps import PLANNED_BY_ID

    planned = PLANNED_BY_ID.get(params.get("brief", ""))
    return planned.brief if planned else ""


@login_required
@require_http_methods(["GET", "POST"])
def create_page(request):
    # GET prefill comes from a planned app's "Build this app" link.
    source = request.POST if request.method == "POST" else request.GET
    form = {
        "name": source.get("name", ""),
        "description": source.get("description", "") or _planned_brief(source),
        "starter": source.get("starter", DEFAULT_STARTER),
    }
    error = None
    if request.method == "POST":
        try:
            project = create_app_project(
                request.user, form["name"], form["description"], form["starter"]
            )
            return redirect("app_workspace", slug=project.slug)
        except AppCreateError as exc:
            error = str(exc)
    return render(
        request,
        "apps_app/appmaker/create.html",
        {"starters": STARTERS, "form": form, "error": error},
        status=400 if error else 200,
    )


@login_required
def workspace_page(request, slug):
    from ..models import DevInstallation
    from ..services.appmaker_agent import resolve_chat_backend
    from ..services.dev_app_loader import read_manifest

    project = owned_app_project(request.user, slug)
    project_dir = project_dir_for(project)
    manifest = read_manifest(project_dir) if project_dir else {}
    install = DevInstallation.objects.filter(
        user=request.user,
        source_owner=request.user.username,
        source_repo=project.slug,
        is_enabled=True,
    ).first()
    files = list_app_files(project)
    context = {
        "project": project,
        "current_project": project,
        "app_label": manifest.get("label") or project.name,
        "files": files,
        "file_base_url": f"/{request.user.username}/{project.slug}/blob/",
        "has_ai_provider": resolve_chat_backend(request.user) is not None,
        "dev_tab_url": dev_tab_url(install) if install else "",
        "chat_url": f"/apps/create/{project.slug}/api/chat/",
        "apply_url": f"/apps/create/{project.slug}/api/apply/",
        "run_url": f"/apps/create/{project.slug}/api/run/",
    }
    return render(request, "apps_app/appmaker/workspace.html", context)


def _json_body(request) -> dict:
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


@login_required
@require_POST
def api_chat(request, slug):
    from scitex_app._chat import sse_keepalive_wrap, stream_chat

    from ..services.appmaker_agent import (
        build_skills,
        build_system_prompt,
        resolve_chat_backend,
    )

    project = owned_app_project(request.user, slug)
    data = _json_body(request)
    prompt = str(data.get("prompt", "")).strip()
    if not prompt:
        return JsonResponse(
            {"success": False, "error": "prompt is required"}, status=400
        )
    backend = resolve_chat_backend(request.user)
    if backend is None:
        return JsonResponse(
            {
                "success": False,
                "error": "No AI provider configured.",
                "settings_url": "/accounts/settings/ai-providers/",
            },
            status=400,
        )
    history = [
        {"role": m["role"], "content": str(m["content"])}
        for m in data.get("history", [])
        if isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and "content" in m
    ]
    system = build_system_prompt(
        build_skills(project_dir_for(project)), list_app_files(project)
    )
    events = stream_chat(
        prompt,
        history=history,
        system_prompt=system,
        max_history=_MAX_HISTORY,
        backend=backend,
    )
    response = StreamingHttpResponse(
        sse_keepalive_wrap(events), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_POST
def api_apply(request, slug):
    project = owned_app_project(request.user, slug)
    data = _json_body(request)
    content = data.get("content")
    if not isinstance(content, str):
        return JsonResponse(
            {"success": False, "error": "content is required"}, status=400
        )
    try:
        written = apply_file_edit(
            request.user, project, str(data.get("path", "")), content
        )
    except EditRefused:
        logger.warning("App edit refused", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "App edit was refused."}, status=403
        )
    return JsonResponse({"success": True, "path": written})


@login_required
@require_POST
def api_run(request, slug):
    project = owned_app_project(request.user, slug)
    try:
        install = run_privately(request.user, project)
    except ValueError:
        logger.warning("Private app launch rejected", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "Unable to launch app."}, status=400
        )
    return JsonResponse({"success": True, "url": dev_tab_url(install)})


# EOF
