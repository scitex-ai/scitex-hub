#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/content.py
"""Section content operations - read, write, save."""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["GET", "POST"])
def section_view(request, project_id, section_name):
    """Read or write a section's .tex file from/to disk.

    Supports hierarchical section IDs (e.g., "shared/title", "manuscript/abstract").

    GET: Read section content from disk
    POST: Write section content to disk
    """
    from apps.project_app.models import Project

    try:
        from ....configs.sections_config import parse_section_id
        from ....services import WriterService

        project = Project.objects.get(id=project_id)

        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        writer_service = WriterService(project_id, user.id)
        category, name = parse_section_id(section_name)

        if request.method == "GET":
            try:
                doc_type = request.GET.get("doc_type", category)

                logger.info(
                    f"[SectionView GET] Reading section: {section_name} -> "
                    f"category={category}, name={name}, doc_type={doc_type}"
                )

                content = writer_service.read_section(name, doc_type)

                if content is None:
                    raise ValueError(f"read_section returned None for {name}")

                logger.info(f"[SectionView GET] Read {len(content)} chars for {name}")

                doc_dir_map = {
                    "manuscript": "01_manuscript/contents",
                    "supplementary": "02_supplementary/contents",
                    "revision": "03_revision/contents",
                    "shared": "shared",
                }
                section_dir = writer_service.writer_dir / doc_dir_map.get(
                    doc_type, "01_manuscript/contents"
                )
                file_path = section_dir / f"{name}.tex"

                return JsonResponse(
                    {
                        "success": True,
                        "content": content,
                        "section_name": name,
                        "section_id": section_name,
                        "doc_type": doc_type,
                        "file_path": str(file_path) if file_path.exists() else None,
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error reading section {section_name}: {e}", exc_info=True
                )
                return JsonResponse(
                    {"success": False, "error": f"Failed to read section: {e}"},
                    status=500,
                )

        elif request.method == "POST":
            try:
                data = json.loads(request.body)
                content = data.get("content")
                doc_type = data.get("doc_type", category)

                if content is None:
                    return JsonResponse(
                        {"success": False, "error": "Content is required"}, status=400
                    )

                if not isinstance(content, str):
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"Content must be string, got {type(content).__name__}",
                        },
                        status=400,
                    )

                logger.info(
                    f"[SectionView POST] Writing section: {section_name} -> "
                    f"category={category}, name={name}, doc_type={doc_type}, "
                    f"length: {len(content)}"
                )

                success = writer_service.write_section(name, content, doc_type)

                if success:
                    return JsonResponse(
                        {
                            "success": True,
                            "content": content,
                            "section_name": name,
                            "section_id": section_name,
                            "doc_type": doc_type,
                        }
                    )
                else:
                    return JsonResponse(
                        {"success": False, "error": "write_section returned False"},
                        status=500,
                    )

            except Exception as e:
                logger.error(
                    f"Error writing section {section_name}: {e}", exc_info=True
                )
                return JsonResponse(
                    {"success": False, "error": f"Failed to write section: {e}"},
                    status=500,
                )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error in section_view: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@api_login_optional
@require_http_methods(["POST"])
def save_sections_view(request, project_id):
    """Save multiple sections at once.

    POST body: {"sections": {"name1": "content1", ...}, "doc_type": "manuscript"}
    """
    from apps.project_app.models import Project

    try:
        data = json.loads(request.body)
        sections = data.get("sections", {})

        if not isinstance(sections, dict):
            return JsonResponse(
                {"success": False, "error": "'sections' must be a dictionary"},
                status=400,
            )

        if not sections:
            return JsonResponse(
                {"success": False, "error": "No sections provided"}, status=400
            )

        from ....services import WriterService

        project = Project.objects.get(id=project_id)

        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        writer_service = WriterService(project_id, user.id)

        saved_count = 0
        error_list = []

        from ....configs.sections_config import parse_section_id

        for section_id, content in sections.items():
            try:
                if not isinstance(content, str):
                    error_list.append(
                        f"{section_id}: Content must be string, "
                        f"got {type(content).__name__}"
                    )
                    continue

                category, section_name = parse_section_id(section_id)
                success = writer_service.write_section(section_name, content, category)

                if success:
                    saved_count += 1
                else:
                    error_list.append(f"{section_id}: write_section returned False")

            except Exception as e:
                logger.error(f"Error saving section {section_id}: {e}", exc_info=True)
                error_list.append(f"{section_id}: {e}")

        if error_list:
            return JsonResponse(
                {
                    "success": saved_count > 0,
                    "sections_saved": saved_count,
                    "sections_skipped": len(error_list),
                    "message": f"Saved {saved_count}/{len(sections)} sections",
                    "errors": error_list,
                },
                status=500 if saved_count == 0 else 200,
            )

        return JsonResponse(
            {
                "success": True,
                "sections_saved": saved_count,
                "message": f"Saved {saved_count} sections",
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error saving sections: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": f"Server error: {e}"}, status=500
        )


@api_login_optional
@require_http_methods(["GET"])
def read_tex_file_view(request, project_id):
    """Read a .tex file directly from disk by path.

    GET params:
        path: File path relative to workspace
    """
    from apps.project_app.models import Project

    try:
        file_path = request.GET.get("path")
        if not file_path:
            return JsonResponse(
                {"success": False, "error": "Missing 'path' query parameter"},
                status=400,
            )

        project = Project.objects.get(id=project_id)

        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        workspace_path = project.get_local_path()
        if not workspace_path:
            return JsonResponse(
                {"success": False, "error": "Project has no local path configured"},
                status=400,
            )
        full_path = workspace_path / file_path

        # Security: Ensure path is within workspace
        try:
            full_path = full_path.resolve()
            workspace_resolved = workspace_path.resolve()
            if not str(full_path).startswith(str(workspace_resolved)):
                return JsonResponse(
                    {"success": False, "error": "Path outside workspace"}, status=403
                )
        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Invalid path: {e}"}, status=400
            )

        if not full_path.exists():
            return JsonResponse(
                {"success": False, "error": f"File not found: {file_path}"}, status=404
            )

        try:
            content = full_path.read_text(encoding="utf-8")
            return JsonResponse(
                {
                    "success": True,
                    "content": content,
                    "path": file_path,
                    "filename": full_path.name,
                }
            )
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return JsonResponse(
                {"success": False, "error": f"Failed to read file: {e}"}, status=500
            )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error in read_tex_file_view: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# View aliases for backward compatibility
section_history_view = section_view  # Temp stub
section_diff_view = section_view  # Temp stub
section_checkout_view = section_view  # Temp stub
section_commit_view = section_view  # Temp stub
available_sections_view = section_view  # Temp stub
presence_update_view = section_view  # Temp stub

# EOF
