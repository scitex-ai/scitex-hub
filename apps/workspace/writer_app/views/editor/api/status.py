#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manuscript status - lets the editor ask what exists instead of probing with 404s."""

from __future__ import annotations

from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.writer_workspace_layout import (
    get_writer_workspace_path,
    is_writer_initialized,
)

from ..auth_utils import api_login_optional
from .files import find_writer_pdf


def _plain_pdf_filename(value: str) -> str | None:
    if value and Path(value).name == value and value.endswith(".pdf"):
        return value
    return None


@api_login_optional
@require_http_methods(["GET"])
def manuscript_status_view(request, project_id):
    """Report whether the project has a Writer manuscript and a given PDF.

    GET params:
        pdf: optional PDF filename (e.g. ``preview-abstract-light.pdf``).
    """
    project = Project.objects.get(id=project_id)
    project_root = get_project_filesystem_manager(project.owner).get_project_root_path(
        project
    )
    exists = bool(project_root) and is_writer_initialized(project_root)
    pdf_filename = _plain_pdf_filename(request.GET.get("pdf", ""))
    has_pdf = bool(
        exists
        and pdf_filename
        and find_writer_pdf(get_writer_workspace_path(project_root), pdf_filename)
    )
    return JsonResponse({"success": True, "exists": exists, "has_pdf": has_pdf})
