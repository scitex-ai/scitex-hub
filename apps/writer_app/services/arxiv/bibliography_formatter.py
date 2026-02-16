"""
Bibliography Formatting for arXiv Submission

Delegates BibTeX cleaning to scitex.scholar.formatting.
"""

from scitex.scholar.formatting import clean_bibtex_for_arxiv

from ...models import Citation, Manuscript


class ArxivBibliographyFormatter:
    """Format bibliography for arXiv submission."""

    def format_bibliography(self, manuscript: Manuscript) -> str:
        """Generate arXiv-compatible bibliography file."""
        citations = manuscript.citations.all()
        if not citations:
            return self._get_default_bibliography()

        bib_entries = [
            "% Bibliography for arXiv submission",
            "% Generated from SciTeX Writer",
            "",
        ]

        for citation in citations:
            formatted_entry = self._format_citation_entry(citation)
            bib_entries.append(formatted_entry)
            bib_entries.append("")

        return "\n".join(bib_entries)

    def _format_citation_entry(self, citation: Citation) -> str:
        """Format individual citation entry for BibTeX."""
        if citation.bibtex_entry:
            return clean_bibtex_for_arxiv(citation.bibtex_entry)
        return self._generate_bibtex_entry(citation)

    def _generate_bibtex_entry(self, citation: Citation) -> str:
        """Generate BibTeX entry from citation fields."""
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
        return f"@{citation.entry_type}{{{citation.citation_key},\n  {fields_str}\n}}"

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
