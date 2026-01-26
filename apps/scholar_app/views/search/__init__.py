"""search feature views"""

# Import main views
from .citations import (
    get_impact_factor_instance,
    get_journal_impact_factor,
    get_pubmed_citations,
    is_open_access_journal,
    validate_citation_count,
)

# Import modular views (refactored from monolithic views.py)
from .page_views import (
    bibtex_enrichment_view,
    features,
    index,
    literature_search_view,
    personal_library,
    pricing,
    scholar_bibtex,
    scholar_graph,
    scholar_search,
)
from .pdf_download import (
    api_check_pdf_status,
    api_download_pdf,
    api_download_pdf_bulk,
    api_serve_pdf,
)
from .preferences import (
    get_user_preferences,
    save_source_preferences,
    save_user_preferences,
)
from .recommendations import (
    paper_recommendations,
    user_recommendations,
)
from .views import *

# Make all imports available at package level
__all__ = [
    # Page views
    "index",
    "scholar_bibtex",
    "scholar_search",
    "scholar_graph",
    "bibtex_enrichment_view",
    "literature_search_view",
    "features",
    "pricing",
    "personal_library",
    # Preferences
    "get_user_preferences",
    "save_user_preferences",
    "save_source_preferences",
    # Citations
    "get_impact_factor_instance",
    "get_journal_impact_factor",
    "is_open_access_journal",
    "get_pubmed_citations",
    "validate_citation_count",
    # Recommendations
    "paper_recommendations",
    "user_recommendations",
    # PDF Download
    "api_download_pdf",
    "api_check_pdf_status",
    "api_download_pdf_bulk",
    "api_serve_pdf",
]
