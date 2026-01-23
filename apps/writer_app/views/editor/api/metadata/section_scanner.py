#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/section_scanner.py
"""Project section scanning utilities."""

from __future__ import annotations
import json
import logging

logger = logging.getLogger(__name__)


def _scan_project_sections(project_path):
    """Scan project directories to build section hierarchy from actual files.

    Excludes:
    - Symlinked files (e.g., authors.tex symlinked from shared to manuscript)
    - System files (wordcount.tex, .compiled.tex, etc.)
    - Template files
    - Subdirectories (figures/, tables/, latex_styles/, etc.)

    Args:
        project_path: Path to project root (contains 00_shared/, 01_manuscript/, etc.)

    Returns:
        dict: Hierarchy matching SECTION_HIERARCHY structure
    """

    hierarchy = {
        "shared": {
            "label": "Shared",
            "description": "Shared content across all documents",
            "sections": [],
        },
        "manuscript": {
            "label": "Manuscript",
            "description": "Main manuscript content",
            "sections": [],
        },
        "supplementary": {
            "label": "Supplementary",
            "description": "Supplementary materials",
            "sections": [],
        },
        "revision": {
            "label": "Revision",
            "description": "Revision materials",
            "supports_crud": True,
            "sections": [],
        },
    }

    # System files to skip
    skip_files = {
        "wordcount.tex",
        ".compiled.tex",
        "compiled.tex",
        "main.tex",
        "preamble.tex",
        "base.tex",
    }

    # Load excluded sections from config
    config_file = project_path / ".scitex_section_config.json"
    excluded_sections = []
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            excluded_sections = config.get("excluded_sections", [])
        except Exception as e:
            logger.warning(f"Failed to load section config: {e}")
            excluded_sections = []

    # Scan 00_shared/ directory (renamed from shared/ in v2.0.0-rc1)
    shared_dir = project_path / "00_shared"
    if shared_dir.exists() and shared_dir.is_dir():
        for tex_file in sorted(shared_dir.glob("*.tex")):
            if tex_file.name in skip_files:
                continue
            if tex_file.is_symlink():
                logger.debug(f"Skipping symlink: {tex_file}")
                continue

            section_name = tex_file.stem
            section_id = f"shared/{section_name}"
            hierarchy["shared"]["sections"].append(
                {
                    "id": section_id,
                    "name": section_name,
                    "label": section_name.replace("_", " ").title(),
                    "path": str(tex_file.relative_to(project_path)),
                    "excluded": section_id in excluded_sections,
                }
            )

    # Scan manuscript/contents/ directory
    manuscript_dir = project_path / "01_manuscript" / "contents"
    manuscript_sections = []

    if manuscript_dir.exists() and manuscript_dir.is_dir():
        for tex_file in sorted(manuscript_dir.glob("*.tex")):
            if tex_file.name in skip_files:
                continue
            if tex_file.is_symlink():
                logger.debug(f"Skipping symlink: {tex_file}")
                continue

            section_name = tex_file.stem
            # Mark optional sections (can be excluded from compilation)
            # Core sections: abstract, introduction, methods, discussion, results
            # Optional sections: everything else
            optional_sections = [
                "highlights",
                "graphical_abstract",
                "additional_info",
                "data_availability",
                "conclusion",
                "acknowledgments",
                "funding",
                "conflict_of_interest",
            ]
            section_id = f"manuscript/{section_name}"
            manuscript_sections.append(
                {
                    "id": section_id,
                    "name": section_name,
                    "label": section_name.replace("_", " ").title(),
                    "path": str(tex_file.relative_to(project_path)),
                    "optional": section_name in optional_sections,
                    "excluded": section_id in excluded_sections,
                }
            )

    # Define preferred order for manuscript sections (matches standard manuscript structure)
    section_order = {
        "abstract": 0,
        "introduction": 1,
        "methods": 2,
        "discussion": 3,
        "results": 4,
        "highlights": 5,
        "graphical_abstract": 6,
        "additional_info": 7,
        "data_availability": 8,
        "conclusion": 9,
        # Everything else goes after
    }

    # Sort sections by preferred order, then alphabetically
    manuscript_sections.sort(
        key=lambda s: (section_order.get(s["name"], 999), s["name"])
    )

    # Add sorted sections to hierarchy
    hierarchy["manuscript"]["sections"] = manuscript_sections

    # Add "Full Manuscript" compiled PDF section at the END
    compiled_tex_path = project_path / "01_manuscript" / "manuscript.tex"
    if compiled_tex_path.exists():
        hierarchy["manuscript"]["sections"].append(
            {
                "id": "manuscript/compiled_pdf",
                "name": "compiled_pdf",
                "label": "📄 Full Manuscript",
                "path": str(compiled_tex_path.relative_to(project_path)),
                "view_only": True,
                "is_compiled": True,
                "no_preview": True,
            }
        )

    # Scan supplementary/contents/ directory
    supplementary_dir = project_path / "02_supplementary" / "contents"
    if supplementary_dir.exists() and supplementary_dir.is_dir():
        for tex_file in sorted(supplementary_dir.glob("*.tex")):
            if tex_file.name in skip_files:
                continue
            if tex_file.is_symlink():
                logger.debug(f"Skipping symlink: {tex_file}")
                continue

            section_name = tex_file.stem
            section_id = f"supplementary/{section_name}"
            hierarchy["supplementary"]["sections"].append(
                {
                    "id": section_id,
                    "name": section_name,
                    "label": f"Supplementary {section_name.replace('_', ' ').title()}",
                    "path": str(tex_file.relative_to(project_path)),
                    "excluded": section_id in excluded_sections,
                }
            )

    # Add "Full Supplementary File" compiled PDF section at the END
    supplementary_tex_path = project_path / "02_supplementary" / "supplementary.tex"
    if supplementary_tex_path.exists():
        hierarchy["supplementary"]["sections"].append(
            {
                "id": "supplementary/compiled_pdf",
                "name": "compiled_pdf",
                "label": "📄 Full Supplementary File",
                "path": str(supplementary_tex_path.relative_to(project_path)),
                "view_only": True,
                "is_compiled": True,
                "no_preview": True,
            }
        )

    # Scan revision/contents/ directory
    revision_dir = project_path / "03_revision" / "contents"
    if revision_dir.exists() and revision_dir.is_dir():
        for tex_file in sorted(revision_dir.glob("*.tex")):
            if tex_file.name in skip_files:
                continue
            if tex_file.is_symlink():
                logger.debug(f"Skipping symlink: {tex_file}")
                continue

            section_name = tex_file.stem
            section_id = f"revision/{section_name}"
            hierarchy["revision"]["sections"].append(
                {
                    "id": section_id,
                    "name": section_name,
                    "label": f"Revision {section_name.replace('_', ' ').title()}",
                    "path": str(tex_file.relative_to(project_path)),
                    "excluded": section_id in excluded_sections,
                }
            )

    # Add "Full Revision" compiled PDF section at the END
    revision_tex_path = project_path / "03_revision" / "revision.tex"
    if revision_tex_path.exists():
        hierarchy["revision"]["sections"].append(
            {
                "id": "revision/compiled_pdf",
                "name": "compiled_pdf",
                "label": "📄 Full Revision",
                "path": str(revision_tex_path.relative_to(project_path)),
                "view_only": True,
                "is_compiled": True,
                "no_preview": True,
            }
        )

    logger.info(
        f"Scanned project sections: {sum(len(cat['sections']) for cat in hierarchy.values())} total sections"
    )
    return hierarchy


# EOF
