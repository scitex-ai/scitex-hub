"""Custom OAuth2 validator for SciTeX OIDC provider.

Returns user profile claims (username, email) for OpenID Connect tokens
used by external apps like orochi.scitex.ai.
"""

from oauth2_provider.oauth2_validators import OAuth2Validator


class SciTexOAuth2Validator(OAuth2Validator):
    """Extend default validator to include user claims in OIDC tokens."""

    oidc_claim_scope = OAuth2Validator.oidc_claim_scope
    oidc_claim_scope.update(
        {
            "username": "profile",
            "name": "profile",
            "email": "email",
            "email_verified": "email",
        }
    )

    def get_additional_claims(self, request):
        """Return OIDC claims based on granted scopes."""
        user = request.user
        claims = {}
        if "profile" in request.scopes:
            claims["username"] = user.username
            claims["name"] = user.get_full_name() or user.username
        if "email" in request.scopes:
            claims["email"] = user.email
            claims["email_verified"] = True
        return claims

    def get_userinfo_claims(self, request):
        """Return claims for the /oauth/userinfo/ endpoint."""
        claims = super().get_userinfo_claims(request)
        claims.update(self.get_additional_claims(request))
        claims["sub"] = str(request.user.id)
        return claims
