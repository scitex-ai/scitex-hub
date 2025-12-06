"""search feature views"""

# Import main views
from .views import *

# Import modular views (refactored from monolithic views.py)
from .page_views import (
    index,
    scholar_bibtex,
    scholar_search,
    scholar_graph,
    bibtex_enrichment_view,
    literature_search_view,
    features,
    pricing,
    personal_library,
)

from .preferences import (
    get_user_preferences,
    save_user_preferences,
    save_source_preferences,
)

from .citations import (
    get_impact_factor_instance,
    get_journal_impact_factor,
    is_open_access_journal,
    get_pubmed_citations,
    validate_citation_count,
)

from .recommendations import (
    paper_recommendations,
    user_recommendations,
)

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
]
