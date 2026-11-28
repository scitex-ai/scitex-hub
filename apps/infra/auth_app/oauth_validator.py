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
            from .email_addresses import is_verified

            claims["email"] = user.email
            claims["email_verified"] = is_verified(user)
        return claims

    def is_pkce_required(self, client_id, request):
        """PKCE for every client, except confidential clients still migrating.

        Public clients cannot keep a secret, so PKCE is their only proof that
        the code they redeem is theirs; they are never exempt. A confidential
        client may be listed in ``OAUTH_PKCE_EXEMPT_CLIENT_IDS`` while it is
        updated to send a code_challenge.
        """
        from django.conf import settings
        from oauth2_provider.models import get_application_model

        exempt = getattr(settings, "OAUTH_PKCE_EXEMPT_CLIENT_IDS", frozenset())
        if client_id not in exempt:
            return True
        application = (
            get_application_model().objects.filter(client_id=client_id).first()
        )
        return application is None or application.client_type != "confidential"

    def get_userinfo_claims(self, request):
        """Return claims for the /oauth/userinfo/ endpoint."""
        claims = super().get_userinfo_claims(request)
        claims.update(self.get_additional_claims(request))
        claims["sub"] = str(request.user.id)
        return claims
