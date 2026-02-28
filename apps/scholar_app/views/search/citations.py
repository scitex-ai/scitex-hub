#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/scholar_app/views/search/citations.py
"""
Scholar App - Citations Module

Functions for journal impact factors, citations, and open access checking.
Extracted from monolithic views.py for better modularity.
"""

import threading

from scitex import logging

# Set up logger
logger = logging.getLogger(__name__)

# Thread-local storage for impact factor instance (SQLite is not thread-safe)
_local = threading.local()


def get_impact_factor_instance():
    """Get or create a thread-local impact factor instance.

    Each thread gets its own Factor() instance to avoid SQLite threading errors.
    The impact_factor package uses SQLite internally, and SQLite connections
    cannot be shared across threads safely in async environments like Daphne.
    """
    if not hasattr(_local, 'impact_factor_instance'):
        try:
            from impact_factor.core import Factor

            _local.impact_factor_instance = Factor()
        except ImportError:
            print(
                "Warning: impact_factor package not available. Using fallback method."
            )
            _local.impact_factor_instance = False
        except Exception as e:
            print(f"Warning: Failed to initialize impact_factor: {e}")
            _local.impact_factor_instance = False
    return _local.impact_factor_instance


def get_journal_impact_factor(journal_name):
    """Get impact factor using the impact_factor package with fallback."""
    if not journal_name:
        return None

    fa = get_impact_factor_instance()

    # Use impact_factor package if available
    if fa:
        try:
            # Clean journal name
            journal_clean = journal_name.strip()

            # Try exact match first
            results = fa.search(journal_clean)
            if results and len(results) > 0:
                impact_factor = results[0].get(
                    "factor"
                )  # The field is 'factor' not 'impact_factor'
                if impact_factor and impact_factor != "-" and impact_factor != 0:
                    return float(impact_factor)

            # Try fuzzy match with wildcard
            if len(journal_clean) > 3:  # Avoid very short searches
                fuzzy_results = fa.search(f"{journal_clean}%")
                if fuzzy_results and len(fuzzy_results) > 0:
                    impact_factor = fuzzy_results[0].get(
                        "factor"
                    )  # The field is 'factor' not 'impact_factor'
                    if impact_factor and impact_factor != "-" and impact_factor != 0:
                        return float(impact_factor)

        except Exception as e:
            print(f"Error getting IF for {journal_name}: {e}")

    # Fallback to hardcoded values for most common journals
    fallback_if_map = {
        "nature": 64.8,
        "science": 56.9,
        "cell": 66.8,
        "new england journal of medicine": 176.1,
        "lancet": 168.9,
        "plos one": 3.7,
        "nature communications": 16.6,
        "scientific reports": 4.9,
        "proceedings of the national academy of sciences": 12.8,
        "pnas": 12.8,
    }

    journal_lower = journal_name.lower()
    for journal_key, if_value in fallback_if_map.items():
        if journal_key in journal_lower:
            return if_value

    return None


def is_open_access_journal(journal_name):
    """Check if journal is typically open access.

    Uses scitex.scholar.core.open_access for consistent OA detection.
    """
    try:
        from scitex.scholar.core import is_open_access_journal as scitex_is_oa_journal
        return scitex_is_oa_journal(journal_name)
    except ImportError:
        # Fallback if scitex not available
        open_access_journals = [
            "plos one",
            "plos biology",
            "plos medicine",
            "plos genetics",
            "elife",
            "scientific reports",
            "nature communications",
            "frontiers in",
            "bmc",
            "journal of medical internet research",
            "nucleic acids research",
            "bioinformatics",
            "genome biology",
        ]
        journal_lower = journal_name.lower()
        return any(oa_journal in journal_lower for oa_journal in open_access_journals)


def get_pubmed_citations(pmid):
    """
    Try to get citation count for PubMed article.
    Note: PubMed API doesn't provide citation counts directly.
    Returns 0 until proper citation service integration is implemented.
    """
    # TODO: Integrate with CrossRef, OpenCitations, or Semantic Scholar API
    # for accurate citation counts based on DOI/PMID
    return 0


def validate_citation_count(citation_count, source=None):
    """
    Validate and clean citation count data.
    Returns (validated_count, is_reliable) tuple.
    """
    try:
        count = int(citation_count) if citation_count is not None else 0

        # Basic validation
        if count < 0:
            return 0, False

        # Flag potentially unreliable data
        is_reliable = True

        # Very high citation counts need verification
        if count > 10000:
            logger.warning(f"Unusually high citation count: {count} from {source}")
            is_reliable = False

        # Mark zero citations from certain sources as less reliable
        if count == 0 and source in ["pubmed", "arxiv"]:
            is_reliable = False

        return count, is_reliable

    except (ValueError, TypeError):
        return 0, False
