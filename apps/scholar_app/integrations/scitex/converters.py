"""SciTeX to Django model conversion."""

import logging
from typing import Dict
from datetime import datetime
from ...models import SearchIndex

logger = logging.getLogger(__name__)

def scitex_to_django_paper(scitex_result: Dict, user=None) -> SearchIndex:
    """
    Convert SciTeX search result to Django SearchIndex model.

    Args:
        scitex_result: Result dictionary from SciTeX pipeline
        user: Optional Django user for tracking

    Returns:
        SearchIndex model instance (saved to database)
    """
    # Extract data from SciTeX result format
    title = scitex_result.get("title", "")
    doi = scitex_result.get("doi", "").strip() or None
    pmid = scitex_result.get("pmid", "").strip() or None
    arxiv_id = scitex_result.get("arxiv_id", "").strip() or None

    # Check if paper already exists (by DOI, PMID, or arXiv ID)
    existing_paper = None

    if doi:
        existing_paper = SearchIndex.objects.filter(doi=doi).first()

    if not existing_paper and pmid:
        existing_paper = SearchIndex.objects.filter(pmid=pmid).first()

    if not existing_paper and arxiv_id:
        existing_paper = SearchIndex.objects.filter(arxiv_id=arxiv_id).first()

    # If paper exists, update it; otherwise create new
    if existing_paper:
        paper = existing_paper
    else:
        paper = SearchIndex()

    # Update fields
    paper.title = title if title else "Untitled"
    paper.abstract = scitex_result.get("abstract", "")
    paper.doi = doi
    paper.pmid = pmid
    paper.arxiv_id = arxiv_id

    # Document type (required field)
    paper.document_type = scitex_result.get("document_type", "article")

    # Publication info
    year = scitex_result.get("year")
    if year:
        try:
            paper.publication_date = datetime(int(year), 1, 1).date()
        except (ValueError, TypeError):
            pass

    # Authors (store as comma-separated for now)
    authors = scitex_result.get("authors", [])
    if authors:
        # TODO: Create Author instances and link via AuthorPaper
        pass

    # Journal info - Create or get Journal instance
    journal_name = scitex_result.get("journal", "").strip()
    if journal_name:
        from ..models import Journal

        # Get or create journal by name
        journal, created = Journal.objects.get_or_create(
            name=journal_name,
            defaults={
                "impact_factor": scitex_result.get("impact_factor"),
                # Add other journal fields if available
            },
        )
        # Update impact factor if it's provided and different
        if scitex_result.get("impact_factor") is not None:
            if journal.impact_factor != scitex_result.get("impact_factor"):
                journal.impact_factor = scitex_result.get("impact_factor")
                journal.save()

        paper.journal = journal

    # Metrics
    paper.citation_count = scitex_result.get("citation_count", 0)
    paper.is_open_access = scitex_result.get("is_open_access", False)

    # URLs
    paper.pdf_url = scitex_result.get("pdf_url", "")
    paper.external_url = scitex_result.get("external_url", "")

    # Source tracking (required field)
    source_engines = scitex_result.get("source_engines", [])
    if source_engines:
        paper.source = source_engines[0]  # Use first engine as primary source
    else:
        paper.source = "scitex"  # Default source if none provided

    # Keywords
    keywords = scitex_result.get("keywords", [])
    if keywords:
        paper.keywords = ", ".join(keywords)

    # Set indexed timestamp
    paper.indexed_at = datetime.now()

    # Save to database
    paper.save()

    return paper



# EOF
