"""
Public API proxy for CrossRef Local database
Provides external access with authentication and rate limiting
"""

import requests
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
import hashlib
import time


class CrossRefAPIThrottle(AnonRateThrottle):
    """Rate limit for CrossRef API: 100 requests per hour"""
    rate = '100/hour'


def get_crossref_url():
    """Get internal CrossRef service URL"""
    return getattr(settings, 'CROSSREF_INTERNAL_URL', 'http://crossref:3333')


def create_cache_key(endpoint, params):
    """Create cache key from endpoint and params"""
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    key_str = f"crossref:{endpoint}:{param_str}"
    return hashlib.md5(key_str.encode()).hexdigest()


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([CrossRefAPIThrottle])
def search(request):
    """
    Search CrossRef database
    
    GET /api/scholar/crossref/search/
    Query params: doi, title, year, authors, limit
    
    Example:
        curl "https://scitex.ai/api/scholar/crossref/search/?doi=10.1038/nature12373"
    """
    # Get query parameters
    params = {
        'doi': request.GET.get('doi'),
        'title': request.GET.get('title'),
        'year': request.GET.get('year'),
        'authors': request.GET.get('authors'),
        'limit': request.GET.get('limit', 10),
    }
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    if not params:
        return Response(
            {'error': 'At least one search parameter required (doi, title, year, or authors)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check cache
    cache_key = create_cache_key('search', params)
    cached_data = cache.get(cache_key)
    if cached_data:
        cached_data['cached'] = True
        return Response(cached_data)
    
    # Proxy to internal CrossRef service
    try:
        url = f"{get_crossref_url()}/api/search/"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Cache for 1 hour
        cache.set(cache_key, data, 3600)
        
        data['cached'] = False
        return Response(data)
        
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'Internal service error: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([CrossRefAPIThrottle])
def citations(request):
    """
    Get citation graph for a paper
    
    GET /api/scholar/crossref/citations/
    Query params: doi, depth (default: 2)
    
    Example:
        curl "https://scitex.ai/api/scholar/crossref/citations/?doi=10.1038/nature12373&depth=2"
    """
    doi = request.GET.get('doi')
    if not doi:
        return Response(
            {'error': 'DOI parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    depth = int(request.GET.get('depth', 2))
    if depth > 3:
        return Response(
            {'error': 'Maximum depth is 3'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    params = {'doi': doi, 'depth': depth}
    
    # Check cache
    cache_key = create_cache_key('citations', params)
    cached_data = cache.get(cache_key)
    if cached_data:
        cached_data['cached'] = True
        return Response(cached_data)
    
    # Proxy to internal CrossRef service
    try:
        url = f"{get_crossref_url()}/api/citations/"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Cache for 1 hour
        cache.set(cache_key, data, 3600)
        
        data['cached'] = False
        return Response(data)
        
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'Internal service error: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """
    Health check endpoint (no rate limiting)
    
    GET /api/scholar/crossref/health/
    
    Example:
        curl "https://scitex.ai/api/scholar/crossref/health/"
    """
    try:
        url = f"{get_crossref_url()}/health"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        data['public_api'] = 'healthy'
        return Response(data)
        
    except requests.exceptions.RequestException as e:
        return Response(
            {
                'public_api': 'unhealthy',
                'error': str(e)
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def stats(request):
    """
    Get database statistics (no rate limiting)
    
    GET /api/scholar/crossref/stats/
    
    Example:
        curl "https://scitex.ai/api/scholar/crossref/stats/"
    """
    try:
        url = f"{get_crossref_url()}/api/stats/"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        return Response(response.json())
        
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'Internal service error: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
