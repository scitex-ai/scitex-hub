"""Shared scope-meta injection for hub leaf-app bridges.

The scitex-app manifest is the single source of truth for a leaf app's
release scope (``user`` vs ``project``, d8528de / #185). scitex-app's host
view layer (``scitex_editor_page`` -> ``_inject_scope_meta``) stamps
``<meta name="stx-app-scope" content="project">`` into the served HTML ONLY
for leaves embedded through that factory (e.g. Scholar's /apps/scholar/v2/).

The Hub's Writer + FigRecipe bridges do NOT go through that factory — they
call the raw leaf ``editor_page`` via WorkingDirScopedView (a pure
pass-through), so their pages carry no scope marker, and the leaf's
``mountProjectSelectorByScope`` (which reads the marker) has nothing to mount
against. This helper applies the SAME injection contract to a hub-served leaf
response, reusing scitex-app's own emitter (never re-implementing it) and the
leaf manifest scope (never duplicating leaf logic).

Scope semantics (from scitex-app ``_app_scope``): project-scoped -> emit the
marker; user-scoped / absent -> emit NOTHING (page byte-identical). This keeps
the "global header never forces a selector" ruling intact — the marker only
tells the per-app surface it MAY offer selection.

Two correctness properties this module is responsible for (both were
independent-review findings on the first cut):
  * IDEMPOTENT — if a leaf later stamps ``stx-app-scope`` itself, the hub
    wrapper must NOT add a second marker (scitex-app's ``_inject_scope_meta``
    always inserts, so we guard on the existing marker before calling it).
  * NO PER-REQUEST FILE I/O — the resolved scope is cached at process level,
    invalidated deterministically on the installed leaf package identity (the
    spec origin path), so we never parse the manifest on every HTML request.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from django.http import HttpResponse

# scitex-app is an editable source mount; the contract module may be absent if
# the mount predates d8528de. Guard the import so a stale mount degrades to
# "no marker" (the safe direction) rather than 500'ing every leaf page.
try:
    from scitex_app._app_scope import _inject_scope_meta
except Exception:  # noqa: BLE001 - scitex-app not advanced to the contract yet
    _inject_scope_meta = None

#: registry module name -> the importable scitex leaf package whose
#: ``_django/manifest.json`` declares the SDK ``scope`` (the SSoT). The hub's
#: OWN wrapper manifests (apps/workspace/<app>/manifest.json, what the registry
#: reads) do NOT carry ``scope`` — it lives in the leaf package. The package
#: name follows the scitex_app manifest ``pip_package`` convention
#: (hyphenated -> underscored).
_LEAF_MANIFEST_PKG: Dict[str, str] = {
    "figrecipe": "figrecipe._django",
    "writer": "scitex_writer._django",
    "scholar": "scitex_scholar._django",
}

# The scitex-app marker shape (scope_meta_tag in _app_scope.py):
#   <meta name="stx-app-scope" content="project">
# We only need to detect that a stx-app-scope marker is ALREADY present (any
# content), so the hub does not duplicate it if a leaf emits one itself.
_EXISTING_SCOPE_MARKER = re.compile(
    r"""<meta\b[^>]*\bname=["']stx-app-scope["']""", re.IGNORECASE
)

# Process-level cache: app_name -> (installed-package-identity, resolved_scope).
# The identity is the spec origin path of the leaf's _django package — a stable
# marker of "which install is present" (editable mount path or wheel site).
# When that identity changes (a different checkout / version is live), the entry
# is recomputed. This is deterministic invalidation, not a TTL.
_scope_cache: Dict[str, tuple] = {}


def _leaf_spec_identity(pkg: str) -> Optional[str]:
    """The installed-package identity for ``pkg`` (its spec origin path).

    ``None`` when the leaf is not importable (no marker, safely).
    """
    import importlib.util

    try:
        spec = importlib.util.find_spec(pkg)
    except Exception:  # noqa: BLE001 - leaf not importable
        return None
    if spec is None:
        return None
    return spec.origin or (
        str(sorted(spec.submodule_search_locations)[0])
        if spec.submodule_search_locations
        else None
    )


def _scope_for(app_name: str) -> Optional[str]:
    """The leaf manifest ``scope`` for ``app_name``, cached by install identity.

    Reads the leaf package's ``_django/manifest.json`` ONCE per installed
    package identity (process-level cache). Re-reads only when the identity
    changes (different checkout/version live) — no per-request file I/O.
    Returns None for an unknown app, an unimportable leaf, a manifest without
    the key, or an unreadable manifest (all -> no marker, the safe default).
    """
    pkg = _LEAF_MANIFEST_PKG.get(app_name)
    if pkg is None:
        return None
    identity = _leaf_spec_identity(pkg)
    if identity is None:
        return None
    cached = _scope_cache.get(app_name)
    if cached is not None and cached[0] == identity:
        return cached[1]
    scope = _read_scope_from_identity(identity, pkg)
    _scope_cache[app_name] = (identity, scope)
    return scope


def _read_scope_from_identity(identity: str, pkg: str) -> Optional[str]:
    import json
    from pathlib import Path

    # identity is the _django package's spec origin (e.g. .../figrecipe/_django/__init__.py)
    d = Path(identity)
    if d.name in ("__init__.py", "module"):
        d = d.parent
    manifest = d / "manifest.json"
    try:
        data = json.loads(manifest.read_text())
    except Exception:  # noqa: BLE001 - missing/unreadable manifest -> no marker
        return None
    scope = data.get("scope")
    return scope if isinstance(scope, str) and scope else None


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
