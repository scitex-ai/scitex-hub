# -*- coding: utf-8 -*-
# File: config/settings/settings_security_headers.py
"""Browser-facing security policy shared by every environment.

Read by :mod:`config.security_headers` (middleware) and
:mod:`config.security_views` (CSP report sink, security.txt, sitemap).

Everything here is a plain value so an environment module (or a test) can
override it; nothing reads os.environ at request time.
"""

from __future__ import annotations

import datetime as _dt

from config._env import getenv_with_legacy_alias as _getenv_alias

# ── HTTP -> HTTPS at the origin ─────────────────────────────────────────
# Cloudflare terminates TLS and reaches the origin through the tunnel over
# plain HTTP, so the visitor's scheme is only known from the edge headers
# (CF-Visitor / X-Forwarded-Proto). EdgeHttpsRedirectMiddleware answers a
# request whose edge scheme is explicitly "http" with a redirect to https.
# A request with no edge header (container-to-container, health checks,
# webhooks delivered to http://django:8000) is left alone, which is why this
# is not Django's SECURE_SSL_REDIRECT: that one redirects every request that
# is not *proven* https and would break those internal callers.
EDGE_HTTPS_REDIRECT = (
    _getenv_alias("SCITEX_HUB_EDGE_HTTPS_REDIRECT", "true").lower() == "true"
)

# ── Content-Security-Policy ─────────────────────────────────────────────
# "report-only" (default): Content-Security-Policy-Report-Only, nothing is
# blocked, violations are POSTed to CSP_REPORT_PATH and logged.
# "enforce": Content-Security-Policy (only after a clean observation window).
# "off": no header.
CSP_MODE = _getenv_alias("SCITEX_HUB_CSP_MODE", "report-only").strip().lower()
CSP_REPORT_PATH = "/api/csp-report/"

# Sources inventoried from the templates, static TS and mounted leaf apps
# (2026-11-28). 'unsafe-inline' / 'unsafe-eval' are present because the
# templates carry ~130 inline <script> blocks and ~350 on* handlers, and
# pdf.js / xterm are loaded through new Function(); removing them needs
# nonces and a loader change first (see the rollout plan). The Umami origin
# is added from UMAMI_SCRIPT_URL by the middleware, so it follows the
# deployment's analytics host instead of being hard-coded here.
CSP_DIRECTIVES: dict[str, list[str]] = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'",
        "'unsafe-inline'",
        "'unsafe-eval'",
        "'wasm-unsafe-eval'",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "https://cdn.plot.ly",
        "https://static.cloudflareinsights.com",
    ],
    "style-src": [
        "'self'",
        "'unsafe-inline'",
        "https://fonts.googleapis.com",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
    ],
    "font-src": [
        "'self'",
        "data:",
        "https://fonts.gstatic.com",
        "https://cdnjs.cloudflare.com",
        "https://cdn.jsdelivr.net",
    ],
    # Rendered READMEs / markdown may embed any https image.
    "img-src": ["'self'", "data:", "blob:", "https:"],
    "media-src": ["'self'", "data:", "blob:"],
    "connect-src": [
        "'self'",
        "wss:",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "https://cloudflareinsights.com",
    ],
    "frame-src": ["'self'", "blob:", "https://*.readthedocs.io"],
    "worker-src": ["'self'", "blob:"],
    "manifest-src": ["'self'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    # Chrome applies form-action to the redirect after a POST, so the OAuth
    # providers and Stripe's hosted pages are listed.
    "form-action": [
        "'self'",
        "https://accounts.google.com",
        "https://orcid.org",
        "https://sandbox.orcid.org",
        "https://github.com",
        "https://checkout.stripe.com",
        "https://billing.stripe.com",
    ],
    "frame-ancestors": ["'self'"],
}

# ── Permissions-Policy ──────────────────────────────────────────────────
# Camera and microphone are used by the AI chat (recorder, webcam capture),
# fullscreen by zen mode. Stripe is a redirect (no Stripe.js), so payment is
# off with everything else.
PERMISSIONS_POLICY: dict[str, list[str]] = {
    "accelerometer": [],
    "autoplay": ["self"],
    "bluetooth": [],
    "browsing-topics": [],
    "camera": ["self"],
    "display-capture": [],
    "fullscreen": ["self"],
    "geolocation": [],
    "gyroscope": [],
    "hid": [],
    "magnetometer": [],
    "microphone": ["self"],
    "midi": [],
    "payment": [],
    "serial": [],
    "usb": [],
}

# ── Django admin ────────────────────────────────────────────────────────
# The admin is mounted at ADMIN_URL_PATH (configurable, so a deployment can
# move it off the well-known default) and AdminAccessMiddleware answers 404
# -- not a redirect to a login form -- to anyone who is not an active staff
# user, and, when ADMIN_ALLOWED_NETWORKS is set, to any client outside those
# networks. Staff sign in through the normal site sign-in, then open it.
ADMIN_URL_PATH = (
    _getenv_alias("SCITEX_HUB_ADMIN_PATH", "admin/").strip().strip("/") + "/"
)
ADMIN_ALLOWED_NETWORKS = [
    cidr.strip()
    for cidr in _getenv_alias("SCITEX_HUB_ADMIN_ALLOWED_NETWORKS", "").split(",")
    if cidr.strip()
]

# ── /.well-known/security.txt (RFC 9116) ────────────────────────────────
# Expires must be renewed before it lapses: tests/config/test_security_txt.py
# fails once it is within 30 days, so the renewal is a red CI leg rather than
# a silent expiry.
SECURITY_TXT_CONTACT = "mailto:security@scitex.ai"
SECURITY_TXT_EXPIRES = _dt.datetime(2027, 11, 27, tzinfo=_dt.timezone.utc)
SECURITY_TXT_PREFERRED_LANGUAGES = "en, ja"
SECURITY_TXT_CANONICAL = "https://scitex.ai/.well-known/security.txt"

# ── /sitemap.xml ────────────────────────────────────────────────────────
# Public, indexable pages only (URL names). robots.txt points here.
SITEMAP_URL_NAMES = [
    "public_app:index",
    "public_app:about",
    "public_app:pricing",
    "public_app:services",
    "public_app:security",
    "public_app:open_source",
    "public_app:publications",
    "public_app:demos",
    "public_app:funding",
    "public_app:contact",
    "public_app:api_docs",
    "public_app:releases",
    "public_app:privacy",
    "public_app:terms",
    "public_app:cookies",
    "public_app:tokushoho",
    "public_app:tokushoho_en",
]
