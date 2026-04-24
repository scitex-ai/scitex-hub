"""OAuth2 userinfo endpoint for external apps (e.g. orochi).

Returns the authenticated user's profile when called with a valid
OAuth2 Bearer token.
"""

from django.http import JsonResponse
from oauth2_provider.decorators import protected_resource


def _get_user_type(user):
    """Derive user type from username/email patterns."""
    if user.username.startswith("visitor-"):
        return "visitor"
    if user.email.endswith("@visitor.scitex.local"):
        return "visitor"
    if not user.email or user.email.endswith("@readonly.scitex.local"):
        return "readonly"
    return "member"


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
            "user_type": _get_user_type(user),
        }
    )
