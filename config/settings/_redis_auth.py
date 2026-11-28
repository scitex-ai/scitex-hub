#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/_redis_auth.py
"""Redis password for every hub client (cache, sessions, channels, Celery).

The deployed Redis requires a password (``requirepass``). The password lives
in the environment's env file as ``SCITEX_HUB_REDIS_PASSWORD``, like every
other secret, and the redis URLs stay password-free
(``SCITEX_HUB_REDIS_URL``, ``SCITEX_HUB_CELERY_BROKER_URL``). This module
joins the two, so existing env files keep working unchanged and the password
is set in exactly one place.

A URL that already carries a password is left alone: an operator who wrote
one explicitly meant it.
"""

from __future__ import annotations

import os
from urllib.parse import quote, urlsplit, urlunsplit

PASSWORD_ENV = "SCITEX_HUB_REDIS_PASSWORD"

_REDIS_SCHEMES = ("redis", "rediss")


def redis_password(environ=None):
    """The configured password, or ``None`` when Redis runs without one."""
    env = os.environ if environ is None else environ
    value = env.get(PASSWORD_ENV, "")
    return value or None


def with_redis_password(url, password):
    """Return ``url`` with ``password`` added, when there is one to add.

    ``redis://redis:6379/1`` + ``pw`` -> ``redis://:pw@redis:6379/1``. The
    password is percent-encoded, so any character is safe. Non-redis URLs
    (``memory://`` in tests) and URLs with a password are returned unchanged.
    """
    if not password:
        return url
    parts = urlsplit(url)
    if parts.scheme not in _REDIS_SCHEMES or parts.password:
        return url
    userinfo, _, hostport = parts.netloc.rpartition("@")
    user = quote(userinfo, safe="") if userinfo else ""
    netloc = f"{user}:{quote(password, safe='')}@{hostport}"
    return urlunsplit(parts._replace(netloc=netloc))


def authenticated_redis_url(url, environ=None):
    """``url`` with the configured password (see :func:`with_redis_password`)."""
    return with_redis_password(url, redis_password(environ))


# EOF
