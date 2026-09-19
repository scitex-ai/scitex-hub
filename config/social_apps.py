#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which social providers this deployment can ACTUALLY serve, from its credentials.

THE INVARIANT THIS MODULE EXISTS TO KEEP. ``allauth`` can build a provider's app
from two places: ``SocialApp`` database rows, and
``settings.SOCIALACCOUNT_PROVIDERS[provider]["APP"]``. What must never happen is
the third state — a provider that is half-configured, so that a visitor gets a
button and then an error. That exact failure shipped once: ``signin.html``
hardcoded Google/ORCID anchors onto a deployment with no usable app, and both
returned HTTP 500 to anonymous visitors two clicks from the landing page
(guarded by tests/apps/auth_app/test_social_login_buttons.py).

WHY THE CREDENTIALS LAND HERE AND NOT ONLY IN THE DATABASE. This deployment
receives its Google and ORCID credentials as environment variables
(``SCITEX_HUB_GOOGLE_CLIENT_ID``/``_SECRET``, ``SCITEX_HUB_ORCID_CLIENT_ID``/
``_SECRET``). They used to reach allauth only through ``manage.py
setup_social_auth``, which copies them into database rows — so a deployment that
HAD complete credentials still rendered no button and could not complete a
social login, until an operator remembered to run a command whose output is
invisible from the settings. Wiring them into the provider configuration makes
the deployment's declared credentials the thing that decides, and one code path
(``with_credential_apps``) decides it for the button exactly as for the login.

WHY "COMPLETE" IS THE TEST, RATHER THAN "PRESENT". A client id with no secret
builds a perfectly usable-looking app object; allauth hands it to the provider
happily and the failure lands later, at the token exchange, as an HTTP 500 on a
page that promised a working login. So the pair must be complete, and both
halves must look like credentials rather than like the placeholder a
``.env.example`` ships — a stub that reaches allauth is the same defect wearing
a different hat.

SECRETS ARE NOT RENDERED. Nothing here reads a template or a page; the app
config goes to allauth, which uses it server-side. The pages assert the secret's
absence separately (``test_social_provider_credentials.py``), because "we do not
template it" is a claim about code that can change.
"""

from __future__ import annotations

from typing import Iterable, Mapping

__all__ = [
    "ORCID_ALLOWED_BASE_DOMAINS",
    "PROVIDER_APP_NAMES",
    "STUB_MARKERS",
    "credential_is_complete",
    "orcid_base_domain",
    "with_credential_apps",
]

#: The only two hosts ORCID operates. An EXACT allowlist, not a pattern: the
#: value decides where the OAuth2 token exchange POSTs the client id AND the
#: client SECRET, so "looks like a hostname" is not a good enough test —
#: ``attacker.invalid`` is a hostname too.
ORCID_ALLOWED_BASE_DOMAINS = ("orcid.org", "sandbox.orcid.org")


def orcid_base_domain(value, *, default="sandbox.orcid.org") -> str:
    """The ORCID host this deployment may talk to — allowlisted, fail closed.

    WHY THIS EXISTS. ``ORCID_BASE_DOMAIN`` used to be passed straight from the
    environment into ``SOCIALACCOUNT_PROVIDERS["orcid"]["BASE_DOMAIN"]``, and
    allauth's ``OrcidOAuth2Adapter`` concatenates it into its endpoints at import
    time::

        authorize_url    = f"https://{base_domain}/oauth/authorize"
        access_token_url = f"https://pub.{base_domain}/oauth/token"

    So ``ORCID_BASE_DOMAIN=attacker.invalid`` yielded
    ``https://pub.attacker.invalid/oauth/token`` and the token exchange POSTED
    THE CLIENT SECRET to a host this deployment does not own. Nothing errored:
    the button worked and the page looked identical.

    The smallest possible normalisation is applied first (whitespace, scheme,
    case, trailing slash), so ``https://ORCID.ORG/`` is accepted rather than
    surprising an operator with a refusal. Everything else raises AT SETTINGS
    LOAD: a configuration that cannot name a safe endpoint must not boot with an
    unsafe one. An absent or empty value takes the sandbox default (which is the
    deployment's only non-production host, and is itself allowlisted).
    """
    candidate = (value or "").strip()
    if not candidate:
        candidate = default
    normalized = candidate.lower()
    if "://" in normalized:
        # Tolerate a URL an operator pasted from the developer console.
        normalized = normalized.split("://", 1)[1]
    normalized = normalized.split("/", 1)[0].strip()
    if normalized not in ORCID_ALLOWED_BASE_DOMAINS:
        raise ValueError(
            f"ORCID_BASE_DOMAIN={value!r} is not one of "
            f"{list(ORCID_ALLOWED_BASE_DOMAINS)}. Refusing to build OAuth "
            "endpoints from it: the value decides which host receives the ORCID "
            "client secret at the token exchange, so it is an allowlist rather "
            "than a free-form host."
        )
    return normalized


#: Human labels for the provider's app, as the operator consoles name them.
#: A provider absent from this map is still supported: its id is titled.
PROVIDER_APP_NAMES = {"google": "Google", "orcid": "ORCID"}

#: Values that mean "this was never filled in". Matched case-insensitively as a
#: SUBSTRING, so ``your-client-id``, ``<client-id>`` and ``TODO`` are all caught
#: by the shape rather than by an exhaustive list of the exact strings an
#: operator might have left behind.
STUB_MARKERS = (
    "changeme",
    "change-me",
    "placeholder",
    "your-",
    "todo",
    "fixme",
    "xxx",
    "example",
    "<",
    ">",
)


def _usable(value) -> bool:
    """Whether this half of a credential pair is a credential at all."""
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if not candidate:
        return False
    lowered = candidate.lower()
    return not any(marker in lowered for marker in STUB_MARKERS)


def credential_is_complete(client_id, secret) -> bool:
    """Whether BOTH halves are present and look like real credentials.

    This single predicate is what makes the button and the login agree: a
    provider whose pair is not complete contributes no app, so no page can offer
    it and no callback can reach it.
    """
    return _usable(client_id) and _usable(secret)


def with_credential_apps(
    providers: Mapping[str, Mapping],
    credentials: Mapping[str, Iterable],
) -> dict:
    """A copy of ``providers`` with ``APP`` filled in where the pair is complete.

    * The input mapping is NOT mutated: it is the deployment's shared provider
      configuration, and a settings-time helper that edited it would corrupt
      every later reader.
    * Only providers the configuration already DECLARES are considered. A
      credential for a provider that has no scopes, no base domain and no other
      configuration would produce an app nobody described; the credential is
      ignored rather than turned into one implicitly.
    * Each part of ``credentials`` is ``(client_id, secret)``; a provider
      missing from it keeps its configuration untouched.
    """
    configured = {provider: dict(config) for provider, config in providers.items()}

    for provider, pair in credentials.items():
        if provider not in configured:
            continue
        client_id, secret = pair
        if not credential_is_complete(client_id, secret):
            continue
        configured[provider]["APP"] = {
            "name": PROVIDER_APP_NAMES.get(provider, provider.title()),
            "client_id": client_id.strip(),
            "secret": secret.strip(),
        }

    return configured


# EOF
