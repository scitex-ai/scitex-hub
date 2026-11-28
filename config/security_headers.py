# -*- coding: utf-8 -*-
# File: config/security_headers.py
"""Origin-side browser security: HTTPS redirect, CSP, Permissions-Policy,
and access to the Django admin.

Policy values live in config/settings/settings_security_headers.py.
"""

from __future__ import annotations

import ipaddress
import json
import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.http import Http404, HttpResponsePermanentRedirect

logger = logging.getLogger("scitex_hub.security")


# ── HTTP -> HTTPS ───────────────────────────────────────────────────────


def edge_scheme(request) -> str | None:
    """The scheme the visitor used at the edge, or None when unknown.

    CF-Visitor (set by Cloudflare, JSON ``{"scheme": "http"}``) wins over
    X-Forwarded-Proto because the prod nginx overwrites the latter with
    "https" for every request it proxies.
    """
    visitor = request.META.get("HTTP_CF_VISITOR", "")
    if visitor:
        try:
            scheme = json.loads(visitor).get("scheme")
        except (ValueError, AttributeError):
            scheme = None
        if scheme in ("http", "https"):
            return scheme
    proto = request.META.get("HTTP_X_FORWARDED_PROTO", "").split(",")[0].strip()
    if proto in ("http", "https"):
        return proto.lower()
    return None


class EdgeHttpsRedirectMiddleware:
    """Redirect a request the visitor made over plain HTTP to https.

    Only an explicit "http" from the edge triggers it; a request carrying no
    edge header is an internal caller and passes untouched. GET/HEAD get a
    301, other methods a 308 so the body is not silently dropped.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "EDGE_HTTPS_REDIRECT", False) and (
            edge_scheme(request) == "http"
        ):
            # get_host() validates against ALLOWED_HOSTS, so the target can
            # only ever be one of our own hosts.
            target = f"https://{request.get_host()}{request.get_full_path()}"
            response = HttpResponsePermanentRedirect(target)
            if request.method not in ("GET", "HEAD"):
                response.status_code = 308
            return response
        return self.get_response(request)


# ── CSP + Permissions-Policy ────────────────────────────────────────────


def build_csp(directives: dict[str, list[str]], report_path: str) -> str:
    parts = [
        f"{name} {' '.join(sources)}".strip() for name, sources in directives.items()
    ]
    parts.append(f"report-uri {report_path}")
    parts.append("report-to csp-endpoint")
    return "; ".join(parts)


def with_analytics_origin(
    directives: dict[str, list[str]], script_url: str
) -> dict[str, list[str]]:
    """Allow the analytics script host for script-src and connect-src (its
    collect endpoint lives on the same host)."""
    parsed = urlsplit(script_url or "")
    if not (parsed.scheme and parsed.netloc):
        return directives
    origin = f"{parsed.scheme}://{parsed.netloc}"
    out = {name: list(sources) for name, sources in directives.items()}
    for name in ("script-src", "connect-src"):
        if name in out and origin not in out[name]:
            out[name].append(origin)
    return out


def build_permissions_policy(policy: dict[str, list[str]]) -> str:
    return ", ".join(
        f"{feature}=({' '.join(allow)})" for feature, allow in policy.items()
    )


class SecurityHeadersMiddleware:
    """Add CSP (report-only by default) and Permissions-Policy.

    A response that already carries its own Content-Security-Policy (e.g.
    the sandboxed artifact views) keeps it: the site-wide policy is only
    added to responses that declare none of their own.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        mode = getattr(settings, "CSP_MODE", "report-only")
        if mode not in ("report-only", "enforce", "off"):
            raise ValueError(
                f"CSP_MODE must be report-only, enforce or off, not {mode!r}"
            )
        self.csp_header = {
            "report-only": "Content-Security-Policy-Report-Only",
            "enforce": "Content-Security-Policy",
            "off": None,
        }[mode]
        self.csp_value = build_csp(
            with_analytics_origin(
                settings.CSP_DIRECTIVES, getattr(settings, "UMAMI_SCRIPT_URL", "")
            ),
            settings.CSP_REPORT_PATH,
        )
        self.reporting_endpoints = f'csp-endpoint="{settings.CSP_REPORT_PATH}"'
        self.permissions_policy = build_permissions_policy(settings.PERMISSIONS_POLICY)

    def __call__(self, request):
        response = self.get_response(request)
        if self.csp_header and not (
            response.has_header("Content-Security-Policy")
            or response.has_header("Content-Security-Policy-Report-Only")
        ):
            response[self.csp_header] = self.csp_value
            response.setdefault("Reporting-Endpoints", self.reporting_endpoints)
        response.setdefault("Permissions-Policy", self.permissions_policy)
        return response


# ── Django admin ────────────────────────────────────────────────────────


def client_ip(request) -> str:
    """The visitor's address: CF-Connecting-IP, then X-Real-IP (nginx), then
    the socket peer. Both headers are set by our own edge, not the client."""
    for key in ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP", "REMOTE_ADDR"):
        value = request.META.get(key, "").strip()
        if value:
            return value
    return ""


def ip_in_networks(ip: str, networks: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in ipaddress.ip_network(cidr, strict=False) for cidr in networks)


class AdminAccessMiddleware:
    """404 for every admin URL unless the user is active staff (and, when
    ADMIN_ALLOWED_NETWORKS is set, the client is inside one of them).

    A 404 rather than the admin login form: anonymous visitors cannot tell
    the admin exists and get no password form to try. Must run after the
    authentication middlewares so request.user is final.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefix = "/" + settings.ADMIN_URL_PATH
        self.networks = list(getattr(settings, "ADMIN_ALLOWED_NETWORKS", []))
        for cidr in self.networks:
            ipaddress.ip_network(cidr, strict=False)  # fail loud at startup

    def __call__(self, request):
        if request.path.startswith(self.prefix):
            user = getattr(request, "user", None)
            allowed = bool(
                user is not None
                and user.is_authenticated
                and user.is_active
                and user.is_staff
            )
            if allowed and self.networks:
                allowed = ip_in_networks(client_ip(request), self.networks)
            if not allowed:
                raise Http404()
        return self.get_response(request)
