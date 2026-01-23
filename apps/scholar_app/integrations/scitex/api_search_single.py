"""API endpoint for single-source SciTeX search."""

import asyncio
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .pipelines import get_single_pipeline, SCITEX_AVAILABLE
from .filters import django_to_scitex_filters
from .converters import scitex_to_django_paper
from .tracking import track_search_query

logger = logging.getLogger(__name__)

def api_scitex_search_single(request):
    """
    API endpoint for SciTeX-powered paper search (single/sequential pipeline).

    Same parameters as api_scitex_search but uses sequential engine querying.
    Better for rate-limited scenarios or when you want predictable behavior.
    """
    import time

    start_time = time.time()

    if not SCITEX_AVAILABLE:
        return JsonResponse(
            {"error": "SciTeX search engine not available", "results": []}, status=503
        )

    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse(
            {"error": 'Query parameter "q" is required', "results": []}, status=400
        )

    # Get filters
    filters = django_to_scitex_filters(request)

    # Get max results
    try:
        max_results = int(request.GET.get("max_results", 100))
        max_results = min(max_results, 1000)  # Cap at 1000
    except ValueError:
        max_results = 100

    pipeline = get_single_pipeline()
    if not pipeline:
        return JsonResponse(
            {"error": "Failed to initialize search pipeline", "results": []}, status=500
        )

    try:
        logger.info(
            f"SciTeX single search: query='{query[:50]}...', filters={filters}, max_results={max_results}"
        )

        # Run async search
        # Note: ScholarPipelineSearchSingle does not accept search_fields parameter
        # It searches across all fields by default
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            scitex_result = loop.run_until_complete(
                pipeline.search_async(
                    query=query, filters=filters, max_results=max_results
                )
            )
        finally:
            loop.close()

        # Convert to Django format
        django_results = []
        for scitex_paper in scitex_result.get("results", []):
            try:
                django_paper = scitex_to_django_paper(
                    scitex_paper,
                    request.user if request.user.is_authenticated else None,
                )
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
                logger.error(f"Failed to process result: {e}")

        execution_time = time.time() - start_time

        # Track search query
        track_search_query(
            request,
            query_text=query,
            search_type="scitex_single",
            result_count=len(django_results),
            execution_time=execution_time,
            filters=filters,
        )

        logger.info(
            f"SciTeX single search completed: {len(django_results)} results in {execution_time:.2f}s"
        )

        return JsonResponse(
            {
                "query": query,
                "filters": filters,
                "results": django_results,
                "metadata": {
                    **scitex_result.get("metadata", {}),
                    "search_time": execution_time,
                    "django_stored": len(django_results),
                    "note": "Single mode searches across all fields by default",
                },
                "stats": pipeline.get_statistics(),
            }
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return JsonResponse({"error": str(e), "results": []}, status=500)


# EOF
