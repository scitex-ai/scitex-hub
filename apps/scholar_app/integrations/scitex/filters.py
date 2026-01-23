"""Django to SciTeX filter conversion."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

def django_to_scitex_filters(request) -> Dict:
    """
    Convert Django request parameters to SciTeX filter format.

    Args:
        request: Django HttpRequest object

    Returns:
        Dictionary of filters compatible with SciTeX pipelines
    """
    filters = {}

    # Year range
    year_start = request.GET.get("year_from") or request.GET.get("year_start")
    year_end = request.GET.get("year_to") or request.GET.get("year_end")

    if year_start:
        try:
            filters["year_start"] = int(year_start)
        except ValueError:
            pass

    if year_end:
        try:
            filters["year_end"] = int(year_end)
        except ValueError:
            pass

    # Open access
    open_access = request.GET.get("open_access")
    if open_access and open_access.lower() in ["true", "1", "yes"]:
        filters["open_access"] = True

    # Document type
    doc_type = request.GET.get("document_type") or request.GET.get("type")
    if doc_type:
        filters["document_type"] = doc_type

    # Author
    author = request.GET.get("author", "").strip()
    if author:
        filters["author"] = author

    # Journal
    journal = request.GET.get("journal", "").strip()
    if journal:
        filters["journal"] = journal

    # DOI
    doi = request.GET.get("doi", "").strip()
    if doi:
        filters["doi"] = doi

    # PMID
    pmid = request.GET.get("pmid", "").strip()
    if pmid:
        filters["pmid"] = pmid

    # Sorting
    sort_by = request.GET.get("sort_by", "").strip()
    if sort_by:
        filters["sort_by"] = sort_by

    sort_order = request.GET.get("sort_order", "desc").strip()
    if sort_order in ["asc", "desc"]:
        filters["sort_order"] = sort_order

    # Threshold filters
    min_year = request.GET.get("min_year", "").strip()
    if min_year:
        try:
            filters["min_year"] = int(min_year)
        except ValueError:
            pass

    max_year = request.GET.get("max_year", "").strip()
    if max_year:
        try:
            filters["max_year"] = int(max_year)
        except ValueError:
            pass

    min_citations = request.GET.get("min_citations", "").strip()
    if min_citations:
        try:
            filters["min_citations"] = int(min_citations)
        except ValueError:
            pass

    min_impact_factor = request.GET.get("min_impact_factor", "").strip()
    if min_impact_factor:
        try:
            filters["min_impact_factor"] = float(min_impact_factor)
        except ValueError:
            pass

    return filters



# EOF
