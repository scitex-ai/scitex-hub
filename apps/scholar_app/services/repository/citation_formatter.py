"""
Citation formatting service for DOI metadata.
Formats dataset and paper citations in various citation styles.
"""

import logging
from typing import Dict

from ...models import Dataset, SearchIndex

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Service for formatting citations from DOI metadata"""

    def __init__(self):
        self.styles = {}
        self._load_citation_styles()

    def _load_citation_styles(self):
        """Load citation style templates"""

        self.styles = {
            "apa": {
                "dataset": "{authors} ({year}). {title} [Data set]. {publisher}. {doi}",
                "article": "{authors} ({year}). {title}. {journal}, {volume}({issue}), {pages}. {doi}",
            },
            "mla": {
                "dataset": '{authors}. "{title}." {publisher}, {year}, {doi}.',
                "article": '{authors}. "{title}." {journal}, vol. {volume}, no. {issue}, {year}, pp. {pages}. {doi}.',
            },
            "chicago": {
                "dataset": '{authors}. "{title}." {publisher}, {year}. {doi}.',
                "article": '{authors}. "{title}." {journal} {volume}, no. {issue} ({year}): {pages}. {doi}.',
            },
            "vancouver": {
                "dataset": "{authors}. {title} [dataset]. {publisher}; {year}. Available from: {doi}",
                "article": "{authors}. {title}. {journal}. {year};{volume}({issue}):{pages}. Available from: {doi}",
            },
        }

    def format_dataset_citation(self, dataset: Dataset, style: str = "apa") -> str:
        """Format a dataset citation"""

        if style not in self.styles:
            style = "apa"

        template = self.styles[style].get("dataset", self.styles["apa"]["dataset"])

        # Prepare authors
        authors = dataset.owner.get_full_name() or dataset.owner.username
        collaborators = dataset.collaborators.all()

        if collaborators.count() == 1:
            authors += f" & {collaborators.first().get_full_name() or collaborators.first().username}"
        elif collaborators.count() > 1:
            collab_names = [c.get_full_name() or c.username for c in collaborators]
            authors += f", {', '.join(collab_names[:-1])}, & {collab_names[-1]}"

        # Prepare data
        citation_data = {
            "authors": authors,
            "year": dataset.published_at.year
            if dataset.published_at
            else dataset.created_at.year,
            "title": dataset.title,
            "publisher": dataset.repository_connection.repository.name,
            "doi": dataset.repository_doi or dataset.repository_url,
            "version": dataset.version,
        }

        try:
            return template.format(**citation_data)
        except KeyError as e:
            logger.warning(f"Missing field in citation template: {e}")
            return f"{authors} ({citation_data['year']}). {dataset.title}. {citation_data['publisher']}."

    def format_paper_citation(self, paper: SearchIndex, style: str = "apa") -> str:
        """Format a paper citation"""

        if style not in self.styles:
            style = "apa"

        template = self.styles[style].get("article", self.styles["apa"]["article"])

        # Prepare authors
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

        # Prepare data
        citation_data = {
            "authors": authors,
            "year": paper.publication_date.year
            if paper.publication_date
            else paper.created_at.year,
            "title": paper.title,
            "journal": paper.journal.name
            if paper.journal
            else paper.get_source_display(),
            "volume": "",  # Would need to extract from paper metadata
            "issue": "",  # Would need to extract from paper metadata
            "pages": "",  # Would need to extract from paper metadata
            "doi": f"https://doi.org/{paper.doi}" if paper.doi else paper.external_url,
        }

        try:
            return template.format(**citation_data)
        except KeyError as e:
            logger.warning(f"Missing field in citation template: {e}")
            return f"{authors} ({citation_data['year']}). {paper.title}. {citation_data['journal']}."
