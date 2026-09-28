#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/writer_app/views/editor/api/content.py
"""Section content operations - read, write, save."""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.platform_app.services.paths import resolve_within
from apps.security import safe_log_field

from ..auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)

DOCUMENT_DIRS = {
    "manuscript": "01_manuscript/contents",
    "supplementary": "02_supplementary/contents",
    "revision": "03_revision/contents",
    "shared": "shared",
}


def _section_target(writer_service, section_name: str, doc_type: str):
    """Return the canonical section path only when Writer would stay confined."""
    directory = DOCUMENT_DIRS.get(doc_type)
    if directory is None or not isinstance(section_name, str):
        return None
    section_dir = resolve_within(writer_service.writer_dir, directory)
    if section_dir is None:
        return None
    return resolve_within(section_dir, f"{section_name}.tex")


def _workspace_is_not_ready(error: RuntimeError) -> bool:
    """Whether Writer explicitly reports an absent or incomplete workspace."""
    message = str(error)
    return message.startswith("Project directory not found for project ") or (
        "Failed to initialize Writer: Project structure invalid: missing " in message
        and message.endswith(" directory")
    )


@api_login_optional
@require_http_methods(["GET", "POST"])
def section_view(request, project_id, section_name):
    """Read or write a section's .tex file from/to disk.

    Supports hierarchical section IDs (e.g., "shared/title", "manuscript/abstract").

    GET: Read section content from disk
    POST: Write section content to disk
    """
    from apps.infra.project_app.models import Project

    try:
        from ....configs.sections_config import parse_section_id
        from ....services import WriterService

        Project.objects.get(id=project_id)

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

                file_path = _section_target(writer_service, name, doc_type)
                if file_path is None:
                    return JsonResponse(
                        {"success": False, "error": "Invalid section path"}, status=400
                    )

                logger.info(
                    "[SectionView GET] Reading section=%s category=%s name=%s doc_type=%s",
                    safe_log_field(section_name),
                    safe_log_field(category),
                    safe_log_field(name),
                    safe_log_field(doc_type),
                )

                doc_dir_map = {
                    "manuscript": "01_manuscript/contents",
                    "supplementary": "02_supplementary/contents",
                    "revision": "03_revision/contents",
                    "shared": "shared",
                }
                try:
                    section_dir = writer_service.writer_dir / doc_dir_map.get(
                        doc_type, "01_manuscript/contents"
                    )
                    file_path = section_dir / f"{name}.tex"
                    # Captured BEFORE the read: scitex-writer materialises a
                    # section file from its packaged template while reading it, so
                    # checking `exists()` afterwards answers "was it written by
                    # this request", not "had the author written it".
                    was_missing = not file_path.exists()
                    # The READ is inside this guard on purpose, and this is the
                    # part that took a second attempt to get right. Two ordinary
                    # states of an unready workspace both raise RuntimeError:
                    #   - the project directory is not on disk at all (scaffolded
                    #     lazily by initialize-workspace);
                    #   - the writer workspace EXISTS but is half-created, e.g.
                    #     missing 01_manuscript — the leaf then ATTACHES to it and
                    #     fails its own structure check instead of scaffolding
                    #     (scitex_writer/writer.py, _attach_or_create_project).
                    # Guarding only the path lookup covered the first and let the
                    # second escape one line later as a 500.
                    content = writer_service.read_section(name, doc_type)
                except RuntimeError as exc:
                    if not _workspace_is_not_ready(exc):
                        raise
                    # Writer creates its workspace lazily (initialize-workspace
                    # does), so the page's own first section fetch can arrive
                    # before it is ready — the ordinary state of a project that
                    # was just registered, and exactly the registered-project
                    # journey. It used to fall through to the handler below and
                    # answer as a same-origin 500 (the hub allowlists no 5xx).
                    # The client renders `success: true` with empty content as an
                    # empty editor, so "not written yet" and "workspace not ready
                    # yet" look the same to it on purpose.
                    logger.info(
                        "[SectionView GET] workspace not ready for project "
                        "%s (%s); serving empty content",
                        safe_log_field(project_id),
                        safe_log_field(exc),
                    )
                    return JsonResponse(
                        {
                            "success": True,
                            "content": "",
                            "section_name": name,
                            "section_id": section_name,
                            "doc_type": doc_type,
                            "file_path": None,
                            "missing": True,
                            "workspace_ready": False,
                        }
                    )


                if content is None:
                    # A section that has not been written yet is the ORDINARY
                    # state of a project that was just registered: the project
                    # row exists (owner + slug), the workspace exists, the .tex
                    # does not. This branch used to `raise ValueError`, which the
                    # handler below turned into a 500 — so opening Writer in the
                    # registered-project journey answered the page's own
                    # section-load with a same-origin 5xx, and the editor came up
                    # blank with a console error instead of simply blank.
                    #
                    # `None` for a file that DOES exist is not ordinary: that is
                    # a read that failed, and it still raises (500) below.
                    if file_path.exists():
                        raise ValueError(
                            f"read_section returned None for existing {file_path}"
                        )
                    content = ""
                    logger.info(
                        "[SectionView GET] %s has not been written yet; "
                        "serving empty content (%s)",
                        safe_log_field(name),
                        safe_log_field(file_path),
                    )
                else:
                    if not isinstance(content, str):
                        raise TypeError("read_section returned non-text content")
                    logger.info(
                        "[SectionView GET] Read %d chars for %s",
                        len(content),
                        safe_log_field(name),
                    )


                return JsonResponse(
                    {
                        "success": True,
                        "content": content,
                        "section_name": name,
                        "section_id": section_name,
                        "doc_type": doc_type,
                        "file_path": str(file_path) if file_path.exists() else None,
                        # Additive: lets a caller tell "empty because unwritten"
                        # from "empty because the author emptied it".
                        "missing": was_missing,
                        "workspace_ready": True,
                    }
                )

            except Exception:
                logger.exception(
                    "Error reading section %s", safe_log_field(section_name)
                )
                return JsonResponse(
                    {"success": False, "error": "Failed to read section."},
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

                if _section_target(writer_service, name, doc_type) is None:
                    return JsonResponse(
                        {"success": False, "error": "Invalid section path"}, status=400
                    )

                logger.info(
                    "[SectionView POST] Writing section=%s category=%s name=%s "
                    "doc_type=%s length=%d",
                    safe_log_field(section_name),
                    safe_log_field(category),
                    safe_log_field(name),
                    safe_log_field(doc_type),
                    len(content),
                )

                try:
                    success = writer_service.write_section(name, content, doc_type)
                except RuntimeError as exc:
                    # Same state on the write side: there is nowhere to write
                    # yet. A refusal the caller can act on, not a 5xx — the
                    # workspace is created by initialize-workspace, and the
                    # client can retry once it is.
                    logger.info(f"[SectionView POST] workspace not on disk: {exc}")
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "workspace not initialized for this project",
                            "workspace_ready": False,
                        },
                        status=409,
                    )

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

            except Exception:
                logger.exception(
                    "Error writing section %s", safe_log_field(section_name)
                )
                return JsonResponse(
                    {"success": False, "error": "Failed to write section."},
                    status=500,
                )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception:
        logger.exception("Error in section_view for project %s", safe_log_field(project_id))
        return JsonResponse({"success": False, "error": "Unable to process request."}, status=500)


@api_login_optional
@require_http_methods(["POST"])
def save_sections_view(request, project_id):
    """Save multiple sections at once.

    POST body: {"sections": {"name1": "content1", ...}, "doc_type": "manuscript"}
    """
    from apps.infra.project_app.models import Project

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

        Project.objects.get(id=project_id)

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
                if _section_target(writer_service, section_name, category) is None:
                    error_list.append(f"{section_id}: Invalid section path")
                    continue
                success = writer_service.write_section(section_name, content, category)

                if success:
                    saved_count += 1
                else:
                    error_list.append(f"{section_id}: write_section returned False")

            except Exception:
                logger.exception(
                    "Error saving section %s", safe_log_field(section_id)
                )
                error_list.append(f"{section_id}: Save failed")

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
                "sections_skipped": 0,
                "message": f"Saved {saved_count} sections",
                "errors": [],
                "error_details": {},
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception:
        logger.exception("Error saving sections for project %s", safe_log_field(project_id))
        return JsonResponse(
            {"success": False, "error": "Unable to save sections."}, status=500
        )


@api_login_optional
@require_http_methods(["GET"])
def read_tex_file_view(request, project_id):
    """Read a .tex file directly from disk by path.

    GET params:
        path: File path relative to workspace
    """
    from apps.infra.project_app.models import Project

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
        full_path = resolve_within(workspace_path, file_path)
        if full_path is None:
            return JsonResponse(
                {"success": False, "error": "Invalid path"}, status=400
            )

        if not full_path.exists():
            # An absent file is an answer, not an error; a 404 here spams the editor console.
            return JsonResponse({"success": True, "exists": False, "path": file_path})

        try:
            content = full_path.read_text(encoding="utf-8")
            return JsonResponse(
                {
                    "success": True,
                    "exists": True,
                    "content": content,
                    "path": file_path,
                    "filename": full_path.name,
                }
            )
        except Exception:
            logger.exception("Error reading file %s", safe_log_field(file_path))
            return JsonResponse(
                {"success": False, "error": "Failed to read file."}, status=500
            )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception:
        logger.exception(
            "Error in read_tex_file_view for project %s", safe_log_field(project_id)
        )
        return JsonResponse({"success": False, "error": "Unable to read file."}, status=500)


# View aliases for backward compatibility
section_history_view = section_view  # Temp stub
section_diff_view = section_view  # Temp stub
section_checkout_view = section_view  # Temp stub
section_commit_view = section_view  # Temp stub
available_sections_view = section_view  # Temp stub
presence_update_view = section_view  # Temp stub

# EOF
