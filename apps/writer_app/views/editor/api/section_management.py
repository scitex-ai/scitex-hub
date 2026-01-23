#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/section_management.py
"""Section management operations - create, delete, toggle, move."""

from __future__ import annotations
import json
import logging
import re
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from ..auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def section_create_view(request, project_id):
    """Create a new custom section.

    POST body:
        {
            "doc_type": "manuscript|shared|supplementary|revision",
            "section_name": "background",  # lowercase, underscore-separated
            "section_label": "Background"  # optional, display label
        }
    """
    try:
        from ....services import WriterService
        from apps.project_app.models import Project

        # Get project
        project = Project.objects.get(id=project_id, owner=request.user)
        writer_service = WriterService(project_id, request.user.id)

        # Parse request body
        data = json.loads(request.body)
        doc_type = data.get("doc_type", "manuscript")
        section_name = data.get("section_name", "").strip().lower()
        section_label = data.get("section_label", "").strip()

        if not section_name:
            return JsonResponse(
                {"success": False, "error": "Section name is required"}, status=400
            )

        # Validate section name format
        if not re.match(r"^[a-z0-9_]+$", section_name):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Section name must contain only lowercase letters, numbers, and underscores",
                },
                status=400,
            )

        # Determine directory path based on doc_type
        doc_dir_map = {
            "manuscript": "01_manuscript/contents",
            "supplementary": "02_supplementary/contents",
            "revision": "03_revision/contents",
            "shared": "shared",
        }

        if doc_type not in doc_dir_map:
            return JsonResponse(
                {"success": False, "error": f"Invalid doc_type: {doc_type}"}, status=400
            )

        # Create section file
        section_dir = writer_service.writer_dir / doc_dir_map[doc_type]
        section_file = section_dir / f"{section_name}.tex"

        if section_file.exists():
            return JsonResponse(
                {"success": False, "error": f"Section '{section_name}' already exists"},
                status=400,
            )

        # Create directory if needed
        section_dir.mkdir(parents=True, exist_ok=True)

        # Create empty section file with header comment
        section_file.write_text(
            f"% {section_label or section_name.replace('_', ' ').title()}\n\n",
            encoding="utf-8",
        )

        logger.info(f"[SectionCreate] Created section: {section_name} in {doc_type}")

        return JsonResponse(
            {
                "success": True,
                "section_id": f"{doc_type}/{section_name}",
                "section_name": section_name,
                "section_label": section_label
                or section_name.replace("_", " ").title(),
                "message": "Section created successfully",
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[SectionCreate] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def section_delete_view(request, project_id, section_name):
    """Delete a custom section.

    Only custom sections can be deleted (not core sections like abstract, introduction, etc.).
    """
    try:
        from ....services import WriterService
        from apps.project_app.models import Project
        from ....configs.sections_config import parse_section_id

        # Get project
        project = Project.objects.get(id=project_id, owner=request.user)
        writer_service = WriterService(project_id, request.user.id)

        # Parse section ID
        category, name = parse_section_id(section_name)

        # Prevent deletion of core sections
        core_sections = [
            "abstract",
            "introduction",
            "methods",
            "results",
            "discussion",
            "title",
            "authors",
            "keywords",
            "compiled_pdf",
            "compiled_tex",
            "highlights",
            "conclusion",
            "references",
        ]

        if name in core_sections:
            return JsonResponse(
                {"success": False, "error": f"Cannot delete core section: {name}"},
                status=400,
            )

        # Determine file path
        doc_dir_map = {
            "manuscript": "01_manuscript/contents",
            "supplementary": "02_supplementary/contents",
            "revision": "03_revision/contents",
            "shared": "shared",
        }

        section_dir = writer_service.writer_dir / doc_dir_map.get(
            category, "01_manuscript/contents"
        )
        section_file = section_dir / f"{name}.tex"

        if not section_file.exists():
            return JsonResponse(
                {"success": False, "error": f"Section file not found: {name}.tex"},
                status=404,
            )

        # Delete the file
        section_file.unlink()

        logger.info(f"[SectionDelete] Deleted section: {name} from {category}")

        return JsonResponse(
            {"success": True, "message": f"Section '{name}' deleted successfully"}
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[SectionDelete] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@api_login_optional
@require_http_methods(["POST"])
def section_toggle_exclude_view(request, project_id, section_name):
    """Toggle section include/exclude state for compilation.

    POST body:
        {
            "excluded": true/false
        }

    This will be stored in a project-level configuration file.
    """
    try:
        from apps.project_app.models import Project
        from ....configs.sections_config import parse_section_id

        # Get effective user (authenticated or visitor)
        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Get project
        project = Project.objects.get(id=project_id)

        # Parse request body
        data = json.loads(request.body)
        excluded = data.get("excluded", False)

        # Parse section ID
        category, name = parse_section_id(section_name)

        # Store in project configuration file
        from ....services import WriterService

        writer_service = WriterService(project_id, user.id)
        config_file = writer_service.writer_dir / ".scitex_section_config.json"

        # Load existing config
        config = {}
        if config_file.exists():
            config = json.loads(config_file.read_text())

        # Update excluded sections list
        if "excluded_sections" not in config:
            config["excluded_sections"] = []

        section_id = f"{category}/{name}"
        if excluded:
            if section_id not in config["excluded_sections"]:
                config["excluded_sections"].append(section_id)
        else:
            if section_id in config["excluded_sections"]:
                config["excluded_sections"].remove(section_id)

        # Save config
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

        logger.info(f"[SectionToggleExclude] {section_name} excluded={excluded}")

        return JsonResponse(
            {
                "success": True,
                "excluded": excluded,
                "message": f"Section {'excluded' if excluded else 'included'}",
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[SectionToggleExclude] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def section_move_up_view(request, project_id, section_name):
    """Move section up in the compilation order.

    This will be stored in a project-level configuration file.
    """
    try:
        from apps.project_app.models import Project
        from ....configs.sections_config import parse_section_id
        from ....services import WriterService

        # Get project
        project = Project.objects.get(id=project_id, owner=request.user)
        writer_service = WriterService(project_id, request.user.id)

        # Parse section ID
        category, name = parse_section_id(section_name)
        section_id = f"{category}/{name}"

        # Load section order configuration
        config_file = writer_service.writer_dir / ".scitex_section_config.json"
        config = {}
        if config_file.exists():
            config = json.loads(config_file.read_text())

        if "section_order" not in config:
            config["section_order"] = {}

        if category not in config["section_order"]:
            config["section_order"][category] = []

        order = config["section_order"][category]

        # Find current index
        if section_id in order:
            idx = order.index(section_id)
            if idx > 0:
                # Swap with previous
                order[idx], order[idx - 1] = order[idx - 1], order[idx]
                config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

                logger.info(f"[SectionMoveUp] Moved {section_name} up")

                return JsonResponse({"success": True, "message": "Section moved up"})
            else:
                return JsonResponse(
                    {"success": False, "error": "Section is already at the top"},
                    status=400,
                )
        else:
            return JsonResponse(
                {"success": False, "error": "Section not in custom order"}, status=400
            )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[SectionMoveUp] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def section_move_down_view(request, project_id, section_name):
    """Move section down in the compilation order.

    This will be stored in a project-level configuration file.
    """
    try:
        from apps.project_app.models import Project
        from ....configs.sections_config import parse_section_id
        from ....services import WriterService

        # Get project
        project = Project.objects.get(id=project_id, owner=request.user)
        writer_service = WriterService(project_id, request.user.id)

        # Parse section ID
        category, name = parse_section_id(section_name)
        section_id = f"{category}/{name}"

        # Load section order configuration
        config_file = writer_service.writer_dir / ".scitex_section_config.json"
        config = {}
        if config_file.exists():
            config = json.loads(config_file.read_text())

        if "section_order" not in config:
            config["section_order"] = {}

        if category not in config["section_order"]:
            config["section_order"][category] = []

        order = config["section_order"][category]

        # Find current index
        if section_id in order:
            idx = order.index(section_id)
            if idx < len(order) - 1:
                # Swap with next
                order[idx], order[idx + 1] = order[idx + 1], order[idx]
                config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

                logger.info(f"[SectionMoveDown] Moved {section_name} down")

                return JsonResponse({"success": True, "message": "Section moved down"})
            else:
                return JsonResponse(
                    {"success": False, "error": "Section is already at the bottom"},
                    status=400,
                )
        else:
            return JsonResponse(
                {"success": False, "error": "Section not in custom order"}, status=400
            )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[SectionMoveDown] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
