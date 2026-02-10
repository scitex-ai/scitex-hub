"""
Citation Graph API Endpoints

Provides REST API for building and analyzing citation networks.
"""

import logging
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle

from ..services.citation_graph import get_citation_graph_service

logger = logging.getLogger(__name__)


class CitationGraphThrottle(AnonRateThrottle):
    """Rate limit for citation graph API: 50 requests per hour (computation intensive)"""
    rate = '50/hour'


class HealthCheckThrottle(AnonRateThrottle):
    """Rate limit for health checks: 10 requests per minute (prevents flood attacks)"""
    rate = '10/minute'


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([CitationGraphThrottle])
def build_network(request):
    """
    Build citation network graph for a paper.

    GET /api/scholar/citation-graph/network/

    Query params:
        - doi (required): DOI of the seed paper
        - top_n (optional): Number of similar papers to include (default: 20, max: 50)
        - weight_coupling (optional): Weight for bibliographic coupling (default: 2.0)
        - weight_cocitation (optional): Weight for co-citation (default: 2.0)
        - weight_direct (optional): Weight for direct citations (default: 1.0)
        - no_cache (optional): Skip cache and rebuild (default: false)

    Returns:
        JSON with network graph:
        {
            "seed": "10.1038/...",
            "nodes": [...],
            "edges": [...],
            "metadata": {
                "top_n": 20,
                "weights": {...},
                "cached": false
            }
        }

    Example:
        curl "https://scitex.ai/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=20"
    """
    # Validate DOI
    doi = request.GET.get('doi')
    if not doi:
        return Response(
            {'error': 'DOI parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parse parameters
    try:
        top_n = int(request.GET.get('top_n', 20))
        if top_n < 1 or top_n > 50:
            return Response(
                {'error': 'top_n must be between 1 and 50'},
                status=status.HTTP_400_BAD_REQUEST
            )

        weight_coupling = float(request.GET.get('weight_coupling', 2.0))
        weight_cocitation = float(request.GET.get('weight_cocitation', 2.0))
        weight_direct = float(request.GET.get('weight_direct', 1.0))

        use_cache = request.GET.get('no_cache', 'false').lower() != 'true'

    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Build network
    try:
        service = get_citation_graph_service()
        network = service.build_network(
            doi=doi,
            top_n=top_n,
            weight_coupling=weight_coupling,
            weight_cocitation=weight_cocitation,
            weight_direct=weight_direct,
            use_cache=use_cache
        )

        return Response(network, status=status.HTTP_200_OK)

    except FileNotFoundError as e:
        logger.error(f"Database not found: {e}")
        return Response(
            {'error': 'Citation graph service unavailable - database not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Error building citation network for {doi}: {e}", exc_info=True)
        return Response(
            {'error': f'Failed to build citation network: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([CitationGraphThrottle])
def get_related_papers(request):
    """
    Get list of papers related to a given paper (lightweight endpoint).

    GET /api/scholar/citation-graph/related/

    Query params:
        - doi (required): DOI of the paper
        - limit (optional): Number of papers to return (default: 10, max: 30)
        - no_cache (optional): Skip cache (default: false)

    Returns:
        JSON with list of related papers sorted by similarity:
        {
            "doi": "10.1038/...",
            "related": [
                {
                    "id": "10.1016/...",
                    "title": "...",
                    "year": 2020,
                    "authors": [...],
                    "similarity_score": 42.5
                },
                ...
            ]
        }

    Example:
        curl "https://scitex.ai/api/scholar/citation-graph/related/?doi=10.1038/s41586-020-2008-3&limit=10"
    """
    # Validate DOI
    doi = request.GET.get('doi')
    if not doi:
        return Response(
            {'error': 'DOI parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parse parameters
    try:
        limit = int(request.GET.get('limit', 10))
        if limit < 1 or limit > 30:
            return Response(
                {'error': 'limit must be between 1 and 30'},
                status=status.HTTP_400_BAD_REQUEST
            )

        use_cache = request.GET.get('no_cache', 'false').lower() != 'true'

    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get related papers
    try:
        service = get_citation_graph_service()
        related = service.get_related_papers(
            doi=doi,
            limit=limit,
            use_cache=use_cache
        )

        return Response(
            {
                'doi': doi,
                'related': related,
                'count': len(related)
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error getting related papers for {doi}: {e}", exc_info=True)
        return Response(
            {'error': f'Failed to get related papers: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def paper_summary(request):
    """
    Get summary information for a paper (no rate limiting - simple lookup).

    GET /api/scholar/citation-graph/paper/

    Query params:
        - doi (required): DOI of the paper

    Returns:
        JSON with paper summary:
        {
            "doi": "10.1038/...",
            "title": "...",
            "year": 2020,
            "authors": [...],
            "journal": "Nature",
            "reference_count": 45,
            "citation_count": 123
        }

    Example:
        curl "https://scitex.ai/api/scholar/citation-graph/paper/?doi=10.1038/s41586-020-2008-3"
    """
    # Validate DOI
    doi = request.GET.get('doi')
    if not doi:
        return Response(
            {'error': 'DOI parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get summary
    try:
        service = get_citation_graph_service()
        summary = service.get_paper_summary(doi)

        if summary:
            return Response(summary, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Paper not found in database'},
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logger.error(f"Error getting paper summary for {doi}: {e}", exc_info=True)
        return Response(
            {'error': f'Failed to get paper summary: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([HealthCheckThrottle])
def health(request):
    """
    Health check for citation graph service.

    Rate limited to 10 requests/minute to prevent flood attacks.

    GET /api/scholar/citation-graph/health/

    Returns:
        JSON with service health status

    Example:
        curl "https://scitex.ai/api/scholar/citation-graph/health/"
    """
    try:
        service = get_citation_graph_service()
        health_status = service.health_check()
        return Response(health_status, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e)
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
