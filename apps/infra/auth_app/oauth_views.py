"""OAuth2 userinfo endpoint for external apps (e.g. orochi).

Returns the authenticated user's profile when called with a valid
OAuth2 Bearer token.
"""

from django.http import JsonResponse
from oauth2_provider.decorators import protected_resource


@protected_resource(scopes=["profile", "email"])
def userinfo(request):
    """GET /oauth/userinfo/ — return user profile for OAuth2 token."""
    user = request.resource_owner
    return JsonResponse(
        {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "name": user.get_full_name() or user.username,
            "email_verified": True,
        }
    )
