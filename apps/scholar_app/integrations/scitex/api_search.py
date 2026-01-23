"""API endpoint for parallel SciTeX search."""

import asyncio
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .pipelines import get_parallel_pipeline, SCITEX_AVAILABLE
from .filters import django_to_scitex_filters
from .converters import scitex_to_django_paper
from .tracking import track_search_query

logger = logging.getLogger(__name__)

def api_scitex_search(request):
    """
    API endpoint for SciTeX-powered paper search (parallel pipeline).

    Query Parameters:
        q: Search query string (required)
        search_fields: Comma-separated fields to search (title,abstract,keywords)
        year_start: Start year filter
        year_end: End year filter
        open_access: Filter for open access papers (true/false)
        author: Filter by author name
        journal: Filter by journal name
        max_results: Maximum number of results (default: 100)

    Returns:
        JSON response with search results and metadata
    """
    import time

    start_time = time.time()

    # Check if SciTeX is available
    if not SCITEX_AVAILABLE:
        return JsonResponse(
            {
                "error": "SciTeX search engine not available",
                "detail": SCITEX_IMPORT_ERROR,
                "results": [],
            },
            status=503,
        )

    # Get query parameter
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse(
            {"error": 'Query parameter "q" is required', "results": []}, status=400
        )

    # Get search fields
    search_fields_param = request.GET.get("search_fields", "title,abstract")
    search_fields = [f.strip() for f in search_fields_param.split(",")]

    # Get filters
    filters = django_to_scitex_filters(request)

    # Get max results
    try:
        max_results = int(request.GET.get("max_results", 100))
        max_results = min(max_results, 1000)  # Cap at 1000
    except ValueError:
        max_results = 100

    # Get pipeline
    pipeline = get_parallel_pipeline()
    if not pipeline:
        return JsonResponse(
            {"error": "Failed to initialize search pipeline", "results": []}, status=500
        )

    # Execute search
    try:
        logger.info(
            f"SciTeX search: query='{query[:50]}...', fields={search_fields}, filters={filters}"
        )

        # Run async search in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            scitex_result = loop.run_until_complete(
                pipeline.search_async(
                    query=query,
                    search_fields=search_fields,
                    filters=filters,
                    max_results=max_results,
                )
            )
        finally:
            loop.close()

        # Convert results to Django format
        django_results = []

        for scitex_paper in scitex_result.get("results", []):
            # Store in database
            try:
                django_paper = scitex_to_django_paper(
                    scitex_paper,
                    request.user if request.user.is_authenticated else None,
                )

                # Format for API response
                django_results.append(
                    {
                        "id": str(django_paper.id),
                        "title": scitex_paper.get("title", ""),
                        "authors": scitex_paper.get("authors", []),
                        "year": scitex_paper.get("year"),
                        "abstract": scitex_paper.get("abstract", ""),
                        "journal": scitex_paper.get("journal", ""),
                        "impact_factor": scitex_paper.get("impact_factor"),
                        "doi": scitex_paper.get("doi", ""),
                        "pmid": scitex_paper.get("pmid", ""),
                        "arxiv_id": scitex_paper.get("arxiv_id", ""),
                        "citation_count": scitex_paper.get("citation_count", 0),
                        "is_open_access": scitex_paper.get("is_open_access", False),
                        "pdf_url": scitex_paper.get("pdf_url", ""),
                        "external_url": scitex_paper.get("external_url", ""),
                        "source_engines": scitex_paper.get("source_engines", []),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to convert SciTeX result to Django model: {e}")
                # Still include in results even if DB save fails
                django_results.append(
                    {
                        "title": scitex_paper.get("title", ""),
                        "authors": scitex_paper.get("authors", []),
                        "year": scitex_paper.get("year"),
                        "error": "Failed to save to database",
                    }
                )

        # Track search query
        execution_time = time.time() - start_time
        track_search_query(
            request,
            query_text=query,
            search_type="scitex_parallel",
            result_count=len(django_results),
            execution_time=execution_time,
            filters=filters,
        )

        # Return response
        response_data = {
            "query": query,
            "search_fields": search_fields,
            "filters": filters,
            "results": django_results,
            "metadata": {
                **scitex_result.get("metadata", {}),
                "search_time": execution_time,
                "django_stored": len(django_results),
            },
            "stats": pipeline.get_statistics(),
        }

        logger.info(
            f"SciTeX search completed: {len(django_results)} results in {execution_time:.2f}s"
        )

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"SciTeX search failed: {e}", exc_info=True)
        return JsonResponse(
            {"error": "Search failed", "detail": str(e), "results": []}, status=500
        )


# EOF
