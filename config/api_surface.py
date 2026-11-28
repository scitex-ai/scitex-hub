# -*- coding: utf-8 -*-
"""The Hub's public API surface, enumerated from the live URLconf (API contract v1).

Rule API-D001/D004 (scitex-sdk docs/design/api-contract-v1/01-rules.md): a
public API route exists only when scitex-sdk generated it from a declared
operation (``api_urlpatterns``, URL names ``api-*``). Every OTHER API-shaped
route the Hub itself serves is legacy and must be listed in
``config/api_legacy_allowlist.tsv``; the allowlist may only shrink.

``LEGACY_DEPRECATIONS`` feeds ``SCITEX_API_DEPRECATIONS`` (the SDK's
``LegacyApiDeprecationMiddleware``): the public legacy families that have a v1
successor carry ``Deprecation``/``Sunset``/``Link`` headers (API-H003).
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

ALLOWLIST = Path(__file__).with_name("api_legacy_allowlist.tsv")
CATEGORIES = ("public", "internal", "standard")
#: A route is API-shaped when one of its segments is ``api`` or it is MCP.
_API_SHAPED = re.compile(r"(^|/)(api|mcp)(/|$)")
#: Deprecation announced (operator decision 3, 2026-11-28).
DEPRECATED_AT = "2026-11-28"

#: Public legacy families with a v1 successor (migration table rows in the
#: comments). Sunset = beta launch + months; scholar search keeps 12 months.
LEGACY_DEPRECATIONS = [
    {"pattern": r"^/api/token/", "successor": "/oauth/token/"},  # 1-2
    {"pattern": r"^/api/me/$", "successor": "/api/v1/hub/users/me"},  # 3
    {"pattern": r"^/api/me/tokens?/", "successor": "/api/v1/hub/tokens"},  # 4-6
    {
        "pattern": r"^/api/project/(create|list)/$",
        "successor": "/api/v1/hub/projects",
    },  # 9-10
    {
        "pattern": r"^/api/project/check-name/$",
        "successor": "/api/v1/hub/projects/validate",
    },  # 14
    {
        "pattern": r"^/[^/]+/[^/]+/api/(file-tree|files)/",
        "successor": "/api/v1/hub/files",
    },  # 15-21
    {"pattern": r"^/api/workspace/", "successor": "/api/v1/hub/files"},  # 25-26
    {"pattern": r"^/apps/files/api/", "successor": "/api/v1/hub/files"},  # 27
    {"pattern": r"^/platform/api/", "successor": "/api/v1/hub/files"},  # 28-33
    {"pattern": r"^/api/events/", "successor": "/api/v1/hub/events"},  # 34-35
    {
        "pattern": r"^/api/apps/submit/$",
        "successor": "/api/v1/hub/app-submissions",
    },  # 36
    {"pattern": r"^/api/users/search/$", "successor": "/api/v1/hub/users"},  # 39
    {"pattern": r"^/api/mcp/tools/$", "successor": "/api/v1/mcp"},  # 47
    {"pattern": r"^/api/v1/tools/", "successor": "/api/v1/mcp"},  # 48-49
    {
        "pattern": r"^/api/v1/scholar/(search|info)/$",
        "successor": "/api/v1/scholar/papers",
        "sunset_months_after_beta": 12,
    },  # 57-58
    {
        "pattern": r"^/api/(stats|plot|docx2tex|read-image-metadata)/",
        "successor": "/api/v1/stats",
    },  # 59-69
]
for _entry in LEGACY_DEPRECATIONS:
    _entry.setdefault("deprecated_at", DEPRECATED_AT)
    _entry.setdefault("sunset_months_after_beta", 6)


def _route(pattern) -> str:
    text = str(pattern.pattern)
    return text[1:] if text.startswith("^") else text


def _owner(callback) -> str:
    """The module that really implements a view (through wrappers)."""
    target = inspect.unwrap(callback)
    target = getattr(target, "view_class", target)
    return getattr(target, "__module__", "") or ""


def _walk(patterns, prefix=""):
    from django.urls import URLPattern, URLResolver

    for item in patterns:
        route = prefix + _route(item)
        if isinstance(item, URLResolver):
            yield from _walk(item.url_patterns, route)
        elif isinstance(item, URLPattern):
            yield route.rstrip("$"), item


def api_routes(urlconf=None) -> dict:
    """``{route: owner_module}`` of every Hub-implemented API-shaped route.

    SDK-generated operations (URL names ``api-*``) are excluded: they are the
    contract. Routes implemented outside the Hub (leaf packages mounted under
    /apps/) are excluded too: each leaf migrates its own (migration table
    §8.3) and its routes depend on which leaves are installed.
    """
    from django.urls import get_resolver

    out = {}
    for route, item in _walk(get_resolver(urlconf).url_patterns):
        name = item.name or ""
        if name.startswith("api-") or not _API_SHAPED.search(route):
            continue
        if "/old-direct/" in route:
            # Dev-only parity references, never mounted in production and
            # deleted once parity closes (config/urls.py, CCT 2806).
            continue
        owner = _owner(item.callback)
        if not (owner.startswith("apps.") or owner.startswith("config.")):
            continue
        out[_family(route, owner)] = owner
    return out


#: Route families generated at startup from whatever is installed (one route
#: per MCP tool); listed as one entry so the allowlist does not depend on the
#: tool set of the environment.
GENERATED_FAMILIES = {
    "apps.infra.mcp_api": ("api/v1/tools/", "api/v1/tools/<generated>")
}


def _family(route: str, owner: str) -> str:
    for module, (prefix, family) in GENERATED_FAMILIES.items():
        if owner.startswith(module) and route.startswith(prefix) and route != prefix:
            return family
    return route


def read_allowlist(path: Path = ALLOWLIST) -> dict:
    """``{route: (category, migration_rows)}`` from the allowlist file."""
    entries = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3 or parts[1] not in CATEGORIES:
            raise ValueError(
                f"{path.name}:{number}: expected 'route<TAB>category<TAB>rows'"
            )
        entries[parts[0]] = (parts[1], parts[2])
    return entries
