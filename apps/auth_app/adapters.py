"""
Custom adapters for django-allauth social authentication.

These adapters handle the integration between social login providers
(Google, ORCID) and SciTeX's user system.
"""

import re
import logging
from django.contrib.auth import get_user_model
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)
User = get_user_model()


class SciTexAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for SciTeX.
    Handles standard account operations with SciTeX-specific logic.
    """

    def save_user(self, request, user, form, commit=True):
        """
        Save user with additional SciTeX-specific fields.
        UserProfile is automatically created via signal in models.py.
        """
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()
        return user


class SciTexSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for SciTeX.
    Handles social login (Google, ORCID) with proper username generation
    and integration with SciTeX's user system.
    """

    def populate_user(self, request, sociallogin, data):
        """
        Populate user instance with data from social provider.
        Called when creating a new user from social login.
        """
        user = super().populate_user(request, sociallogin, data)

        # Extract provider-specific data
        provider = sociallogin.account.provider

        if provider == "google":
            # Google provides email, first_name, last_name
            user.email = data.get("email", "")
            user.first_name = data.get("first_name", "")
            user.last_name = data.get("last_name", "")

        elif provider == "orcid":
            # ORCID provides orcid, name, given_name, family_name
            user.first_name = data.get("given_name", "")
            user.last_name = data.get("family_name", "")
            # ORCID might not provide email
            user.email = data.get("email", "")

        # Generate unique username if not set
        if not user.username:
            user.username = self._generate_unique_username(user, data, provider)

        return user

    def _generate_unique_username(self, user, data, provider):
        """
        Generate a unique username from social account data.

        Priority:
        1. Use email prefix (before @)
        2. Use first_name + last_name
        3. Use provider + uid

        All usernames are sanitized and made unique.
        """
        # Try email-based username first
        email = data.get("email") or user.email
        if email and "@" in email:
            base_username = email.split("@")[0]
        elif user.first_name or user.last_name:
            # Combine name parts
            name_parts = [p for p in [user.first_name, user.last_name] if p]
            base_username = "_".join(name_parts).lower()
        else:
            # Fallback to provider + partial uid
            base_username = f"{provider}_user"

        # Sanitize: only alphanumeric and underscores, max 30 chars
        base_username = re.sub(r"[^a-zA-Z0-9_]", "_", base_username)
        base_username = re.sub(r"_+", "_", base_username)  # collapse multiple underscores
        base_username = base_username.strip("_")[:25]  # leave room for suffix

        if not base_username:
            base_username = "user"

        # Make unique
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            if counter > 1000:
                # Safety valve - use random suffix
                import uuid
                username = f"{base_username}_{uuid.uuid4().hex[:6]}"
                break

        return username.lower()

    def pre_social_login(self, request, sociallogin):
        """
        Called before social login completes.
        Used to connect social account to existing user with same email.
        """
        # If user is already logged in, connect the social account
        if request.user.is_authenticated:
            return

        # Try to find existing user with same email
        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                existing_user = User.objects.get(email__iexact=email)
                # Connect social account to existing user
                sociallogin.connect(request, existing_user)
                logger.info(
                    f"Connected {sociallogin.account.provider} account to existing user: {existing_user.username}"
                )
            except User.DoesNotExist:
                pass
            except User.MultipleObjectsReturned:
                # Multiple users with same email - don't auto-connect
                logger.warning(f"Multiple users found with email {email}, not auto-connecting")

    def save_user(self, request, sociallogin, form=None):
        """
        Save user from social login.
        UserProfile is automatically created via signal.
        """
        user = super().save_user(request, sociallogin, form)

        # Log successful social signup
        provider = sociallogin.account.provider
        logger.info(f"New user signed up via {provider}: {user.username} ({user.email})")

        return user

    def get_login_redirect_url(self, request):
        """
        Return the URL to redirect to after successful social login.
        """
        from django.conf import settings
        return getattr(settings, "LOGIN_REDIRECT_URL", "/")
