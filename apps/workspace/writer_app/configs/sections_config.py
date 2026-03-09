"""
Section configuration for Writer app dropdowns.

Defines hierarchical structure matching scitex.writer backend.
"""

# Hierarchical section structure
SECTION_HIERARCHY = {
    "shared": {
        "label": "Shared",
        "description": "Shared content across all documents",
        "sections": [
            {
                "id": "shared/title",
                "name": "title",
                "label": "Title",
                "path": "00_shared/title.tex",
            },
            {
                "id": "shared/authors",
                "name": "authors",
                "label": "Authors",
                "path": "00_shared/authors.tex",
            },
            {
                "id": "shared/keywords",
                "name": "keywords",
                "label": "Keywords",
                "path": "00_shared/keywords.tex",
            },
            {
                "id": "shared/journal_name",
                "name": "journal_name",
                "label": "Journal Name",
                "path": "00_shared/journal_name.tex",
            },
        ],
    },
    "manuscript": {
        "label": "Manuscript",
        "description": "Main manuscript content",
        "sections": [
            {
                "id": "manuscript/abstract",
                "name": "abstract",
                "label": "Abstract",
                "path": "01_manuscript/contents/abstract.tex",
            },
            {
                "id": "manuscript/highlights",
                "name": "highlights",
                "label": "Highlights",
                "path": "01_manuscript/contents/highlights.tex",
                "optional": True,
            },
            {
                "id": "manuscript/introduction",
                "name": "introduction",
                "label": "Introduction",
                "path": "01_manuscript/contents/introduction.tex",
            },
            {
                "id": "manuscript/methods",
                "name": "methods",
                "label": "Methods",
                "path": "01_manuscript/contents/methods.tex",
            },
            {
                "id": "manuscript/results",
                "name": "results",
                "label": "Results",
                "path": "01_manuscript/contents/results.tex",
            },
            {
                "id": "manuscript/discussion",
                "name": "discussion",
                "label": "Discussion",
                "path": "01_manuscript/contents/discussion.tex",
            },
            {
                "id": "manuscript/conclusion",
                "name": "conclusion",
                "label": "Conclusion",
                "path": "01_manuscript/contents/conclusion.tex",
            },
            {
                "id": "manuscript/compiled_pdf",
                "name": "compiled_pdf",
                "label": "Full Manuscript",
                "path": "01_manuscript/manuscript.tex",
                "view_only": True,
                "is_compiled": True,
                "no_preview": True,
                "instruction": "This is the compiled full manuscript. Click 'Compile Full Manuscript' to regenerate.",
            },
        ],
    },
    "supplementary": {
        "label": "Supplementary",
        "description": "Supplementary materials",
        "sections": [
            {
                "id": "supplementary/methods",
                "name": "methods",
                "label": "Supplementary Methods",
                "path": "02_supplementary/contents/methods.tex",
            },
            {
                "id": "supplementary/results",
                "name": "results",
                "label": "Supplementary Results",
                "path": "02_supplementary/contents/results.tex",
            },
            {
                "id": "supplementary/compiled_pdf",
                "name": "compiled_pdf",
                "label": "Full Supplementary File",
                "path": "02_supplementary/supplementary.tex",
                "view_only": True,
                "is_compiled": True,
                "no_preview": True,
                "instruction": "This is the compiled full supplementary file. Click 'Compile Full Supplementary' to regenerate.",
            },
        ],
    },
    "revision": {
        "label": "Revision",
        "description": "Revision materials",
        "supports_crud": True,
        "sections": [
            {
                "id": "revision/introduction",
                "name": "introduction",
                "label": "Revision Introduction",
                "path": "03_revision/contents/introduction.tex",
            },
            {
                "id": "revision/editor",
                "name": "editor",
                "label": "Response to Editor",
                "path": "03_revision/contents/editor.tex",
            },
            {
                "id": "revision/reviewer1",
                "name": "reviewer1",
                "label": "Response to Reviewer 1",
                "path": "03_revision/contents/reviewer1.tex",
            },
            {
                "id": "revision/reviewer2",
                "name": "reviewer2",
                "label": "Response to Reviewer 2",
                "path": "03_revision/contents/reviewer2.tex",
            },
            {
                "id": "revision/compiled_pdf",
                "name": "compiled_pdf",
                "label": "Full Revision",
                "path": "03_revision/revision.tex",
                "view_only": True,
                "is_compiled": True,
                "no_preview": True,
                "instruction": "This is the compiled full revision document. Click 'Compile Full Revision' to regenerate.",
            },
        ],
    },
}


def get_all_sections_flat():
    """Get all sections as a flat list."""
    sections = []
    for category_key, category in SECTION_HIERARCHY.items():
        for section in category["sections"]:
            section_with_category = {**section, "category": category_key}
            sections.append(section_with_category)
    return sections


def get_sections_by_category(category):
    """Get sections for a specific category."""
    if category in SECTION_HIERARCHY:
        return SECTION_HIERARCHY[category]["sections"]
    return []


def parse_section_id(section_id):
    """
    Parse a hierarchical section ID into category and name.

    Args:
        section_id: e.g., "shared/title", "manuscript/abstract"

    Returns:
        tuple: (category, name) e.g., ("shared", "title")
    """
    if "/" in section_id:
        parts = section_id.split("/", 1)
        return parts[0], parts[1]
    # Fallback for old-style IDs
    return "manuscript", section_id
