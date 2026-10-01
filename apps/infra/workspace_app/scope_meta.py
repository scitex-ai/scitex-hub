"""Scope markers for installed SDK apps bridged through a legacy Hub route.

A ready SDK AppConfig owns its slug, scope validation and cached manifest.
The host consumes those generic properties; it names no leaf packages and
never independently opens their manifest files. This adapter remains until
legacy bridges are retired after leaf parity is reviewed.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from django.http import HttpResponse

# SDK GUI support is optional. An unavailable marker emitter leaves host
# responses unchanged; scope metadata never grants project or storage access.
try:
    from scitex_sdk.app._app_scope import _inject_scope_meta
except Exception:  # noqa: BLE001 - preserve the optional GUI import boundary
    _inject_scope_meta = None

# The SDK marker shape (scope_meta_tag in _app_scope.py):
#   <meta name="stx-app-scope" content="project">
# We only need to detect that a stx-app-scope marker is ALREADY present (any
# content), so the hub does not duplicate it if a leaf emits one itself.
_EXISTING_SCOPE_MARKER = re.compile(
    r"""<meta\b[^>]*\bname=["']stx-app-scope["']""", re.IGNORECASE
)

# Cache is tied to the ready configuration object, never to a package path.
_scope_cache: Dict[str, tuple] = {}
logger = logging.getLogger(__name__)


def _scope_for(app_name: str) -> Optional[str]:
    """Resolve only an installed SDK AppConfig with the requested slug.

    SDK owns scope validation and manifest caching. A new ready registry
    object invalidates this adapter's cache. An ambiguous slug fails loudly
    rather than choosing whichever application happened to register first.
    """
    from django.apps import apps
    from django.core.exceptions import ImproperlyConfigured
    from scitex_sdk.app.embed import ScitexAppConfig

    if ScitexAppConfig is None:
        return None
    matches = []
    for config in apps.get_app_configs():
        if not isinstance(config, ScitexAppConfig):
            continue
        try:
            slug = config.app_slug
        except (OSError, ValueError):
            # SDK owns reading its metadata. An unreadable optional app must
            # not block other owners; its scope cannot be guessed from a name.
            logger.warning(
                "Unreadable SDK application metadata: %s", config.label, exc_info=True
            )
            continue
        if slug == app_name:
            matches.append(config)
    if len(matches) > 1:
        raise ImproperlyConfigured(
            f"Ambiguous installed SDK application slug: {app_name}"
        )
    if not matches:
        return None
    config = matches[0]
    cached = _scope_cache.get(app_name)
    if cached is not None and cached[0] is config:
        return cached[1]
    scope = config.app_scope
    _scope_cache[app_name] = (config, scope)
    return scope


def clear_scope_cache() -> None:
    """Drop the process-level scope cache. Test hook / manual invalidation."""
    _scope_cache.clear()


def inject_scope_meta(response: HttpResponse, app_name: str) -> HttpResponse:
    """Return ``response`` with the scope marker injected for HTML pages.

    Idempotent: if the page already carries a ``stx-app-scope`` marker (a leaf
    that stamps it itself), the response is returned unchanged so the hub never
    duplicates it. Non-HTML responses, and the user-scoped/absent/unknown-app
    cases, are returned unchanged (byte-identical) — only a project-scoped leaf
    page without a marker gains the marker.
    """
    if not isinstance(response, HttpResponse):
        return response
    content_type = response.get("Content-Type", "") or ""
    if "html" not in content_type.lower():
        return response
    if _inject_scope_meta is None:
        return response  # scitex-app mount predates the contract -> no marker
    html = response.content.decode("utf-8", "replace")
    # IDEMPOTENCY GUARD: a marker the leaf already emitted wins; do not add a second.
    if _EXISTING_SCOPE_MARKER.search(html):
        return response
    scope = _scope_for(app_name)
    if scope is None:
        return response
    new_html = _inject_scope_meta(html, scope)
    if new_html == html:
        return response
    response.content = new_html.encode("utf-8")
    return response
