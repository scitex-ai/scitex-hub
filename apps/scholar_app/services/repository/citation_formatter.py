"""
Citation formatting service for DOI metadata.

Delegates text citation formatting to scitex.scholar.formatting.
"""

import logging

from scitex.scholar.formatting import to_text_citation

from ...models import Dataset, SearchIndex

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Service for formatting citations from DOI metadata."""

    def format_dataset_citation(self, dataset: Dataset, style: str = "apa") -> str:
        """Format a dataset citation."""
        authors = dataset.owner.get_full_name() or dataset.owner.username
        collaborators = dataset.collaborators.all()

        if collaborators.count() == 1:
            collab = collaborators.first()
            authors += f" & {collab.get_full_name() or collab.username}"
        elif collaborators.count() > 1:
            collab_names = [c.get_full_name() or c.username for c in collaborators]
            authors += f", {', '.join(collab_names[:-1])}, & {collab_names[-1]}"

        paper = {
            "authors_str": authors,
            "year": str(
                dataset.published_at.year
                if dataset.published_at
                else dataset.created_at.year
            ),
            "title": dataset.title,
            "publisher": dataset.repository_connection.repository.name,
            "doi": dataset.repository_doi or dataset.repository_url,
            "volume": "",
            "number": "",
            "pages": "",
        }
        return to_text_citation(paper, style=style, doc_type="dataset")

    def format_paper_citation(self, paper: SearchIndex, style: str = "apa") -> str:
        """Format a paper citation."""
        author_papers = paper.authors.through.objects.filter(paper=paper).order_by(
            "author_order"
        )
        author_names = [ap.author.full_name for ap in author_papers]

        if len(author_names) == 1:
            authors = author_names[0]
        elif len(author_names) == 2:
            authors = f"{author_names[0]} & {author_names[1]}"
        elif len(author_names) > 2:
            authors = f"{', '.join(author_names[:-1])}, & {author_names[-1]}"
        else:
            authors = "Unknown Author"

        paper_dict = {
            "authors_str": authors,
            "year": str(
                paper.publication_date.year
                if paper.publication_date
                else paper.created_at.year
            ),
            "title": paper.title,
            "journal": (
                paper.journal.name if paper.journal else paper.get_source_display()
            ),
            "doi": f"https://doi.org/{paper.doi}" if paper.doi else paper.external_url,
            "volume": "",
            "number": "",
            "pages": "",
        }
        return to_text_citation(paper_dict, style=style, doc_type="article")
