#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bibliography upload API endpoint."""

from __future__ import annotations

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.writer_workspace_layout import (
    get_writer_workspace_path,
)

from ...auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["POST"])
def upload_bibliography(request, project_id):
    """
    Upload .bib files to project bibliography.

    Merges uploaded .bib entries into the project's shared bibliography.
    Uses scitex.scholar.storage.BibTeXHandler for parsing and merging.

    Accepts multipart/form-data with files array (.bib files).

    Returns:
        JSON with success status, entries added count, and total count
    """
    try:
        from pathlib import Path

        from apps.infra.project_app.models import Project

        project = Project.objects.get(id=project_id)
        user, is_visitor = get_user_for_request(request, project_id)

        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        # Get uploaded files
        files = request.FILES.getlist("files")
        if not files:
            return JsonResponse(
                {"success": False, "error": "No files provided"}, status=400
            )

        # Validate file extensions
        for f in files:
            ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
            if ext not in ("bib", "bibtex"):
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Invalid file type: {f.name}. Only .bib and .bibtex files are supported.",
                    },
                    status=400,
                )

        # Get project path
        if hasattr(project, "git_clone_path") and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.infra.project_app.services.project_filesystem import (
                get_project_filesystem_manager,
            )

            if not hasattr(project, "owner") or not project.owner:
                raise ValueError("Cannot determine project owner")
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                raise ValueError(f"Project path not found for project {project.id}")

        # Target: shared bib_files directory
        bib_dir = get_writer_workspace_path(project_path) / "00_shared" / "bib_files"
        bib_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded .bib files
        uploaded_files = []
        for uploaded_file in files:
            file_path = bib_dir / uploaded_file.name
            with open(file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            uploaded_files.append(uploaded_file.name)
            logger.info(
                f"[Bibliography Upload] Saved: {uploaded_file.name} ({uploaded_file.size} bytes)"
            )

        # Merge all .bib files into bibliography.bib
        entries_added = _merge_bibliography(bib_dir)

        logger.info(
            f"[Bibliography Upload] Uploaded {len(uploaded_files)} files, "
            f"{entries_added} entries in merged bibliography for project {project_id}"
        )

        return JsonResponse(
            {
                "success": True,
                "files": uploaded_files,
                "entries_added": entries_added,
                "message": f"Uploaded {len(uploaded_files)} file(s). {entries_added} total entries in bibliography.",
            }
        )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Bibliography Upload] Error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _merge_bibliography(bib_dir):
    """Merge all .bib files in directory into bibliography.bib.

    Returns total entry count in merged file.
    """

    merged_path = bib_dir / "bibliography.bib"

    # Collect all .bib files except the merged output
    bib_files = sorted(f for f in bib_dir.glob("*.bib") if f.name != "bibliography.bib")

    if not bib_files:
        return 0

    # Use scitex BibTeXHandler for proper parsing and deduplication
    try:
        from scitex.scholar.storage import BibTeXHandler

        handler = BibTeXHandler()
        all_papers = []
        seen_keys = set()

        for bib_file in bib_files:
            try:
                papers = handler.papers_from_bibtex(bib_file)
                for paper in papers:
                    key = getattr(paper, "_bibtex_key", None)
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        all_papers.append(paper)
            except Exception as e:
                logger.warning(
                    f"[Bibliography Merge] Failed to parse {bib_file.name}: {e}"
                )

        # Write merged bibliography
        if all_papers:
            handler.papers_to_bibtex(all_papers, merged_path)

        return len(all_papers)
    except ImportError:
        # Fallback: simple concatenation if scitex not available
        logger.warning(
            "[Bibliography Merge] scitex.scholar not available, using raw concatenation"
        )
        entries = set()
        merged_content = []
        for bib_file in bib_files:
            content = bib_file.read_text(encoding="utf-8", errors="replace")
            merged_content.append(content)
            # Rough count of entries
            entries.update(
                line.split("{")[1].split(",")[0].strip()
                for line in content.splitlines()
                if line.strip().startswith("@") and "{" in line
            )

        merged_path.write_text("\n\n".join(merged_content), encoding="utf-8")
        return len(entries)


# EOF
