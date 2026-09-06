# -*- coding: utf-8 -*-
# File: config/settings/settings_secret_key.py
"""Django signing key and the retired keys that must still verify.

WHY THIS MODULE EXISTS
----------------------
Rotating ``SECRET_KEY`` on its own invalidates every signature made with the
old key: every session cookie, every password-reset link, every signed URL.
In practice that means "rotate the key" reads as "log every user out and break
the reset mails currently in inboxes" — a visible, immediate cost, where
LEAVING an exposed key in place has no visible cost at all.

That asymmetry is the whole problem. It is why a key known to be compromised
can sit un-rotated for days: the safe action is the one that hurts.

``SECRET_KEY_FALLBACKS`` (Django >= 4.1) removes the cost. Django signs only
with ``SECRET_KEY``, but VERIFIES against ``SECRET_KEY`` first and then each
fallback in turn. Park the retired key in the fallback list for one rotation
window and existing signatures keep validating while every new one uses the
new key. Nobody is logged out.

OPERATIONAL CONTRACT — and the third step is the one that gets skipped
---------------------------------------------------------------------
1. Set the NEW key as ``SCITEX_HUB_DJANGO_SECRET_KEY``.
2. Put the OLD key in ``SCITEX_HUB_DJANGO_SECRET_KEY_FALLBACKS``. Restart.
   Leave it for at least one ``SESSION_COOKIE_AGE`` so live sessions re-sign.
3. **REMOVE the old key from the fallback list.**

Step 3 is not tidying. A fallback left in place indefinitely means the exposed
key still validates sessions, which is most of the risk the rotation existed to
escape — a rotation that never completes is a rotation that did not happen.
"""

from config._env import getenv_with_legacy_alias as _getenv_alias

__all__ = [
    "SECRET_KEY_ENV",
    "SECRET_KEY_FALLBACKS_ENV",
    "parse_secret_key_fallbacks",
    "resolve_secret_key",
    "resolve_secret_key_fallbacks",
]

SECRET_KEY_ENV = "SCITEX_HUB_DJANGO_SECRET_KEY"
SECRET_KEY_FALLBACKS_ENV = "SCITEX_HUB_DJANGO_SECRET_KEY_FALLBACKS"


def parse_secret_key_fallbacks(raw):
    """Split a comma-separated key list into a list of keys.

    Blank entries and surrounding whitespace are dropped, so a trailing comma
    or a value pasted with spaces does not become an empty "key" that Django
    would then try to verify against.

    Always returns a LIST, never ``None``: Django iterates
    ``SECRET_KEY_FALLBACKS`` directly, and ``None`` would fail at signature
    check time — deep inside a request, on a code path only exercised once a
    cookie signed with a retired key shows up.
    """
    if not raw:
        return []
    return [key.strip() for key in raw.split(",") if key.strip()]


def resolve_secret_key():
    """The active signing key, or an empty value for the caller to reject.

    Deliberately does NOT raise. The environment modules differ in how they
    refuse a missing key (shared raises ``ValueError``; prod and staging use
    ``require_env_with_legacy_alias``), and moving that decision here would
    silently change which error a misconfigured deploy produces.
    """
    return _getenv_alias(SECRET_KEY_ENV)


def resolve_secret_key_fallbacks():
    """Retired keys that must still VERIFY while a rotation rolls out.

    Optional, and deliberately NOT fail-loud — unlike the signing key. The
    normal steady state is an empty list: "no rotation in flight" is the
    common case, not a misconfiguration, and refusing to boot without it
    would make the safe path harder than the unsafe one all over again.
    """
    return parse_secret_key_fallbacks(_getenv_alias(SECRET_KEY_FALLBACKS_ENV, ""))


# EOF
