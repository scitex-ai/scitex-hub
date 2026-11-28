"""Encryption for secrets stored in database fields (API keys, OAuth tokens).

Field encryption has its OWN keys, separate from Django's ``SECRET_KEY``, so
that rotating ``SECRET_KEY`` (which signs sessions, reset tokens and cookies)
never makes stored ciphertext unreadable.

``settings.FIELD_ENCRYPTION_KEYS`` comes from ``SCITEX_HUB_FIELD_ENCRYPTION_KEYS``:
a comma-separated list of Fernet keys, NEWEST FIRST. New values are encrypted
with the first key. Every key can decrypt, which is how a field key is rotated:
prepend a new key, run ``manage.py reencrypt_encrypted_fields``, then drop the
old key.

Before this module existed, values were encrypted with a key derived as
``sha256(SECRET_KEY)``. That legacy derivation, for ``SECRET_KEY`` and every
``SECRET_KEY_FALLBACKS`` entry, is accepted for DECRYPTION only once a field key
is configured. While no field key is configured the legacy key also encrypts,
so a deployment that has not provisioned a field key keeps working exactly as
before; ``reencrypt_encrypted_fields`` refuses to run in that state.

Generate a key with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Fernet keys are urlsafe base64 and never contain ``$``, ``,`` or quotes, so they
are safe in a compose env file.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ENV_NAME = "SCITEX_HUB_FIELD_ENCRYPTION_KEYS"

# Key states reported by ``key_state``.
CURRENT = "current"  # readable with the newest configured field key
STALE = "stale"  # readable, but only with an older or legacy key
UNREADABLE = "unreadable"  # no accepted key decrypts it


def parse_keys(raw: str | None) -> list[str]:
    """Split the env value into keys, newest first, dropping blanks."""
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def configured_keys() -> list[Fernet]:
    """The dedicated field keys, newest first. Never echoes a key in errors."""
    keys = []
    for index, key in enumerate(getattr(settings, "FIELD_ENCRYPTION_KEYS", ()) or ()):
        try:
            keys.append(Fernet(key))
        except (TypeError, ValueError):
            raise ImproperlyConfigured(
                f"{ENV_NAME} entry {index} is not a valid Fernet key"
            ) from None
    return keys


def _legacy_fernet(secret: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def legacy_keys() -> list[Fernet]:
    """Keys derived the pre-field-key way from SECRET_KEY and its fallbacks."""
    secrets = [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", ())]
    return [_legacy_fernet(secret) for secret in secrets if secret]


def _encrypting_key() -> Fernet:
    keys = configured_keys()
    return keys[0] if keys else legacy_keys()[0]


def _all_keys() -> MultiFernet:
    return MultiFernet([*configured_keys(), *legacy_keys()])


def encrypt(value: str | None) -> str:
    """Encrypt ``value`` with the newest key. Empty stays empty."""
    if not value:
        return ""
    return _encrypting_key().encrypt(value.encode()).decode()


def decrypt(token: str | None) -> str:
    """Decrypt with any accepted key. Raises ``InvalidToken`` if none fits."""
    if not token:
        return ""
    return _all_keys().decrypt(token.encode()).decode()


def key_state(token: str) -> str:
    """Classify a non-empty token as CURRENT, STALE or UNREADABLE."""
    keys = configured_keys()
    if keys:
        try:
            keys[0].decrypt(token.encode())
            return CURRENT
        except InvalidToken:
            pass
    try:
        _all_keys().decrypt(token.encode())
    except InvalidToken:
        return UNREADABLE
    return STALE if keys else CURRENT


def reencrypt(token: str) -> str:
    """Decrypt with any accepted key and encrypt again with the newest key."""
    return encrypt(decrypt(token))
