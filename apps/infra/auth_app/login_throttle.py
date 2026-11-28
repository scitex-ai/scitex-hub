"""Failed sign-in throttling for every password check on the hub.

Every credential check goes through ``django.contrib.auth.authenticate``:
the sign-in form, allauth, the admin, ``/api/token/``, ``/api/me/token/``
and the SSH gateway. Failures are counted in the shared cache over a sliding
window in three buckets:

- per (account, client IP): stops guessing one account from one place,
- per account: stops one account being guessed from many places,
- per client IP: stops one place guessing many accounts.

While any bucket is full, :class:`LoginThrottleBackend` (first in
``AUTHENTICATION_BACKENDS``) refuses the attempt before a password is
checked, so callers see their ordinary "invalid credentials" answer. The
lockout ends when the oldest counted failure leaves the window. Refused
attempts are not counted again, so the lock lasts one window after the last
real failure. A successful sign-in clears its (account, IP) bucket.
"""

from __future__ import annotations

import hashlib
import time

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.dispatch import receiver

from apps.client_ip import UNKNOWN_IP, get_client_ip

#: Sliding window and per-bucket failure limits. Overridable per deployment
#: through ``settings.LOGIN_THROTTLE``.
DEFAULTS = {
    "window_seconds": 15 * 60,
    "pair_limit": 5,
    "account_limit": 50,
    "ip_limit": 30,
}

_REFUSED_ATTR = "_login_throttle_refused"


def _config() -> dict:
    return {**DEFAULTS, **getattr(settings, "LOGIN_THROTTLE", {})}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _account(identity: str | None) -> str | None:
    identity = (identity or "").strip().lower()
    return identity or None


def _client_ip(request) -> str | None:
    if request is None:
        return None
    ip = get_client_ip(request)
    return None if ip == UNKNOWN_IP else ip


def _key(kind: str, value: str) -> str:
    # ``namespace`` keeps independent counter sets apart (the test suite
    # gives every test its own).
    namespace = _config().get("namespace", "")
    return f"login-fail:{kind}:{_digest(namespace + '|' + value)}"


def _buckets(identity: str | None, ip: str | None) -> list[tuple[str, int]]:
    cfg = _config()
    account = _account(identity)
    buckets = []
    if account and ip:
        buckets.append((_key("pair", account + "|" + ip), cfg["pair_limit"]))
    if account:
        buckets.append((_key("account", account), cfg["account_limit"]))
    if ip:
        buckets.append((_key("ip", ip), cfg["ip_limit"]))
    return buckets


def _recent(key: str, now: float) -> list[float]:
    start = now - _config()["window_seconds"]
    return [ts for ts in cache.get(key, []) if ts > start]


def retry_after(identity: str | None, ip: str | None) -> int:
    """Seconds until no bucket is full; 0 when the attempt may proceed."""
    now = time.time()
    window = _config()["window_seconds"]
    wait = 0.0
    for key, limit in _buckets(identity, ip):
        recent = _recent(key, now)
        if len(recent) >= limit:
            # Unlocks once enough failures age out to fall below the limit.
            oldest_to_expire = sorted(recent)[len(recent) - limit]
            wait = max(wait, oldest_to_expire + window - now)
    return int(wait) + 1 if wait > 0 else 0


def is_locked(identity: str | None, ip: str | None) -> bool:
    return retry_after(identity, ip) > 0


def record_failure(identity: str | None, ip: str | None) -> None:
    now = time.time()
    timeout = _config()["window_seconds"] + 60
    for key, _limit in _buckets(identity, ip):
        recent = _recent(key, now)
        recent.append(now)
        cache.set(key, recent, timeout=timeout)


def clear_success(identity: str | None, ip: str | None) -> None:
    account = _account(identity)
    if account and ip:
        cache.delete(_key("pair", account + "|" + ip))


def identity_of(credentials: dict) -> str | None:
    """The account a credential set names (Django strips the password)."""
    for field in ("username", "email", "login"):
        value = credentials.get(field)
        if value:
            return str(value)
    return None


class LoginThrottleBackend(ModelBackend):
    """Refuses a credential check while its buckets are full; never signs anyone in.

    Subclasses ModelBackend only so sessions that name it as their backend
    (``Client.force_login`` picks the first backend) still resolve the user.
    Permissions are left to the real backends.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        identity = username or kwargs.get("email") or kwargs.get("login")
        if is_locked(identity, _client_ip(request)):
            if request is not None:
                setattr(request, _REFUSED_ATTR, True)
            raise PermissionDenied("Too many failed sign-in attempts.")
        return None

    def get_user_permissions(self, user_obj, obj=None):
        return set()

    def get_group_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        return set()

    def has_perm(self, user_obj, perm, obj=None):
        return False

    def has_module_perms(self, user_obj, app_label):
        return False


@receiver(user_login_failed, dispatch_uid="auth_app.login_throttle.failed")
def _count_failure(sender, credentials, request=None, **kwargs):
    if request is not None and getattr(request, _REFUSED_ATTR, False):
        return
    record_failure(identity_of(credentials), _client_ip(request))


@receiver(user_logged_in, dispatch_uid="auth_app.login_throttle.success")
def _clear_on_success(sender, request, user, **kwargs):
    ip = _client_ip(request)
    clear_success(user.get_username(), ip)
    if getattr(user, "email", ""):
        clear_success(user.email, ip)
