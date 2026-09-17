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

    def get_signup_redirect_url(self, request):
        """
        Where a COMPLETED SIGNUP goes next — the same step the email path goes to.

        THE GAP THIS CLOSES (measured through allauth's own flow, not read off
        the source): the email path is OTP-first, and once the code verifies the
        address the verification endpoint publishes the next step with
        ``post_signup_redirect_url(user)``. The social path published nothing of
        the sort — a brand-new Google/ORCID signup fell through to
        ``ACCOUNT_SIGNUP_REDIRECT_URL`` ("/") and was dropped into the product,
        past the card/trial step its account is subject to ever since
        card-required onboarding landed.

        WHY THIS METHOD AND NOT THE SOCIAL ADAPTER'S. allauth 65 calls
        ``get_signup_redirect_url`` on the ACCOUNT adapter (from ``post_login``,
        via ``account.utils.get_login_redirect_url``) with ``signup=True``; the
        ``get_login_redirect_url`` that used to sit on ``SciTexSocialAccountAdapter``
        was never called by allauth at all, so the social redirect was governed
        by a default nobody had chosen. Only SIGNUP is redirected here: an
        existing account signing in takes the ``signup=False`` branch and keeps
        the ordinary login target.

        WHY IT CALLS THE FUNCTION RATHER THAN THE URL. One source, two callers —
        the email publisher and this hook. Repeating the route here would let
        the two drift the moment the funnel target moves (it is moving right now:
        PR #934 takes it from the billing page to a dedicated payment step), and
        the drift would be silent. Tests assert equality with that function, not
        with a literal.
        """
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            from apps.infra.public_app.services.billing_provider import (
                post_signup_redirect_url,
            )

            return post_signup_redirect_url(user)
        return super().get_signup_redirect_url(request)


class SciTexSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for SciTeX.
    Handles social login (Google, ORCID) with proper username generation
    and integration with SciTeX's user system.
    """

    def list_apps(self, request, provider=None, client_id=None):
        """
        The apps allauth may serve, with SETTINGS AUTHORITATIVE over leftover rows.

        ``DefaultSocialAccountAdapter.list_apps`` blends database ``SocialApp``
        rows with the apps declared in ``SOCIALACCOUNT_PROVIDERS[provider]["APP"]``
        (which this deployment now builds from its credential settings). The two
        sources COLLIDE for any operator who ever ran ``manage.py
        setup_social_auth``: that command writes a row for the same credentials
        the settings now declare. ``get_app`` refuses when more than one app is
        visible for a provider (``MultipleObjectsReturned``), and the login view
        turns that into an HTTP 500 — so the button the pages just started
        offering would be the broken one, which is the exact defect
        ``test_social_login_buttons.py`` exists to prevent.

        So: for a provider the settings declare an app for, the settings win and
        the database row is an artefact rather than a rival. Providers the
        settings declare nothing for keep their database rows untouched, so a
        deployment configured ONLY through the database (the previous path) is
        unaffected. A settings-built app is an unsaved ``SocialApp``
        (``pk is None``) — that is the marker used here, and it is the same
        object the provider is handed.
        """
        apps = super().list_apps(request, provider=provider, client_id=client_id)
        from_settings = {app.provider for app in apps if app.pk is None}
        if not from_settings:
            return apps
        return [app for app in apps if app.pk is None or app.provider not in from_settings]

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
        base_username = re.sub(
            r"_+", "_", base_username
        )  # collapse multiple underscores
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
        Auto-connect this social account to an existing user with the same
        address — but ONLY when the provider VERIFIED that address.

        SECURITY (this is the whole reason the method is not two lines).
        Auto-connecting on a bare address match is account takeover: the
        address in a provider payload is only a claim, and a provider willing
        to assert an address it never checked lets its holder sign straight
        into the existing SciTeX account that uses it. The previous version
        read ``extra_data["email"]`` and connected on ``email__iexact`` with
        no verification check at all, which is exactly that hole — and it is
        reachable by anyone on the public site.

        So the gate is the provider's own verification claim, read through
        the three-valued verdict in
        :mod:`apps.infra.auth_app.account_linking.verification`. Anything but
        ``verified`` declines to connect and lets allauth take its normal
        path (which asks the user to prove the address instead of assuming
        it). Fail-closed: "cannot tell" never connects.
        """
        # If user is already logged in, connect the social account
        if request.user.is_authenticated:
            return

        from apps.infra.auth_app.account_linking.verification import (
            verified_email_of,
        )

        verdict = verified_email_of(sociallogin)
        if not verdict.is_account_key:
            if verdict.email:
                logger.warning(
                    "Refusing to auto-connect %s account to an existing user "
                    "on address %s: provider verification is %r (source=%s). "
                    "Auto-connecting an unverified address would be account "
                    "takeover; the user must verify it instead.",
                    sociallogin.account.provider,
                    verdict.email,
                    verdict.status,
                    verdict.source,
                )
            return

        email = verdict.email
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return
        except User.MultipleObjectsReturned:
            # Multiple users with same email - don't auto-connect
            logger.warning(
                f"Multiple users found with email {email}, not auto-connecting"
            )
            return

        sociallogin.connect(request, existing_user)
        logger.info(
            "Connected %s account to existing user %s on a provider-VERIFIED "
            "address",
            sociallogin.account.provider,
            existing_user.username,
        )

    def save_user(self, request, sociallogin, form=None):
        """
        Save user from social login.
        UserProfile is automatically created via signal.
        """
        user = super().save_user(request, sociallogin, form)

        # Log successful social signup
        provider = sociallogin.account.provider
        logger.info(
            f"New user signed up via {provider}: {user.username} ({user.email})"
        )

        return user

    # get_login_redirect_url USED TO LIVE HERE, and nothing called it.
    #
    # It returned ``LOGIN_REDIRECT_URL`` and read as the social-redirect policy.
    # It was not one: ``get_login_redirect_url`` is an ACCOUNT-adapter hook, and
    # allauth 65 reaches it through ``account.utils.get_login_redirect_url``
    # (which asks ``allauth.account.adapter.get_adapter()``). The social adapter's
    # copy on this class had no call site, so the social redirect was decided
    # entirely by a default nobody had chosen — which is why a brand-new
    # Google/ORCID signup landed on "/" while the email path published the
    # payment step.
    #
    # The behaviour now lives where allauth actually looks:
    # ``SciTexAccountAdapter.get_signup_redirect_url`` (a NEW signup converges on
    # the funnel step) and the untouched account ``get_login_redirect_url``
    # (existing-account logins keep the ordinary target). Left as a note rather
    # than silently dropped, because the next person looking for "the social
    # redirect" will look for this name.

