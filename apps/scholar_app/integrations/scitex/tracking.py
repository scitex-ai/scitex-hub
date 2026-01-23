"""Search query tracking utilities."""

import logging
from typing import Dict
from ...models import SearchQuery

logger = logging.getLogger(__name__)

def track_search_query(
    request,
    query_text: str,
    search_type: str,
    result_count: int,
    execution_time: float,
    filters: Dict = None,
):
    """
    Track user search query in database for analytics.

    Args:
        request: Django HttpRequest
        query_text: The search query string
        search_type: Type of search performed
        result_count: Number of results returned
        execution_time: Time taken for search in seconds
        filters: Applied filters dictionary
    """
    if not request.user.is_authenticated:
        return

    try:
        SearchQuery.objects.create(
            user=request.user,
            query_text=query_text,
            search_type=search_type,
            filters=filters or {},
            result_count=result_count,
            execution_time=execution_time,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
    except Exception as e:
        logger.warning(f"Failed to track search query: {e}")


# EOF
