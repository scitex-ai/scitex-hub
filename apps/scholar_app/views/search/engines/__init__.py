"""Search engine integrations - modular organization"""

# Core search
from .core import search_papers_online, search_with_scitex_scholar

# arXiv
from .arxiv import search_arxiv_real, search_arxiv

# PubMed
from .pubmed import search_pubmed_fast, search_pubmed

# PubMed Central
from .pubmed_central import search_pubmed_central_fast, search_pubmed_central

# Open Access
from .openaccess import search_doaj, search_biorxiv, search_plos

# Semantic Scholar
from .semantic import search_semantic_scholar

__all__ = [
    "search_papers_online", "search_with_scitex_scholar",
    "search_arxiv_real", "search_arxiv",
    "search_pubmed_fast", "search_pubmed",
    "search_pubmed_central_fast", "search_pubmed_central",
    "search_doaj", "search_biorxiv", "search_plos",
    "search_semantic_scholar",
]
