"""
User API Views

RESTful API endpoints for user-related operations.
"""

from django.contrib.auth.models import User
from django.http import JsonResponse


def api_search_users(request):
    """
    API endpoint to search for users by username.
    Used for collaborator autocomplete.

    Query params:
        q: Search query (username or email)

    Returns:
        JSON response with matching users
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"users": []})

    # Search by username (case-insensitive, contains)
    users = User.objects.filter(username__icontains=query)[:10]  # Limit to 10 results

    users_data = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email if u.email else None,
            "full_name": u.get_full_name() or u.username,
        }
        for u in users
    ]

    return JsonResponse({"users": users_data})
