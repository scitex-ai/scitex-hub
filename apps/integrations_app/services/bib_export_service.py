"""BibTeX export service for project bibliographies.

Delegates formatting to scitex.scholar.formatting.
"""

from django.utils import timezone
from scitex.scholar.formatting import generate_cite_key, to_bibtex


class BibExportService:
    """Service for exporting bibliographies as BibTeX format."""

    def __init__(self, project):
        self.project = project

    def generate_bibtex(self, references):
        """Generate BibTeX format from references.

        Args:
            references: List of dicts with keys like title, author, year, etc.

        Returns:
            str: BibTeX formatted string
        """
        entries = []
        for ref in references:
            paper = {
                "title": ref.get("title") or "",
                "authors_str": (
                    " and ".join(ref["author"])
                    if isinstance(ref.get("author"), list)
                    else ref.get("author") or ""
                ),
                "journal": ref.get("journal") or "",
                "year": str(ref.get("year") or ""),
                "doi": ref.get("doi") or "",
                "url": ref.get("url") or "",
                "volume": ref.get("volume") or "",
                "number": ref.get("number") or "",
                "pages": ref.get("pages") or "",
                "abstract": ref.get("abstract") or "",
                "document_type": ref.get("entry_type") or "article",
                "cite_key": ref.get("cite_key")
                or generate_cite_key(
                    {
                        "authors_str": (
                            " and ".join(ref["author"])
                            if isinstance(ref.get("author"), list)
                            else ref.get("author") or ""
                        ),
                        "year": str(ref.get("year") or ""),
                    }
                ),
            }
            entries.append(to_bibtex(paper))
        return "\n\n".join(entries)

    def export_to_file(self, references, file_path):
        """Export references to .bib file."""
        bibtex_content = self.generate_bibtex(references)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(bibtex_content)
        return file_path

    def export_project_bibliography(self, file_path=None):
        """Export project's bibliography."""
        references = self._get_project_references()
        if not file_path:
            safe_name = self.project.get_filesystem_safe_name()
            file_path = f"/tmp/{safe_name}_references.bib"

        exported_path = self.export_to_file(references, file_path)
        return {
            "success": True,
            "file_path": exported_path,
            "reference_count": len(references),
            "exported_at": timezone.now().isoformat(),
        }

    def _get_project_references(self):
        """Get references from project (placeholder)."""
        return []
