#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production-derived settings for the ACCEPTANCE screenshot/mobile capture.

CARD: hub-screenshots-are-taken-with-debug-1-not-production-20260816.
Leader HOLD 2026-09-11: a capture that still runs the DEV configuration is not a
picture of production, and the claim must not outrun the evidence.

WHY THIS MODULE EXISTS, stated as the defect it removes. Until now the capture
ran under ``settings_dev``. Flipping its ``DEBUG`` to 0 (the previous fix) made
the job green while leaving the artifact a photograph of a configuration that
exists NOWHERE:

  - ``STORAGES["staticfiles"]`` = plain ``StaticFilesStorage`` -> ``collectstatic``
    copies files UNCHANGED, ``{% static %}`` emits UNHASHED urls, and the
    content-hash/manifest pipeline production actually serves is never exercised.
    Measured: ``settings_dev.py`` inherits the plain backend from
    ``settings_static.py``; ``settings_prod.py:356`` and ``settings_staging.py:283``
    both opt in with ``STORAGES = hashed_storages(STORAGES)``.
  - ``WHITENOISE_AUTOREFRESH = True`` + ``WHITENOISE_MAX_AGE = 0`` (settings_dev
    :136/:138) -> every request re-stats the filesystem and nothing is cacheable.
  - ``DevNoCacheMiddleware`` + ``django_browser_reload`` (:242-243) -> dev-only
    middleware in the render path.
  - so a green run could not tell production static behaviour from dev's, which
    is exactly the property the artifact is supposed to prove.

WHY IT IS NOT ``settings_prod`` OR ``settings_staging`` DIRECTLY. Both are
unusable in this container and in CI, measured:
  - ``settings_staging`` RAISES ImproperlyConfigured at import when
    ``SCITEX_HUB_POSTGRES_PASSWORD`` is unset (settings_staging.py:110-122,
    deliberately: "there is no default"), and it points at ``pgbouncer:6432``.
  - ``settings_prod`` requires prod hosts/secrets and defaults
    ``SESSION_COOKIE_SECURE=True`` (:87) and ``SECURE_SSL_REDIRECT`` — cookies
    would not be set over the runner's plain http, and every request would 301.
So the accepted design is: DERIVE from the module whose datastore/broker/Gitea
wiring CI already provides (``settings_dev``), then OVERLAY the production
static + DEBUG posture. That keeps the working CI plumbing and replaces the four
dev-only behaviours above with the ones production actually runs.

WHAT THIS MODULE DELIBERATELY DOES NOT CHANGE, and why each is safe to leave:
  - ``SCITEX_ENV`` stays ``development`` for now. It drives the tab-title marker
    and favicon colour, neither of which appears in a captured page image (the
    capture photographs page content, not browser chrome). Changing it would
    touch branding surfaces unrelated to this card; recorded as a known gap
    rather than silently altered.
  - ``ALLOWED_HOSTS`` stays dev's. It is a HOST-HEADER gate, not a render path;
    the runner serves plain http on 127.0.0.1.
  - The database/broker/Gitea wiring stays exactly as the workflow already sets
    it, so this module cannot be the reason a capture step fails to boot.
"""

from __future__ import annotations

# Derive the CI plumbing (DB *_DEV, redis, Gitea opt-out, VITE_USE_BUILD).
from .settings_dev import *  # noqa: F401,F403
from .settings_static import hashed_storages

# ---------------------------------------------------------------------------
# 1. DEBUG OFF, EXPLICITLY.
# Not env-defaulted: a capture that photographs production must not be one
# stray env var away from photographing the dev error pages again.
# ---------------------------------------------------------------------------
DEBUG = False

# ---------------------------------------------------------------------------
# 2. THE PRODUCTION STATIC PIPELINE (the property the HOLD says is untested).
# The same one-line opt-in prod and staging use. It is STRICT on purpose: a
# dangling {% static %} / CSS url() raises instead of serving a silent 404, so
# collectstatic now hashes and the manifest is exercised by every page render.
# ---------------------------------------------------------------------------
STORAGES = hashed_storages(STORAGES)  # noqa: F405  (star-imported above, as prod/staging do)
# ---------------------------------------------------------------------------
# 3. No dev static/caching behaviour in the artifact.
# AUTOREFRESH re-scans the filesystem on every request and is documented for
# DEVELOPMENT; production serves immutable content-hashed files, which is what
# makes a long max-age correct rather than harmful (settings_static.py's own
# rationale for hashing).
# ---------------------------------------------------------------------------
WHITENOISE_AUTOREFRESH = False
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days, matching the hashed-URL TTL

# ---------------------------------------------------------------------------
# 4. Drop the dev-only middleware, so the render path is not dev-shaped.
# Filtered by dotted path rather than rebuilt, so any middleware this module
# adds later cannot silently drop one.
# ---------------------------------------------------------------------------
_DEV_ONLY_MIDDLEWARE = frozenset(
    {
        "config.middleware.DevNoCacheMiddleware",
        "django_browser_reload.middleware.BrowserReloadMiddleware",
    }
)
MIDDLEWARE = [m for m in MIDDLEWARE if m not in _DEV_ONLY_MIDDLEWARE]  # noqa: F405

# EOF
