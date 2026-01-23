#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX reference tracking for figures."""
import re
from pathlib import Path
import logging

from .constants import shared_task

logger = logging.getLogger(__name__)


@shared_task
def update_latex_references(project_id):
    """
    Check which figures are referenced in LaTeX files.

    Scans all .tex files for \\includegraphics{} commands and updates
    the database with reference information.

    Args:
        project_id: Project ID
    """
    from apps.project_app.models import Project
    from ...utils.project_db import get_project_db

    try:
        project = Project.objects.get(id=project_id)

        # Get project path
        if hasattr(project, 'git_clone_path') and project.git_clone_path:
            project_path = Path(project.git_clone_path)
        else:
            from apps.project_app.services.project_filesystem import get_project_filesystem_manager
            if not hasattr(project, 'owner') or not project.owner:
                logger.error(f"[RefTracker] Cannot determine user for project {project_id}")
                return
            manager = get_project_filesystem_manager(project.owner)
            project_path = manager.get_project_root_path(project)
            if not project_path:
                logger.error(f"[RefTracker] Project path not found for project {project_id}")
                return

        db = get_project_db(project)

        logger.info(f"[RefTracker] Starting reference tracking for project {project_id}")

        # Get all figures from DB
        figures = db.get_all_figures()

        # Scan all .tex files
        tex_files = list(project_path.glob('scitex/writer/**/*.tex'))

        references_updated = 0

        for figure in figures:
            file_name = figure['file_name']
            file_stem = Path(file_name).stem

            ref_count = 0
            references = []

            # Search in .tex files
            for tex_file in tex_files:
                try:
                    content = tex_file.read_text()

                    # Pattern 1: \includegraphics{...filename...}
                    pattern1 = rf'\\includegraphics[^{{]*\{{[^}}]*{re.escape(file_name)}[^}}]*\}}'
                    matches1 = re.findall(pattern1, content, re.IGNORECASE)

                    # Pattern 2: \includegraphics{...stem...} (without extension)
                    pattern2 = rf'\\includegraphics[^{{]*\{{[^}}]*{re.escape(file_stem)}[^}}]*\}}'
                    matches2 = re.findall(pattern2, content, re.IGNORECASE)

                    matches = matches1 + matches2

                    if matches:
                        ref_count += len(matches)
                        references.append({
                            'tex_file': str(tex_file.relative_to(project_path)),
                            'count': len(matches),
                        })
                except Exception as e:
                    logger.debug(f"[RefTracker] Error reading {tex_file}: {e}")
                    continue

            # Update database
            db.update_references(
                figure['id'],
                is_referenced=(ref_count > 0),
                reference_count=ref_count
            )

            # Clear and add new references
            db.clear_latex_references(figure['id'])
            for ref in references:
                db.add_latex_reference(
                    figure['id'],
                    ref['tex_file'],
                    context=f"Referenced {ref['count']} times"
                )

            if ref_count > 0:
                references_updated += 1

        logger.info(f"[RefTracker] Completed for project {project_id}: {references_updated} figures referenced")

    except Exception as e:
        logger.error(f"[RefTracker] Error tracking references for project {project_id}: {e}")


# EOF
