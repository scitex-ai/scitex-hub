"""BibTeX export service for project bibliographies"""

from django.utils import timezone


class BibExportService:
    """Service for exporting bibliographies as BibTeX format"""

    def __init__(self, project):
        self.project = project

    def generate_bibtex(self, references):
        """
        Generate BibTeX format from references

        Args:
            references: List of dicts with keys:
                - entry_type: article, book, inproceedings, etc.
                - cite_key: Citation key
                - title: Title
                - author: Authors (can be list or string)
                - year: Publication year
                - journal/booktitle: Journal or book title
                - volume, number, pages, publisher, doi, url, etc.

        Returns:
            str: BibTeX formatted string
        """
        bibtex_entries = []

        for ref in references:
            entry_type = ref.get("entry_type", "article")
            cite_key = ref.get("cite_key", self._generate_cite_key(ref))

            # Start entry
            entry = f"@{entry_type}{{{cite_key},\n"

            # Add fields
            fields = []

            # Required and optional fields based on entry type
            field_mapping = {
                "title": "title",
                "author": "author",
                "year": "year",
                "journal": "journal",
                "booktitle": "booktitle",
                "volume": "volume",
                "number": "number",
                "pages": "pages",
                "publisher": "publisher",
                "doi": "doi",
                "url": "url",
                "abstract": "abstract",
                "keywords": "keywords",
                "note": "note",
                "editor": "editor",
                "series": "series",
                "edition": "edition",
                "month": "month",
                "address": "address",
                "isbn": "isbn",
                "issn": "issn",
            }

            for key, bibtex_field in field_mapping.items():
                value = ref.get(key)
                if value:
                    # Handle author lists
                    if key == "author" and isinstance(value, list):
                        value = " and ".join(value)

                    # Escape special characters
                    value = self._escape_bibtex(str(value))

                    # Format field
                    fields.append(f"  {bibtex_field} = {{{value}}}")

            entry += ",\n".join(fields)
            entry += "\n}\n"

            bibtex_entries.append(entry)

        return "\n".join(bibtex_entries)

    def export_to_file(self, references, file_path):
        """
        Export references to .bib file

        Args:
            references: List of reference dicts
            file_path: Output file path

        Returns:
            str: File path of exported file
        """
        bibtex_content = self.generate_bibtex(references)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(bibtex_content)

        return file_path

    def export_project_bibliography(self, file_path=None):
        """
        Export project's bibliography

        Args:
            file_path: Optional custom file path

        Returns:
            dict: Export result with file_path and reference_count
        """
        # Get references from project (this will depend on your project structure)
        # For now, we'll use a placeholder
        references = self._get_project_references()

        if not file_path:
            # Generate default file path
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
        """
        Get references from project
        This is a placeholder - implement based on your project's reference storage
        """
        # TODO: Integrate with actual reference storage
        # This could be from scholar_app, writer_app, or a dedicated references model

        # Example structure:
        return []
        # return [
        #     {
        #         'entry_type': 'article',
        #         'title': 'Example Paper Title',
        #         'author': ['Smith, John', 'Doe, Jane'],
        #         'year': '2024',
        #         'journal': 'Nature',
        #         'volume': '123',
        #         'pages': '456--789',
        #         'doi': '10.1038/example',
        #     }
        # ]

    def _generate_cite_key(self, ref):
        """Generate citation key from reference data"""
        # Format: FirstAuthorLastNameYYYY
        author = ref.get("author", "")
        year = ref.get("year", "")

        if isinstance(author, list) and author:
            author = author[0]

        # Extract last name
        if "," in author:
            last_name = author.split(",")[0].strip()
        else:
            last_name = author.split()[-1] if author else "Unknown"

        # Clean last name
        last_name = "".join(c for c in last_name if c.isalnum())

        return f"{last_name}{year}" if year else last_name

    def _escape_bibtex(self, text):
        """Escape special BibTeX characters"""
        # Handle common special characters
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
            "\\": r"\textbackslash{}",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    @staticmethod
    def parse_bibtex(bibtex_content):
        """
        Parse BibTeX content into structured data

        Args:
            bibtex_content: BibTeX formatted string

        Returns:
            list: List of reference dicts
        """
        # This is a basic parser - for production use, consider using bibtexparser library
        import re

        references = []
        pattern = r"@(\w+){([^,]+),\s*(.*?)\n}"

        for match in re.finditer(pattern, bibtex_content, re.DOTALL):
            entry_type = match.group(1)
            cite_key = match.group(2)
            fields_str = match.group(3)

            ref = {
                "entry_type": entry_type,
                "cite_key": cite_key,
            }

            # Parse fields
            field_pattern = r'(\w+)\s*=\s*[{"]([^}"]+)[}"]'
            for field_match in re.finditer(field_pattern, fields_str):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2)
                ref[field_name] = field_value

            references.append(ref)

        return references
