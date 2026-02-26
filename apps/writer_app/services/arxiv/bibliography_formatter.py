"""
Bibliography Formatting for arXiv Submission

Provides formatter for converting manuscript citations
to arXiv-compatible BibTeX format.
"""

import re

from ...models import Citation, Manuscript


class ArxivBibliographyFormatter:
    """Format bibliography for arXiv submission."""

    def __init__(self):
        self.biblatex_to_bibtex_map = {
            "journaltitle": "journal",
            "location": "address",
            "date": "year",
        }

    def format_bibliography(self, manuscript: Manuscript) -> str:
        """
        Generate arXiv-compatible bibliography file.

        Args:
            manuscript: Manuscript with citations

        Returns:
            BibTeX content string
        """
        citations = manuscript.citations.all()
        if not citations:
            return self._get_default_bibliography()

        bib_entries = []
        bib_entries.append("% Bibliography for arXiv submission")
        bib_entries.append("% Generated from SciTeX Writer")
        bib_entries.append("")

        for citation in citations:
            formatted_entry = self._format_citation_entry(citation)
            bib_entries.append(formatted_entry)
            bib_entries.append("")

        return "\n".join(bib_entries)

    def _format_citation_entry(self, citation: Citation) -> str:
        """Format individual citation entry for BibTeX."""
        if citation.bibtex_entry:
            # Clean existing BibTeX entry
            return self._clean_bibtex_entry(citation.bibtex_entry)
        else:
            # Generate BibTeX entry from citation fields
            return self._generate_bibtex_entry(citation)

    def _clean_bibtex_entry(self, bibtex_entry: str) -> str:
        """Clean BibTeX entry for arXiv compatibility."""
        # Convert biblatex fields to bibtex
        for biblatex_field, bibtex_field in self.biblatex_to_bibtex_map.items():
            bibtex_entry = re.sub(
                rf"\b{biblatex_field}\s*=", f"{bibtex_field} =", bibtex_entry
            )

        # Remove unsupported fields
        unsupported_fields = ["url", "urldate", "file", "abstract"]
        for field in unsupported_fields:
            bibtex_entry = re.sub(
                rf"\s*{field}\s*=\s*\{{[^}}]*\}},?\s*",
                "",
                bibtex_entry,
                flags=re.IGNORECASE,
            )

        # Clean up formatting
        bibtex_entry = re.sub(r",\s*}", "\n}", bibtex_entry)

        return bibtex_entry

    def _generate_bibtex_entry(self, citation: Citation) -> str:
        """Generate BibTeX entry from citation fields."""
        entry_type = citation.entry_type
        key = citation.citation_key

        fields = []
        fields.append(f"title = {{{citation.title}}}")
        fields.append(f"author = {{{citation.authors}}}")
        fields.append(f"year = {{{citation.year}}}")

        if citation.journal:
            fields.append(f"journal = {{{citation.journal}}}")
        if citation.volume:
            fields.append(f"volume = {{{citation.volume}}}")
        if citation.number:
            fields.append(f"number = {{{citation.number}}}")
        if citation.pages:
            fields.append(f"pages = {{{citation.pages}}}")
        if citation.doi:
            fields.append(f"doi = {{{citation.doi}}}")

        fields_str = ",\n  ".join(fields)

        return f"""@{entry_type}{{{key},
  {fields_str}
}}"""

    def _get_default_bibliography(self) -> str:
        """Get default bibliography template."""
        return """% Bibliography for arXiv submission
% Add your citations here in BibTeX format

% Example entry:
% @article{example2023,
%   title={Example Article Title},
%   author={Author, First and Second, Author},
%   journal={Journal Name},
%   volume={1},
%   number={1},
%   pages={1--10},
%   year={2023}
% }
"""
